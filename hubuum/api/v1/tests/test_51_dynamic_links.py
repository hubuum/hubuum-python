"""Test the dynamic classes in hubuum."""

from typing import Any, Dict

from hubuum.api.v1.tests.base import HubuumHubuumClassesAndObjects
from hubuum.models.dynamic import ClassLink, HubuumClass, HubuumObject, ObjectLink


class HubuumObjectTestCase(HubuumHubuumClassesAndObjects):
    """Test HubuumObject functionality."""

    def test_internal_class_and_object_count(self) -> None:
        """Test the internals of the class generation."""
        # Test that the number of objects and classes is correct
        self.assertEqual(HubuumClass.objects.count(), len(self.all_classes()))
        self.assertEqual(HubuumObject.objects.count(), len(self.all_objects()))

    def test_str_of_ClassLink_and_ObjectLink(self) -> None:
        """Test the str representation of link types and dynamic links."""
        # Test creating a link type between Host and Room
        self.create_class_link_via_api("Host", "Room", max_links=3)
        class_link = ClassLink.objects.get(
            source_class__name="Host", target_class__name="Room"
        )
        self.assertEqual(str(class_link), "Host <-> Room (3)")

        # Test creating a link between host1 and room1
        self.create_object_link_via_api("Host.host1", "Room.room1")

        # Test str representation of the link
        link = ObjectLink.objects.get(source__name="host1", target__name="room1")
        self.assertEqual(str(link), "host1 [Host] <-> room1 [Room]")

    def test_basic_operations(self) -> None:
        """Test basic operations of classes, objects, and links."""
        # Try patching a non-existing ClassLink
        self.assert_patch_and_404(
            "/dynamic/Room/link/Host/",
            {"namespace": self.namespace.id, "max_links": 1},
        )

        # Test creating a link type between Host and Room
        self.create_class_link_via_api("Host", "Room", max_links=1)
        self.assert_get("/dynamic/Host/link/Room/")
        self.assert_get("/dynamic/Room/link/Host/")
        self.assert_post_and_409(
            "/dynamic/Host/link/Room/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        # Upgrading links:
        for i in range(2, 4):
            self.assert_patch("/dynamic/Host/link/Room/", {"max_links": i})
            hrret = self.assert_get("/dynamic/Host/link/Room/")
            rhret = self.assert_get("/dynamic/Room/link/Host/")
            self.assertEqual(hrret.data["max_links"], i)
            self.assertEqual(rhret.data["max_links"], i)

        ns_create_ret = self._create_namespace("ns2")
        # Sending {"namespace", foo} fails with an exception
        # namespace_id = request.data.get("namespace", None)
        # AttributeError: 'list' object has no attribute 'get'
        nsret = self.assert_patch(
            "/dynamic/Room/link/Host/", {"namespace": ns_create_ret.id}
        )
        self.assertEqual(nsret.data["namespace"], ns_create_ret.id)

        # Try patching a non-existing namespace
        self.assert_patch_and_404("/dynamic/Room/link/Host/", {"namespace": 999999999})

        # Test str representation of the link type
        class_link = ClassLink.objects.get(
            source_class__name="Host", target_class__name="Room"
        )
        self.assertEqual(str(class_link), "Host <-> Room (3)")

        # Test creating a link between host1 and room1
        self.create_object_link_via_api("Host.host1", "Room.room1")
        self.assert_get("/dynamic/Host/host1/link/Room/room1")
        self.assert_post_and_409(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        self.assert_post_and_409(
            "/dynamic/Room/room1/link/Host/host1",
            {"namespace": self.namespace.id},
        )

        # Test str representation of the link
        link = ObjectLink.objects.get(source__name="host1", target__name="room1")
        self.assertEqual(str(link), "host1 [Host] <-> room1 [Room]")

    def test_failing_specific_link_get(self) -> None:
        """Test that fetching non-existent links fails."""
        self.assert_get_and_404("/dynamic/Host/link/Room/")
        self.assert_get_and_404(
            "/dynamic/Host/host1/link/Room/room1",
        )
        self.create_class_link_via_api("Host", "Room", max_links=1)
        self.assert_get_and_404(
            "/dynamic/nope/host1/link/Room/room1",
        )
        self.assert_get_and_404(
            "/dynamic/Host/nope/link/Room/room1",
        )
        self.assert_get_and_404(
            "/dynamic/Host/host1/link/nope/room1",
        )
        self.assert_get_and_404(
            "/dynamic/Host/host1/link/Room/nope",
        )
        self.assert_get_and_404(
            "/dynamic/Host/nope/links/Room/?transitive=true",
        )
        self.assert_get_and_404(
            "/dynamic/Host/host1/links/Nope/?transitive=true",
        )

    def test_failing_ClassLink_creation(self) -> None:
        """Test that creating ClassLinks between non-existing classes fails."""
        self.assert_post_and_404(
            "/dynamic/Host/Nope/link/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_post_and_404(
            "/dynamic/Nope/Room/link/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        # Test that sending a non-existent namespace fails.
        self.assert_post_and_404(
            "/dynamic/Host/link/Room/",
            {"max_links": 1, "namespace": 999999},
        )

    def test_failing_link_creation(self) -> None:
        """Test that creating a link fails when the link type is not defined."""
        # Test creating a link between host1 and room1, which should fail as we have not
        # defined a link type between Host and Room
        self.assert_post_and_404(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        # Source class does not exist
        self.assert_post_and_404(
            "/dynamic/Nope/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        # Target class does not exist
        self.assert_post_and_404(
            "/dynamic/Host/host1/link/Nope/room1",
            {"namespace": self.namespace.id},
        )
        # Source object does not exist
        self.assert_post_and_404(
            "/dynamic/Host/nope/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        # Target object does not exist
        self.assert_post_and_404(
            "/dynamic/Host/host1/link/Room/nope",
            {"namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Host/link/Room/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_post_and_404(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": 999999},
        )

    def test_loops_during_transitive_links(self) -> None:
        """Test that loops during transitive links don't break anything."""
        self.create_class_and_object("Person", "person1")
        self.create_class_link_via_api("Host", "Room")
        self.create_class_link_via_api("Room", "Building")
        self.create_class_link_via_api("Building", "Person")
        self.create_class_link_via_api("Building", "Host")

        # host1 -> room1 -> building1 -> person1
        self.create_object_link_via_api("Host.host1", "Room.room1")
        self.create_object_link_via_api("Room.room1", "Building.building1")
        self.create_object_link_via_api("Building.building1", "Person.person1")

        # This creates the loop back to host1
        # host1 -> room1 -> building1 -> host1
        # Note that due to bidirectionality, this is the same as saying
        # host1 -> building1
        # Which again leads to the following secondary path to person1
        # host1 -> building1 -> person1
        self.create_object_link_via_api("Building.building1", "Host.host1")

        self.check_link_exists_via_api(
            "Host.host1",
            "Person",
            [
                {
                    "name": "person1",
                    "class": "Person",
                    "path": [
                        "Host.host1",
                        "Building.building1",
                        "Person.person1",
                    ],
                },
                {
                    "name": "person1",
                    "class": "Person",
                    "path": [
                        "Host.host1",
                        "Room.room1",
                        "Building.building1",
                        "Person.person1",
                    ],
                },
            ],
        )

    def test_that_link_creation_fails_when_max_links_is_reached(self) -> None:
        """Test that creating a link fails when the max number of links is reached."""
        self.create_class_link_via_api("Host", "Room", max_links=1)
        # Test creating a link between host1 and room1
        self.create_object_link_via_api("Host.host1", "Room.room1")
        # Test creating a link between host1 and room2, which should fail as we have
        # defined a link type between Host and Room with max_links=1
        self.assert_post_and_409(
            "/dynamic/Host/host1/link/Room/room2",
            {"namespace": self.namespace.id},
        )

    def test_non_existing_ClassLink(self) -> None:
        """Test that non-existing link types are handled correctly."""
        self.assert_delete_and_404("/dynamic/Nope/Room/link/")
        self.assert_delete_and_404("/dynamic/Host/Nope/link/")
        self.assert_delete_and_404("/dynamic/Host/link/Room/")

    def test_deleting_ClassLink(self) -> None:
        """Test that deleting a link type works."""
        self.create_class_link_via_api("Host", "Room", max_links=1)
        self.create_object_link_via_api("Host.host1", "Room.room1")
        # Verify that the link exists, bidirectionally
        self.assert_get("/dynamic/Host/host1/link/Room/room1")
        self.assert_get("/dynamic/Room/room1/link/Host/host1")
        self.assert_delete("/dynamic/Host/link/Room/")
        # Verify that the ClassLink is gone
        self.assert_delete_and_404("/dynamic/Host/link/Room/")
        self.assert_delete_and_404("/dynamic/Room/link/Host/")
        # And that removing the link type also removed the link
        self.assert_get_and_404("/dynamic/Host/host1/link/Room/room1")
        self.assert_get_and_404("/dynamic/Room/room1/link/Host/host1")

    def test_creating_object_in_nonexisting_class(self) -> None:
        """Test creating an object in a non-existing class."""
        self.assert_post_and_404(
            "/dynamic/NonExistingClass/",
            {
                "name": "test",
                "namespace": self.namespace.id,
                "json_data": {},
            },
        )

    def test_linking_between_objects(self) -> None:
        """Test that manipulating links between objects works."""
        self.create_class_link_via_api("Host", "Room")
        self.create_object_link_via_api("Host.host1", "Room.room1")
        self.assert_get("/dynamic/Host/host1/link/Room/room1")
        # implicit bidirectionality
        self.assert_get("/dynamic/Room/room1/link/Host/host1")
        self.assert_get_elements("/dynamic/Host/host1/links/", 1)
        self.assert_get_elements("/dynamic/Room/room1/links/", 1)
        self.create_object_link_via_api("Host.host1", "Room.room2")
        self.assert_get_elements("/dynamic/Host/host1/links/", 2)
        self.assert_get_elements("/dynamic/Room/room1/links/", 1)
        self.assert_delete("/dynamic/Host/host1/link/Room/room1")
        self.assert_delete_and_404("/dynamic/Host/host1/link/Room/room1")
        # Verify that the reverse link is also deleted
        self.assert_delete_and_404("/dynamic/Room/room1/link/Host/host1")
        self.assert_get_elements("/dynamic/Host/host1/links/", 1)
        # Delete in opposite direction.
        self.assert_delete("/dynamic/Room/room2/link/Host/host1")
        self.assert_get_and_404("/dynamic/Host/notfound/links/")

    def test_multiple_links_to_same_class(self) -> None:
        """Test that multiple links to the same class works."""
        self.create_class_link_via_api("Host", "Room")
        for room in ["room1", "room2"]:
            self.create_object_link_via_api("Host.host1", f"Room.{room}")
        self.assert_get_elements("/dynamic/Host/host1/links/Room/", 2)
        self.assert_get_elements("/dynamic/Host/host1/links/", 2)

    def test_transitive_linking(self) -> None:
        """Test transitive linking."""
        self.create_class_link_via_api("Host", "Room")
        self.create_class_link_via_api("Room", "Building")
        self.create_object_link_via_api("Host.host1", "Room.room1")

        self.check_link_exists_via_api(
            "Host.host1",
            "Room",
            [
                {
                    "name": "room1",
                    "class": "Room",
                    "path": ["Host.host1", "Room.room1"],
                },
            ],
        )

        self.assert_get_and_404("/dynamic/Host/host1/links/Building/")
        self.create_object_link_via_api("Room.room1", "Building.building1")

        self.check_link_exists_via_api(
            "Host.host1",
            "Building",
            [
                {
                    "name": "building1",
                    "class": "Building",
                    "path": ["Host.host1", "Room.room1", "Building.building1"],
                }
            ],
        )

        # Create a person class and a person object
        self.create_class_and_object("Person", "person1")

        # First verify that there is no path between Host:host1 and Person
        self.assert_get_and_404("/dynamic/Host/host1/links/Person/?transitive=true")

        # Link person1 to building1, but first link Building to Person
        # This should create a transitive link between Host and Person via Room and Building
        self.create_class_link_via_api("Building", "Person")
        self.create_object_link_via_api("Building.building1", "Person.person1")

        self.check_link_exists_via_api(
            "Host.host1",
            "Person",
            [
                {
                    "name": "person1",
                    "class": "Person",
                    "path": [
                        "Host.host1",
                        "Room.room1",
                        "Building.building1",
                        "Person.person1",
                    ],
                },
            ],
        )
        self.check_link_exists_via_api(
            "Person.person1",
            "Host",
            [
                {
                    "name": "host1",
                    "class": "Host",
                    "path": [
                        "Person.person1",
                        "Building.building1",
                        "Room.room1",
                        "Host.host1",
                    ],
                },
            ],
        )

        # Allow links between Room to Person and then link room1 to person1
        self.create_class_link_via_api("Room", "Person")
        self.create_object_link_via_api("Room.room1", "Person.person1")

        self.check_link_exists_via_api(
            "Host.host1",
            "Person",
            [
                {
                    "name": "person1",
                    "class": "Person",
                    "path": ["Host.host1", "Room.room1", "Person.person1"],
                },
                {
                    "name": "person1",
                    "class": "Person",
                    "path": [
                        "Host.host1",
                        "Room.room1",
                        "Building.building1",
                        "Person.person1",
                    ],
                },
            ],
        )

        self.assert_get_and_404(
            "/dynamic/Host/host1/links/Person/?transitive=true&max-depth=1"
        )

    def test_fetching_classes_and_objects(self) -> None:
        """Test fetching objects.

        We have the following classes and objects created behind the scenes:
        - Host (host1, host2, host3)
        - Room (room1, room2)
        - Building (building1)
        """
        objectmap: Dict[str, Any] = {
            "Host": ["host1", "host2", "host3"],
            "Room": ["room1", "room2"],
            "Building": ["building1"],
        }

        # Fetch all classes
        self.assert_get_elements(
            "/dynamic/",
            len(objectmap),
        )

        # Fetch each class by name
        for dynamic_class in objectmap.keys():
            self.assert_get(f"/dynamic/{dynamic_class}")

        # Fetch objects of a specific class
        self.assert_get_elements("/dynamic/Host/", len(objectmap["Host"]))

        # Fetch every object created in every class by name, and test that the name is correct
        for dynamic_class, objects in objectmap.items():
            for obj in objects:
                ret = self.get_object_via_api(dynamic_class, obj)
                self.assertEqual(ret.data["name"], obj)

    def test_404(self) -> None:
        """Test that 404 is returned when fetching a non-existing classes or objects."""
        self.assert_get_and_404("/dynamic/classdoesnotexist")
        self.assert_get_and_404("/dynamic/Host/doesnotexist")
        self.assert_get_and_404("/dynamic/Host/999999")
