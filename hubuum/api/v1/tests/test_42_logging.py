"""Test the logging in hubuum."""

import json

from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient
from structlog import get_logger
from structlog.testing import capture_logs

from hubuum.api.v1.tests.base import HubuumAPITestCase
from hubuum.log import critical, debug, error, info, warning
from hubuum.models.auth import User
from hubuum.models.permissions import HubuumModel, Namespace
from hubuum.models.resources import Host


class HubuumLoggingTestCase(HubuumAPITestCase):
    """Test class for logging."""

    def setUp(self):
        """Set up the test environment."""
        super().setUp()
        self.namespace, _ = Namespace.objects.get_or_create(name="namespace")
        self.host_data = {
            "name": "test",
            "fqdn": "test.domain.tld",
            "namespace": self.namespace.id,
        }

    def tearDown(self):
        """Clean up after tests."""
        self.namespace.delete()
        super().tearDown()

    def _check_levels(self, cap_logs, expected_levels):
        """Check the log levels in the log."""
        for i, level in enumerate(expected_levels):
            self.assertEqual(cap_logs[i]["log_level"], level)

    def _check_events(self, cap_logs, expected_events):
        """Check the events in the log."""
        for i, event in enumerate(expected_events):
            self.assertEqual(cap_logs[i]["event"], event)

    def _check_request_started(self, log, method_and_expected_path):
        """Check the request_started log entry."""
        self.assertEqual(log["event"], "request_started")
        self.assertEqual(log["request"], method_and_expected_path)

    def _check_request_finished(self, log, method_and_expected_path, code):
        """Check the request_finished log entry."""
        self.assertEqual(log["event"], "request_finished")
        self.assertEqual(log["request"], method_and_expected_path)
        self.assertEqual(log["code"], code)

    def _check_response(
        self, log, method, path, status_code, status_label
    ):  # pylint: disable=too-many-arguments
        """Check the HTTP response log entry."""
        self.assertEqual(log["event"], "response")
        self.assertEqual(log["method"], method)
        self.assertEqual(log["path"], path)
        self.assertEqual(log["status_label"], status_label)
        self.assertEqual(log["status_code"], status_code)
        self.assertTrue(float(log["run_time_ms"]) > 0)

    def _check_json(
        self, cls: HubuumModel, content: str, expected_content: dict, element=0, count=0
    ):  # pylint: disable=too-many-arguments
        """Check the JSON against expected_content.

        Args:
            content: The JSON content to check.
            expected_content: The expected content.
            count: Expect a list of this many elements.
            element: The element to check in the list.
        """
        json_data = json.loads(content)
        if count:
            self.assertEqual(len(json_data), count)
            json_data = json_data[element]

        self._check_structure(cls, json_data, expected_content)

    def _check_structure(self, cls: HubuumModel, content: dict, expected_content: dict):
        """Check the structure of a response."""
        self.assert_is_iso_date(content["created_at"])
        self.assert_is_iso_date(content["updated_at"])

        if cls == Host:
            self.assert_is_iso_date(content["registration_date"])

        for key, value in expected_content.items():
            self.assertEqual(content[key], value)

    def _check_object_change(
        self, log, operation, model, instance, user
    ):  # pylint: disable=too-many-arguments
        """Check the object change log entry."""
        self.assertEqual(log["event"], operation)
        self.assertEqual(log["model"], model)
        self.assertEqual(log["instance"], instance)
        self.assertEqual(log["user"], user)

    def test_logging_of_namespace_get(self):
        """Test logging of a namespace being retrieved."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            self.assert_get("/namespaces/")

        self.assertEqual(len(cap_logs), 3)

        self._check_events(
            cap_logs, ["request_started", "response", "request_finished"]
        )
        self._check_levels(cap_logs, ["info", "debug", "info"])
        self._check_request_started(cap_logs[0], "GET /api/v1/namespaces/")
        self._check_response(cap_logs[1], "GET", "/api/v1/namespaces/", 200, "OK")
        self._check_json(
            Namespace,
            cap_logs[1]["content"],
            {"id": self.namespace.id, "name": self.namespace.name},
            element=0,
            count=1,
        )
        self._check_request_finished(cap_logs[2], "GET /api/v1/namespaces/", 200)

    def test_logging_of_failed_namespace_get(self):
        """Test logging of a failed namespace retrieval."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            self.assert_get_and_404("/namespaces/nope")

        self.assertEqual(len(cap_logs), 3)
        self._check_events(
            cap_logs, ["request_started", "response", "request_finished"]
        )
        self._check_levels(cap_logs, ["info", "warning", "info"])
        self._check_request_started(cap_logs[0], "GET /api/v1/namespaces/nope")
        self._check_response(
            cap_logs[1], "GET", "/api/v1/namespaces/nope", 404, "Not Found"
        )
        self._check_request_finished(cap_logs[2], "GET /api/v1/namespaces/nope", 404)

    def test_logging_object_creation(self):
        """Test logging of a host being created."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            host_blob = self.assert_post("/hosts/", self.host_data)
            host_id = host_blob.data["id"]

        self.assertEqual(len(cap_logs), 5)

        self._check_events(
            cap_logs,
            [
                "request_started",
                "created",
                "created",
                "response",
                "request_finished",
            ],
        )

        self._check_levels(cap_logs, ["info", "info", "info", "debug", "info"])

        self._check_request_started(cap_logs[0], "POST /api/v1/hosts/")
        self.assertTrue(cap_logs[1]["id"] == host_id)
        self._check_object_change(cap_logs[2], "created", "Host", host_id, "superuser")
        self._check_response(cap_logs[3], "POST", "/api/v1/hosts/", 201, "Created")
        self._check_json(
            Host,
            cap_logs[3]["content"],
            {
                "id": host_id,
                "name": "test",
                "fqdn": "test.domain.tld",
                "namespace": self.namespace.id,
            },
        )
        self._check_request_finished(cap_logs[4], "POST /api/v1/hosts/", 201)

    def test_manual_logging(self):
        """Test manual logging."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            debug("debugtest")
            info("infotest")
            warning("warningtest")
            critical("criticaltest")
            error("errortest")

        self.assertTrue(len(cap_logs) == 5)

        self.assertTrue(cap_logs[0]["event"] == "debugtest")
        self.assertTrue(cap_logs[1]["event"] == "infotest")
        self.assertTrue(cap_logs[2]["event"] == "warningtest")
        self.assertTrue(cap_logs[3]["event"] == "criticaltest")
        self.assertTrue(cap_logs[4]["event"] == "errortest")

        self.assertTrue(cap_logs[0]["log_level"] == "debug")
        self.assertTrue(cap_logs[1]["log_level"] == "info")
        self.assertTrue(cap_logs[2]["log_level"] == "warning")
        self.assertTrue(cap_logs[3]["log_level"] == "critical")
        self.assertTrue(cap_logs[4]["log_level"] == "error")

    def test_successful_auth_logging(self):
        """Test logging of successful authentication."""
        plaintext = "django"
        user, _ = User.objects.get_or_create(
            username="testuser", password=make_password(plaintext)
        )  # nosec
        auth = self.basic_auth("testuser", plaintext)

        with capture_logs() as cap_logs:
            get_logger().bind()
            self.client = APIClient()
            self.client.credentials(HTTP_AUTHORIZATION=auth)
            auth = self.client.post(
                "/api/auth/login/",
            )
            self.client.credentials(HTTP_AUTHORIZATION="Token " + auth.data["token"])
            self.client.post(
                "/api/auth/logout/",
            )

        self.assertTrue(len(cap_logs) == 11)
        self._check_events(
            cap_logs,
            [
                "request_started",
                "created",
                "updated",
                "login",
                "response",
                "request_finished",
                "request_started",
                "deleted",
                "logout",
                "response",
                "request_finished",
            ],
        )
        self._check_levels(
            cap_logs,
            [
                "info",
                "info",
                "info",
                "info",
                "debug",
                "info",
                "info",
                "info",
                "info",
                "debug",
                "info",
            ],
        )

        # Check that we're deleting the right token
        self.assertTrue(cap_logs[1]["id"] == cap_logs[7]["id"])

        # Check that we have the right users.
        self.assertTrue(cap_logs[2]["id"] == user.id == cap_logs[8]["id"])

        json_data = json.loads(cap_logs[4]["content"])
        self.assertIn("token", json_data)
        self.assert_is_iso_date(json_data["expiry"])

        self.assertEqual(cap_logs[4]["status_code"], 200)

        user.delete()

    def test_unsuccessful_auth_logging(self):
        """Test logging of successful authentication."""
        plaintext = "django"
        user, _ = User.objects.get_or_create(
            username="testuser", password=make_password("wrongpassword")
        )  # nosec
        auth = self.basic_auth("testuser", plaintext)

        with capture_logs() as cap_logs:
            get_logger().bind()
            self.client = APIClient()
            self.client.credentials(HTTP_AUTHORIZATION=auth)
            auth = self.client.post(
                "/api/auth/login/",
            )

        self.assertTrue(len(cap_logs) == 4)
        self._check_events(
            cap_logs,
            [
                "request_started",
                "failure",
                "response",
                "request_finished",
            ],
        )
        self._check_levels(cap_logs, ["info", "error", "warning", "info"])

        self.assertIsNone(cap_logs[1]["id"])

        json_data = json.loads(cap_logs[2]["content"])
        self.assertIn(json_data["detail"], "Invalid username/password.")

        self.assertEqual(cap_logs[2]["status_code"], 401)

        user.delete()
