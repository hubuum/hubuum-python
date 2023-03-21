"""Test module: Users and Groups."""
import pytest
from rest_framework.exceptions import NotFound, ValidationError

from hubuum.exceptions import MissingParam
from hubuum.models.auth import User
from hubuum.models.base import Host, Namespace, model_supports_extensions
from hubuum.tools import get_object
from hubuum.validators import validate_model

from .base import HubuumModelTestCase


class InternalsTestCase(HubuumModelTestCase):
    """This class defines the test suite for internal structures."""

    def test_exception_missing_param(self):
        """Test the MissingParam exception."""
        # _create_object requires kwarg model.
        with pytest.raises(MissingParam):
            self._create_object()

        # _test_has_identical_values requires kwargs dictionary and object
        with pytest.raises(MissingParam):
            self._test_has_identical_values()
        with pytest.raises(MissingParam):
            self._test_has_identical_values(obj=self.user)
        with pytest.raises(MissingParam):
            self._test_has_identical_values(dictionary={})

    def test_get_object(self):
        """Test the get_object interface from tools."""
        self.assertTrue(isinstance(get_object(User, "test"), User))
        self.assertTrue(get_object(User, "doesnotexist", raise_exception=False) is None)
        with pytest.raises(NotFound):
            self.assertTrue(get_object(User, "doesnotexist"))

    def test_has_perm(self):
        """Test the internals of has_perm."""
        # These should never happen, but are handled.
        test = User.objects.get(username="test")
        self.assertFalse(test.has_perm("hubuum.read_namespace", None))
        with pytest.raises(MissingParam):
            test.has_perm("nosuchperm", None)
        with pytest.raises(MissingParam):
            test.has_perm("hubuum.x_y", None)
        with pytest.raises(MissingParam):
            test.has_perm("hubuum.nosuchperm_host", None)
        with pytest.raises(MissingParam):
            test.has_perm("hubuum.read_nosuchmodel", None)
        with pytest.raises(MissingParam):
            test.namespaced_can("nosuchperm", None)

        Namespace.objects.get_or_create(name="root")
        self.assertFalse(test.has_namespace("root"))
        with pytest.raises(NotFound):
            test.has_namespace("rootnotfound.no")
        with pytest.raises(NotFound):
            test.has_namespace("rootnotfound.no.reallyno")
        with pytest.raises(NotFound):
            test.has_namespace(12)

    def test_extensions_validation_errors(self):
        """Test exceptions from the extensions."""
        # Test that extension support checking works.
        self.assertTrue(model_supports_extensions("Host"))
        self.assertTrue(model_supports_extensions(Host))

        # Test that we require data["model"] to be a string
        with pytest.raises(ValidationError):
            validate_model({})

        with pytest.raises(ValidationError):
            validate_model({})

        # Test that when we have a string, we have a model with that name.
        with pytest.raises(ValidationError):
            validate_model("nosuchmodel")

        # Test that when we have a string, and a model with the name, but it does
        # not support extensions.
        with pytest.raises(ValidationError):
            validate_model("user")

        with pytest.raises(ValidationError):
            validate_model("permission")

        self.assertTrue(validate_model("host"))
