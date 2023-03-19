"""Test hubuum extensions."""
from hubuum.models import Host, Namespace

from .base import HubuumAPITestCase


class HubuumExtensionTestCase(HubuumAPITestCase):
    """Base class for testing Hubuum Extensions."""

    def setUp(self):
        """Set up the test environment for the class."""
        self.client = self.get_superuser_client()
        self.namespace, _ = Namespace.objects.get_or_create(name="test")
        self.extension_blob = {
            "namespace": self.namespace.id,
            "name": "fleet",
            "model": "host",
            "url": "https://fleet.my.domain/api/v1/fleet/hosts/identifier/{fqdn}",
            "header": "Authorization: Bearer sh...==",
        }
        self.extension_blob2 = {
            "namespace": self.namespace.id,
            "name": "ansible",
            "model": "host",
            "url": "https://ansible.data/{fqdn}",
            "header": "Authorization: Bearer sh...==",
        }
        self.host, _ = Host.objects.get_or_create(name="test", namespace=self.namespace)
        self.host2, _ = Host.objects.get_or_create(
            name="test2", namespace=self.namespace
        )

    def tearDown(self) -> None:
        """Tear down the test environment for the class."""
        self.namespace.delete()
        return super().tearDown()

    def _extension_data_blob(self, extension_id, value="value", content_type="host"):
        """Create an extension data blob."""
        return {
            "namespace": self.namespace.id,
            "extension": extension_id,
            "content_type": content_type,
            "object_id": self.host.id,
            "json_data": {"key": value, "listkey": [1, 2, 3]},
        }


class APIExtension(HubuumExtensionTestCase):
    """Test extensions."""

    def test_creating_extension(self):
        """Create extension."""
        exblob = self.assert_post("/extensions/", self.extension_blob)
        exid = exblob.data["id"]
        self.assert_get_elements("/extensions/", 1)
        self.assert_get(f"/extensions/{exid}")
        self.assert_get("/extensions/fleet")
        self.assert_delete("/extensions/fleet")


class APIExtensionsData(HubuumExtensionTestCase):
    """Test extension data."""

    def test_create_and_update_extension_data(self):
        """Create and update extension data."""
        exblob = self.assert_post("/extensions/", self.extension_blob)
        extension_id = exblob.data["id"]

        exdblob = self.assert_post(
            "/extension_data/", self._extension_data_blob(extension_id)
        )
        exdid = exdblob.data["id"]
        self.assert_get(f"/extension_data/{exdid}")
        self.assertTrue(exdblob.data["json_data"]["key"] == "value")

        # Updating by using post
        newvalue = "newvalue"
        self.assert_post(
            "/extension_data/",
            self._extension_data_blob(extension_id, value=newvalue),
        )
        exdblob = self.assert_get(f"/extension_data/{exdid}")
        self.assertTrue(exdblob.data["json_data"]["key"] == newvalue)

        # Posting with the wrong content_type (user vs host)
        exdblob = self.assert_post_and_400(
            "/extension_data/",
            self._extension_data_blob(extension_id, content_type="user"),
        )
        exdblob = self.assert_post("/extensions/", self.extension_blob2)

        hblob = self.assert_get("/hosts/test")
        self.assertTrue(hblob.data["extensions"]["fleet"]["key"] == newvalue)
        self.assertTrue(hblob.data["extensions"]["ansible"] is None)
        hblob = self.assert_get("/hosts/test2")
        self.assertTrue(hblob.data["extensions"]["fleet"] is None)
        self.assertTrue(hblob.data["extensions"]["ansible"] is None)
