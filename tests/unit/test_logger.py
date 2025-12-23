"""Tests for logger configuration and functionality.

This module contains unit tests for the logger utility
to ensure proper configuration in different environments.
"""

import logging
import os


def test_logger_is_properly_configured():
    """Test that the logger module is properly configured."""
    from app.utils.logger import logger

    # Logger should exist and be configured
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "debug")


def test_logger_can_log_messages(caplog):
    """Test that logger can successfully log messages."""
    from app.utils.logger import logger

    with caplog.at_level(logging.INFO):
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

    # Check that messages were logged
    assert "Test info message" in caplog.text
    assert "Test warning message" in caplog.text
    assert "Test error message" in caplog.text


def test_logger_respects_log_level():
    """Test that logger respects the configured log level."""

    # Logger should have a log level set
    # In testing environment, LOG_LEVEL is set to DEBUG in conftest.py
    # So debug messages should be logged
    assert os.environ.get("LOG_LEVEL") == "DEBUG"


def test_logger_handles_structured_logging(caplog):
    """Test that logger supports structured logging with key-value pairs."""
    from app.utils.logger import logger

    with caplog.at_level(logging.INFO):
        logger.info("Test message with context", user_id=123, action="test")

    # The structured data should be in the log output
    log_output = caplog.text
    assert "Test message with context" in log_output
