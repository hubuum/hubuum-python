"""Test the internals of the Populator class."""

from typing import Optional

import pytest
from django.test import TestCase

from hubuum.exceptions import MissingParam
from hubuum.models.dynamic import HubuumClass, HubuumObject
from hubuum.models.iam import Namespace
from hubuum.tests.helpers.populators import BasePopulator


class TestPopulators(BasePopulator, TestCase):
    """Test internal BasePopulator functionality."""

    def setUp(self) -> None:
        """Set up common test scenario."""
        self.namespace: Optional[Namespace] = None

    def create_namespace(self, name: str = "default") -> Namespace:
        """Create namespace for testing."""
        return Namespace.objects.create(name=name)

    def validate_class(
        self, class_instance: HubuumClass, name: str, namespace: Namespace
    ) -> None:
        """Validate class instance."""
        self.assertIsInstance(class_instance, HubuumClass)
        self.assertEqual(class_instance.name, name)
        self.assertEqual(class_instance.namespace, namespace)

    def validate_object(
        self, object_instance: HubuumObject, name: str, namespace: Namespace
    ) -> None:
        """Validate object instance."""
        self.assertIsInstance(object_instance, HubuumObject)
        self.assertEqual(object_instance.name, name)
        self.assertEqual(object_instance.namespace, namespace)

    def test_creating_class_with_self_namespace(self) -> None:
        """Test creating a class with self.namespace."""
        self.namespace = self.create_namespace()
        class1 = self.create_class_direct(name="Class1")

        self.validate_class(class1, "Class1", self.namespace)

        self.namespace.delete()

        with pytest.raises(HubuumClass.DoesNotExist):
            HubuumClass.objects.get(name="Class1")

    def test_creating_class_with_direct_namespace(self) -> None:
        """Test creating a class with explicit namespace."""
        namespace = self.create_namespace()
        class1 = self.create_class_direct(name="Class1", namespace=namespace)

        self.validate_class(class1, "Class1", namespace)

        namespace.delete()

        with pytest.raises(HubuumClass.DoesNotExist):
            HubuumClass.objects.get(name="Class1")

    def test_creating_class_with_no_namespace(self) -> None:
        """Test creating a class with no namespace."""
        self.namespace = None

        with pytest.raises(MissingParam):
            self.create_class_direct(name="Class1")

    def test_creating_object_with_self_namespace(self) -> None:
        """Test creating an object with self.namespace."""
        self.namespace = self.create_namespace()
        class1 = self.create_class_direct(name="Class1")
        object1 = self.create_object_direct(dynamic_class=class1, name="Object1")

        self.validate_object(object1, "Object1", self.namespace)

        self.namespace.delete()

        with pytest.raises(HubuumObject.DoesNotExist):
            HubuumObject.objects.get(name="Object1")

    def test_creating_object_with_direct_namespace(self) -> None:
        """Test creating an object with explicit namespace."""
        namespace = self.create_namespace()
        class1 = self.create_class_direct(name="Class1", namespace=namespace)
        object1 = self.create_object_direct(
            dynamic_class=class1, name="Object1", namespace=namespace
        )

        self.validate_object(object1, "Object1", namespace)

        namespace.delete()

        with pytest.raises(HubuumObject.DoesNotExist):
            HubuumObject.objects.get(name="Object1")

    def test_creating_object_with_no_namespace(self) -> None:
        """Test creating an object with no namespace."""
        self.namespace = None
        namespace = self.create_namespace()
        class1 = self.create_class_direct(name="Class1", namespace=namespace)

        with pytest.raises(MissingParam):
            self.create_object_direct(dynamic_class=class1, name="Object1")

    def test_create_in_model(self):
        """Test that create_in_model works."""
        namespace = self.create_namespace()
        obj = self.create_in_model("HubuumClass", name="Test", namespace=namespace)
        self.validate_class(obj, "Test", namespace)

        with pytest.raises(MissingParam):
            self.create_in_model("Nosuchmodel")
