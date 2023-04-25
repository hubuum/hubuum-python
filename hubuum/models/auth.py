"""Authentication-related models for the hubuum project."""
import re

from django.contrib.auth.models import AbstractUser, Group
from rest_framework.exceptions import NotFound

from hubuum.exceptions import MissingParam
from hubuum.models.permissions import Namespace, Permission
from hubuum.permissions import operation_exists
from hubuum.tools import get_model, get_object


def get_user(user_identifier, raise_exception=True):
    """Try to find a user based on the identifier.

    Searches in User.lookup_fields
    """
    return get_object(User, user_identifier, raise_exception=raise_exception)


def get_group(group_identifier, raise_exception=True):
    """Try to find a group based on the identifier.

    param: group_identifier

    return: group object

    raises: NotFound if no object found.
    """
    return get_object(
        Group,
        group_identifier,
        lookup_fields=["id", "name"],
        raise_exception=raise_exception,
    )


class User(AbstractUser):
    """Extension to the default User class."""

    model_permissions_pattern = re.compile(
        r"^hubuum.(create|read|update|delete|namespace)_(\w+)$"
    )
    lookup_fields = ["id", "username", "email"]

    _group_list = None

    def is_admin(self):
        """Check if the user is any type of admin (staff/superadmin) (or in a similar group?)."""
        return self.is_staff or self.is_superuser

    @classmethod
    def supports_extensions(cls):
        """Check if a class supports extensions."""
        return False

    @property
    def group_list(self):
        """List the names of all the groups the user is a member of."""
        if self._group_list is None:
            self._group_list = list(self.groups.values_list("name", flat=True))
        return self._group_list

    def group_count(self):
        """Return the number of groups the user is a member of."""
        return self.groups.count()

    def has_only_one_group(self):
        """Return true if the user is a member of only one group."""
        return self.group_count() == 1

    def is_member_of(self, group):
        """Check if the user is a member of a specific group."""
        return self.is_member_of_any([group])

    def is_member_of_any(self, groups):
        """Check to see if a user is a member of any of the groups in the list."""
        return bool([i for i in groups if i in self.groups.all()])

    def namespaced_can(self, perm, namespace) -> bool:
        """Check to see if the user can perform perm for namespace.

        param: perm (permission string, 'has_[create|read|update|delete|namespace])
        param: namespace (namespace object)
        return True|False
        """
        if not operation_exists(perm, fully_qualified=True):
            raise MissingParam(f"Unknown permission '{perm}' passed to namespaced_can.")

        # We need to check if the user is a member of a group
        # that has the given permission the namespace.
        groups = namespace.groups_that_can(perm)
        return self.is_member_of_any(groups)

    def has_namespace(
        self,
        namespace,
        write_perm="has_namespace",
    ):
        """Check if the user has namespace permissions for the given namespace.

        Only admin users can create or populate root namespaces.

        For users, if the namespace isn't scoped (contains no dots), return False.
        Otherwise, check if the user can:
          - create the namespace (using has_namespace) or,
          - create objects in the namespace (using has_create) on the last element.
        """
        if isinstance(namespace, int):
            try:
                namespace_obj = Namespace.objects.get(pk=namespace)
                return self.namespaced_can(write_perm, namespace_obj)
            except Namespace.DoesNotExist as exc:
                raise NotFound from exc

        scope = namespace.split(".")
        if len(scope) == 1:
            return False

        if write_perm == "has_namespace":
            target = scope[-2]

        try:
            namespace_obj = Namespace.objects.get(name=target)
        except Namespace.DoesNotExist as exc:
            raise NotFound from exc

        return self.namespaced_can(write_perm, namespace_obj)

    #        try:
    #            parent = Namespace.objects.get(name=scope[-1])
    #        except Namespace.DoesNotExist:
    #            return False

    #        return Permission.objects.filter(
    #            namespace=parent.id, has_namespace=True, group__in=self.groups.all()
    #        ).exists()

    def has_perm(self, perm: str, obj: object = None) -> bool:
        """
        Model (?) permissions check for an object.

        perm: see permissions.py
        obj: Hubuum Object
        """
        field = None

        try:
            operation, model = re.match(User.model_permissions_pattern, perm).groups()
        except AttributeError as exc:
            raise MissingParam(
                f"Unknown permission '{perm}' passed to has_perm"
            ) from exc

        if operation_exists(operation) and get_model(model):
            field = "has_" + operation
        else:
            raise MissingParam(
                f"Unknown operation or model '{operation} / {model}' passed to has_perm"
            )

        # We should always get an object to test against.
        if obj:
            return Permission.objects.filter(
                namespace=obj.namespace, **{field: True}, group__in=self.groups.all()
            ).exists()

        return False

    class Meta:
        """Meta class for User."""

        ordering = ["id"]
