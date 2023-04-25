"""Test module for the Room model."""
from hubuum.models.resources import Room

from .base import HubuumModelTestCase


class RoomTestCase(HubuumModelTestCase):
    """This class defines the test suite for the Room model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {"room_id": "701", "building": "BL14", "floor": "7"}
        self.obj = self._test_can_create_object(model=Room, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
