"""Test the dynamic classes in hubuum."""

from typing import cast

from hubuum.models.dynamic import DynamicClass, DynamicObject
from hubuum.models.iam import Namespace
from hubuum.tests.base import HubuumModelTestCase


class DynamicBaseTestCase(HubuumModelTestCase):
    """Base class for testing dynamic structures."""

    def _create_dynamic_class(
        self, name: str = "Test", namespace: Namespace = None
    ) -> DynamicClass:
        """Create a dynamic class."""
        if not namespace:
            namespace = self.namespace

        attributes = {"name": name, "namespace": namespace}
        return cast(DynamicClass, self._create_object(model=DynamicClass, **attributes))

    def _create_dynamic_object(
        self, dynamic_class: DynamicClass = None, namespace: Namespace = None
    ) -> DynamicObject:
        """Create a dynamic object."""
        if not namespace:
            namespace = self.namespace

        attributes = {
            "json_data": {"key": "value", "listkey": [1, 2, 3]},
            "namespace": namespace,
        }
        return cast(
            DynamicObject,
            self._create_object(
                model=DynamicObject, dynamic_class=dynamic_class, **attributes
            ),
        )


class DynamicClassTestCase(DynamicBaseTestCase):
    """Test DynamicClass functionality."""

    def test_creating_dynamic_class(self):
        """Test creating a dynamic class."""
        dynamic_class = self._create_dynamic_class()
        self.assertEqual(dynamic_class.name, "Test")
        self.assertEqual(dynamic_class.__str__(), "Test")

    def test_creating_dynamic_object(self):
        """Test creating a dynamic object."""
        dynamic_class = self._create_dynamic_class()
        dynamic_object = self._create_dynamic_object(dynamic_class=dynamic_class)
        self.assertEqual(
            dynamic_object.__str__(), f"{dynamic_object.name} [{dynamic_class.name}]"
        )
