"""Meta views for hubuum API v1."""

import json
from datetime import timedelta
from typing import Any

from django.http import HttpRequest, HttpResponse
from rest_framework.views import APIView
from structlog.dev import ConsoleRenderer

from hubuum import __version__, debug, runtimes
from hubuum.permissions import IsAuthenticated, IsSuperOrAdmin


def handle_debug_data(obj: Any) -> Any:
    """Handle timedelta objects."""
    if isinstance(obj, (timedelta, type, ConsoleRenderer)):
        return str(obj)
    raise TypeError(f"Failed to serialize {type(obj).__name__}")  # pragma: no cover


class VersionView(APIView):
    """View to get the version of the API."""

    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Get the version of the API."""
        return HttpResponse(__version__, content_type="text/plain")


class RuntimesView(APIView):
    """View to get the versions of the runtimes/subsystems involved."""

    permission_classes = [IsSuperOrAdmin]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Get the versions of the runtimes/subsystems."""
        return HttpResponse(json.dumps(runtimes), content_type="application/json")


class DebugView(APIView):
    """View to get debug data."""

    permission_classes = [IsSuperOrAdmin]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Get debug data."""
        return HttpResponse(
            json.dumps(debug, default=handle_debug_data),
            content_type="application/json",
        )
