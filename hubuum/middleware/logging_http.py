"""Middleware to handle logging."""
import http
import logging
import time

import structlog

logger = structlog.getLogger("hubuum.request")


class LogHttpResponseMiddleware:
    """
    Middleware to log HTTP responses with their status codes, messages, and URLs.

    This middleware checks the status code of the response and logs a message
    based on the response code range (success, redirection, client error, or server error).
    The time it took to process the response is also logged.
    """

    def __init__(self, get_response):
        """
        Initialize the middleware.

        :param get_response: A reference to the next middleware or view in the chain.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process the request and log the response.

        :param request: The incoming request.
        :return: A response object
        """
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        status_code = response.status_code
        run_time_ms = (end_time - start_time) * 1000

        status_label = http.client.responses[status_code]

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
        else:  # pragma: no cover
            log_level = logging.ERROR

        if run_time_ms >= 5000:  # pragma: no cover
            log_level = logging.CRITICAL
        elif run_time_ms >= 1000:  # pragma: no cover
            log_level = logging.WARNING

        content = "[]"
        if "application/json" in response.headers.get("Content-Type", ""):
            content = response.content.decode("utf-8")

        logger.bind(
            method=request.method,
            status_code=status_code,
            status_label=status_label,
            path=request.path_info,
            content=content,
            run_time_ms=round(run_time_ms, 2),
        ).log(log_level, "response")

        return response
