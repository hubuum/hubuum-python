"""Test the logging in hubuum."""

import logging

from .base import HubuumAPITestCase


class HubuumLoggingTestCase(HubuumAPITestCase):
    """Test class for logging."""

    def setUp(self):
        """Set up the test environment."""
        super().setUp()
        logging.disable(logging.NOTSET)  # Enable logging temporarily

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.CRITICAL)  # Disable logging after the test
        super().tearDown()

    def _test_logging_helper(self, url, status_code, status_name, level="DEBUG"):
        with self.assertLogs("hubuum.middleware", level=level) as log_context:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

        log_message = log_context.output[0]

        expected_pattern = (
            f"{level}:hubuum.middleware:GET: \\({status_code}/{status_name}\\)"
            f" {url} \\[\\] \\(.*ms\\)"
        )

        self.assertRegex(log_message, expected_pattern)

    def test_success_logging(self):
        """Test logging for 200 status code."""
        url = "/api/v1/hosts/"
        self._test_logging_helper(url, 200, "Success")

    def test_not_found_logging(self):
        """Test logging for 404 status code."""
        url = "/hosts/notahost"
        self._test_logging_helper(url, 404, "Client Error", level="INFO")
