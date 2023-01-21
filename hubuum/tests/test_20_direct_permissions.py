"""Test module: Permissions."""
from django.test import TestCase
from django.contrib.auth.models import Group

from hubuum.models import User, Host, Namespace, Permissions


class PermissionsTestCase(TestCase):
    """This class defines the test suite for the Permission model."""

    def setUp(self) -> None:
        """Set up example users and groups."""
        self.one = User.objects.create(username="one", password="test")
        self.two = User.objects.create(username="two", password="test")
        self.staff = User.objects.create(username="staff", password="test")
        self.superuser = User.objects.create(username="superuser", password="test")

        self.superuser.is_superuser = True
        self.staff.is_staff = True

        self.onegroup = Group.objects.create(name="one")
        self.twogroup = Group.objects.create(name="two")

        self.onenamespace = Namespace.objects.create(name="one")
        self.twonamespace = Namespace.objects.create(name="two")

        self.onepermissions = Permissions.objects.create(
            namespace=self.onenamespace,
            group=self.onegroup,
            has_create=True,
            has_read=True,
            has_update=True,
            has_delete=True,
            has_namespace=True,
        )

        self.twopermissions = Permissions.objects.create(
            namespace=self.twonamespace,
            group=self.twogroup,
            has_create=True,
            has_read=True,
            has_update=True,
            has_delete=True,
            has_namespace=True,
        )

        self.one.groups.set([self.onegroup])
        self.two.groups.set([self.twogroup])

        self.onehost = Host.objects.create(name="one", namespace=self.onenamespace)
        self.twohost = Host.objects.create(name="two", namespace=self.twonamespace)

        self.read_perm = "hubuum.read_host"

    def test_access_to_host_belonging_to_one(self):
        """This object readable by one via onegroup, but not readable by two via twogroup."""
        self.assertTrue(self.one.has_perm(self.read_perm, self.onehost))
        self.assertFalse(self.two.has_perm(self.read_perm, self.onehost))

    def test_access_to_host_belonging_to_two(self):
        """This object readable by two via twogroup, but not readable by one via onegroup."""
        self.assertFalse(self.one.has_perm(self.read_perm, self.twohost))
        self.assertTrue(self.two.has_perm(self.read_perm, self.twohost))

    def test_access_grant_and_revoke_read_to_two(self):
        """This object readable by two via twogroup, but full access via onegroup."""
        # 1. Find the namespace for the object.
        # 2. Add an entry to the permissions model where twogroup has read to the namespace.
        self.assertFalse(self.two.has_perm(self.read_perm, self.onehost))
        Permissions.objects.create(
            namespace=self.onehost.namespace, group=self.twogroup, has_read=True
        )
        self.assertTrue(self.two.has_perm(self.read_perm, self.onehost))
        Permissions.objects.filter(
            namespace=self.onehost.namespace, group=self.twogroup
        ).delete()
        self.assertFalse(self.two.has_perm(self.read_perm, self.onehost))
