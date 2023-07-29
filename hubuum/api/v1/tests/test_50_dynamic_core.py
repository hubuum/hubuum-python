"""Test the dynamic classes in hubuum."""

from copy import deepcopy
from typing import Any, Dict, List, Type

from hubuum.api.v1.tests.base import HubuumAPITestCase, create_mocked_view
from hubuum.api.v1.views.dynamic import (
    DynamicAutoSchema,
    DynamicBaseView,
    HubuumObjectDetail,
    HubuumObjectList,
)
from hubuum.models.dynamic import HubuumClass, HubuumObject


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
            HubuumObjectDetail,
            HubuumObjectList,
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

    def create_class_direct(
        self,
        name: str = "Test",
        namespace_id: int = None,
        json_schema: str = None,
        validate_schema: bool = False,
    ) -> HubuumClass:
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

    def create_object_direct(
        self,
        dynamic_class: str = None,
        namespace: int = None,
        name: str = None,
        json_data: Dict[str, Any] = None,
    ) -> HubuumObject:
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


class HubuumClassTestCase(DynamicBaseTestCase):
    """Test HubuumClass functionality."""

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
        ret = self.create_class_direct(name="Test")
        self.assertEqual(ret.data["name"], "Test")

    def test_creating_dynamic_object(self):
        """Test creating a dynamic object."""
        cret = self.create_class_direct()
        json_data = {"key": "value", "listkey": [1, 2, 3]}
        oret = self.create_object_direct(
            dynamic_class=cret.data["name"],
            json_data=json_data,
            name="test",
            namespace=cret.data["namespace"],
        )
        self.assertEqual(oret.data["name"], "test")

    def test_creating_dynamic_object_with_schema(self):
        """Test creating a dynamic object with a schema."""
        cret = self.create_class_direct(
            json_schema=self.valid_schema,
            validate_schema=True,
        )
        json_data = {"age": 42}
        oret = self.create_object_direct(
            dynamic_class=cret.data["name"],
            json_data=json_data,
            name="test_name",
            namespace=cret.data["namespace"],
        )
        self.assertEqual(oret.data["name"], "test_name")

    def test_schema_is_valid(self):
        """Test that an uploaded schema is valid."""
        cret = self.create_class_direct(
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
        cret = self.create_class_direct(
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
        cret = self.create_class_direct(
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
