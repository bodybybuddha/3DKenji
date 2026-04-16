"""Structured logging configuration for 3D Kenji."""

import logging
import logging.handlers
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Outputs logs as JSON for easy parsing and analysis.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: LogRecord to format.

        Returns:
            JSON string with log data.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present in record (use type ignore for dynamic attributes)
        user_id = getattr(record, "user_id", None)
        if user_id:
            log_data["user_id"] = user_id
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms:
            log_data["duration_ms"] = duration_ms

        return json.dumps(log_data)


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Get a configured logger with JSON formatting.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default INFO).
        log_file: Optional file path for file handler. If not provided,
                 logs go to stdout only.
        max_bytes: Maximum file size before rotation (default 10 MB).
        backup_count: Number of backup files to keep (default 5).

    Returns:
        Configured Logger instance.

    Example:
        ```python
        logger = get_logger(__name__)
        logger.info("Server started", extra={"user_id": "123"})
        ```
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    logger.handlers = []

    # Create JSON formatter
    formatter = JSONFormatter()

    # Add stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Add file handler if log_file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        # Force a rollover on startup if a prior log exists
        if log_path.exists() and log_path.stat().st_size > 0:
            file_handler.doRollover()
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Root logger for the application
# Use environment variable or default to relative path
default_log_file = os.getenv("LOG_FILE", "data/logs/app.log") if os.getenv("ENABLE_FILE_LOGGING", "true").lower() in ("true", "1", "yes") else None

logger = get_logger(
    "3dkenji",
    level=logging.INFO,
    log_file=default_log_file,
)


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Log level as string ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        log_file: Optional file path for logging.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Update root logger
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

    # Update child loggers
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and log_file:
            # Replace file handler with new path
            logger.removeHandler(handler)
            new_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
            )
            new_handler.setLevel(level)
            new_handler.setFormatter(JSONFormatter())
            logger.addHandler(new_handler)
