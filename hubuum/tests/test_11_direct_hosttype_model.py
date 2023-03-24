"""Test module for the HostType model."""
from hubuum.models.base import HostType

from .base import HubuumModelTestCase


class HostTypeTestCase(HubuumModelTestCase):
    """This class defines the test suite for the HostType model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {"name": "testname", "description": "test_description"}
        self.obj = self._test_can_create_object(model=HostType, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
