"""Logging tools for hubuum."""

import structlog

logger = structlog.get_logger("hubuum.manual")


def debug(message, **kwargs):
    """Log a debug message."""
    logger.debug(message, **kwargs)


def info(message, **kwargs):
    """Log an info message."""
    logger.info(message, **kwargs)


def warning(message, **kwargs):
    """Log a warning message."""
    logger.warning(message, **kwargs)


def critical(message, **kwargs):
    """Log a critical message."""
    logger.critical(message, **kwargs)


def error(message, **kwargs):
    """Log an error message."""
    logger.error(message, **kwargs)
