"""Test hubuum attachments."""

from hubuum.models.permissions import Namespace

from .base import HubuumAPITestCase


class HubuumAttachmentTestCase(HubuumAPITestCase):
    """Base class for testing Hubuum Attachments."""

    def setUp(self):
        """Set up the test environment for the class."""
        self.client = self.get_superuser_client()
        self.namespace, _ = Namespace.objects.get_or_create(name="test")

    def tearDown(self) -> None:
        """Tear down the test environment for the class."""
        self.namespace.delete()
        return super().tearDown()

    def _create_host_attachment(self):
        """Create a host attachment."""
        return self.assert_post(
            "/api/v1/attachments/",
            {"model": "host", "enabled": True, "namespace": self.namespace.id},
        )


class APIAttachmentTestCase(HubuumAttachmentTestCase):
    """Test attachment availability."""

    def test_attachment_create_and_enabled(self):
        """Test that attachments are enabled."""
        self._create_host_attachment()
        res = self.assert_get("/api/v1/attachments/host")

        self.assert_post_and_400(
            "/api/v1/attachments/",
            {"model": "host", "enabled": True, "namespace": self.namespace.id},
        )

        self.assertEqual(res.data["enabled"], True)
        self.assertTrue(res.data["enabled"])
        self.assert_patch("/api/v1/attachments/host", {"enabled": False})

        res = self.assert_get("/api/v1/attachments/host")
        self.assertEqual(res.data["enabled"], False)
        self.assertFalse(res.data["enabled"])

    def test_attachment_unsupported_model(self):
        """Test that unsupported models are rejected."""
        self.assert_post_and_400(
            "/api/v1/attachments/",
            {"model": "user", "enabled": True, "namespace": self.namespace.id},
        )
        self.assert_post_and_400(
            "/api/v1/attachments/",
            {"model": "namespace", "enabled": True, "namespace": self.namespace.id},
        )

    def test_attachment_limits(self):
        """Test that attachment limitations."""
        self._create_host_attachment()
        res = self.assert_get("/api/v1/attachments/host")
        self.assertEqual(res.data["per_object_count_limit"], 0)
        self.assertEqual(res.data["per_object_individual_size_limit"], 0)
        self.assertEqual(res.data["per_object_total_size_limit"], 0)

        self.assert_patch("/api/v1/attachments/host", {"per_object_count_limit": 1})

        # This will pass even though the per_object_total_size_limit is 0, as 0 is
        # considered unlimited.
        self.assert_patch(
            "/api/v1/attachments/host", {"per_object_individual_size_limit": 20}
        )
        self.assert_patch(
            "/api/v1/attachments/host", {"per_object_total_size_limit": 100}
        )

        # Test that we can't set the total size limit to be smaller than the
        # individual size limit.
        self.assert_patch_and_400(
            "/api/v1/attachments/host", {"per_object_total_size_limit": 19}
        )

        # Test that we can't set the individual size limit to be larger than the
        # total size limit.
        self.assert_patch_and_400(
            "/api/v1/attachments/host", {"per_object_individual_size_limit": 101}
        )

        res = self.assert_get("/api/v1/attachments/host")
        self.assertEqual(res.data["per_object_count_limit"], 1)
        self.assertEqual(res.data["per_object_individual_size_limit"], 20)
        self.assertEqual(res.data["per_object_total_size_limit"], 100)
