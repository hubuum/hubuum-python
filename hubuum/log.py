"""Logging tools for hubuum."""

from collections import defaultdict
from functools import singledispatch
from typing import Any

from rich.console import Console
from rich.text import Text
from structlog import get_logger
from structlog.types import EventDict

from hubuum.exceptions import InvalidParam
from hubuum.middleware.context import get_request_id

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


def add_request_id(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    """Add the request_id to the event."""
    event_dict["request_id"] = get_request_id()
    return event_dict


def collapse_request_id(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    """Collapse request_id into the event."""
    event_dict["request_id"] = _replace_token(event_dict["request_id"])
    return event_dict


def reorder_keys_processor(_: Any, __: Any, event_dict: EventDict) -> EventDict:
    """Reorder keys in a structlogs event_dict, ensuring that request_id is first."""
    event_dict = {
        k: event_dict[k]
        for k in sorted(event_dict.keys(), key=lambda k: k != "request_id")
    }
    return event_dict


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


class RequestColorTracker:
    """Add an easy to track colored bubbles based on an events request_id.

    :ivar COLORS: A list of color names to use for the bubbles.
    :ivar request_to_color: A dictionary mapping request_ids to colors.
    """

    COLORS = ["red", "white", "green", "yellow", "blue", "magenta", "cyan"]

    def __init__(self):
        """Initialize a new RequestColorizer.

        Sets the initial mapping of request_ids to colors to be an empty defaultdict.
        """
        self.console = Console()
        self.request_to_color = defaultdict(self._color_generator().__next__)

    def _colorize(self, color: str, s: str) -> str:
        """Colorize a string using Rich.

        :param color: The name of the color to use.
        :param s: The string to colorize.
        :return: The colorized string.
        """
        text = Text(s, style=f"bold {color}")

        with self.console.capture() as capture:
            self.console.print(text)

        output = capture.get()

        return output.rstrip()  # remove trailing newline

    def _color_generator(self):
        """Create a generator that cycles through the colors.

        :yield: A color from the COLORS list.
        """
        i = 0
        while True:
            yield self.COLORS[i % len(self.COLORS)]
            i += 1

    def __call__(self, _: Any, __: Any, event_dict: EventDict) -> EventDict:
        """Add a colored bubble to the event message.

        :param _: The logger instance. This argument is ignored.
        :param __: The log level. This argument is ignored.
        :param event_dict: The event dictionary of the log entry.
        :return: The modified event dictionary.
        """
        request_id = event_dict.get("request_id", "None")
        color = self.request_to_color[request_id]
        colored_bubble = self._colorize(color, " • ")

        event_dict["event"] = colored_bubble + event_dict.get("event", "")

        return event_dict
