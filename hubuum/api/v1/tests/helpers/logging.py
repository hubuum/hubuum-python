"""Analyzes log entries captured during testing."""

import json
from typing import Any, Callable, Dict, List

from dateutil.parser import parse
from django.db import models
from structlog.types import EventDict

from hubuum.tools import get_model


class LogAnalyzer:
    """A class used to validate log entries captured during testing.

    :param cap_logs: The captured log entries.
    :type cap_logs: List[EventDict]
    :param expected_method: The expected HTTP method.
    :type expected_method: str
    :param expected_path: The expected request path.
    :type expected_path: str
    """

    DATEFIELDS = ["created_at", "updated_at", "registration_date"]
    ALLOWED_MISSING_FROM_LOG = ["user"]
    ALLOWED_MISSING_FROM_EXPECTED = ["model", "id"]

    def __init__(
        self,
        cap_logs: List[EventDict],
        expected_method: str,
        expected_path: str,
        expected_status_code: int,
        expected_status_label: str = None,
    ):
        """Initialize the class.

        param cap_logs: The captured log entries.
        type cap_logs: List[EventDict]
        param expected_method: The expected HTTP method.
        type expected_method: str
        param expected_path: The expected request path.
        type expected_path: str
        param expected_status_code: The expected status code.
        type expected_status_code: int
        param expected_status_label: The expected status label.
        type expected_status_label: str
        """
        self.cap_logs = cap_logs
        self.expected_method = expected_method
        self.expected_path = expected_path
        self.expected_status_code = expected_status_code
        self.expected_status_label = expected_status_label

        self.expected_response_content = None
        self.expected_response_model = None
        self.expected_response_model_string = ""
        self.expected_user = None
        self.expected_instance_id = None

        self._override_path: Dict[str, str] = {}
        self._override_status_code: Dict[str, int] = {}

        self.event_to_check_method: Dict[str, Callable[[int], None]] = {
            "request_started": self.request_started,
            "request": self.request,
            "response": self.response,
            "request_finished": self.request_finished,
            "has_perm": self.has_perm,
            "has_perm_n": self.has_perm_n,
            "created": self.created,
            "updated": self.updated,
            "deleted": self.deleted,
            "login": self.login,
            "logout": self.logout,
            "failure": self.failure,
            "m_get_object": self.m_get_object,
        }

    #    def dummy(self, index: int) -> None:
    #        """Perform a no-operation test."""
    #        log = self.cap_logs[index]
    #        olog = self._order_keys(log)
    #        print(f"{log['event']} ({len(log)} entries}: {olog}")

    def override_path(self, index: int, path: str) -> None:
        """Override the default path."""
        self._override_path[index] = path

    def override_status_code(self, index: int, status_code: int) -> None:
        """Override the default status code."""
        self._override_status_code[index] = status_code

    def get_path(self, index: int) -> str:
        """Get the default path or the indexed override."""
        return self._override_path.get(index, self.expected_path)

    def get_status_code(self, index: int) -> int:
        """Get the default status code or the indexed override."""
        return self._override_status_code.get(index, self.expected_status_code)

    def show(self) -> None:  # pragma: no cover
        """Print expectations and the captures logs."""
        print("Expectations:")
        print(f"  Method: {self.expected_method}")
        print(f"  Path: {self.expected_path}")
        print(f"  Status code: {self.expected_status_code}")
        if self.expected_status_label:
            print(f"  Status label: {self.expected_status_label}")
        if self.expected_response_content:
            print(f"  Response content: {self.expected_response_content}")
        if self.expected_response_model:
            print(f"  Response model: {self.expected_response_model}")
        if self.expected_user:
            print(f"  User: {self.expected_user}")
        if self.expected_instance_id:
            print(f"  Instance: {self.expected_instance_id}")

        for i, log in enumerate(self.cap_logs):
            olog = self._order_keys(log)
            print(f"Log {i}: {olog}")

    def set_user(self, user: str) -> None:
        """Set the expected user that shows up in the logs."""
        self.expected_user = user

    def set_instance_id(self, instance_id: str) -> None:
        """Set the expected instance ID that shows up in the logs."""
        self.expected_instance_id = instance_id

    def set_response_content(
        self, content: List[Dict[str, Any]], model: models.Model = ""
    ) -> None:
        """Set the expected response content.

        :param model: The model class.
        :type model: Model
        :param content: The expected response content.
        :type content: List[Dict[str, Any]]

        """
        self.expected_response_model_string = model
        if model:
            model = get_model(model)
            assert issubclass(model, models.Model), "model must be a Django model"

        self.expected_response_model = model
        self.expected_response_content = content

    def get_log(self, index: int) -> EventDict:
        """Get a log entry from cap_logs."""
        return self.cap_logs[index]

    def entry_count_equals(self, expected_entries: int) -> None:
        """Assert that the number of log entries matches the expected count.

        :param expected_entries: The expected count of log entries.
        :type expected_entries: int
        """
        assert (
            len(self.cap_logs) == expected_entries
        ), f"Expected {expected_entries} log entries, got {len(self.cap_logs)}"

    def check_events_are(self, expected_events: List[str]) -> None:
        """Assert that the log entries match the expected event types."""
        for index, expected_event in enumerate(expected_events):
            # expected_event may be a list of events
            log = self.get_log(index)
            assert (
                log["event"] == expected_event
            ), f"Expected event(s) {expected_event} got {log['event']} at index {index}"
        self.entry_count_equals(len(expected_events))

    def check_levels_are(self, expected_levels: List[str]) -> None:
        """Assert that the log entries match the expected log levels."""
        for index, expected_level in enumerate(expected_levels):
            log = self.get_log(index)
            if not isinstance(expected_level, list):
                expected_level = [expected_level]

            assert (
                log["log_level"] in expected_level
            ), f"Expected levels(s) {expected_level} got {log['log_level']} at index {index}"
        self.entry_count_equals(len(expected_levels))

    def check_event(self, index: int) -> None:
        """Check a specific log entry based on its event type.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        event_type = self.cap_logs[index]["event"]
        check_method = self.event_to_check_method.get(event_type)
        assert check_method, f"No check method for event type '{event_type}'"
        check_method(index)

    # Event check methods

    def request_started(self, index: int) -> None:
        """Assert that a specific log entry is a 'request_started' event with correct details.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "request_started",
            "request": f"{self.expected_method} {self.get_path(index)}",
        }

        self._check_log_entry_count(log, 4)
        self._check_log_values(log, expected_values)

    def request_finished(self, index: int) -> None:
        """Assert that a specific log entry is a 'request_finished' event with correct details.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "request_finished",
            "request": f"{self.expected_method} {self.get_path(index)}",
            "code": self.get_status_code(index),
        }

        self._check_log_entry_count(log, 4)
        self._check_log_values(log, expected_values)

    def request(self, index: int) -> None:
        """Assert that a specific log entry is a 'request' event with correct details.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "request",
            "method": self.expected_method,
            "path": self.get_path(index),
        }

        self._check_log_entry_count(log, 8)
        self._check_log_values(log, expected_values)

    def response(self, index: int) -> None:
        """Assert that a specific log entry is a 'response' event and its details are correct.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "response",
            "method": self.expected_method,
            "path": self.get_path(index),
            "status_code": self.get_status_code(index),
        }

        if self.expected_status_label:
            expected_values["status_label"] = self.expected_status_label

        ignored_keys = ["slow_response", "very_slow_response"]
        expected_count = 11 if any(key in log for key in ignored_keys) else 9

        self._check_log_entry_count(log, expected_count)
        self._check_log_values(log, expected_values)

        self._check_response_content(log["content"])

    def has_perm_n(self, index: int) -> None:
        """Assert that a specific log entry is "has_perm_n" and its details are correct.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "has_perm_n",
            "method": self.expected_method,
        }

        self._check_log_values(log, expected_values)

    def has_perm(self, index: int) -> None:
        """Assert that a specific log entry is "has_perm" and its details are correct.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "has_perm",
        }

        self._check_log_values(log, expected_values)

    def created(self, index: int) -> None:
        """Assert that a specific log entry is "created" and its details are correct.

        :param index: The index of the log entry in cap_logs.
        :type index: int
        """
        log = self.cap_logs[index]
        expected_values = {
            "event": "created",
            "model": self.expected_response_model_string,
        }

        if self.expected_instance_id:
            expected_values["id"] = self.expected_instance_id

        if self.expected_user:
            expected_values["user"] = self.expected_user

        log_count = 5
        # AuthToken removes _str from the logs, to avoid leaking the token
        if log["model"] == "AuthToken":
            log_count = 4
        # HubuumObject logs has two extra fields (_class_id and _class_name)
        elif log["model"] == "HubuumObject":
            log_count = 7

        self._check_log_entry_count(log, log_count)
        self._check_log_values(log, expected_values)

    def updated(self, index: int) -> None:
        """Check updated entries."""
        log = self.cap_logs[index]
        expected_values = {
            "event": "updated",
            "model": self.expected_response_model_string,
        }

        self._check_log_entry_count(log, 5)
        self._check_log_values(log, expected_values)

    def login(self, index: int) -> None:
        """Check login entries."""
        log = self.cap_logs[index]
        expected_values = {
            "event": "login",
        }

        self._check_log_entry_count(log, 3)
        self._check_log_values(log, expected_values)

    def deleted(self, index: int) -> None:
        """Check deleted entries."""
        log = self.cap_logs[index]
        expected_values = {
            "event": "deleted",
            "model": self.expected_response_model_string,
            "id": self.expected_instance_id,
        }

        self._check_log_entry_count(log, 4)
        self._check_log_values(log, expected_values)

    def logout(self, index: int) -> None:
        """Check logout entries."""
        log = self.cap_logs[index]
        expected_values = {
            "event": "logout",
        }

        self._check_log_entry_count(log, 3)
        self._check_log_values(log, expected_values)

    def m_get_object(self, index: int) -> None:
        """Check m_get_object entries."""
        log = self.cap_logs[index]
        expected_values = {
            "event": "m_get_object",
            "log_level": "debug",
        }

        self._check_log_entry_count(log, 6)
        self._check_log_values(log, expected_values)

    def failure(self, index: int) -> None:
        """Check failure entries."""
        log = self.cap_logs[index]
        expected_values = {
            "event": "failure",
        }

        self._check_log_entry_count(log, 3)
        self._check_log_values(log, expected_values)

    def check_events(self) -> None:
        """Check all log entries in cap_logs."""
        for index in range(len(self.cap_logs)):
            self.check_event(index)

    def _check_response_content(self, content: str) -> None:
        """Check the response content against the expected response content and model."""
        if len(content) == 0:
            return
        content = json.loads(content)
        content = [content] if not isinstance(content, list) else content

        if self.expected_response_content:
            self._check_content_equals_expected(content)

        if self.expected_response_model:
            self._check_content_against_model(content)

    def _check_content_equals_expected(self, content: List[Dict[str, Any]]) -> None:
        """Check the response content against the expected response content."""
        for content_item, expected_item in zip(content, self.expected_response_content):
            self._check_content_keys_and_values(content_item, expected_item)

    def _check_content_keys_and_values(
        self, content_item: Dict[str, Any], expected_item: Dict[str, Any]
    ) -> None:
        """Check that the keys and values in the response content are as expected."""
        for key, value in expected_item.items():
            assert key in content_item, f'Key "{key}" not found in content'
            assert content_item[key] == value, f'Content value mismatch for key "{key}"'

    def _check_instance_exists(self, obj_data: Dict[str, Any]) -> Any:
        """Check if a single instance exists based on provided data."""
        instances = self.expected_response_model.objects.filter(**obj_data)

        if len(instances) != 1:  # pragma: no cover
            raise AssertionError(
                f"{obj_data} gave multiple instances of {self.expected_response_model}"
            )

        return instances[0]

    def _validate_response_content(
        self, instance: Any, obj_data: Dict[str, Any]
    ) -> None:
        """Validate if a model instance matches the response content."""
        for key, value in obj_data.items():
            instance_value = getattr(instance, key)

            # Handle date fields separately
            if key in self.DATEFIELDS:
                assert instance_value == parse(
                    value
                ), f'Value mismatch on "{key}", expected "{value}", got "{instance_value}"'
            elif key == "namespace":
                assert (
                    instance_value.id == value
                ), f'Value mismatch on "{key}", expected "{value}", got "{instance_value.id}"'
            else:
                assert (
                    instance_value == value
                ), f'Value mismatch on "{key}", expected "{value}", got "{instance_value}"'

    def _check_content_against_model(self, content: List[Dict[str, Any]]) -> None:
        """Check the response content against the expected response model."""
        for obj_data in content:
            instance = self._check_instance_exists(obj_data)
            self._validate_response_content(instance, obj_data)

    def _order_keys(self, log: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        """Orders the keys of a given dictionary.

        The key 'event' comes first, followed by 'log_level',
        and then the rest of the keys alphabetically.

        :param log: The dictionary to order.
        :type log: dict
        :return: The ordered dictionary.
        :rtype: dict
        """
        ordered_keys = ["event", "log_level"] + sorted(
            [k for k in log.keys() if k not in ["event", "log_level"]]
        )
        return {k: log[k] for k in ordered_keys}

    def _check_log_values(
        self, log: EventDict, expected_values: Dict[str, Any]
    ) -> None:
        """Check if the values in a log match the expected values.

        :param log: The log entry to check.
        :type log: EventDict
        :param expected_values: The expected values.
        :type expected_values: Dict[str, Any]
        """
        for key, expected in expected_values.items():
            if key in self.ALLOWED_MISSING_FROM_LOG and key not in log:
                continue
            elif key in self.ALLOWED_MISSING_FROM_EXPECTED and key in log:
                continue

            assert log[key] == expected, f"{key}: expected {expected}, got {log[key]}"

    def _check_log_entry_count(self, log: EventDict, count: int) -> None:
        """Check if the log entry count matches the expected count.

        :param log: The log entry to check.
        :type log: EventDict
        :param count: The expected count.
        :type count: int
        """
        assert len(log) == count, f"Expected {count} log entries, got {len(log)}"
