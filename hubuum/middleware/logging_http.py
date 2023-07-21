"""Middleware to handle logging."""
import http
import logging
import time
from typing import Callable, cast

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponse

from hubuum.middleware.context import get_request_id

request_logger = structlog.getLogger("hubuum.request")
response_logger = structlog.getLogger("hubuum.response")


class LogHttpResponseMiddleware:
    """Middleware to log HTTP responses with their status codes, messages, and URLs.

    This middleware checks the status code of the response and logs a message
    based on the response code range (success, redirection, client error, or server error).
    The time it took to process the response is also logged.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Initialize the middleware.

        :param get_response: A reference to the next middleware or view in the chain.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process the request and log the response.

        :param request: The incoming request.
        :return: A response object
        """
        start_time = time.time()

        request.id = get_request_id()
        self.log_request(request)
        response = self.get_response(request)
        self.log_response(request, response, start_time)
        return response

    def log_request(self, request: HttpRequest) -> None:
        """Log the request."""
        remote_ip = request.META.get("REMOTE_ADDR")

        # Check for a proxy address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            proxy_ip = x_forwarded_for.split(",")[0]
        else:
            proxy_ip = ""

        user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Size of request
        request_size = len(request.body)

        request_logger.bind(
            request_id=request.id,
            method=request.method,
            remote_ip=remote_ip,
            proxy_ip=proxy_ip,
            user_agent=user_agent,
            path=request.path_info,
            request_size=request_size,
        ).debug("request")

    def log_response(
        self, request: HttpRequest, response: HttpResponse, start_time: int
    ) -> HttpResponse:
        """Log the response."""
        end_time = time.time()
        status_code = response.status_code
        run_time_ms = (end_time - start_time) * 1000

        status_label = cast(str, http.client.responses[status_code])

        if status_code == 201:
            log_level = logging.DEBUG
        elif 200 <= status_code < 300:
            log_level = logging.DEBUG
        elif 300 <= status_code < 400:
            log_level = logging.INFO
        elif status_code == 400:
            log_level = logging.WARNING
        elif 400 < status_code < 500:
            log_level = logging.WARNING
        else:
            log_level = logging.ERROR

        extra_data = {}

        if run_time_ms >= settings.REQUESTS_THRESHOLD_VERY_SLOW:
            extra_data["original_log_level"] = log_level
            extra_data["very_slow_response"] = True
            log_level = settings.REQUESTS_LOG_LEVEL_VERY_SLOW
        elif run_time_ms >= settings.REQUESTS_THRESHOLD_SLOW:
            extra_data["original_log_level"] = log_level
            extra_data["slow_response"] = True
            log_level = settings.REQUESTS_LOG_LEVEL_SLOW

        content = "[]"
        if "application/json" in response.headers.get("Content-Type", ""):
            content = response.content.decode("utf-8")

        # For some events, like 301s against the Auth endpoints, we may not have a user.
        username = ""
        if hasattr(request, "user"):
            username = request.user.username

        response_logger.bind(
            request_id=request.id,
            user=username,
            method=request.method,
            status_code=status_code,
            status_label=status_label,
            path=request.path_info,
            content=content,
            **extra_data,
            run_time_ms=round(run_time_ms, 2),
        ).log(log_level, "response")

        return response
