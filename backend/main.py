from dotenv import load_dotenv

load_dotenv()

import os
import time
import uuid

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from langgraph_pipeline import GraphState, compiled_graph
from logger_config import get_logger, save_trace
from models import AnalysisResponse

logger = get_logger("api")

MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024))
)

app = FastAPI(
    title="Call Sentiment Analyzer API",
    description="LangGraph-powered call transcript sentiment & KPI analysis",
    version="1.1.0",
)

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

frontend_urls_env = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
)

origins = [
    url.strip()
    for url in frontend_urls_env.split(",")
    if url.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# ---------------------------------------------------------
# API Key Auth
# ---------------------------------------------------------

API_KEY = os.getenv("API_KEY", "")


def verify_api_key(
    x_api_key: str = Header(default=None),
):
    # Preserve local development compatibility while allowing
    # production deployments to enforce authentication.
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
        )

    return True


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "call-sentiment-analyzer",
    }


# ---------------------------------------------------------
# Analyze
# ---------------------------------------------------------

@app.post(
    "/analyze",
    response_model=AnalysisResponse,
)
async def analyze(
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key),
):
    request_id = str(uuid.uuid4())
    request_start = time.perf_counter()

    logger.info(
        f"[{request_id}] REQUEST RECEIVED | "
        f"filename={file.filename!r}"
    )

    try:
        # -------------------------------------------------
        # Validate filename
        # -------------------------------------------------

        if (
            not file.filename
            or not file.filename.lower().endswith(".txt")
        ):
            raise HTTPException(
                status_code=400,
                detail="Only .txt files are supported.",
            )

        # -------------------------------------------------
        # Read file safely with an upload-size limit
        # -------------------------------------------------

        chunks = []
        total_size = 0

        while True:
            chunk = await file.read(64 * 1024)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Transcript file is too large. "
                        f"Maximum supported size is "
                        f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                    ),
                )

            chunks.append(chunk)

        content_bytes = b"".join(chunks)

        if not content_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        # -------------------------------------------------
        # Decode
        # -------------------------------------------------

        try:
            raw_text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be UTF-8 encoded plain text.",
            )

        raw_text = raw_text.replace("\x00", "").strip()

        if not raw_text:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file contains no readable text.",
            )

        logger.info(
            f"[{request_id}] FILE ACCEPTED | "
            f"bytes={len(content_bytes)} "
            f"lines={len(raw_text.splitlines())}"
        )

        initial_state: GraphState = {
            "request_id": request_id,
            "raw_text": raw_text,
            "turns": [],
            "sentence_results": [],
            "overall_sentiment": "Neutral",
            "overall_confidence": 0.0,
            "kpis": {},
            "summary": "",
            "error": None,
        }

        # -------------------------------------------------
        # Run LangGraph
        # -------------------------------------------------

        try:
            final_state = compiled_graph.invoke(initial_state)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                f"[{request_id}] PIPELINE CRASHED"
            )

            raise HTTPException(
                status_code=502,
                detail="Analysis pipeline failed.",
            ) from exc

        total_duration = round(
            time.perf_counter() - request_start,
            3,
        )

        # -------------------------------------------------
        # Pipeline-level errors
        # -------------------------------------------------

        if final_state.get("error"):
            error_message = final_state["error"]

            logger.error(
                f"[{request_id}] PIPELINE ERROR | "
                f"{error_message} | "
                f"duration={total_duration}s"
            )

            save_trace(
                request_id,
                {
                    "request_id": request_id,
                    "status": "error",
                    "filename": file.filename,
                    "duration_seconds": total_duration,
                    "error": error_message,
                },
            )

            # Do not expose raw provider exceptions.
            if (
                "failed" in error_message.lower()
                or "model" in error_message.lower()
                or "analysis" in error_message.lower()
            ):
                raise HTTPException(
                    status_code=502,
                    detail=error_message,
                )

            raise HTTPException(
                status_code=422,
                detail=error_message,
            )

        # -------------------------------------------------
        # Validate API response schema
        # -------------------------------------------------

        try:
            response = AnalysisResponse(
                overall_sentiment=final_state["overall_sentiment"],
                overall_confidence=final_state["overall_confidence"],
                summary=final_state["summary"],
                sentences=final_state["sentence_results"],
                kpis=final_state["kpis"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                f"[{request_id}] RESPONSE VALIDATION FAILED"
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to construct the analysis response.",
            ) from exc

        # -------------------------------------------------
        # Sanitized trace
        # -------------------------------------------------

        save_trace(
            request_id,
            {
                "request_id": request_id,
                "status": "success",
                "filename": file.filename,
                "duration_seconds": total_duration,
                "sentence_count": len(response.sentences),
                "overall_sentiment": response.overall_sentiment,
            },
        )

        logger.info(
            f"[{request_id}] REQUEST COMPLETED | "
            f"sentiment={response.overall_sentiment} "
            f"sentences={len(response.sentences)} "
            f"duration={total_duration}s"
        )

        return response

    finally:
        await file.close()