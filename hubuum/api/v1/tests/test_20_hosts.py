"""Test host object creation."""
from rest_framework.test import APIClient

from .base import HubuumAPITestCase


class APIHost(HubuumAPITestCase):
    """Test hosts."""

    def _create_host(
        self, hostname: str = "yes", namespace: str = "namespace1"
    ) -> None:
        """Create a default host (yes) in a namespace (namespace1) [as superuser]."""
        oldclient = self.client
        self.client = self.get_superuser_client()
        nsblob = self.assert_get(f"/iam/namespaces/{namespace}")
        self.assert_post(
            "/resources/hosts/", {"name": hostname, "namespace": nsblob.data["id"]}
        )
        self.client = oldclient

    def test_namespace_access_as_noone(self):
        """Test access to namespaces as a noone."""
        self._create_namespace()
        self._create_host()
        self.client = APIClient()
        self.assert_post_and_401("/resources/hosts/", {"name": "no"})
        self.assert_patch_and_401("/resources/hosts/yes", {"name": "maybe"})
        self.assert_get_and_401("/resources/hosts/yes")
        self.assert_get_and_401("/resources/hosts/no")
        self.assert_delete_and_401("/resources/hosts/yes")
        self.assert_get_and_401("/resources/hosts/")
        self.client = self.get_superuser_client()
        self.assert_delete("/iam/namespaces/namespace1")

    def test_field_validation(self):
        """Test that we can't write to read-only fields."""
        self._create_namespace()
        self._create_host()
        self.assert_patch_and_400("/resources/hosts/yes", {"created_at": "2022-01-01"})
        self.assert_patch_and_400("/resources/hosts/yes", {"nosuchkey": "2022-01-01"})

        # NOTICE: Comma, not colon. This leads to a set being serialized as a list...
        self.assert_patch_and_400("/resources/hosts/yes", {"not_a", "dict"})
        self.assert_delete("/iam/namespaces/namespace1")

    def test_host_listing(self):
        """Test that a user sees the correct number of hosts."""
        self._create_namespace("namespace1")
        self._create_host("one", "namespace1")
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/resources/hosts/", 0)
        self.grant("tmpgroup", "namespace1", ["has_read"])
        self.assert_get_elements("/resources/hosts/", 1)
        self._create_host("two", "namespace1")
        self.assert_get_elements("/resources/hosts/", 2)
        self._create_namespace("namespace2")
        self._create_host("three", "namespace2")
        self.assert_get_elements("/resources/hosts/", 2)

    def test_user_create_host(self):
        """Test user host creation."""
        self._create_namespace("namespace1")
        nsblob = self.assert_get("/iam/namespaces/namespace1")
        nsid = nsblob.data["id"]

        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/resources/hosts/", 0)
        self.assert_post_and_403(
            "/resources/hosts/", {"name": "yes", "namespace": nsid}
        )
        self.grant("tmpgroup", "namespace1", ["has_create", "has_read"])
        self.assert_post("/resources/hosts/", {"name": "yes", "namespace": nsid})
        self.client = self.get_superuser_client()
        self.assert_delete("/iam/namespaces/namespace1")

    def test_user_delete_host(self):
        """Test user host deletion."""
        self._create_namespace("namespace1")
        self._create_host("yes", "namespace1")

        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/resources/hosts/", 0)
        self.assert_delete_and_403("/resources/hosts/yes")
        self.grant("tmpgroup", "namespace1", ["has_create", "has_read", "has_delete"])
        self.assert_get_elements("/resources/hosts/", 1)
        self.assert_delete("/resources/hosts/yes")
        self.assert_get_elements("/resources/hosts/", 0)

        self.client = self.get_superuser_client()
        self.assert_delete("/iam/namespaces/namespace1")

    def test_user_patch_host(self):
        """Test user host patching."""
        self._create_namespace("namespace1")
        self._create_host("yes")
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_patch_and_403("/resources/hosts/yes", {"serial": 1})
        self.grant("tmpgroup", "namespace1", ["has_update", "has_read"])
        self.assert_patch("/resources/hosts/yes", {"serial": 1})
        self.client = self.get_superuser_client()
        self.assert_delete("/iam/namespaces/namespace1")
