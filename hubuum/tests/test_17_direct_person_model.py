"""Test module for the Person model."""
from hubuum.models.resources import Person

from .base import HubuumModelTestCase


class PersonTestCase(HubuumModelTestCase):
    """Define the test suite for the Person model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {"username": "octocat", "email": "octocat@github.com"}
        self.obj = self._test_can_create_object(model=Person, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(obj=self.obj, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()
