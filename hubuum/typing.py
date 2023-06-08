"""Typing assistance for Hubuum."""

from typing import Dict, cast

from django import http

from hubuum.models.iam import User


def typed_query_params_from_request(request: http.HttpRequest) -> Dict[str, str]:
    """Return a str, str-typed dictionary of query parameters."""
    return cast(Dict[str, str], request.query_params)


def typed_user_from_request(request: http.HttpRequest) -> User:
    """Return a User object from a request."""
    return cast(User, request.user)
