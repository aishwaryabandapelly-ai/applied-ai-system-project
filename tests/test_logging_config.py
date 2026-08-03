"""
Focused tests for the reusable logging utility (src/logging_config.py).

These avoid asserting on machine-specific paths or exact timestamps; they only
check the utility's contract: it returns a logger, it does not accumulate
duplicate handlers, and it does not crash when the log directory already exists.
"""

import logging

from src.logging_config import get_logger


def test_get_logger_returns_a_logger():
    logger = get_logger("tuneguide_test_returns")
    assert isinstance(logger, logging.Logger)


def test_repeated_calls_do_not_add_duplicate_handlers():
    name = "tuneguide_test_no_duplicates"
    first = get_logger(name)
    handler_count = len(first.handlers)

    # Calling again (as happens when many modules import the utility) must not
    # keep stacking handlers.
    second = get_logger(name)
    assert second is first
    assert len(second.handlers) == handler_count

    # A third call for good measure.
    get_logger(name)
    assert len(logging.getLogger(name).handlers) == handler_count


def test_setup_does_not_crash_when_log_dir_exists():
    # First call creates logs/ if needed; the second runs with the dir present.
    get_logger("tuneguide_test_existing_dir_1")
    # Should complete without raising even though logs/ now exists.
    logger = get_logger("tuneguide_test_existing_dir_2")
    assert isinstance(logger, logging.Logger)
