import logging
import sys
from typing import Optional

from app.config.settings import settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """Configure logging for the application.

    Args:
        level: The logging level to use. If None, uses the level from settings.
        format_string: The log format string to use. If None, uses a default format.
    """
    log_level = level or settings.LOG_LEVEL or "INFO"
    log_format = format_string or settings.LOG_FORMAT

    formatter = logging.Formatter(log_format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # root logger
    root_logger = logging.getLogger()

    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    app_logger = logging.getLogger("test_service_python")
    app_logger.setLevel(getattr(logging, log_level.upper()))

    # configure external libraries to use our format
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers.clear()
        lib_logger.propagate = True
        lib_logger.setLevel(getattr(logging, log_level.upper()))

    app_logger.info("Initialize logging with level: %s", log_level)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: The name for the logger. If None, uses "test_service_python".

    Returns:
        A configured logger instance.
    """
    logger_name = f"test_service_python.{name}" if name else "test_service_python"
    return logging.getLogger(logger_name)
