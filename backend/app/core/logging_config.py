# @TASK LOG-T1 - Structured logging configuration
# @SPEC stdlib logging, no external dependencies

"""Structured logging setup for the Memory SCM backend.

Configures the root logger with a single StreamHandler that emits log
records in a consistent pipe-delimited format:

    %(asctime)s | %(levelname)s | %(name)s | %(message)s

Call ``setup_logging()`` once at application startup (inside main.py)
before any other module-level loggers are used.

The default log level is read from ``settings.LOG_LEVEL`` so it can be
controlled via the ``LOG_LEVEL`` environment variable (or ``.env`` file).
"""

import logging
import sys

from app.core.config import settings


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Resolve the configured log level string (e.g. "DEBUG") to a numeric value.
_DEFAULT_LEVEL: int = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)


def setup_logging(level: int | None = None) -> None:
    """Configure the root logger.

    Parameters
    ----------
    level:
        Minimum log level that will be emitted.  When *None* (the default),
        the level is determined by the ``LOG_LEVEL`` setting from
        ``app.core.config.settings``.
    """
    if level is None:
        level = _DEFAULT_LEVEL
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Avoid adding duplicate handlers if setup_logging is called more than once
    # (e.g., during test collection that imports main multiple times).
    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Silence noisy third-party loggers so they don't flood the output.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # we log via middleware
