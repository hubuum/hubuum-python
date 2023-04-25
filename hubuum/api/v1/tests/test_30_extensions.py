"""Test hubuum extensions."""
from hubuum.models.core import ExtensionData
from hubuum.models.permissions import Namespace
from hubuum.models.resources import Host

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
            "url": "https://fleet.my.domain/api/v1/fleet/hosts/identifier/{name}",
            "header": "Authorization: Bearer sh...==",
        }
        self.extension_blob2 = {
            "namespace": self.namespace.id,
            "name": "ansible",
            "model": "host",
            "url": "https://ansible.data/{fqdn}",
            "header": "Authorization: Bearer sh...==",
            "require_interpolation": True,
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


class APIExtensionURLValidation(HubuumExtensionTestCase):
    """Test URL validation extensions."""

    def _make_extension_blob(self, url, model="host"):
        """Make an extension blob with the given URL."""
        return {
            "namespace": self.namespace.id,
            "name": "ansible",
            "model": model,
            "url": url,
            "header": "Authorization: Bearer sh...==",
        }

    def test_url_must_be_string(self):
        """Test that URL must be a string."""
        self.assert_post_and_400("/extensions/", self._make_extension_blob([1, 2]))
        self.assert_post_and_400(
            "/extensions/", self._make_extension_blob({"key": "value "})
        )
        self.assert_post(
            "/extensions/", self._make_extension_blob("https://www.foo.bar/{fqdn}")
        )

    def test_url_must_be_well_formed(self):
        """Test that URL is well-formed."""
        self.assert_post_and_400(
            "/extensions/", self._make_extension_blob("httg://www.foo.bar/{fqdn}")
        )
        self.assert_post_and_400(
            "/extensions/", self._make_extension_blob("http://foobar.d")
        )
        self.assert_post_and_400(
            "/extensions/", self._make_extension_blob("www.foo.bar/{fqdn}")
        )
        self.assert_post(
            "/extensions/", self._make_extension_blob("https://www.foo.bar/{fqdn}")
        )

    def test_url_interpolation(self):
        """Test that URL interpolates as required."""
        host = self.assert_post(
            "/extensions/",
            self._make_extension_blob("https://www.foo.bar/{fqdn}"),
        )
        # Field doesn't exist in the model
        self.assert_patch_and_400(
            f"/extensions/{host.data['id']}",
            {"url": "https://www.foo.bar/{has_create}"},
        )
        # Interpolation required, but we didn't provide one
        self.assert_patch_and_400(
            f"/extensions/{host.data['id']}",
            {"url": "https://www.foo.bar/nothing/"},
        )
        # Field exists, but model doesn't support extensions.
        self.assert_post_and_400(
            "/extensions/",
            self._make_extension_blob("https://www.foo.bar/{username}", model="user"),
        )
        # No interpolation required.
        self.assert_post_and_400(
            "/extensions/",
            self._make_extension_blob("https://www.foo.bar/no/interpolation"),
        )
        self.assert_post_and_400(
            "/extensions/",
            self._make_extension_blob("https://www.foo.bar/{fqdn}", model="user"),
        )
        self.assert_post_and_400(
            "/extensions/",
            self._make_extension_blob(
                "https://www.foo.bar/{fqdn}", model="nosuchmodel"
            ),
        )
        self.assert_post_and_400(
            "/extensions/",
            self._make_extension_blob("https://www.foo.bar/{fqdnasd}"),
        )


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
        # Test the __str__ method. Due to dependecies, it's easiest done here.
        self.assertEqual(str(exdid), str(ExtensionData.objects.get(id=exdid)))
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

        # Before we add the ansible extension itself, there is no such data entry.
        hblob = self.assert_get("/hosts/test")
        self.assertFalse("ansible" in hblob.data["extension_data"])

        # We add the ansible extension and dig around a bit.
        self.assert_post("/extensions/", self.extension_blob2)
        hblob = self.assert_get("/hosts/test")
        self.assertTrue(hblob.data["extension_data"]["fleet"]["key"] == newvalue)
        self.assertIsNone(hblob.data["extension_data"]["ansible"])
        self.assertEqual(hblob.data["extensions"], ["ansible", "fleet"])
        self.assertEqual(
            hblob.data["extension_urls"]["fleet"],
            f"https://fleet.my.domain/api/v1/fleet/hosts/identifier/{hblob.data['name']}",
        )
        hblob = self.assert_get("/hosts/test2")
        self.assertIsNone(hblob.data["extension_data"]["fleet"])
        self.assertIsNone(hblob.data["extension_data"]["ansible"])
