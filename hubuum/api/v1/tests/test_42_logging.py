"""Test the logging in hubuum."""

import logging

from hubuum.api.v1.tests.base import HubuumAPITestCase
from hubuum.models.base import Host, Namespace


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


class HubuumObjectLoggingTestCase(HubuumAPITestCase):
    """Test case for object logging when creating, updating, or deleting."""

    def setUp(self):
        """Set up the test environment."""
        super().setUp()
        self.namespace, _ = Namespace.objects.get_or_create(name="namespace1")
        self.host_data = {
            "name": "host1",
            "fqdn": "host1.domain.tld",
            "namespace": self.namespace.id,
        }
        self.url = "/api/v1/hosts/"

        logging.disable(logging.NOTSET)  # Enable logging temporarily

    def tearDown(self):
        """Clean up after tests."""
        logging.disable(logging.CRITICAL)  # Disable logging after the test
        super().tearDown()

    def _create_expected_pattern(self, operation, id=None):
        """Create an expected pattern string."""
        prefix = "INFO:hubuum.objects:OBJECT"
        if not id:
            id = self.host_data["name"]
        target = f"Host:{id}"
        return f"{prefix} \\[{operation}\\] {target} by superuser"

    def test_create_logging(self):
        """Test logging for object creation."""
        with self.assertLogs("hubuum.objects", level="INFO") as cm:
            self.host_data["namespace"] = self.namespace.id
            host = self.assert_post(self.url, self.host_data)

        log_message = cm.output[0]
        expected_pattern = self._create_expected_pattern("create")

        self.assertRegex(log_message, expected_pattern)
        self.assert_delete(f"{self.url}{host.data['id']}")

    def test_update_logging(self):
        """Test logging for object update."""
        self.host_data["namespace"] = self.namespace
        host = Host.objects.create(**self.host_data)
        url = f"{self.url}{self.host_data['name']}"
        data = {"name": "updated", "fqdn": "updated.domain.tld"}

        with self.assertLogs("hubuum.objects", level="INFO") as cm:
            self.assert_patch(url, data)

        log_message = cm.output[0]

        expected_pattern = self._create_expected_pattern("update", id="updated")

        self.assertRegex(log_message, expected_pattern)
        host.delete()

    def test_delete_logging(self):
        """Test logging for object deletion."""
        self.host_data["namespace"] = self.namespace
        Host.objects.create(**self.host_data)
        url = f"{self.url}{self.host_data['name']}"

        with self.assertLogs("hubuum.objects", level="INFO") as cm:
            self.assert_delete(url)

        log_message = cm.output[0]
        expected_pattern = self._create_expected_pattern("delete")

        self.assertRegex(log_message, expected_pattern)
