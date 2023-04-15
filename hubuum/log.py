"""Logging tools for hubuum."""

import structlog

logger = structlog.get_logger("hubuum.manual")


def _replace_token(token):
    """Replace a token with a shortened and safe version of it."""
    if len(token) > 10:
        return token[:3] + "..." + token[-3:]

    return "..."


def _filter_sensitive_data(record):
    """Filter sensitive data from a log record."""
    if record is None:
        return None

    if isinstance(record, dict):
        if "model" in record and record["model"] == "AuthToken":
            value = record["id"]
            (token, username) = value.split(" : ")
            record["id"] = _replace_token(token) + " : " + username

        for key, value in record.items():
            if key in ["token"]:
                record[key] = _replace_token(value)
            else:
                record[key] = _filter_sensitive_data(value)

    elif record and isinstance(record, str) and '"token":"' in record:
        token = record.split('"token":"')[1].split('"')[0]
        record = record.replace(token, _replace_token(token))

    return record


def filter_sensitive_data(_, __, event_dict):
    """Filter sensitive data from a structlogs event_dict."""
    return _filter_sensitive_data(event_dict)


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
