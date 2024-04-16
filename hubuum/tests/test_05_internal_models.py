"""Test module for the internal models."""

from hubuum.models.iam import Namespace

from .base import HubuumModelTestCase


class NamespaceTestCase(HubuumModelTestCase):
    """Define the test suite for the Namespace model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {
            "name": "namespace1",
            "description": "The first namespace",
        }
        self.obj = self._test_can_create_object(model=Namespace, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
