from dotenv import load_dotenv
load_dotenv()

import os
import time
import uuid
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from models import AnalysisResponse
from langgraph_pipeline import compiled_graph, GraphState
from logger_config import get_logger, save_trace

logger = get_logger("api")

app = FastAPI(
    title="Call Sentiment Analyzer API",
    description="LangGraph-powered call transcript sentiment & KPI analysis",
    version="1.0.0",
)

# ---------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------
frontend_urls_env = os.getenv("FRONTEND_URL", "http://localhost:3000")
origins = [u.strip() for u in frontend_urls_env.split(",") if u.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Simple API Key Auth
# ---------------------------------------------------------
API_KEY = os.getenv("API_KEY", "")


def verify_api_key(x_api_key: str = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key),
):
    request_id = str(uuid.uuid4())
    request_start = time.perf_counter()

    logger.info(f"[{request_id}] ===== REQUEST RECEIVED ===== filename={file.filename}")

    if not file.filename or not file.filename.lower().endswith(".txt"):
        logger.warning(f"[{request_id}] REJECTED — invalid file type")
        raise HTTPException(status_code=400, detail="Only .txt files are supported.")

    content_bytes = await file.read()
    if not content_bytes:
        logger.warning(f"[{request_id}] REJECTED — empty file")
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        raw_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning(f"[{request_id}] REJECTED — file not UTF-8 encoded")
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded plain text.")

    if not raw_text.strip():
        logger.warning(f"[{request_id}] REJECTED — no readable text")
        raise HTTPException(status_code=400, detail="Uploaded file contains no readable text.")

    logger.info(
        f"[{request_id}] File accepted | size={len(content_bytes)} bytes | "
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

    try:
        final_state = compiled_graph.invoke(initial_state)
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"[{request_id}] PIPELINE CRASHED")
        raise HTTPException(status_code=502, detail=f"Analysis pipeline failed: {exc}")

    total_duration = round(time.perf_counter() - request_start, 3)

    if final_state.get("error"):
        logger.error(
            f"[{request_id}] PIPELINE RETURNED ERROR: {final_state['error']} "
            f"| total_time={total_duration}s"
        )
        save_trace(request_id, {
            "request_id": request_id,
            "filename": file.filename,
            "status": "error",
            "error": final_state["error"],
            "duration_seconds": total_duration,
            "final_state": final_state,
        })
        raise HTTPException(status_code=422, detail=final_state["error"])

    try:
        response = AnalysisResponse(
            overall_sentiment=final_state["overall_sentiment"],
            overall_confidence=final_state["overall_confidence"],
            summary=final_state["summary"],
            sentences=final_state["sentence_results"],
            kpis=final_state["kpis"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"[{request_id}] RESPONSE BUILD FAILED")
        raise HTTPException(status_code=500, detail=f"Failed to build response: {exc}")

    logger.info(
        f"[{request_id}] ===== REQUEST COMPLETED ===== "
        f"overall_sentiment={response.overall_sentiment} "
        f"total_time={total_duration}s"
    )

    # Save a full JSON trace of this request for debugging/audit purposes
    save_trace(request_id, {
        "request_id": request_id,
        "filename": file.filename,
        "status": "success",
        "duration_seconds": total_duration,
        "final_state": final_state,
        "response": response.model_dump(),
    })

    return response