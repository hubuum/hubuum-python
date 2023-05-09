"""Test cascading effects on models."""
from .base import HubuumAPITestCase


class APICascade(HubuumAPITestCase):
    """Test cascading effects on models."""

    def test_cascading_namespaces(self):
        """Test what happens when a namespace goes away."""
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})
        nsblob = self.assert_get("/iam/namespaces/yes")
        self.assert_post(
            "/resources/hosts/", {"name": "host1", "namespace": nsblob.data["id"]}
        )
        self.assert_post(
            "/resources/hosts/", {"name": "host2", "namespace": nsblob.data["id"]}
        )
        self.assert_get_elements("/resources/hosts/", 2)
        self.assert_get("/resources/hosts/host1")
        self.assert_delete("/iam/namespaces/yes")
        self.assert_get_elements("/resources/hosts/", 0)

    def test_cascading_permissions(self):
        """Test what happens when a namespace goes away."""
        self.assert_post("/iam/namespaces/", {"name": "yes"})
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.grant("tmpgroup", "yes", ["has_read"])
        self.assert_get_elements("/iam/permissions/", 1)
        self.client = self.get_superuser_client()
        self.assert_delete("/iam/groups/tmpgroup")
        self.assert_get_elements("/iam/permissions/", 0)

        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/iam/permissions/", 0)
        self.grant("tmpgroup", "yes", ["has_read"])
        self.assert_get_elements("/iam/permissions/", 1)
        self.client = self.get_superuser_client()
        self.assert_delete("/iam/namespaces/yes")
        self.assert_get_elements("/iam/permissions/", 0)

        self.assert_post("/iam/namespaces/", {"name": "yes"})
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/iam/permissions/", 0)
        self.grant("tmpgroup", "yes", ["has_read"])
        self.assert_get_elements("/iam/permissions/", 1)
        perms = self.assert_get("/iam/permissions/")
        pid = perms.data[0]["id"]
        self.client = self.get_superuser_client()
        self.assert_delete(f"/iam/permissions/{pid}")
        self.assert_get_elements("/iam/permissions/", 0)
        self.assert_get_elements("/iam/namespaces/", 1)
        self.assert_get_elements("/iam/groups/", 1)

    def test_cascading_groups(self):
        """Test cascading groups."""
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})
        self.grant("tmpgroup", "yes", ["has_read"])
        self.assert_get_elements("/iam/permissions/", 1)
        self.assert_get_elements("/iam/namespaces/", 1)
        self.assert_get_elements("/iam/groups/", 1)

        self.assert_delete("/iam/groups/tmpgroup")
        self.assert_get_elements("/iam/permissions/", 0)
        self.assert_get_elements("/iam/namespaces/", 1)
        self.assert_get_elements("/iam/groups/", 0)
