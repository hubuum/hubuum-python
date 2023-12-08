"""Test the meta interface."""

import sys

import django
import rest_framework
from rest_framework.test import APIClient

from hubuum import __version__, module_versions

from .base import HubuumAPITestCase


class TestVersion(HubuumAPITestCase):
    """Test the version endpoint."""

    def test_version(self):
        """Test the version endpoint."""
        response = self.client.get("/api/v1/.meta/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), __version__)

    def test_version_as_normal_user(self):
        """Test the version endpoint as a normal user."""
        client = self.get_user_client()
        response = client.get("/api/v1/.meta/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), __version__)

    def test_version_no_auth(self):
        """Test the version endpoint without auth."""
        client = APIClient()
        response = client.get("/api/v1/.meta/version")
        self.assertEqual(response.status_code, 401)

    def test_runtimes(self):
        """Test the runtimes endpoint."""
        response = self.client.get("/api/v1/.meta/runtimes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["python"], sys.version)
        self.assertEqual(response.json()["django"], django.get_version())
        self.assertEqual(response.json()["rest_framework"], rest_framework.VERSION)
        self.assertEqual(response.json()["django-rest-knox"], module_versions["django-rest-knox"])

    def test_runtimes_no_auth(self):
        """Test the runtimes endpoint without auth."""
        client = APIClient()
        response = client.get("/api/v1/.meta/runtimes")
        self.assertEqual(response.status_code, 401)

    def test_runtimes_normal_user(self):
        """Test the runtimes endpoint as a normal user."""
        client = self.get_user_client()
        response = client.get("/api/v1/.meta/runtimes")
        self.assertEqual(response.status_code, 403)

    def test_debug(self):
        """Test the debug endpoint."""
        response = self.client.get("/api/v1/.meta/debug")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["module_versions"], module_versions)
        self.assertIn("config", response.json())

    def test_debug_no_auth(self):
        """Test the debug endpoint without auth."""
        client = APIClient()
        response = client.get("/api/v1/.meta/debug")
        self.assertEqual(response.status_code, 401)

    def test_debug_normal_user(self):
        """Test the debug endpoint as a normal user."""
        client = self.get_user_client()
        response = client.get("/api/v1/.meta/debug")
        self.assertEqual(response.status_code, 403)
