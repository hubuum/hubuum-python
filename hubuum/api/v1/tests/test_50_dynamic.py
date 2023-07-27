"""Test the dynamic classes in hubuum."""

from copy import deepcopy
from typing import Any, Dict, List, Tuple, Type

from django.http import HttpResponse

from hubuum.api.v1.tests.base import (
    HubuumAPITestCase,
    HubuumDynamicClassesAndObjects,
    create_mocked_view,
)
from hubuum.api.v1.views.dynamic import (
    DynamicAutoSchema,
    DynamicBaseView,
    DynamicObjectDetail,
    DynamicObjectList,
)
from hubuum.models.dynamic import DynamicClass, DynamicLink, DynamicObject, LinkType


class HubuumAttachmentSchemaTestCase(HubuumAPITestCase):
    """Test the custom autoschema for operation IDs."""

    def setUp(self):
        """Set up the test environment for the class."""
        self.action = "list"
        self.model_name = "MockModel"
        self.schema = DynamicAutoSchema()
        self.schema.view = create_mocked_view(self.action, self.model_name)
        return super().setUp()

    def test_operation_id_generation_from_url(self):
        """Test different URLs and see what we get back."""
        # We're using lists rather than a dict because black refuses
        # to break key-value pairs into multiple lines, causing the line
        # length to exceed limits.
        question = ["/{id}", "/<classname>/<pk>/link/<object1>/<object2>"]

        # The first three are the same because the prefix is stripped
        answer = [
            "mockmodel_list_id",
            "mockmodel_list_classname_pk_link_object1_object2",
        ]

        # Enumerate through the lists and test each one
        for i, value in enumerate(question):
            operation_id = self.schema.get_operation_id(value, "GET")
            self.assertEqual(operation_id, answer[i])


class DynamicGenerateSchemaTestCase(HubuumAPITestCase):
    """Test that generateschema specifics are handled correctly."""

    def test_get_queryset_for_generateschema(self):
        """Test that get_queryset returns nothing when called from generateschema."""
        class_list: List[Type[DynamicBaseView]] = [
            DynamicObjectDetail,
            DynamicObjectList,
        ]
        for cls in class_list:
            view = cls()
            view.request = None
            self.assertEqual(view.get_queryset().count(), 0)


class DynamicBaseTestCase(HubuumAPITestCase):
    """Base class for testing dynamic structures."""

    def setUp(self):
        """Create a default namespace."""
        super().setUp()
        self.namespace = self._create_namespace()

    def tearDown(self) -> None:
        """Delete all dynamic classes and objects."""
        super().tearDown()
        self.namespace.delete()

    def _create_dynamic_class(
        self,
        name: str = "Test",
        namespace_id: int = None,
        json_schema: str = None,
        validate_schema: bool = False,
    ) -> DynamicClass:
        """Create a dynamic class."""
        if not namespace_id:
            namespace_id = self.namespace.id

        ret = self.assert_post(
            "/dynamic/",
            {
                "name": name,
                "namespace": namespace_id,
                "json_schema": json_schema,
                "validate_schema": validate_schema,
            },
        )

        return ret

    def _create_dynamic_object(
        self,
        dynamic_class: str = None,
        namespace: int = None,
        name: str = None,
        json_data: Dict[str, Any] = None,
    ) -> DynamicObject:
        """Create a dynamic object."""
        ret = self.assert_post(
            f"/dynamic/{dynamic_class}/",
            {
                "name": name,
                "namespace": namespace,
                "json_data": json_data,
            },
        )

        return ret


class DynamicClassTestCase(DynamicBaseTestCase):
    """Test DynamicClass functionality."""

    valid_schema = {
        "$id": "https://example.com/person.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Person",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "age": {
                "description": "Age in years which must be equal to or greater than zero.",
                "type": "integer",
                "minimum": 0,
                "maximum": 150,
            },
        },
    }

    def test_creating_dynamic_class(self):
        """Test creating a dynamic class."""
        ret = self._create_dynamic_class(name="Test")
        self.assertEqual(ret.data["name"], "Test")

    def test_creating_dynamic_object(self):
        """Test creating a dynamic object."""
        cret = self._create_dynamic_class()
        json_data = {"key": "value", "listkey": [1, 2, 3]}
        oret = self._create_dynamic_object(
            dynamic_class=cret.data["name"],
            json_data=json_data,
            name="test",
            namespace=cret.data["namespace"],
        )
        self.assertEqual(oret.data["name"], "test")

    def test_creating_dynamic_object_with_schema(self):
        """Test creating a dynamic object with a schema."""
        cret = self._create_dynamic_class(
            json_schema=self.valid_schema,
            validate_schema=True,
        )
        json_data = {"age": 42}
        oret = self._create_dynamic_object(
            dynamic_class=cret.data["name"],
            json_data=json_data,
            name="test_name",
            namespace=cret.data["namespace"],
        )
        self.assertEqual(oret.data["name"], "test_name")

    def test_schema_is_valid(self):
        """Test that an uploaded schema is valid."""
        cret = self._create_dynamic_class(
            name="SchemaOK",
            json_schema=self.valid_schema,
            validate_schema=True,
        )

        invalid_schemas: List[Any] = [
            "not a schema",
            [],
            {"type": "wrong"},
        ]

        for invalid_schema in invalid_schemas:
            self.assert_post_and_400(
                "/dynamic/",
                {
                    "name": "FailingSchema",
                    "namespace": cret.data["namespace"],
                    "json_schema": invalid_schema,
                    "validate_schema": True,
                },
            )

    def test_schema_patching(self):
        """Test that schemas can be patched in an additive way only."""
        cret = self._create_dynamic_class(
            name="SchemaOK",
            json_schema=self.valid_schema,
            validate_schema=True,
        )

        # Patching additional properties should work
        new_valid_schema = deepcopy(self.valid_schema)
        new_valid_schema["properties"]["location"] = {
            "description": "Location",
            "type": "string",
        }
        pret = self.assert_patch(
            f"/dynamic/{cret.data['name']}",
            {"json_schema": new_valid_schema},
        )
        self.assertEqual(pret.data["json_schema"], new_valid_schema)
        self.assertNotEqual(pret.data["json_schema"], self.valid_schema)

        # Patching and removing properties should NOT work
        new_invalid_schema = deepcopy(self.valid_schema)
        del new_invalid_schema["additionalProperties"]
        self.assert_patch_and_400(
            f"/dynamic/{cret.data['name']}",
            {"json_schema": new_invalid_schema},
        )

        new_invalid_schema = deepcopy(self.valid_schema)
        del new_invalid_schema["properties"]["age"]["minimum"]
        self.assert_patch_and_400(
            f"/dynamic/{cret.data['name']}",
            {"json_schema": new_invalid_schema},
        )

    def test_schema_validation(self):
        """Test that schema validation works."""
        schema = {
            "$id": "https://example.com/person.schema.json",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Person",
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The persons name.",
                },
                "age": {
                    "description": "Age in years which must be equal to or greater than zero.",
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 150,
                },
            },
        }

        # Create a class with a schema
        cret = self._create_dynamic_class(
            name="SchemaPerson",
            json_schema=schema,
            validate_schema=True,
        )

        # Create an object with valid data
        self.assert_post(
            f"/dynamic/{cret.data['name']}/",
            {
                "name": "test_ok",
                "namespace": cret.data["namespace"],
                "json_data": {"name": "John Doe", "age": 21},
            },
        )

        failing_data = [
            # Negative age
            {"name": "John Doe", "age": -1},
            # Too old
            {"name": "John Doe", "age": 151},
            # Wrong type for name, must be string
            {"name": [], "age": 21},
            {"name": {}, "age": 21},
            {"name": 42, "age": 21},
            # Missing name
            {"age": 21},
            # Wrong type for age, must be integer
            {"name": "John Doe", "age": {}},
            # "21" is a string, not an integer
            {"name": "John Doe", "age": "21"},
            # The schema does not allow additional properties (like aage)
            # Note that "age" is missing, but is not required
            {"name": "John Doe", "aage": 21},
        ]

        # Test failing schemas
        for data in failing_data:
            self.assert_post_and_400(
                f"/dynamic/{cret.data['name']}/",
                {
                    "name": "test_fail",
                    "namespace": cret.data["namespace"],
                    "json_data": data,
                },
            )


class DynamicObjectTestCase(HubuumDynamicClassesAndObjects):
    """Test DynamicObject functionality."""

    def _get_object(self, dynamic_class: str, name: str) -> DynamicObject:
        """Get a dynamic object."""
        return self.assert_get(f"/dynamic/{dynamic_class}/{name}")

    def split_class_object(self, class_object: str) -> Tuple[str, str]:
        """Split a class.object string into class and object."""
        return class_object.split(".")

    def create_link_type(self, class1: str, class2: str) -> HttpResponse:
        """Create a link type between two classes."""
        return self.assert_post(
            f"/dynamic/{class1}/{class2}/linktype/",
            {"max_links": 0, "namespace": self.namespace.id},
        )

    def create_link(self, class1_obj1: str, class2_obj2: str) -> HttpResponse:
        """Create a link between two objects."""
        class1, obj1 = self.split_class_object(class1_obj1)
        class2, obj2 = self.split_class_object(class2_obj2)
        return self.assert_post(
            f"/dynamic/{class1}/{obj1}/link/{class2}/{obj2}",
            {"namespace": self.namespace.id},
        )

    def check_link_exists(
        self, class1_obj1: str, class2: str, expected_data_list: List[Dict[str, Any]]
    ) -> HttpResponse:
        """Check that a link exists between two objects."""
        class1, obj1 = self.split_class_object(class1_obj1)
        ret = self.assert_get_elements(
            f"/dynamic/{class1}/{obj1}/links/{class2}/?transitive=true",
            len(expected_data_list),
        )
        for returned_obj in ret.data:
            self.assertEqual(returned_obj["object"]["dynamic_class"], class2)

        # Check each returned object against expected data
        for expected_data, actual_data in zip(
            expected_data_list, ret.data, strict=True
        ):
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
    ) -> Tuple[DynamicClass, DynamicObject]:
        """Create a class and an object."""
        dynamic_class = DynamicClass.objects.create(
            name=class_name,
            namespace=self.namespace,
        )
        dynamic_object = DynamicObject.objects.create(
            name=obj_name,
            dynamic_class=dynamic_class,
            namespace=self.namespace,
            json_data=json_data or {"name": "Noone"},
        )
        return dynamic_class, dynamic_object

    def test_internals(self):
        """Test the internals of the class generation."""
        # Test that the number of objects and classes is correct
        self.assertEqual(DynamicClass.objects.count(), len(self.all_classes()))
        self.assertEqual(DynamicObject.objects.count(), len(self.all_objects()))

        # Try patching a non-existing linktype
        self.assert_patch_and_404(
            "/dynamic/Room/Host/linktype/",
            {"namespace": self.namespace.id, "max_links": 1},
        )

        # Test creating a link type between Host and Room
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_get("/dynamic/Host/Room/linktype/")
        self.assert_get("/dynamic/Room/Host/linktype/")
        self.assert_post_and_409(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        # Upgrading links:
        for i in range(2, 4):
            self.assert_patch("/dynamic/Host/Room/linktype/", {"max_links": i})
            hrret = self.assert_get("/dynamic/Host/Room/linktype/")
            rhret = self.assert_get("/dynamic/Room/Host/linktype/")
            self.assertEqual(hrret.data["max_links"], i)
            self.assertEqual(rhret.data["max_links"], i)

        ns_create_ret = self._create_namespace("ns2")
        # Sending {"namespace", foo} fails with an exception
        # namespace_id = request.data.get("namespace", None)
        # AttributeError: 'list' object has no attribute 'get'
        nsret = self.assert_patch(
            "/dynamic/Room/Host/linktype/", {"namespace": ns_create_ret.id}
        )
        self.assertEqual(nsret.data["namespace"], ns_create_ret.id)

        # Try patching a non-existing namespace
        self.assert_patch_and_404(
            "/dynamic/Room/Host/linktype/", {"namespace": 999999999}
        )

        # Test str representation of the link type
        linktype = LinkType.objects.get(
            source_class__name="Host", target_class__name="Room"
        )
        self.assertEqual(str(linktype), "Host <-> Room (3)")

        # Test creating a link between host1 and room1
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )

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
        link = DynamicLink.objects.get(source__name="host1", target__name="room1")
        self.assertEqual(str(link), "host1 [Host] <-> room1 [Room]")

    def test_failing_specific_link_get(self):
        """Test that fetching non-existent links fails."""
        self.assert_get_and_404("/dynamic/Host/Room/linktype/")
        self.assert_get_and_404(
            "/dynamic/Host/host1/link/Room/room1",
        )
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
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

    def test_failing_linktype_creation(self):
        """Test that creating linktypes between non-existing classes fails."""
        self.assert_post_and_404(
            "/dynamic/Host/Nope/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_post_and_404(
            "/dynamic/Nope/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        # Test that sending a non-existent namespace fails.
        self.assert_post_and_404(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": 999999},
        )

    def test_failing_link_creation(self):
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
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_post_and_404(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": 999999},
        )

    def test_that_link_creation_fails_when_max_links_is_reached(self):
        """Test that creating a link fails when the max number of links is reached."""
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        # Test creating a link between host1 and room1
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        # Test creating a link between host1 and room2, which should fail as we have
        # defined a link type between Host and Room with max_links=1
        self.assert_post_and_409(
            "/dynamic/Host/host1/link/Room/room2",
            {"namespace": self.namespace.id},
        )

    def test_deleting_linktype(self):
        """Test that deleting a link type works."""
        self.assert_delete_and_404("/dynamic/Nope/Room/linktype/")
        self.assert_delete_and_404("/dynamic/Host/Nope/linktype/")
        self.assert_delete_and_404("/dynamic/Host/Room/linktype/")
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        self.assert_get("/dynamic/Host/host1/link/Room/room1")
        self.assert_delete("/dynamic/Host/Room/linktype/")
        self.assert_get_and_404("/dynamic/Host/host1/link/Room/room1")

    def test_creating_object_in_nonexisting_class(self):
        """Test creating an object in a non-existing class."""
        self.assert_post_and_404(
            "/dynamic/NonExistingClass/",
            {
                "name": "test",
                "namespace": self.namespace.id,
                "json_data": {},
            },
        )

    def test_linking_between_objects(self):
        """Test that manipulating links between objects works."""
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 0, "namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        self.assert_get("/dynamic/Host/host1/link/Room/room1")
        # implicit bidirectionality
        self.assert_get("/dynamic/Room/room1/link/Host/host1")
        self.assert_get_elements("/dynamic/Host/host1/links/", 1)
        self.assert_get_elements("/dynamic/Room/room1/links/", 1)
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room2",
            {"namespace": self.namespace.id},
        )
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

    def test_multiple_links_to_same_class(self):
        """Test that multiple links to the same class works."""
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 0, "namespace": self.namespace.id},
        )
        for room in ["room1", "room2"]:
            self.assert_post(
                "/dynamic/Host/host1/link/Room/" + room,
                {"namespace": self.namespace.id},
            )
        self.assert_get_elements("/dynamic/Host/host1/links/Room/", 2)
        self.assert_get_elements("/dynamic/Host/host1/links/", 2)

    def test_transitive_linking(self):
        """Test transitive linking."""
        self.create_link_type("Host", "Room")
        self.create_link_type("Room", "Building")
        self.create_link("Host.host1", "Room.room1")

        self.check_link_exists(
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
        self.create_link("Room.room1", "Building.building1")

        self.check_link_exists(
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
        self.create_link_type("Building", "Person")
        self.create_link("Building.building1", "Person.person1")

        self.check_link_exists(
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
        self.check_link_exists(
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
        self.create_link_type("Room", "Person")
        self.create_link("Room.room1", "Person.person1")

        self.check_link_exists(
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

    def test_fetching_classes_and_objects(self):
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
                ret = self._get_object(dynamic_class, obj)
                self.assertEqual(ret.data["name"], obj)

    def test_404(self):
        """Test that 404 is returned when fetching a non-existing classes or objects."""
        self.assert_get_and_404("/dynamic/classdoesnotexist")
        self.assert_get_and_404("/dynamic/Host/doesnotexist")
        self.assert_get_and_404("/dynamic/Host/999999")
