"""Structured logging configuration for 3D Kenji."""

import logging
import logging.handlers
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Extra structured fields forwarded through record.extra -> log_data
_EXTRA_FIELDS = (
    "user_id",
    "username",
    "client_ip",
    "request_id",
    "duration_ms",
    "method",
    "path",
    "status_code",
    "event",
    "detail",
)


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

        # Add structured extra fields forwarded via logger.xxx(..., extra={...})
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                log_data[field] = value

        return json.dumps(log_data)


def _parse_max_bytes() -> int:
    """Read LOG_MAX_SIZE_MB env var and convert to bytes (default 10 MB)."""
    try:
        return int(os.getenv("LOG_MAX_SIZE_MB", "10")) * 1024 * 1024
    except (ValueError, TypeError):
        return 10 * 1024 * 1024


def _parse_backup_count() -> int:
    """Read LOG_BACKUP_COUNT env var (default 5)."""
    try:
        return max(1, int(os.getenv("LOG_BACKUP_COUNT", "5")))
    except (ValueError, TypeError):
        return 5


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
) -> logging.Logger:
    """
    Get a configured logger with JSON formatting.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default INFO).
        log_file: Optional file path for file handler. If not provided,
                 logs go to stdout only.
        max_bytes: Maximum file size before rotation. Defaults to LOG_MAX_SIZE_MB env var.
        backup_count: Number of backup files to keep. Defaults to LOG_BACKUP_COUNT env var.

    Returns:
        Configured Logger instance.

    Example:
        ```python
        logger = get_logger(__name__)
        logger.info("Server started", extra={"user_id": "123"})
        ```
    """
    if max_bytes is None:
        max_bytes = _parse_max_bytes()
    if backup_count is None:
        backup_count = _parse_backup_count()

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


# ---------------------------------------------------------------------------
# Module-level application logger (singleton)
# ---------------------------------------------------------------------------

def _file_logging_enabled() -> bool:
    return os.getenv("ENABLE_FILE_LOGGING", "true").lower() in ("true", "1", "yes")


_default_log_file: Optional[str] = (
    os.getenv("LOG_FILE", "data/logs/app.log") if _file_logging_enabled() else None
)
_initial_level_str: str = os.getenv("LOG_LEVEL", "INFO").upper()
_initial_level: int = getattr(logging, _initial_level_str, logging.INFO)

logger = get_logger(
    "3dkenji",
    level=_initial_level,
    log_file=_default_log_file,
)


# ---------------------------------------------------------------------------
# Runtime control helpers (called at startup and from admin settings endpoint)
# ---------------------------------------------------------------------------

_VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


def get_current_log_level() -> str:
    """Return the current effective log level name (e.g. 'INFO')."""
    return logging.getLevelName(logger.level)


def get_current_backup_count() -> int:
    """Return the backup count configured on the file handler (or env default)."""
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            return handler.backupCount
    return _parse_backup_count()


def get_current_max_size_mb() -> int:
    """Return the max file size in MB configured on the file handler (or env default)."""
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            return handler.maxBytes // (1024 * 1024)
    return _parse_max_bytes() // (1024 * 1024)


def set_log_level(level_name: str) -> None:
    """Change the log level of all handlers at runtime.

    Args:
        level_name: One of DEBUG, INFO, WARNING, ERROR.
    """
    level_name = level_name.upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def set_backup_count(count: int) -> None:
    """Update the RotatingFileHandler backup count at runtime.

    Args:
        count: Number of rotated backup files to keep (minimum 1).
    """
    count = max(1, count)
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.backupCount = count


def set_max_size_mb(mb: int) -> None:
    """Update the RotatingFileHandler max file size at runtime.

    Args:
        mb: Maximum file size in megabytes (minimum 1).
    """
    mb = max(1, mb)
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.maxBytes = mb * 1024 * 1024


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: Optional[int] = None,
    backup_count: Optional[int] = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Log level as string ("DEBUG", "INFO", "WARNING", "ERROR").
        log_file: Optional file path for logging.
        max_size_mb: Max log file size in MB before rotation.
        backup_count: Number of rotated backup files to keep.
    """
    set_log_level(log_level)

    if max_size_mb is not None:
        set_max_size_mb(max_size_mb)

    if backup_count is not None:
        set_backup_count(backup_count)

    if log_file:
        level = getattr(logging, log_level.upper(), logging.INFO)
        resolved_max = (max_size_mb or get_current_max_size_mb()) * 1024 * 1024
        resolved_backup = backup_count or get_current_backup_count()
        # Replace or add file handler with new path
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
        new_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=resolved_max,
            backupCount=resolved_backup,
        )
        new_handler.setLevel(level)
        new_handler.setFormatter(JSONFormatter())
        logger.addHandler(new_handler)
