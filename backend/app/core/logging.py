import logging
import sys
import json
import time
from typing import Any, Dict, Optional

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            # Mask any potential sensitive keys
            safe_extra = {}
            for k, v in record.extra_data.items():
                if any(sec in k.lower() for sec in ["key", "secret", "token", "password", "auth"]):
                    safe_extra[k] = "[REDACTED]"
                else:
                    safe_extra[k] = v
            log_obj["metadata"] = safe_extra
        return json.dumps(log_obj)

def get_logger(name: str = "docintel") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = get_logger()

class StageTimer:
    """Helper to track elapsed time per processing stage."""
    def __init__(self, stage_name: str, document_name: Optional[str] = None):
        self.stage_name = stage_name
        self.document_name = document_name
        self.start_time = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        logger.info(
            f"Stage started: {self.stage_name}",
            extra={"extra_data": {"stage": self.stage_name, "document_name": self.document_name}}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        if exc_type:
            logger.error(
                f"Stage failed: {self.stage_name} after {self.elapsed_ms}ms: {exc_val}",
                extra={"extra_data": {
                    "stage": self.stage_name,
                    "document_name": self.document_name,
                    "elapsed_ms": self.elapsed_ms,
                    "error": str(exc_val)
                }}
            )
        else:
            logger.info(
                f"Stage completed: {self.stage_name} in {self.elapsed_ms}ms",
                extra={"extra_data": {
                    "stage": self.stage_name,
                    "document_name": self.document_name,
                    "elapsed_ms": self.elapsed_ms
                }}
            )
