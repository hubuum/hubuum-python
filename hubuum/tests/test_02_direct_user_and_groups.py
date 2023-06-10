"""Test module: Users and Groups."""
import pytest
from django.contrib.auth.models import Group
from django.test import TestCase

from hubuum.exceptions import MissingParam
from hubuum.models.iam import User


class UserAndGroupTestCase(TestCase):
    """Define the test suite for the User and Group models."""

    def setUp(self) -> None:
        """Set up defaults for the test object."""
        self.username = "tester"
        self.password = "testpassword"  # nosec

        self.groupname = "testgroup"

        self.user = None
        self.group = None

    def test_user_has_perm(self):
        """Test has_perm for input management."""
        self.user = User.objects.create(username=self.username, password=self.password)
        self.assertIsNotNone(self.user)

        with pytest.raises(MissingParam):
            self.user.has_perm("nope")
        with pytest.raises(MissingParam):
            self.user.has_perm("hubuum.view_nosuchmodel")
        with pytest.raises(MissingParam):
            self.user.has_perm("hubuum.nosuchperm_host")

    def test_user_has_groups(self):
        """Test group list from the user."""
        self.user = User.objects.create(username=self.username, password=self.password)
        self.assertIsNotNone(self.user)
        self.group = Group.objects.create(name=self.groupname)
        self.user.groups.set([self.group])
        self.assertEqual(self.user.group_list[0], self.groupname)

    def test_can_create_user(self):
        """Try to create a user."""
        self.user = User.objects.create(username=self.username, password=self.password)
        self.assertIsNotNone(self.user)

    def test_can_create_group(self):
        """Try to create a group."""
        self.group = Group.objects.create(name=self.groupname)
        self.assertIsNotNone(self.group)

    def test_can_assign_group_to_user(self):
        """Try to make a user a member of a group."""
        self.user = User.objects.create(username=self.username, password=self.password)
        self.assertIsNotNone(self.user)
        self.group = Group.objects.create(name=self.groupname)
        self.assertIsNotNone(self.group)
        self.user.groups.set([self.group])
        self.assertEqual(self.user.groups.all()[0].name, self.groupname)
        self.assertCountEqual(self.user.groups.all(), [self.group])
