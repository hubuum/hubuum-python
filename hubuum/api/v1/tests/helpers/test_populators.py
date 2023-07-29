"""Test the internals of the Populator class."""

from hubuum.api.v1.tests.helpers.populators import APIv1Objects
from hubuum.models.dynamic import ClassLink, HubuumClass, HubuumObject, ObjectLink


class TestPopulators(APIv1Objects):
    """Test internal HubuumObject functionality."""

    def test_internal_class_and_object_count(self) -> None:
        """Test the internals of the class generation."""
        # Test that the number of objects and classes is correct
        self.assertEqual(HubuumClass.objects.count(), len(self.all_classes()))
        self.assertEqual(HubuumObject.objects.count(), len(self.all_objects()))

    # This should be moved outside of the API testing suite, but we need direct
    # create_class*-methods to be available first.
    def test_str_of_ClassLink_and_ObjectLink(self) -> None:
        """Test the str representation of link types and dynamic links."""
        self.create_class_link_via_api("Host", "Room", max_links=3)
        class_link = ClassLink.objects.get(
            source_class__name="Host", target_class__name="Room"
        )
        self.assertEqual(str(class_link), "Host <-> Room (3)")

        self.create_object_link_via_api("Host.host1", "Room.room1")
        link = ObjectLink.objects.get(source__name="host1", target__name="room1")
        self.assertEqual(str(link), "host1 [Host] <-> room1 [Room]")
