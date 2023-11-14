"""Test host object creation."""

from hubuum.api.v1.tests.helpers.populators import APIv1Classes, APIv1Objects
from hubuum.models.iam import Namespace


class APIHostClean(APIv1Classes):
    """Test host class witout any objects."""

    def _create_host(self, name: str = "yes", namespace: Namespace = None):
        """Create a host."""
        host_class = self.get_class_from_cache("Host")
        ns = namespace or self.namespace
        return self.create_object_direct(
            dynamic_class=host_class, namespace=ns, name=name
        )

    def test_host_listing_clean(self):
        """Test that a user sees the correct number of hosts."""
        host_class = self.get_class_from_cache("Host")
        ns1 = self._create_namespace("namespace_1")
        self.create_object_direct(dynamic_class=host_class, namespace=ns1, name="one")
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/dynamic/Host/", 0)
        self.grant("tmpgroup", ns1.name, ["has_read"])
        self.assert_get_elements("/dynamic/Host/", 1)
        self.create_object_direct(dynamic_class=host_class, namespace=ns1, name="two")
        self.assert_get_elements("/dynamic/Host/", 2)
        ns2 = self._create_namespace("namespace_2")
        self.create_object_direct(dynamic_class=host_class, namespace=ns2, name="three")
        self.assert_get_elements("/dynamic/Host/", 2)

        for ns in [ns1, ns2]:
            ns.delete()

    def test_user_create_host(self):
        """Test user host creation."""
        ns = self.namespace
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/dynamic/Host/", 0)
        self.assert_post_and_403("/dynamic/Host/", {"name": "yes", "namespace": ns.id})
        self.grant("tmpgroup", ns.name, ["has_create", "has_read"])
        self.assert_post(
            "/dynamic/Host/", {"name": "yes", "namespace": ns.id, "json_data": {}}
        )
        self.assert_get("/dynamic/Host/yes")

    def test_user_delete_host(self):
        """Test user host deletion."""
        self._create_host("one")
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/dynamic/Host/", 0)
        self.assert_delete_and_403("/dynamic/Host/one")
        self.grant(
            "tmpgroup", self.namespace.name, ["has_create", "has_read", "has_delete"]
        )
        self.assert_get_elements("/dynamic/Host/", 1)
        self.assert_delete("/dynamic/Host/one")
        self.assert_get_and_404("/dynamic/Host/one")
        self.assert_get_elements("/dynamic/Host/", 0)

    def test_user_patch_host(self):
        """Test user host patching."""
        self._create_host("one")
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_patch_and_403("/dynamic/Host/one", {"name": "foo"})
        self.grant("tmpgroup", self.namespace.name, ["has_write", "has_read"])
        self.assert_patch_and_403("/dynamic/Host/one", {"name": "foo"})
        self.grant("tmpgroup", self.namespace.name, ["has_update", "has_read"])
        self.assert_patch("/dynamic/Host/one", {"name": "foo"})
        self.assert_get("/dynamic/Host/foo")
        self.client = self.get_superuser_client()


class APIHost(APIv1Objects):
    """Test hosts."""

    def test_host_listing_populated(self):
        """Test that a user sees the correct number of hosts."""
        host_class = self.get_class_from_cache("Host")
        ns1 = self.namespace
        self.client = self.get_user_client(username="tmp", groupname="tmpgroup")
        self.assert_get_elements("/dynamic/Host/", 0)
        self.grant("tmpgroup", ns1.name, ["has_read"])
        self.assert_get_elements("/dynamic/Host/", 3)
        self.create_object_direct(dynamic_class=host_class, namespace=ns1, name="one")
        self.assert_get_elements("/dynamic/Host/", 4)
        ns2 = self.namespaces[1]
        self.create_object_direct(dynamic_class=host_class, namespace=ns2, name="two")
        self.assert_get_elements("/dynamic/Host/", 4)

    def test_field_validation(self):
        """Test that we can't write to read-only fields."""
        self.assert_patch_and_400("/dynamic/Host/host1", {"created_at": "2022-01-01"})
        self.assert_patch_and_400("/dynamic/Host/host1", {"nosuchkey": "2022-01-01"})

        # NOTICE: Comma, not colon. This leads to a set being serialized as a list...
        self.assert_patch_and_400("/dynamic/Host/host1", {"not_a", "dict"})

    # Create hosts in different namespaces and ensure that we see the appropriate number of hosts
    # in each namespace. For cleanup, we delete the namespaces and expect the hosts to be deleted
    # as the deletion cascades.
