"""Test module for the Attachment/AttachmentManager models."""
import hashlib

from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from hubuum.models.core import Attachment, AttachmentManager, get_model
from hubuum.models.resources import Host

from .base import HubuumModelTestCase


class AttachmentTestCase(HubuumModelTestCase):
    """Define the test suite for the Attachment model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.host = Host.objects.create(name="test", namespace=self.namespace)
        model = get_model("host")
        content_type = ContentType.objects.get_for_model(model)

        self.content = b"A bit of content."
        self.attributes = {
            "attachment": SimpleUploadedFile(
                "test_file.txt", self.content, content_type="text/plain"
            ),
            "content_type": content_type,
            "object_id": self.host.id,
            "namespace": self.namespace,
        }
        self.obj = self._test_can_create_object(model=Attachment, **self.attributes)

    def tearDown(self):
        """Clean up after each test."""
        self.host.delete()
        return super().tearDown()

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it."""
        self.assertEqual(self.obj.sha256, hashlib.sha256(self.content).hexdigest())
        self.assertEqual(self.obj.size, len(self.content))
        self.assertEqual(self.obj.original_filename, "test_file.txt")
        self.assertEqual(self.obj.attachment.read(), self.content)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()


class AttachmentManagerTestCase(HubuumModelTestCase):
    """Define the test suite for the AttachmentManager model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {
            "model": "host",
            "enabled": True,
        }
        self.obj = AttachmentManager.objects.create(**self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
