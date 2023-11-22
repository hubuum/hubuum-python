"""Provide a base class for testing model behaviour."""
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Model
from django.test import TestCase

from hubuum.exceptions import MissingParam
from hubuum.models.core import Attachment, AttachmentManager
from hubuum.models.iam import Namespace


class HubuumModelTestCase(TestCase):
    """Define the test suite for a generic model."""

    def setUp(self):
        """Set up defaults for the test object."""
        self.username = "test"
        self.password = "test"  # nosec
        self.groupname = "test"
        self.namespacename = "test"

        self.user, _ = get_user_model().objects.get_or_create(
            username=self.username, password=self.password
        )
        self.assertIsNotNone(self.user)

        self.group, _ = Group.objects.get_or_create(name=self.groupname)
        self.assertIsNotNone(self.group)

        self.namespace, _ = Namespace.objects.get_or_create(
            name=self.namespacename, description="Test namespace."
        )
        self.assertIsNotNone(self.namespace)

        self.attributes: Dict[str, Any] = {}
        self.obj = None

    def tearDown(self):
        """Clean up after each test."""
        self.user.delete()
        self.group.delete()

        if self.obj:
            self.obj.delete()

        self.namespace.delete()

    def attribute(self, key: str) -> Any:
        """Fetch attributes from the attribute dictionary."""
        return self.attributes[key]

    def _test_can_create_object(self, model: Model = None, **kwargs: Any) -> object:
        """Create a generic object of any model."""
        return self._create_object(model=model, **kwargs)

    def _test_has_identical_values(
        self, obj: object = None, dictionary: Dict[str, Any] = None
    ):
        """Compare the dictionary with the same attributes from the self."""
        if not (obj and dictionary):
            raise MissingParam

        for key in dictionary.keys():
            self.assertEqual(getattr(obj, key), dictionary[key])

    def _create_object(self, model: Model = None, **kwargs: Any) -> object:
        """Create an object with overridable default group ownership."""
        if not model:
            raise MissingParam

        obj, _ = model.objects.get_or_create(**kwargs)
        self.assertIsNotNone(obj)
        self.assertIsInstance(obj, model)
        return obj

    def _test_str(self):
        """Test that stringifying objects works as expected."""
        obj = self.obj
        if isinstance(obj, (Attachment, AttachmentManager)):
            self.assertEqual(str(obj), str(obj.id))
        else:
            self.assertEqual(str(obj), self.attribute("name"))
