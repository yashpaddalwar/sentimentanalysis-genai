import logging
import os
import json
from logging.handlers import RotatingFileHandler

LOG_DIR = os.getenv("LOG_DIR", "logs")
TRACE_DIR = os.path.join(LOG_DIR, "traces")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRACE_DIR, exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger that writes to both console and a
    rotating log file at logs/pipeline.log
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # prevent duplicate handlers on hot-reload

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "pipeline.log"),
        maxBytes=5 * 1024 * 1024,   # 5 MB per file
        backupCount=5,               # keep last 5 rotated logs
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def save_trace(request_id: str, data: dict) -> None:
    """
    Saves a full JSON trace of one /analyze request (inputs, LLM outputs,
    final state, timings) to logs/traces/{request_id}.json for debugging
    and audit purposes.
    """
    path = os.path.join(TRACE_DIR, f"{request_id}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        # Never let trace-saving failures break the actual request
        pass