"""Test the dynamic classes in hubuum."""

from copy import deepcopy
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

from hubuum.api.v1.tests.base import HubuumAPITestCase, HubuumAPITestCaseWithDynamics
from hubuum.api.v1.views.dynamic import DynamicAutoSchema
from hubuum.models.dynamic import DynamicClass, DynamicObject


def create_mocked_view(action: str, model_name: str) -> Mock:
    """Create a mocked view for testing the autoschema."""
    mocked_view = Mock()
    mocked_view.action = action

    # Mock the model's __name__ attribute
    mock_model = MagicMock()
    mock_model.configure_mock(__name__=model_name)
    mocked_view.queryset = Mock()
    mocked_view.queryset.model = mock_model

    return mocked_view


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
        operation = "GET"
        # We're using lists rather than a dict because black refuses
        # to break key-value pairs into multiple lines, causing the line
        # length to exceed limits.
        question = [
            "/{id}",
        ]

        # The first three are the same because the prefix is stripped
        answer = [
            f"listMockModelsID_{operation}",
        ]

        # Enumerate through the lists and test each one
        for i, value in enumerate(question):
            operation_id = self.schema.get_operation_id(value, operation)
            self.assertEqual(operation_id, answer[i])


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
        for identifier in ("id", "name"):
            oret = self._create_dynamic_object(
                dynamic_class=cret.data[identifier],
                json_data=json_data,
                name=f"test_{identifier}",
                namespace=cret.data["namespace"],
            )
            self.assertEqual(oret.data["name"], f"test_{identifier}")

    def test_creating_dynamic_object_with_schema(self):
        """Test creating a dynamic object with a schema."""
        cret = self._create_dynamic_class(
            json_schema=self.valid_schema,
            validate_schema=True,
        )
        json_data = {"age": 42}
        for identifier in ("id", "name"):
            oret = self._create_dynamic_object(
                dynamic_class=cret.data[identifier],
                json_data=json_data,
                name=f"test_{identifier}",
                namespace=cret.data["namespace"],
            )
            self.assertEqual(oret.data["name"], f"test_{identifier}")

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
            f"/dynamic/{cret.data['id']}/",
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
                f"/dynamic/{cret.data['id']}/",
                {
                    "name": "test_fail",
                    "namespace": cret.data["namespace"],
                    "json_data": data,
                },
            )


class DynamicObjectTestCase(HubuumAPITestCaseWithDynamics):
    """Test DynamicObject functionality."""

    def _get_object(self, dynamic_class: str, name: str) -> DynamicObject:
        """Get a dynamic object."""
        return self.assert_get(f"/dynamic/{dynamic_class}/{name}")

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

        namemap: Dict[str, int] = {}

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
                # Save the ID for later
                namemap[obj] = ret.data["id"]

        # Fetch every object created in every class by id, and test that the name is correct
        for dynamic_class, objects in objectmap.items():
            for obj in objects:
                ret = self._get_object(dynamic_class, namemap[obj])
                self.assertEqual(ret.data["name"], obj)

    def test_404(self):
        """Test that 404 is returned when fetching a non-existing classes or objects."""
        self.assert_get_and_404("/dynamic/classdoesnotexist")
        self.assert_get_and_404("/dynamic/Host/doesnotexist")
        self.assert_get_and_404("/dynamic/Host/999999")
