"""Middleware to handle logging."""
import logging
import time

logger = logging.getLogger("hubuum.middleware")


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

        if 200 <= status_code < 300:
            log_level = logging.DEBUG
            status_label = "Success"
        elif 300 <= status_code < 400:
            log_level = logging.DEBUG
            status_label = "Redirection"
        elif status_code == 400:
            log_level = logging.INFO
            status_label = "Bad Request"
        elif 400 < status_code < 500:
            log_level = logging.INFO
            status_label = "Client Error"
        else:  # pragma: no cover
            log_level = logging.ERROR
            status_label = "Server Error"

        if run_time_ms >= 1000:  # pragma: no cover
            log_level = logging.WARNING
        elif run_time_ms >= 2000:  # pragma: no cover
            log_level = logging.CRITICAL

        logger.log(
            log_level,
            "%s: %s %s %s %s",
            request.method,
            f"({status_code}/{status_label})",
            request.path_info,
            response.content.decode("utf-8"),
            f"({run_time_ms:.2f}ms)",
        )

        return response
