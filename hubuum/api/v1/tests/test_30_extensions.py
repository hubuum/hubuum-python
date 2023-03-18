"""Test hubuum extensions."""
from .base import HubuumAPITestCase


class APIExtension(HubuumAPITestCase):
    """Test extensions."""

    def test_creating_extension(self):
        """Create extension."""
        self.get_superuser_client()
        nsblob = self.assert_post("/namespaces/", {"name": "test"})
        exblob = self.assert_post(
            "/extensions/",
            {
                "namespace": nsblob.data["id"],
                "name": "fleet",
                "model": "host",
                "url": "https://fleet.my.domain/api/v1/fleet/hosts/identifier/{fqdn}",
                "header": "Authorization: Bearer sh...==",
            },
        )
        exid = exblob.data["id"]
        self.assert_get_elements("/extensions/", 1)
        self.assert_get(f"/extensions/{exid}")
        self.assert_get("/extensions/fleet")
        self.assert_delete("/extensions/fleet")
        self.assert_delete("/namespaces/test")


class APIExtensionsData(HubuumAPITestCase):
    """Test extension data."""

    def test_create_and_update_extension_data(self):
        """Create and update extension data."""
        self.get_superuser_client()
        nsblob = self.assert_post("/namespaces/", {"name": "test"})
        hostblob = self.assert_post(
            "/hosts/", {"name": "test", "namespace": nsblob.data["id"]}
        )

        exblob = self.assert_post(
            "/extensions/",
            {
                "namespace": nsblob.data["id"],
                "name": "fleet",
                "model": "host",
                "url": "https://fleet.my.domain/api/v1/fleet/hosts/identifier/{fqdn}",
                "header": "Authorization: Bearer sh...==",
            },
        )

        exdblob = self.assert_post(
            "/extension_data/",
            {
                "namespace": nsblob.data["id"],
                "extension": exblob.data["id"],
                "content_type": "host",
                "object_id": hostblob.data["id"],
                "json_data": {"key": "value", "listkey": [1, 2, 3]},
            },
        )

        exdid = exdblob.data["id"]
        self.assert_get(f"/extension_data/{exdid}")

        self.assertTrue(exdblob.data["json_data"]["key"] == "value")

        # Updating by using post
        exdblob = self.assert_post(
            "/extension_data/",
            {
                "namespace": nsblob.data["id"],
                "extension": exblob.data["id"],
                "content_type": "host",
                "object_id": hostblob.data["id"],
                "json_data": {"key": "newvalue", "listkey": [1, 2, 3]},
            },
        )

        self.assertTrue(exdblob.data["json_data"]["key"] == "newvalue")

        # Posting with the wrong content_type (user vs host)
        exdblob = self.assert_post_and_400(
            "/extension_data/",
            {
                "namespace": nsblob.data["id"],
                "extension": exblob.data["id"],
                "content_type": "user",
                "object_id": hostblob.data["id"],
                "json_data": {"key": "value", "listkey": [1, 2, 3]},
            },
        )

        self.assert_delete("/namespaces/test")
