"""Typing assistance for Hubuum."""

from typing import Dict, cast

from django import http


def typed_query_params(request: http.HttpRequest) -> Dict[str, str]:
    """Return a str, str-typed dictionary of query parameters."""
    return cast(Dict[str, str], request.query_params)
