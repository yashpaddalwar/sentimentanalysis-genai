import json
import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.getenv("LOG_DIR", "logs")
TRACE_DIR = os.path.join(LOG_DIR, "traces")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRACE_DIR, exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "pipeline.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Avoid duplicate log propagation to the root logger.
    logger.propagate = False

    return logger


def save_trace(request_id: str, data: dict) -> None:
    """
    Save only sanitized request metadata.

    Do not place raw transcripts, prompts, or full LLM responses
    in persistent logs because transcripts can contain sensitive data.
    """
    path = os.path.join(
        TRACE_DIR,
        f"{request_id}.json",
    )

    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                default=str,
            )
    except Exception:
        # Trace persistence must never break the request.
        pass