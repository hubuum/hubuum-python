"""Test module for the Jack model."""
from hubuum.models.base import Jack

from .base import HubuumModelTestCase


class JackTestCase(HubuumModelTestCase):
    """This class defines the test suite for the Jack model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {"name": "BL14=521.A7-UD7056"}
        self.obj = self._test_can_create_object(model=Jack, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
