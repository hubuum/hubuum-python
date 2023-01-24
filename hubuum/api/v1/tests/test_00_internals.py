"""Test internals."""

import pytest
from rest_framework.test import APIClient

from hubuum.exceptions import MissingParam

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

    def test_create_path(self):
        """Test that _create_path generates correct paths."""
        target = "/api/v1/target"
        self.assertEqual(self._create_path("/api/v1/target"), target)
        self.assertEqual(self._create_path("/target"), target)
        self.assertEqual(self._create_path("target"), target)
