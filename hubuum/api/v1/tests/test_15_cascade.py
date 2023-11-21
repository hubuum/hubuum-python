"""Test cascading effects on models."""
from hubuum.models.iam import Namespace

from .base import HubuumAPITestCase
from .helpers.populators import BasePopulator


class APICascade(HubuumAPITestCase, BasePopulator):
    """Test cascading effects on models."""

    def test_cascading_namespaces(self):
        """Test what happens when a namespace goes away."""
        self.client = self.get_superuser_client()
        self.assert_post("/iam/namespaces/", {"name": "yes"})
        self.assert_get("/iam/namespaces/yes")
        ns = Namespace.objects.get(name="yes")
        host_class = self.create_class_direct("Host", namespace=ns)
        self.create_object_direct(host_class, namespace=ns, name="host1")
        self.create_object_direct(host_class, namespace=ns, name="host2")
        self.assert_get_elements("/dynamic/Host/", 2)
        self.assert_get("/dynamic/Host/host1")
        self.assert_delete("/iam/namespaces/yes")
        self.assert_get_elements("/dynamic/Host/", 0)
        host_class.delete()

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
