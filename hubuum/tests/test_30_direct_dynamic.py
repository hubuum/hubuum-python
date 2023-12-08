"""Test the dynamic classes in hubuum."""

from typing import cast

from hubuum.models.core import HubuumClass, HubuumObject
from hubuum.models.iam import Namespace
from hubuum.tests.base import HubuumModelTestCase


class DynamicBaseTestCase(HubuumModelTestCase):
    """Base class for testing dynamic structures."""

    def create_class_direct(self, name: str = "Test", namespace: Namespace = None) -> HubuumClass:
        """Create a dynamic class."""
        if not namespace:
            namespace = self.namespace

        attributes = {"name": name, "namespace": namespace}
        return cast(HubuumClass, self._create_object(model=HubuumClass, **attributes))

    def create_object_direct(
        self, hubuum_class: HubuumClass = None, namespace: Namespace = None
    ) -> HubuumObject:
        """Create a dynamic object."""
        if not namespace:
            namespace = self.namespace

        attributes = {
            "json_data": {"key": "value", "listkey": [1, 2, 3]},
            "namespace": namespace,
        }
        return cast(
            HubuumObject,
            self._create_object(model=HubuumObject, hubuum_class=hubuum_class, **attributes),
        )


class HubuumClassTestCase(DynamicBaseTestCase):
    """Test HubuumClass functionality."""

    def test_creating_hubuum_class(self):
        """Test creating a dynamic class."""
        hubuum_class = self.create_class_direct()
        self.assertEqual(hubuum_class.name, "Test")
        self.assertEqual(hubuum_class.__str__(), "Test")

    def test_creating_dynamic_object(self):
        """Test creating a dynamic object."""
        hubuum_class = self.create_class_direct()
        dynamic_object = self.create_object_direct(hubuum_class=hubuum_class)
        self.assertEqual(dynamic_object.__str__(), f"{dynamic_object.name} [{hubuum_class.name}]")
