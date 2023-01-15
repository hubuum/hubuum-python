"""Test module for the PurchaseOrder model."""

from datetime import datetime

from .base import HubuumModelTestCase

from hubuum.models import PurchaseOrder


class PurchaseOrderTestCase(HubuumModelTestCase):
    """This class defines the test suite for the PurchaseOrder model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {
            "order_date": datetime.now().astimezone(),
            "po_number": "6001",
        }
        self.object = self._test_can_create_object(
            model=PurchaseOrder, **self.attributes
        )

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(object=self.object, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
