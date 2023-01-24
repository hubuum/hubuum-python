"""Test module for the Vendor model."""
from hubuum.models import Vendor

from .base import HubuumModelTestCase


class VendorTestCase(HubuumModelTestCase):
    """This class defines the test suite for the Vendor model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {"vendor_name": "GitHub", "vendor_url": "https://github.com"}
        self.object = self._test_can_create_object(model=Vendor, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(object=self.object, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
