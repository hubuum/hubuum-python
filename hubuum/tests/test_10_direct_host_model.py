"""Test module for the Host model."""

from .base import HubuumModelTestCase

from hubuum.models import Host


class HostTestCase(HubuumModelTestCase):
    """This class defines the test suite for the Host model."""

    def setUp(self):
        """Set up defaults for the test object."""
        super().setUp()
        self.attributes = {"name": "testname", "serial": "testserial"}
        self.object = self._test_can_create_object(model=Host, **self.attributes)

    def test_create_has_correct_values(self):
        """Check that a created object returns the same values we fed it (only name for now)."""
        self._test_has_identical_values(object=self.object, dictionary=self.attributes)

    def test_str(self):
        """Test that stringifying objects works as expected."""
        self._test_str()

    def test_can_create_object_with_passed_namespace(self):
        """Test that we can create an object with an explicit group owner passed."""
        self.object = self._test_can_create_object(
            model=Host, namespace=self.namespace, **self.attributes
        )
