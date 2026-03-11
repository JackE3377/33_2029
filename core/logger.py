# ============================================================
# GEM Protocol — Structured Logging
# ============================================================
from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for audit trail."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> None:
    """Initialise structured JSON rotating file + console logging."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Rotating file handler (10 MB × 5 backups)
    fh = logging.handlers.RotatingFileHandler(
        log_path / "gem_protocol.jsonl",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(JSONFormatter())
    root.addHandler(fh)

    # Console handler (human-readable)
    ch = logging.StreamHandler()
    ch.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)-24s │ %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(ch)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"gem.{name}")
