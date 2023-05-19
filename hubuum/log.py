"""Logging tools for hubuum."""

from functools import singledispatch
from typing import Any

from structlog import get_logger
from structlog.typing import EventDict

from hubuum.exceptions import InvalidParam

logger = get_logger("hubuum.manual")


def _replace_token(token: str) -> str:
    """Replace a token with a shortened and safe version of it."""
    if len(token) > 10:
        return token[:3] + "..." + token[-3:]

    return "..."


# Due to the recursive nature of this function, it is not possible to type it properly.
# It's possible to overload functions in Python, but it's not exactly pretty:
# https://docs.python.org/3/library/functools.html#functools.singledispatch
# https://www.codementor.io/@arpitbhayani/overload-functions-in-python-13e32ahzqt#
@singledispatch
def _filter_sensitive_data(record: Any) -> Any:
    """If no known signatures matches, that's not good."""
    raise InvalidParam(f"Unknown record type: {type(record)}")


@_filter_sensitive_data.register(None.__class__)
def _(record: None) -> None:
    """Return empty records or values as-is."""
    return record


@_filter_sensitive_data.register(int)
def _(record: int) -> int:
    """Return int values as-is."""
    return record


@_filter_sensitive_data.register(float)
def _(record: float) -> float:
    """Return float values as-is."""
    return record


@_filter_sensitive_data.register(dict)
def _(record: EventDict) -> EventDict:
    """Filter sensitive data from a log record, traverse the dict."""
    if "model" in record and record["model"] == "AuthToken":
        value = record["id"]
        (token, username) = value.split(" : ")
        record["id"] = _replace_token(token) + " : " + username

    for key, value in record.items():
        if key in ["token"]:
            record[key] = _replace_token(value)
        else:
            record[key] = _filter_sensitive_data(value)
    return record


@_filter_sensitive_data.register(str)
def _(record: str) -> str:
    """Filter sensitive data from a log record, fix the token."""
    if '"token":"' in record:
        token = record.split('"token":"')[1].split('"')[0]
        record = record.replace(token, _replace_token(token))

    return record


def filter_sensitive_data(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    """Filter sensitive data from a structlogs event_dict."""
    return _filter_sensitive_data(event_dict)


def debug(message: str, **kwargs: Any) -> None:
    """Log a debug message."""
    logger.debug(message, **kwargs)


def info(message: str, **kwargs: Any) -> None:
    """Log an info message."""
    logger.info(message, **kwargs)


def warning(message: str, **kwargs: Any) -> None:
    """Log a warning message."""
    logger.warning(message, **kwargs)


def error(message: str, **kwargs: Any) -> None:
    """Log an error message."""
    logger.error(message, **kwargs)


def critical(message: str, **kwargs: Any) -> None:
    """Log a critical message."""
    logger.critical(message, **kwargs)
