from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": utc_now_iso(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logger(log_dir: str) -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("autobot")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Prevent duplicate handlers on reload.
    if logger.handlers:
        return logger

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())
    logger.addHandler(stream_handler)

    file_path = Path(log_dir) / "bot.log.jsonl"
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger


def log_info(logger: logging.Logger, message: str, **extra: Any) -> None:
    logger.info(message, extra={"extra": extra})


def log_warn(logger: logging.Logger, message: str, **extra: Any) -> None:
    logger.warning(message, extra={"extra": extra})


def log_error(logger: logging.Logger, message: str, **extra: Any) -> None:
    logger.error(message, extra={"extra": extra})

