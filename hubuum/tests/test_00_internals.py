"""Test module: Users and Groups."""
from typing import List

import pytest
from rest_framework.exceptions import NotFound, ValidationError

from hubuum.exceptions import InvalidParam, MissingParam
from hubuum.log import RequestColorTracker, filter_sensitive_data
from hubuum.models.core import model_supports_attachments, model_supports_extensions
from hubuum.models.iam import (
    Namespace,
    User,
    namespace_operation_exists,
    namespace_operations,
)
from hubuum.models.resources import Host
from hubuum.tools import get_object
from hubuum.validators import (
    validate_model,
    validate_model_can_have_attachments,
    validate_model_can_have_extensions,
)

from .base import HubuumModelTestCase


class InternalsTestCase(HubuumModelTestCase):
    """Define the test suite for internal structures."""

    def test_user_get_auto_id(self):
        """Test that the user get_auto_id method works."""
        self.assertEqual(self.user.get_auto_id(), self.user.id)

    def test_namespace_operations(self):
        """Test that the namespaced operations are correct."""
        expected: List[str] = ["create", "read", "update", "delete", "namespace"]
        self.assertListEqual(expected, namespace_operations())
        fq_expected = [f"has_{x}" for x in expected]
        self.assertListEqual(fq_expected, namespace_operations(fully_qualified=True))

        for operation in expected:
            self.assertTrue(namespace_operation_exists(operation))

        for operation in fq_expected:
            self.assertTrue(namespace_operation_exists(operation, fully_qualified=True))

    def test_exception_missing_param(self):
        """Test the MissingParam exception."""
        # _create_object requires kwarg model.
        with pytest.raises(MissingParam):
            self._create_object()

        # _test_has_identical_values requires kwargs dictionary and object
        with pytest.raises(MissingParam):
            self._test_has_identical_values()
        with pytest.raises(MissingParam):
            self._test_has_identical_values(obj=self.user)
        with pytest.raises(MissingParam):
            self._test_has_identical_values(dictionary={})

    def test_get_object(self):
        """Test the get_object interface from tools."""
        self.assertTrue(isinstance(get_object(User, "test"), User))
        self.assertTrue(get_object(User, "doesnotexist", raise_exception=False) is None)
        with pytest.raises(NotFound):
            self.assertTrue(get_object(User, "doesnotexist"))

    def test_has_perm(self):
        """Test the internals of has_perm."""
        # These should never happen, but are handled.
        test = User.objects.get(username="test")
        self.assertFalse(test.has_perm("hubuum.read_namespace", None))
        with pytest.raises(MissingParam):
            test.has_perm("nosuchperm", None)
        with pytest.raises(MissingParam):
            test.has_perm("hubuum.x_y", None)
        with pytest.raises(MissingParam):
            test.has_perm("hubuum.nosuchperm_host", None)
        with pytest.raises(MissingParam):
            test.has_perm("hubuum.read_nosuchmodel", None)
        with pytest.raises(MissingParam):
            test.namespaced_can("nosuchperm", None)

        Namespace.objects.get_or_create(name="root")
        self.assertFalse(test.has_namespace("root"))
        with pytest.raises(NotFound):
            test.has_namespace("rootnotfound.no")
        with pytest.raises(NotFound):
            test.has_namespace("rootnotfound.no.reallyno")
        with pytest.raises(NotFound):
            test.has_namespace(12)

    def test_validate_model(self):
        """Test validate_model interface."""
        # Test that we require data["model"] to be a string
        with pytest.raises(ValidationError):
            validate_model({})

        with pytest.raises(ValidationError):
            validate_model({})

        # Test that when we have a string, we have a model with that name.
        with pytest.raises(ValidationError):
            validate_model("nosuchmodel")

        self.assertTrue(validate_model("host"))

    def test_extensions_validation_errors(self):
        """Test exceptions from the extensions."""
        # Test that extension support checking works.
        self.assertTrue(model_supports_extensions("Host"))
        self.assertTrue(model_supports_extensions(Host))

        # Test that when we have a string, and a model with the name, but it does
        # not support extensions.
        with pytest.raises(ValidationError):
            validate_model_can_have_extensions("user")

        with pytest.raises(ValidationError):
            validate_model_can_have_extensions("permission")

    def test_attachment_validation_errors(self):
        """Test exceptions from the attachments."""
        # Test that extension support checking works.
        self.assertTrue(model_supports_attachments("Host"))
        self.assertTrue(model_supports_attachments(Host))

        # Test that when we have a string, and a model with the name, but it does
        # not support attachments.
        with pytest.raises(ValidationError):
            validate_model_can_have_attachments("user")

        with pytest.raises(ValidationError):
            validate_model_can_have_attachments("permission")

    def test_filtering_of_sensitive_data(self):
        """Test that sensitive data is filtered from structlog records."""
        # create test data and the expected result
        test_data = [
            ['"token":"1234567890abcdef1234567890"', '"token":"123...890"'],
            [{"token": "1234567890abcdef1234567890"}, {"token": "123...890"}],
            ['"token":"1234567890"', '"token":"..."'],
            [{"token": "1234567890"}, {"token": "..."}],
            [
                {"content": '"token":"1234567890abcdef1234567890"'},
                {"content": '"token":"123...890"'},
            ],
        ]

        for data, expected in test_data:
            self.assertEqual(filter_sensitive_data(None, None, data), expected)

        with pytest.raises(InvalidParam):
            filter_sensitive_data(None, None, [])

        with pytest.raises(InvalidParam):
            filter_sensitive_data(None, None, Host)

    def test_request_color_generator(self):
        """Test that the request color generator works."""

    def test_request_color_tracker(self) -> None:
        """Test that the request color tracker works as expected."""

        color_tracker = RequestColorTracker()

        events = [
            {"request_id": "abc123", "event": "Event 1"},
            {"request_id": "def456", "event": "Event 2"},
            {"request_id": "abc123", "event": "Event 3"},
            {"request_id": "abc123", "event": "Event 3"},
            {"request_id": "ghi789", "event": "Event 3"},
        ]

        expected_colors = [
            color_tracker.COLORS[0],
            color_tracker.COLORS[1],
            color_tracker.COLORS[0],
            color_tracker.COLORS[0],
            color_tracker.COLORS[2],
        ]

        for i, event in enumerate(events):
            expected_color = expected_colors[i]
            colored_bubble = color_tracker._colorize(expected_color, " • ")
            expected_event = colored_bubble + event["event"]
            colored_event = color_tracker(None, None, event)

            self.assertEqual(colored_event["event"], expected_event)
