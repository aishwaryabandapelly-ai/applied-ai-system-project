"""
Reusable logging configuration for TuneGuide AI.

This module only establishes a shared logging utility. It intentionally does
NOT wire logging into the recommender functions yet (that belongs to a later
phase). Import ``get_logger`` wherever a logger is needed.

Design goals:
- Use the standard library ``logging`` module.
- Log to both ``logs/tuneguide.log`` and the console.
- Create the ``logs/`` directory automatically when needed.
- Never attach duplicate handlers, even if imported/called many times.
- Fail safely: if file logging cannot be initialized, keep console logging.
"""

import logging
import os

# Where logs live. Relative to the current working directory (the project root
# when the app or tests are run from there), matching how the CLI loads
# ``data/songs.csv``.
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "tuneguide.log")

# timestamp | level | logger name | message
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Marker names so we can recognize handlers this module added and avoid
# attaching them more than once to the same logger.
_CONSOLE_HANDLER_NAME = "tuneguide_console"
_FILE_HANDLER_NAME = "tuneguide_file"


def _has_handler(logger: logging.Logger, handler_name: str) -> bool:
    """Return True if the logger already has one of our named handlers."""
    return any(getattr(h, "name", None) == handler_name for h in logger.handlers)


def get_logger(name: str = "tuneguide") -> logging.Logger:
    """Return a configured logger.

    The returned logger writes readable console output and, when possible, to
    ``logs/tuneguide.log``. Calling this repeatedly with the same ``name`` is
    safe: handlers are added at most once.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Don't propagate to the root logger, so we control formatting and avoid
    # duplicate lines from a root handler.
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console handler (always available).
    if not _has_handler(logger, _CONSOLE_HANDLER_NAME):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        console_handler.name = _CONSOLE_HANDLER_NAME
        logger.addHandler(console_handler)

    # File handler (best effort). If the directory can't be created or the file
    # can't be opened, fall back to console-only logging without crashing.
    if not _has_handler(logger, _FILE_HANDLER_NAME):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            file_handler.name = _FILE_HANDLER_NAME
            logger.addHandler(file_handler)
        except OSError:
            # File logging is optional; console logging still works.
            logger.warning(
                "File logging could not be initialized at %s; "
                "continuing with console logging only.",
                LOG_FILE,
            )

    return logger
