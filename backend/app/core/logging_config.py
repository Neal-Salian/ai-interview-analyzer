"""
Structured logging configuration — JSON-lines in production, human-readable in dev.

Usage:
    from app.core.logging_config import setup_logging, log_event

    # Call once at startup (in lifespan):
    setup_logging()

    # Emit structured events anywhere:
    log_event(logger, "meeting_started", session_id="abc", meeting_id="123")
"""

import json
import logging
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """
    JSON-line formatter for production log aggregation.

    Each log line is a single JSON object with:
      - timestamp (ISO 8601 UTC)
      - level
      - logger
      - message
      - event (if set via log_event)
      - extra context fields (if set via log_event)
    """

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge structured context from log_event()
        if hasattr(record, "_structured_event"):
            entry["event"] = record._structured_event
        if hasattr(record, "_structured_context"):
            entry.update(record._structured_context)

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


def setup_logging() -> None:
    """
    Configure root logger.

    - Production (ENV != "development"): JSON-line format for log aggregation.
    - Development: default human-readable format for terminal readability.
    """
    from app.core.config import settings

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicate output
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENV != "development":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Reduce noise from chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def log_event(
    logger: logging.Logger,
    event: str,
    level: int = logging.INFO,
    message: str = "",
    **context,
) -> None:
    """
    Emit a structured log event.

    Args:
        logger: The logger instance to use.
        event: Event name (e.g. "meeting_started", "consumer_failed").
        level: Log level (default INFO).
        message: Optional human-readable message.
        **context: Arbitrary key-value pairs included in the structured output.

    Example:
        log_event(logger, "meeting_started",
                  session_id="abc-123", meeting_id="99887766",
                  is_orphan=False)

    In production (JSON mode), this emits:
        {"timestamp": "...", "level": "INFO", "logger": "...",
         "message": "meeting_started", "event": "meeting_started",
         "session_id": "abc-123", "meeting_id": "99887766", "is_orphan": false}

    In development, the standard formatter outputs:
        2026-06-25 08:30:00 INFO     [app.api.routes.zoom_webhook]
        meeting_started | session_id=abc-123 meeting_id=99887766 is_orphan=False
    """
    # Build a human-readable message for dev mode
    if not message:
        if context:
            ctx_str = " ".join(f"{k}={v}" for k, v in context.items())
            message = f"{event} | {ctx_str}"
        else:
            message = event

    # Create the log record with structured extras
    extra = {
        "_structured_event": event,
        "_structured_context": context,
    }
    logger.log(level, message, extra=extra)
