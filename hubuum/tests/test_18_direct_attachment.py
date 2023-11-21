"""Test module for the Attachment/AttachmentManager models."""
import hashlib

from django.core.files.uploadedfile import SimpleUploadedFile

from hubuum.models.core import Attachment, AttachmentManager
from hubuum.tests.base import HubuumModelTestCase
from hubuum.tests.helpers.populators import BasePopulator


class AttachmentTestCase(HubuumModelTestCase, BasePopulator):
    """Define the test suite for the Attachment model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.cls = self.create_class_direct(name="Host")
        self.host = self.create_object_direct(
            hubuum_class=self.cls,
            namespace=self.namespace,
            name="test",
            json_data={},
        )

        self.content = b"A bit of content."
        self.attributes = {
            "attachment": SimpleUploadedFile(
                "test_file.txt", self.content, content_type="text/plain"
            ),
            "hubuum_class": self.cls,
            "hubuum_object": self.host,
            "namespace": self.namespace,
        }

        # Enable attachments for the model. This is not required when creating the object
        # directly as there is no validation to catch this case? We do need the class and the
        # object to exist though.
        self.attachment_manager = self._test_can_create_object(
            model=AttachmentManager, **{"hubuum_class": self.cls, "enabled": True}
        )

        self.obj = self._test_can_create_object(model=Attachment, **self.attributes)

    def tearDown(self):
        """Clean up after each test."""
        self.host.delete()  # This should cascade to the attachment.
        self.attachment_manager.delete()
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


class AttachmentManagerTestCase(HubuumModelTestCase, BasePopulator):
    """Define the test suite for the AttachmentManager model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.cls = self.create_class_direct(name="Host")
        self.attributes = {
            "hubuum_class": self.cls,
            "enabled": True,
        }
        self.obj = AttachmentManager.objects.create(**self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
