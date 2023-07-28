"""Test internals."""

import os
import sys

import pytest
from django.http import HttpResponse
from rest_framework.test import APIClient

from hubuum.exceptions import MissingParam
from hubuum.tools import is_iso_date

from ..serializers import GroupSerializer
from .base import HubuumAPITestCase


class APITokenAuthenticationTestCase(HubuumAPITestCase):
    """Test various token authentication operations."""

    def test_different_clients(self):
        """Test various client setups."""
        self.assertIsInstance(self.get_superuser_client(), APIClient)
        self.assertIsInstance(self.get_staff_client(), APIClient)
        self.assertIsInstance(self.get_user_client(), APIClient)
        self.assertIsInstance(self.get_user_client(username="testuser"), APIClient)

    def test_get_token_client_without_group(self):
        """_get_token_client raises an exception if no group is passed along with a username."""
        with pytest.raises(MissingParam):
            self._get_token_client(
                username="test_exceptions", superuser=False, staff=False
            )


class InternalTestAPITestCase(HubuumAPITestCase):
    """Test internal test utilities."""

    def test_create_path(self):
        """Test that _create_path generates correct paths."""
        target = "/api/v1/target"
        self.assertEqual(self._create_path("/api/v1/target"), target)
        self.assertEqual(self._create_path("/target"), target)
        self.assertEqual(self._create_path("target"), target)

    def test_is_iso_date(self):
        """Test that _is_iso_date correctly identifies ISO dates."""
        self.assertTrue(is_iso_date("2020-01-01T00:00:00Z"))
        self.assertFalse(is_iso_date("Not a date"))
        self.assert_is_iso_date("2020-01-01T00:00:00Z")
        self.assert_is_iso_date("2023-04-14T07:11:54.866956Z")

    def test_assert_list_contains(self):
        """Test that _assert_list_contains correctly identifies list contents."""
        self.assert_list_contains(["a", "b", "c"], lambda x: x == "b")

        with pytest.raises(AssertionError):
            self.assert_list_contains(["a", "b", "c"], lambda x: x == "d")

    def test_db_introspection(self):
        """Test that we have some semblance of consistency in our DB introspection."""
        self.assertTrue(
            True in [self.db_engine_is_postgresql(), self.db_engine_is_sqlite()]
        )
        self.assertFalse(self.db_engine_is_postgresql() and self.db_engine_is_sqlite())

    def test_serializer_without_request(self):
        """Test that we can instantiate a serializer without a request."""
        # This happens when openAPI is parsing the serializers, for some reason.
        serializer = GroupSerializer(data={"name": "group"}, context={"request": None})
        self.assertIsNone(serializer.context["request"])

    def test_assert_with_debug_message(self):
        """Test that asserts with unexpected status values fail."""
        response = HttpResponse(status=404, content="Not found")
        response.request = {
            "PATH_INFO": "/api/v1/notfound",
            "method": "GET",
            "QUERY_STRING": "",
        }
        response.data = {"detail": "Not found"}

        # Disable stdout to avoid polluting the test output with the debug message.
        with open(os.devnull, "w", encoding="utf-8") as null_stdout:
            sys.stdout = null_stdout
            with pytest.raises(AssertionError):
                self._assert_status_and_debug(response, 200)
            sys.stdout = sys.__stdout__
