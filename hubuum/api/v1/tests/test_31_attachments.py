"""Test hubuum attachments."""

import hashlib
import os

from django.core.files.uploadedfile import SimpleUploadedFile

from hubuum.models.permissions import Namespace
from hubuum.models.resources import Host

from .base import HubuumAPITestCase


class HubuumAttachmentTestCase(HubuumAPITestCase):
    """Base class for testing Hubuum Attachments."""

    def setUp(self):
        """Set up the test environment for the class."""
        self.client = self.get_superuser_client()
        self.namespace, _ = Namespace.objects.get_or_create(name="test")
        self.file_content = b"this is a test file"

    def tearDown(self) -> None:
        """Tear down the test environment for the class."""
        self.namespace.delete()
        return super().tearDown()

    def _enable_attachments_for_hosts(self):
        """Enable attachments for hosts."""
        return self.assert_post(
            "/api/v1/attachments/", {"model": "host", "enabled": True}
        )

    def _create_host(self):
        """Create a host."""
        return Host.objects.create(name="test_host", namespace=self.namespace)

    def _create_test_file(self, content=None):
        """Create a test file."""
        if content is None:
            content = self.file_content
        return SimpleUploadedFile("test_file.txt", content, content_type="text/plain")


class HubuumAttachmentBasicTestCase(HubuumAttachmentTestCase):
    """Test attachment availability."""

    def test_attachment_create_and_enabled(self):
        """Test that attachments are enabled."""
        self._enable_attachments_for_hosts()
        res = self.assert_get("/api/v1/attachments/host")

        self.assert_post_and_400(
            "/api/v1/attachments/", {"model": "host", "enabled": True}
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

    def test_attachment_set_limits(self):
        """Test that attachment limitations can be set."""
        self._enable_attachments_for_hosts()
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

    def test_attachment_limit_adherence(self):
        """Test that attachment limitations are adhered to."""
        self._enable_attachments_for_hosts()
        self.assert_patch(
            "/api/v1/attachments/host",
            {
                "per_object_count_limit": 1,
                "per_object_individual_size_limit": 20,
                "per_object_total_size_limit": 30,
            },
        )

        host = self._create_host()
        file = self._create_test_file(b"a test file")
        self.assert_post_and_201(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        new_file = self._create_test_file(b"a new test file")
        # Test that we can't upload more than one attachment.
        self.assert_post_and_400(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": new_file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_patch("/api/v1/attachments/host", {"per_object_count_limit": 5})

        new_file = self._create_test_file(b"a new test file")
        self.assert_post_and_201(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": new_file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Test that we can't upload an attachment that is too large.
        # > 20 bytes
        file = self._create_test_file(b"this is a test file that is too large")
        self.assert_post_and_400(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Test that we can't upload an attachment that would make the total size
        # exceed the limit. 12+16=28 bytes, limit is 30 bytes.
        file = self._create_test_file(b"no space")
        self.assert_post_and_400(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_attachment_data_upload(self):
        """Test uploading of an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        res = self.assert_post_and_201(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        file_hash = hashlib.sha256(self.file_content).hexdigest()

        file_meta = self.assert_get(
            f"/api/v1/attachments/host/{host.id}/{res.data['id']}"
        )

        self.assertEqual(file_meta.data["original_filename"], "test_file.txt")
        self.assertEqual(file_meta.data["size"], len(self.file_content))
        self.assertEqual(file_meta.data["sha256"], file_hash)

        fileres = self.assert_get(
            f"/api/v1/attachments/host/{host.id}/{res.data['id']}/download"
        )

        self.assertEqual(fileres.content, self.file_content)

    def test_attachment_data_permissions(self):
        """Test that permissions are enforced."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        att = self.assert_post_and_201(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get(f"/api/v1/attachments/host/{host.id}/{att.data['id']}")
        self.assert_get(f"/api/v1/attachments/host/{host.id}/{att.data['id']}/download")

        self.client = self.get_user_client()
        self.assert_get_and_403(
            f"/api/v1/attachments/host/{host.id}/{att.data['id']}",
        )
        self.assert_delete_and_403(
            f"/api/v1/attachments/host/{host.id}/{att.data['id']}/download",
        )

        new_host = Host.objects.create(name="new_host", namespace=self.namespace)
        self.assert_get_and_404(
            f"/api/v1/attachments/host/{new_host.id}/{att.data['id']}"
        )

    def test_attachment_data_duplicate(self):
        """Test uploading of an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        self.assert_post_and_201(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        file = self._create_test_file()
        self.assert_post_and_409(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

    def test_attachment_failures(self):
        """Test various attachment failures."""
        # No such model
        self.assert_get_and_404("/api/v1/attachments/nope/1")
        self.assert_post_and_404("/api/v1/attachments/nope/1", {})

        host = self._create_host()
        file = self._create_test_file()
        # Model exists, but does not have attachments enabled
        self.assert_post_and_400(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Model exists, but does not have support for attachments
        self.assert_get_and_400("/api/v1/attachments/namespace/1")
        self.assert_post_and_400(
            f"/api/v1/attachments/namespace/{self.namespace.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        # Model exists, has attachments enabled, but the attachment does not exist
        self._enable_attachments_for_hosts()
        self.assert_get_and_404("/api/v1/attachments/host/1")

        # No such host
        self.assert_post_and_404("/api/v1/attachments/host/99", {})

        # Disable attachments for host, and try again
        host = self._create_host()
        self.assert_patch("/api/v1/attachments/host", {"enabled": False})
        self.assert_post_and_400(
            f"/api/v1/attachments/host/{host.id}", format="multipart"
        )

        # Uploading without setting format=multipart
        self.assert_post_and_415(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": "notafile", "namespace": self.namespace.id},
        )

    def test_attachment_delete(self):
        """Test manually deleting an attachment."""
        self._enable_attachments_for_hosts()
        file = self._create_test_file()
        host = self._create_host()

        att = self.assert_post_and_201(
            f"/api/v1/attachments/host/{host.id}",
            {"attachment": file, "namespace": self.namespace.id},
            format="multipart",
        )

        self.assert_get(f"/api/v1/attachments/host/{host.id}/{att.data['id']}")
        self.assert_get(f"/api/v1/attachments/host/{host.id}/{att.data['id']}/download")

        self.assert_delete(f"/api/v1/attachments/host/{host.id}/{att.data['id']}")
        self.assert_get_and_404(f"/api/v1/attachments/host/{host.id}/{att.data['id']}")
        self.assert_get_and_404(
            f"/api/v1/attachments/host/{host.id}/{att.data['id']}/download"
        )


def tearDownModule():  # pylint: disable=invalid-name
    """Global teardown for this test module, cleans up attachments directory."""
    try:  # pragma: no cover
        os.rmdir("attachments/file")
        os.rmdir("attachments")
    except OSError:  # pragma: no cover
        pass
