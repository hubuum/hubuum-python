"""Test classes prepopulated with data structures for testing of api/v1."""

from itertools import zip_longest
from typing import Any, Dict, List, Tuple

from django.http import HttpResponse

from hubuum.api.v1.tests.base import HubuumAPITestCase
from hubuum.models.dynamic import HubuumClass, HubuumObject
from hubuum.models.iam import Namespace
from hubuum.tests.helpers.populators import BasePopulator


class APIv1Empty(HubuumAPITestCase, BasePopulator):
    """A base class for Hubuum API test cases with functionality to create dynamic structures.

    The following classes can be created via
    - Host
    - Room
    - Building

    The following objects are created:
    - Hosts (3, named host1, host2, host3)
    - Rooms (2, named room1, room2, room3)
    - Buildings (1, named building1)
    """

    def setUp(self):
        """Set up a default namespace."""
        super().setUp()

        self.namespaces = []
        for i in range(1, 4):
            self.namespaces.append(
                self._create_namespace(namespacename=f"namespace{i}")
            )

        self.namespace = self.namespaces[0]

        self.host_class = None
        self.room_class = None
        self.building_class = None

        self.hosts = []
        self.rooms = []
        self.buildings = []

    def create_classes(self) -> None:
        """Create the dynamic classes.

        The following classes are created:
        - Host
        - Room
        - Building
        """
        self.host_class = self.create_class_direct(name="Host")
        self.room_class = self.create_class_direct(name="Room")
        self.building_class = self.create_class_direct(name="Building")

    def create_objects(self) -> None:
        """Populate the classes with objects.

        The following objects are created:
        - Hosts (3, named host1, host2, host3)
        - Rooms (2, named room1, room2, room3)
        - Buildings (1, named building1)
        """
        # Create an array of hosts with names host1, host2, host3
        self.hosts = [
            self.create_object_direct(
                dynamic_class=self.host_class, namespace=self.namespace, name=f"host{i}"
            )
            for i in range(1, 4)
        ]

        # Create an array of rooms with names room1, room2, room3
        self.rooms = [
            self.create_object_direct(
                dynamic_class=self.room_class, namespace=self.namespace, name=f"room{i}"
            )
            for i in range(1, 3)
        ]

        # Create a building with name building1
        self.buildings = [
            self.create_object_direct(
                dynamic_class=self.building_class,
                namespace=self.namespace,
                name="building1",
            )
        ]

    def all_classes(self) -> List[HubuumClass]:
        """Return all classes."""
        return [self.host_class, self.room_class, self.building_class]

    def all_objects(self) -> List[HubuumObject]:
        """Return all objects."""
        return self.hosts + self.rooms + self.buildings

    def get_object_via_api(self, dynamic_class: str, name: str) -> HubuumObject:
        """Get a dynamic object."""
        return self.assert_get(f"/dynamic/{dynamic_class}/{name}")

    def split_class_object(self, class_object: str) -> Tuple[str, str]:
        """Split a class.object string into class and object."""
        return class_object.split(".")

    def create_class_link_via_api(
        self, class1: str, class2: str, max_links: int = 0, namespace: Namespace = None
    ) -> HttpResponse:
        """Create a link type between two classes.

        param class1: The source class name (string)
        param class2: The target class name (string)
        """
        namespace = namespace or self.namespace

        return self.assert_post(
            f"/dynamic/{class1}/link/{class2}/",
            {"max_links": max_links, "namespace": self.namespace.id},
        )

    def create_object_link_via_api(
        self, class1_obj1: str, class2_obj2: str
    ) -> HttpResponse:
        """Create a link between two objects.

        param class1_obj1: The class and object (class.object) of the source object
        param class2_obj2: The class and object (class.object) of the target object
        """
        class1, obj1 = self.split_class_object(class1_obj1)
        class2, obj2 = self.split_class_object(class2_obj2)
        return self.assert_post(
            f"/dynamic/{class1}/{obj1}/link/{class2}/{obj2}",
            {"namespace": self.namespace.id},
        )

    def check_link_exists_via_api(
        self,
        class1_obj1: str,
        class2: str,
        expected_data_list: List[Dict[str, Any]],
        transitive: bool = True,
    ) -> HttpResponse:
        """Check that a link exists between two objects.

        param class1_obj1: The class and object (class.object) of the first object
        param class2: The class of the second object
        param expected_data_list: A list of dictionaries containing the expected data
        param transitive: Whether the link should be transitive (default: True)
        """
        class1, obj1 = self.split_class_object(class1_obj1)
        transitive = "true" if transitive else "false"

        # Check that the correct number of links are returned

        ret = self.assert_get(
            f"/dynamic/{class1}/{obj1}/links/{class2}/?transitive={transitive}",
        )

        ret_length = len(ret.data)
        expected_length = len(expected_data_list)
        if ret_length != expected_length:  # pragma: no cover, debug when test fails
            for returned, expected in zip_longest(ret.data, expected_data_list):
                print("Expected:")
                print(expected)
                print("Returned:")
                if returned:
                    pret: Dict[str, Any] = {
                        "name": returned["object"]["name"],
                        "class": returned["object"]["dynamic_class"],
                        "path": [
                            f"{d['dynamic_class']}.{d['name']}"
                            for d in returned["path"]
                        ],
                    }
                    print(pret)
                else:
                    print(returned)

        self.assertEqual(len(ret.data), len(expected_data_list))

        for returned_obj in ret.data:
            self.assertEqual(returned_obj["object"]["dynamic_class"], class2)

        # Check each returned object against expected data
        for expected_data, actual_data in zip(expected_data_list, ret.data):
            self.assertEqual(len(actual_data["path"]), len(expected_data["path"]))

            self.assertEqual(actual_data["object"]["name"], expected_data["name"])
            self.assertEqual(
                actual_data["object"]["dynamic_class"], expected_data["class"]
            )

            # Check each path item against expected values

            for i, class_obj_pair in enumerate(expected_data["path"]):
                expected_class, expected_obj = self.split_class_object(class_obj_pair)
                path_item = actual_data["path"][i]
                self.assertEqual(path_item["name"], expected_obj)
                self.assertEqual(path_item["dynamic_class"], expected_class)

        return ret

    def create_class_and_object(
        self, class_name: str, obj_name: str, json_data: Dict[str, Any] = None
    ) -> Tuple[HubuumClass, HubuumObject]:
        """Create a class and an object."""
        dynamic_class = HubuumClass.objects.create(
            name=class_name,
            namespace=self.namespace,
        )
        dynamic_object = HubuumObject.objects.create(
            name=obj_name,
            dynamic_class=dynamic_class,
            namespace=self.namespace,
            json_data=json_data or {"name": "Noone"},
        )
        return dynamic_class, dynamic_object

    def tearDown(self) -> None:
        """Delete the namespace after the test."""
        for namespace in self.namespaces:
            namespace.delete()
        return super().tearDown()


class APIv1Classes(APIv1Empty):
    """A base class with dynamic classes already created.

    Utilizes the HubuumDynamicBase.create_classes method.
    """

    def setUp(self):
        """Set up a default namespace and creates the classes."""
        super().setUp()
        self.create_classes()


class APIv1Objects(APIv1Classes):
    """A base class with dynamic classes and objects already created.

    Utilizes the following methods:
     - HubuumDynamicBase.create_classes
     - HubuumDynamicBase.create_objects


    """

    def setUp(self):
        """Set up a default namespace and creates the classes."""
        super().setUp()
        self.create_objects()
