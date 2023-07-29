"""Test the logging in hubuum."""

import io
import json
from typing import List, Tuple
from unittest.mock import MagicMock, patch

from django.contrib.auth.hashers import make_password
from django.http import HttpRequest, HttpResponse
from rest_framework.test import APIClient
from structlog import get_logger
from structlog.testing import capture_logs
from structlog.types import EventDict

from hubuum.api.v1.tests.base import HubuumAPITestCase
from hubuum.api.v1.tests.helpers.logging import LogAnalyzer
from hubuum.log import (
    collapse_request_id,
    critical,
    debug,
    error,
    info,
    reorder_keys_processor,
    warning,
)
from hubuum.middleware.logging_http import LogHttpMiddleware
from hubuum.models.iam import Namespace, User


class HubuumLoggingProcessorTestCase(HubuumAPITestCase):
    """Test that our processors are doing their job."""

    def test_reorder_keys_processor(self) -> None:
        """Test that the keys are reordered properly."""
        # Simulate a logging event
        event = {
            "event": "Event 1",
            "request_id": "request_id",
            "another_key": "value",
        }

        # Process the event
        processed_event = reorder_keys_processor(None, None, event)

        # Check that request_id is the first key
        first_key = next(iter(processed_event.keys()))
        self.assertEqual(first_key, "request_id")

    def test_collapse_request_id_processor(self) -> None:
        """Test that the request ID is collapsed properly."""
        testcases: List[Tuple[str, str]] = [
            ("", "..."),  # length 0
            ("12345", "..."),  # length 5
            ("1234567890", "..."),  # length 10
            ("12345678901", "123...901"),  # length 11
            ("12345678901234567890", "123...890"),  # length 20
        ]

        for original_request_id, expected_request_id in testcases:
            # Simulate a logging event
            event = {"event": "Event 1", "request_id": original_request_id}

            # Process the event
            processed_event = collapse_request_id(None, None, event)

            # Check that the request ID has been replaced and properly formatted
            self.assertEqual(processed_event["request_id"], expected_request_id)


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

    def _prune_permissions(self, cap_logs: EventDict) -> EventDict:
        """Remove the permission logs from the log."""
        return [
            d
            for d in cap_logs
            if d.get("event")
            not in {"has_perm_n", "has_perm", "m:get_object", "login_data"}
        ]

    def test_logging_of_namespace_get(self) -> None:
        """Test logging of a namespace being retrieved."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            self.assert_get("/iam/namespaces/")

        log = LogAnalyzer(
            cap_logs, "GET", "/api/v1/iam/namespaces/", 200, expected_status_label="OK"
        )
        log.set_response_content(
            [{"id": self.namespace.id, "name": self.namespace.name}], model="Namespace"
        )
        log.check_events_are(
            [
                "request_started",
                "request",
                "has_perm_n",
                "has_perm",
                "response",
                "request_finished",
            ]
        )
        log.check_levels_are(["info", "info", "debug", "debug", "info", "info"])
        log.check_events()
        log = LogAnalyzer(
            cap_logs, "GET", "/api/v1/iam/namespaces/", 200, expected_status_label="OK"
        )
        log.set_response_content(
            [{"id": self.namespace.id, "name": self.namespace.name}], model="Namespace"
        )
        log.check_events_are(
            [
                "request_started",
                "request",
                "has_perm_n",
                "has_perm",
                "response",
                "request_finished",
            ]
        )
        log.check_levels_are(["info", "info", "debug", "debug", "info", "info"])
        log.check_events()

    def test_logging_of_failed_namespace_get(self) -> None:
        """Test logging of a failed namespace retrieval."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            self.assert_get_and_404("/iam/namespaces/nope")

        cap_logs = self._prune_permissions(cap_logs)

        log = LogAnalyzer(cap_logs, "GET", "/api/v1/iam/namespaces/nope", 404)
        log.check_events_are(
            ["request_started", "request", "response", "request_finished"]

        log = LogAnalyzer(cap_logs, "GET", "/api/v1/iam/namespaces/nope", 404)
        log.check_events_are(
            ["request_started", "request", "response", "request_finished"]
        )
        log.check_levels_are(["info", "info", "warning", "info"])
        log.check_events()

    def test_logging_dynamic_object_creation(self) -> None:
        """Test logging of a dynamic object being created."""
        self.assert_post(
            "/dynamic/", {"name": "Testclass", "namespace": self.namespace.id}
        )
        with capture_logs() as cap_logs:
            get_logger().bind()
            self.assert_post(
                "/dynamic/Testclass/",
                {"name": "testobject", "namespace": self.namespace.id, "json_data": {}},
            )

        log = LogAnalyzer(cap_logs, "POST", "/api/v1/dynamic/Testclass/", 201)
        log.check_events_are(
            [
                "request_started",
                "request",
                "has_perm_n",
                "has_perm",
                "created",
                "response",
                "request_finished",
            ]
        )
        log.check_levels_are(["info", "info", "debug", "debug", "info", "info", "info"])
        log.check_events()

    def test_logging_object_creation(self) -> None:
        """Test logging of a host being created."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            host_blob = self.assert_post("/resources/hosts/", self.host_data)
            host_id = host_blob.data["id"]

        cap_logs = self._prune_permissions(cap_logs)

        log = LogAnalyzer(cap_logs, "POST", "/api/v1/resources/hosts/", 201)
        log.set_user("superuser")
        log.set_instance_id(host_id)
        log.set_response_content(
            [
                {
                    "id": host_id,
                    "name": "test",
                    "fqdn": "test.domain.tld",
                    "namespace": self.namespace.id,
                }
            ],
            model="Host",
        )
        log.check_events_are(

        log = LogAnalyzer(cap_logs, "POST", "/api/v1/resources/hosts/", 201)
        log.set_user("superuser")
        log.set_instance_id(host_id)
        log.set_response_content(
            [
                {
                    "id": host_id,
                    "name": "test",
                    "fqdn": "test.domain.tld",
                    "namespace": self.namespace.id,
                }
            ],
            model="Host",
        )
        log.check_events_are(
            [
                "request_started",
                "request",
                "created",
                "created",
                "response",
                "request_finished",
            ]
        )
        log.check_levels_are(["info", "info", "info", "debug", "info", "info"])
        log.check_events()

    def test_manual_logging(self) -> None:
        """Test manual logging."""
        with capture_logs() as cap_logs:
            get_logger().bind()
            debug("debugtest")
            info("infotest")
            warning("warningtest")
            critical("criticaltest")
            error("errortest")

        log = LogAnalyzer(cap_logs, None, None, None)
        log.check_events_are(
            [
                "debugtest",
                "infotest",
                "warningtest",
                "criticaltest",
                "errortest",
            ]
        log = LogAnalyzer(cap_logs, None, None, None)
        log.check_events_are(
            [
                "debugtest",
                "infotest",
                "warningtest",
                "criticaltest",
                "errortest",
            ]
        )
        log.check_levels_are(["debug", "info", "warning", "critical", "error"])
        log.check_levels_are(["debug", "info", "warning", "critical", "error"])

    def test_successful_auth_logging(self) -> None:
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

        cap_logs = self._prune_permissions(cap_logs)

        # Since we do both a login and a logout, we get two different
        # POST events, so we need to override the path and status code
        # for the logout events.
        log = LogAnalyzer(cap_logs, "POST", "/api/auth/login/", 200)
        for index in [7, 8, 11, 12]:
            log.override_path(index, "/api/auth/logout/")
        for index in [11, 12]:
            log.override_status_code(index, 204)
        log.check_events_are(
        # Since we do both a login and a logout, we get two different
        # POST events, so we need to override the path and status code
        # for the logout events.
        log = LogAnalyzer(cap_logs, "POST", "/api/auth/login/", 200)
        for index in [7, 8, 11, 12]:
            log.override_path(index, "/api/auth/logout/")
        for index in [11, 12]:
            log.override_status_code(index, 204)
        log.check_events_are(
            [
                "request_started",
                "request",
                "created",
                "updated",
                "login",
                "response",
                "request_finished",
                "request_started",
                "request",
                "deleted",
                "logout",
                "response",
                "request_finished",
            ],
        )
        log.check_levels_are(
        log.check_levels_are(
            [
                "info",
                "info",
                "info",
                "info",
                "info",
                ["info", "warning", "critical", "error"],
                "info",
                "info",
                "info",
                "info",
                "info",
                "info",
                "info",
            ]
            ]
        )
        log.check_events()

        # Check that we're deleting the right token
        self.assertTrue(cap_logs[2]["id"] == cap_logs[9]["id"])
        # Check that we have the right users.
        self.assertTrue(cap_logs[4]["id"] == user.id == cap_logs[10]["id"])
        # Check that we have a token in the response.
        # Check that we have a token in the response.
        json_data = json.loads(cap_logs[5]["content"])
        self.assertIn("token", json_data)
        self.assert_is_iso_date(json_data["expiry"])

        user.delete()

    def test_unsuccessful_auth_logging(self) -> None:
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

        cap_logs = self._prune_permissions(cap_logs)

        log = LogAnalyzer(cap_logs, "POST", "/api/auth/login/", 401)
        log.check_events_are(
        log = LogAnalyzer(cap_logs, "POST", "/api/auth/login/", 401)
        log.check_events_are(
            [
                "request_started",
                "request",
                "failure",
                "response",
                "request_finished",
            ],
        )
        log.check_levels_are(
            [
                "info",
                "info",
                "error",
                ["warning", "critical", "error"],
                "info",
            ]
        )
        log.check_events()
        log.check_levels_are(
            [
                "info",
                "info",
                "error",
                ["warning", "critical", "error"],
                "info",
            ]
        )
        log.check_events()

        self.assertIsNone(cap_logs[2]["id"])
        json_data = json.loads(cap_logs[3]["content"])
        self.assertIn(json_data["detail"], "Invalid username/password.")

        user.delete()

    def test_run_time_ms_escalation(self) -> None:
        """Test run_time_ms escalation for logging levels."""
        middleware = LogHttpMiddleware(MagicMock())

        # mock the get_response method to return a response with a specified status code and delay
        def mock_get_response(_):
            return HttpResponse(status=200)

        middleware.get_response = mock_get_response

        # test the behavior of the logging system with different delays
        delay_responses: List[Tuple[float, str]] = [
            (0.1, "info"),
            (0.5, "info"),
            (1.0, "warning"),
            (2.0, "warning"),
            (5.0, "error"),
            (5.5, "error"),
        ]

        for delay, expected_level in delay_responses:
            with patch("time.time", side_effect=[0, delay]):
                with capture_logs() as cap_logs:
                    get_logger().bind()
                    request = HttpRequest()
                    request._body = b"Some request body"
                    request.user = User.objects.get(username="superuser")
                    middleware(request)
                    # cap_logs[0] is the request, cap_logs[1] is the response
                    self.assertEqual(cap_logs[1]["log_level"], expected_level)

    def test_return_500_error(self) -> None:
        """Test middleware returning 500 error."""
        middleware = LogHttpMiddleware(MagicMock())

        def mock_get_response(_):
            return HttpResponse(status=500)

        middleware.get_response = mock_get_response

        with capture_logs() as cap_logs:
            get_logger().bind()
            request = HttpRequest()
            request._read_started = False
            request._stream = io.BytesIO(b"request body")  # mock the _stream attribute
            request.user = User.objects.get(username="superuser")
            middleware(request)
            self.assertEqual(cap_logs[1]["status_code"], 500)

    def test_proxy_ip_in_logs(self) -> None:
        """Check that a proxy IP is logged."""

        def common_test(request: HttpRequest):
            middleware = LogHttpMiddleware(MagicMock())

            def mock_get_response(_):
                return HttpResponse(status=500)

            middleware.get_response = mock_get_response

            with capture_logs() as cap_logs:
                get_logger().bind()
                request._read_started = False
                request._stream = io.BytesIO(b"request body")
                request.user = User.objects.get(username="superuser")
                middleware(request)
                self.assertEqual(cap_logs[0]["proxy_ip"], "192.0.2.0")

        # META-based test
        request = HttpRequest()
        request.META["HTTP_X_FORWARDED_FOR"] = "192.0.2.0"  # set a proxy IP
        common_test(request)

        # headers-based test
        request = HttpRequest()
        request.headers = {
            "http-x-forwarded-for": "192.0.2.0",
            "x-correlation-id": "0123456789",
        }
        common_test(request)

    def test_binary_request_body(self) -> None:
        """Test logging of a request with a binary body."""
        middleware = LogHttpMiddleware(MagicMock())

        def mock_get_response(_):
            return HttpResponse(status=200)

        middleware.get_response = mock_get_response

        with capture_logs() as cap_logs:
            get_logger().bind()
            request = HttpRequest()
            request._read_started = False
            request.user = User.objects.get(username="superuser")

            # Mock a binary request body
            binary_body = b"\x80abc\x01\x02\x03\x04\x05"
            request._stream = io.BytesIO(binary_body)

            middleware(request)

            # Check that the body was logged as '<Binary Data>'
            self.assertEqual(cap_logs[0]["content"], "<Binary Data>")
