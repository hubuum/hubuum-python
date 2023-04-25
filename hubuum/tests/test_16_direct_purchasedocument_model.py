"""Test module for the PurchaseDocuments model."""
from datetime import datetime

from hubuum.models.resources import PurchaseDocuments, PurchaseOrder

from .base import HubuumModelTestCase


class PurchaseDocumentsTestCase(HubuumModelTestCase):
    """This class defines the test suite for the PurchaseDocument model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {
            "document_id": "document_6001_a",
            "purchase_order": self._test_can_create_object(
                model=PurchaseOrder,
                order_date=datetime.now().astimezone(),
                po_number="6001",
            ),
        }
        self.obj = self._test_can_create_object(
            model=PurchaseDocuments, **self.attributes
        )

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
