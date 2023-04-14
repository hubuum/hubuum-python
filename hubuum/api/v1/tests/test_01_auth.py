"""Test authentication."""

from datetime import timedelta
from unittest import mock

from knox.auth import AuthToken
from rest_framework.test import APIClient

from .base import HubuumAPITestCase


class APITokenAuthenticationTestCase(HubuumAPITestCase):
    """Test various token authentication operations."""

    def test_redirect(self):
        """Test redirects of incomplete URLs."""
        self.client = self.get_superuser_client()
        self.assert_get_and_301("/users")
        self.assert_get_and_301("/hosts")

    def test_user_access_without_authentication(self):
        """Test unauthenticated user access."""
        self.client = APIClient()
        self.assert_get_and_401("/users/")

    def test_logout(self):
        """Test authenticated logout."""
        self.assert_get("/hosts/")
        # TODO: #17 Note that logout returns 200 in normal django context,
        self.assert_post_and_204("/api/auth/logout/")
        self.assert_get_and_401("/hosts/")

    def test_logout_without_authentication(self):
        """Test unauthenticated logout."""
        self.client = APIClient()
        self.assert_post_and_401("/api/auth/logout/")

    def test_force_expire(self):
        """Test using a forcibly expired token."""
        self.assert_get("/hosts/")
        token = AuthToken.objects.get(user=self.user)
        minute_after_expiry = token.expiry + timedelta(minutes=1)
        with mock.patch("django.utils.timezone.now") as mock_future:
            mock_future.return_value = minute_after_expiry
            self.assert_get_and_401("/hosts/")

    def test_is_active_false(self):
        """Test using an inactive user."""
        self.assert_get("/hosts/")
        self.user.is_active = False
        self.user.save()
        self.assert_get_and_401("/hosts/")

    def test_is_deleted(self):
        """Test using a deleted user."""
        self.assert_get("/hosts/")
        self.user.delete()
        self.assert_get_and_401("/hosts/")

    def test_login_with_invalid_credentials(self):
        """Test logging in with invalid credentials."""
        self.client = APIClient()
        # Using wrong credentials should result in a 401 unauthorized
        self.assert_post_and_401(
            "/api/auth/login/", {"username": "someone", "password": "incorrect"}
        )
        # TODO: #16 This returns 401, we should check inputs in the login view.
        #        """ Incorrect or missing arguments should still return 400 bad request """
        #        self.assert_post_and_400(
        #            "/api/auth/logout/", {"who": "someone", "why": "because"}
        #        )
        #        self.assert_post_and_400("/api/auth/login/", {})
