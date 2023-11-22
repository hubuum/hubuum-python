"""Test classes prepopulated with data structures for testing of api/v1."""

from itertools import zip_longest
from typing import Any, Dict, List, Tuple, Union

from django.http import HttpResponse

from hubuum.api.v1.tests.base import HubuumAPITestCase
from hubuum.models.core import HubuumClass, HubuumObject
from hubuum.models.iam import Namespace
from hubuum.tests.helpers.populators import BasePopulator


class APIv1Empty(HubuumAPITestCase, BasePopulator):
    """A base class for Hubuum API test cases with functionality to create dynamic structures.

    After setup(), only four namespaces (namespace[1-4]) are created.
    No classes or objects are created.

    The following classes can be created via create_classes:
    - Host
    - Room
    - Building

    The following objects are created via create_objects:
    - Hosts (3, named host1, host2, host3)
    - Rooms (2, named room1, room2, room3)
    - Buildings (1, named building1)
    """

    def setUp(self):
        """Set up a default namespace."""
        super().setUp()

        self.namespaces: List[Namespace] = []
        for i in range(1, 4):
            self.namespaces.append(
                self._create_namespace(namespacename=f"namespace{i}")
            )

        self.namespace = self.namespaces[0]

        self.classes: List[HubuumClass] = []
        self.objects: List[HubuumObject] = []

    def create_classes(self) -> None:
        """Create the dynamic classes.

        The following classes are created:
        - Host
        - Room
        - Building
        """
        self.classes.append(self.create_class_direct(name="Host"))
        self.classes.append(self.create_class_direct(name="Room"))
        self.classes.append(self.create_class_direct(name="Building"))

    def get_class_from_cache(self, name: str) -> HubuumClass:
        """Get a dynamic class from the internal cache.

        param name: The name of the class to get.
        """
        for cls in self.classes:
            if cls.name == name:
                return cls
        raise ValueError(f"Class {name} not found")

    def get_objects_from_cache(
        self, cls_obj_str: str
    ) -> Union[HubuumObject, List[HubuumObject]]:
        """Get a list of dynamic objects from the internal cache.

        param cls_obj_str: A string of the form <class>.<object> or
            <class> to get all objects of a class.
        """
        if "." in cls_obj_str:
            cls, obj_name = self.split_class_object(cls_obj_str)

            for hubuum_obj in self.objects:
                if hubuum_obj.hubuum_class.name == cls and hubuum_obj.name == obj_name:
                    return hubuum_obj
            return None  # or raise an exception if an object with that name should always exist
        else:
            return [
                hubuum_obj
                for hubuum_obj in self.objects
                if hubuum_obj.hubuum_class.name == cls_obj_str
            ]

    def create_objects(self) -> None:
        """Populate the classes with objects.

        The following objects are created:
        - Hosts (3, named host1, host2, host3)
        - Rooms (2, named room1, room2)
        - Buildings (1, named building1)
        """
        # Create an array of hosts with names host1, host2, host3
        for i in range(1, 4):
            self.objects.append(
                self.create_object_direct(
                    hubuum_class=self.get_class_from_cache("Host"),
                    namespace=self.namespace,
                    name=f"host{i}",
                )
            )

        # Create an array of rooms with names room1, room2
        for i in range(1, 3):
            self.objects.append(
                self.create_object_direct(
                    hubuum_class=self.get_class_from_cache("Room"),
                    namespace=self.namespace,
                    name=f"room{i}",
                )
            )

        # Create a building with name building1
        self.objects.append(
            self.create_object_direct(
                hubuum_class=self.get_class_from_cache("Building"),
                namespace=self.namespace,
                name="building1",
            )
        )

        self.hosts = self.objects[0:3]
        self.rooms = self.objects[3:5]
        self.buildings = self.objects[5]

    def all_classes(self) -> List[HubuumClass]:
        """Return all classes."""
        return self.classes

    def all_objects(self) -> List[HubuumObject]:
        """Return all objects."""
        return self.objects

    def get_object_via_api(self, hubuum_class: str, name: str) -> HubuumObject:
        """Get a dynamic object."""
        return self.assert_get(f"/dynamic/{hubuum_class}/{name}")

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
                        "class": returned["object"]["hubuum_class"],
                        "path": [
                            f"{d['hubuum_class']}.{d['name']}" for d in returned["path"]
                        ],
                    }
                    print(pret)
                else:
                    print(returned)

        self.assertEqual(len(ret.data), len(expected_data_list))

        for returned_obj in ret.data:
            self.assertEqual(returned_obj["object"]["hubuum_class"], class2)

        # Check each returned object against expected data
        for expected_data, actual_data in zip(expected_data_list, ret.data):
            self.assertEqual(len(actual_data["path"]), len(expected_data["path"]))

            self.assertEqual(actual_data["object"]["name"], expected_data["name"])
            self.assertEqual(
                actual_data["object"]["hubuum_class"], expected_data["class"]
            )

            # Check each path item against expected values

            for i, class_obj_pair in enumerate(expected_data["path"]):
                expected_class, expected_obj = self.split_class_object(class_obj_pair)
                path_item = actual_data["path"][i]
                self.assertEqual(path_item["name"], expected_obj)
                self.assertEqual(path_item["hubuum_class"], expected_class)

        return ret

    def create_class_and_object(
        self, class_name: str, obj_name: str, json_data: Dict[str, Any] = None
    ) -> Tuple[HubuumClass, HubuumObject]:
        """Create a class and an object."""
        hubuum_class = HubuumClass.objects.create(
            name=class_name,
            namespace=self.namespace,
        )
        dynamic_object = HubuumObject.objects.create(
            name=obj_name,
            hubuum_class=hubuum_class,
            namespace=self.namespace,
            json_data=json_data or {"name": "Noone"},
        )
        return hubuum_class, dynamic_object

    def tearDown(self) -> None:
        """Delete the namespace after the test."""
        for namespace in self.namespaces:
            namespace.delete()
        return super().tearDown()


class APIv1Classes(APIv1Empty):
    """A base class with dynamic classes already created.

    Classes created are:
    - Host
    - Room
    - Building

    No objects are created.

    Utilizes the HubuumDynamicBase.create_classes method.
    """

    def setUp(self):
        """Set up a default namespace and creates the classes."""
        super().setUp()
        self.create_classes()


class APIv1Objects(APIv1Classes):
    """A base class with dynamic classes and objects already created.

    No links are created.

    Classes created are:
    - Host
    - Room
    - Building

    Objects created are:
    - Hosts (3, named host1, host2, host3)
    - Rooms (2, named room1, room2, room3)
    - Buildings (1, named building1)

    Utilizes the following methods:
     - HubuumDynamicBase.create_classes
     - HubuumDynamicBase.create_objects


    """

    def setUp(self):
        """Set up a default namespace and creates the classes."""
        super().setUp()
        self.create_objects()
