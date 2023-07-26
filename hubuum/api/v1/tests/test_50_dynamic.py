"""Test the dynamic classes in hubuum."""

from copy import deepcopy
from typing import Any, Dict, List, Type

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

    def test_internals(self):
        """Test the internals of the class generation."""
        # Test that the number of objects and classes is correct
        self.assertEqual(DynamicClass.objects.count(), len(self.all_classes()))
        self.assertEqual(DynamicObject.objects.count(), len(self.all_objects()))

        # Test creating a link type between Host and Room
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        self.assert_get("/dynamic/Host/Room/linktype/")
        self.assert_post_and_409(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 1, "namespace": self.namespace.id},
        )
        # Upgrading links:
        self.assert_patch("/dynamic/Host/Room/linktype/", {"max_links": 2})

        # Test str representation of the link type
        linktype = LinkType.objects.get(
            source_class__name="Host", target_class__name="Room"
        )
        self.assertEqual(str(linktype), "Host <-> Room (2)")

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
        self.assert_get_elements("/dynamic/Host/host1/links/", 1)
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room2",
            {"namespace": self.namespace.id},
        )
        self.assert_get_elements("/dynamic/Host/host1/links/", 2)
        self.assert_delete("/dynamic/Host/host1/link/Room/room1")
        self.assert_delete_and_404("/dynamic/Host/host1/link/Room/room1")
        self.assert_get_elements("/dynamic/Host/host1/links/", 1)
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
        self.assert_post(
            "/dynamic/Host/Room/linktype/",
            {"max_links": 0, "namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Room/Building/linktype/",
            {"max_links": 0, "namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Host/host1/link/Room/room1",
            {"namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Room/room1/link/Building/building1",
            {"namespace": self.namespace.id},
        )
        ret = self.assert_get_elements("/dynamic/Host/host1/links/Room/", 1)
        self.assertEqual(ret.data[0]["name"], "room1")
        self.assertEqual(ret.data[0]["dynamic_class"], "Room")

        self.assert_get_and_404("/dynamic/Host/host1/links/Building/")
        ret2 = self.assert_get_elements(
            "/dynamic/Host/host1/links/Building/?transitive=true", 1
        )
        self.assertEqual(ret2.data[0]["object"]["name"], "building1")
        self.assertEqual(ret2.data[0]["object"]["dynamic_class"], "Building")
        self.assertEqual(ret2.data[0]["path"], ["Room", "Building"])

        # Create a person class and a person object
        person_class = DynamicClass.objects.create(
            name="Person",
            namespace=self.namespace,
        )
        DynamicObject.objects.create(
            name="person1",
            dynamic_class=person_class,
            namespace=self.namespace,
            json_data={"name": "Noone"},
        )
        # First verify that there is no path between Host:host1 and Person
        self.assert_get_and_404("/dynamic/Host/host1/links/Person/?transitive=true")

        # Link person1 to building1, but first link Building to Person
        # This should create a transitive link between Host and Person
        # via Room and Building
        self.assert_post(
            "/dynamic/Building/Person/linktype/",
            {"max_links": 0, "namespace": self.namespace.id},
        )
        self.assert_post(
            "/dynamic/Building/building1/link/Person/person1",
            {"namespace": self.namespace.id},
        )
        ret3 = self.assert_get_elements(
            "/dynamic/Host/host1/links/Person/?transitive=true", 1
        )
        self.assertEqual(ret3.data[0]["object"]["name"], "person1")
        self.assertEqual(ret3.data[0]["object"]["dynamic_class"], "Person")
        self.assertEqual(ret3.data[0]["path"], ["Room", "Building", "Person"])

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
