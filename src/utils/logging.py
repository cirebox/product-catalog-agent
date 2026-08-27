"""
Logging configuration for Eric Agents.

Provides structured logging with optional JSON output and file handler.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include request_id if available on the record
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    fmt: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    json_output: bool = False,
    file_path: Optional[str] = None,
) -> None:
    """Configure the root logger.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR).
        fmt: Format string for the text formatter.
        json_output: If True, use JSONFormatter for stdout.
        file_path: Optional path for a file handler.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates on repeated calls
    root.handlers.clear()

    # --- stdout handler ---
    stdout_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        stdout_handler.setFormatter(JSONFormatter())
    else:
        stdout_handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(stdout_handler)

    # --- optional file handler ---
    if file_path:
        try:
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(fmt))
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("Could not open log file %s: %s", file_path, exc)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "openai", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root.info(
        "Logging configured — level=%s, json=%s, file=%s", level, json_output, file_path
    )
