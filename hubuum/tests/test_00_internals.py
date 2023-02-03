"""Test module: Users and Groups."""
import pytest
from rest_framework.exceptions import NotFound

from hubuum.exceptions import MissingParam
from hubuum.models import User
from hubuum.tools import get_object

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
        assert isinstance(get_object(User, "test"), User) is True
        assert get_object(User, "doesnotexist", throw_exception=False) is None
        with pytest.raises(NotFound):
            assert get_object(User, "doesnotexist")
