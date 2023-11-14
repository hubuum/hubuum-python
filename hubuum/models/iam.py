"""IAM-related models for the hubuum project."""
# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false

import re
from typing import Any, Dict, List, Union, cast

from django.contrib.auth.models import AbstractUser, AnonymousUser, Group
from django.db import models
from django.db.models import Model
from rest_framework.exceptions import NotFound

from hubuum.exceptions import MissingParam
from hubuum.models.core import (
    AttachmentModel,
    ExtensionsModel,
    HubuumModel,
    NamespacedHubuumModel,
)
from hubuum.tools import get_model, get_object


def namespace_operations(fully_qualified: bool = False) -> List[str]:
    """Return a list of valid namespace permission operations.

    :param: fully_qualified (bool) - if True, the list will be fully qualified

    :returns: (list) - a list of valid namespace permission operations
    """
    operations: List[str] = ["create", "read", "update", "delete", "namespace"]
    if fully_qualified:
        operations = ["has_" + s for s in operations]

    return operations


def namespace_operation_exists(permission: str, fully_qualified: bool = False) -> bool:
    """Check if a permission operation for a namespace exists.

    :param: permission (str) - the permission operation to check
    :param: fully_qualified (bool) - if True, the operation will be checked
        against the fully qualified list of operations

    :returns: (bool) - True if the operation exists, False otherwise
    """
    if fully_qualified:
        return permission in namespace_operations(fully_qualified=True)

    return permission in namespace_operations()


class NamespacedHubuumModelWithExtensions(
    NamespacedHubuumModel, AttachmentModel, ExtensionsModel
):
    """An abstract model that provides Namespaces and Extensions."""

    class Meta:
        """Meta data for the class."""

        abstract = True


class Permission(HubuumModel):
    """Permissions in Hubuum.

    - Permissions are set by group.
    - Objects belong to a namespace.
    - Every namespace has zero or more groups with permissions for the namespace.

    The permission `has_namespace` allows for the group to create new namespaces scoped
    under the current one.
    """

    # If the namespace the permission points to goes away, clear the entry.
    namespace: int = models.ForeignKey(
        "Namespace", related_name="p_namespace", on_delete=models.CASCADE
    )
    # If the group the permission uses goes away, clear the entry.
    group: int = models.ForeignKey(
        "auth.Group", related_name="p_group", on_delete=models.CASCADE
    )

    has_create = models.BooleanField(null=False, default=False)
    has_read = models.BooleanField(null=False, default=False)
    has_update = models.BooleanField(null=False, default=False)
    has_delete = models.BooleanField(null=False, default=False)
    has_namespace = models.BooleanField(null=False, default=False)

    class Meta:
        """Metadata permissions."""

        unique_together = ("namespace", "group")
        ordering = ["id"]

    def __str__(self) -> str:
        """Stringify the object, used to represent the object towards users."""
        return str(self.get_auto_id())


class Namespace(HubuumModel):
    """The namespace ('domain') of an object."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def get_permissions_for_group(
        self, group: Group, raise_exception: bool = True
    ) -> Permission:
        """Try to find a permission object for the given group.

        param: group (Group instance)
        param: raise_exception (True)

        Returns
        -------
            success (Permission): Permission object
            failure (None): None

        Raises
        ------
            exception: NotFound if raise_exception is True and no permission object is found
        """
        try:
            obj = Permission.objects.get(namespace=self, group=group)
            return obj
        except Permission.DoesNotExist as exc:
            if raise_exception:
                raise NotFound() from exc

        return None

    def grant_all(self, group: Group) -> bool:
        """Grant all permissions to the namespace to the given group."""
        create: Dict[str, Any] = {}
        create["namespace"] = self
        create["group"] = group
        for perm in namespace_operations(fully_qualified=True):
            create[perm] = True
        Permission.objects.update_or_create(**create)
        return True

    def groups_that_can(self, perm: str) -> List[Group]:
        """Fetch groups that can perform a specific permission.

        param: perm (permission string, 'has_[read|create|update|delete|namespace])
        return [group objects] (may be empty)
        """
        qs = Permission.objects.filter(namespace=self.id, **{perm: True}).values(
            "group"
        )
        groups = Group.objects.filter(id__in=qs)
        return groups

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

    def __str__(self) -> str:
        """Stringify the object, used to represent the object towards users."""
        return self.name


class User(AbstractUser):
    """Extension to the default User class."""

    model_permissions_pattern = re.compile(
        r"^hubuum.(create|read|update|delete|namespace)_(\w+)$"
    )
    lookup_fields = ["id", "username", "email"]

    _group_list = None

    def get_auto_id(self) -> int:
        """Return the auto id of the user."""
        return cast(int, self.id)

    def is_admin(self):
        """Check if the user is any type of admin (staff/superadmin) (or in a similar group?)."""
        return self.is_staff or self.is_superuser

    @classmethod
    def supports_extensions(cls) -> bool:
        """Check if a class supports extensions."""
        return False

    @classmethod
    def supports_attachments(cls) -> bool:
        """Check if a class supports attachments."""
        return False

    @property
    def group_list(self) -> List[str]:
        """List the names of all the groups the user is a member of."""
        if self._group_list is None:
            self._group_list = list(self.groups.values_list("name", flat=True))
        return self._group_list

    def group_count(self) -> int:
        """Return the number of groups the user is a member of."""
        return self.groups.count()

    def has_only_one_group(self) -> bool:
        """Return true if the user is a member of only one group."""
        return self.group_count() == 1

    def is_member_of(self, group: Group) -> bool:
        """Check if the user is a member of a specific group."""
        return self.is_member_of_any([group])

    def is_member_of_any(self, groups: List[Group]) -> bool:
        """Check to see if a user is a member of any of the groups in the list."""
        return bool([i for i in groups if i in self.groups.all()])

    def namespaced_can(self, perm: str, namespace: Namespace) -> bool:
        """Check to see if the user can perform perm for namespace.

        param: perm (permission string, 'has_[create|read|update|delete|namespace])
        param: namespace (namespace object)
        return True|False
        """
        if not namespace_operation_exists(perm, fully_qualified=True):
            raise MissingParam(f"Unknown permission '{perm}' passed to namespaced_can.")

        # We need to check if the user is a member of a group
        # that has the given permission the namespace.
        groups = namespace.groups_that_can(perm)
        return self.is_member_of_any(groups)

    def has_namespace(
        self,
        namespace: Union[str, int],
        write_perm: str = "has_namespace",
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

        # This needs fixing for sub-namespaces.
        target = scope
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

    # We want to ask for a HubuumNamespaceModel objects, but due to overloading we must
    # also support user objects, anonymous users, generic django models, and None.
    def has_perm(
        self, perm: str, obj: Union[Model, AbstractUser, AnonymousUser, None] = None
    ) -> bool:
        """Model (?) permissions check for an object.

        perm: see permissions.py
        obj: Hubuum Object
        """
        field = None

        try:
            match = re.match(User.model_permissions_pattern, perm)
            operation, model = match.groups()  # type: ignore
        except AttributeError as exc:
            raise MissingParam(
                f"Unknown permission '{perm}' passed to has_perm"
            ) from exc

        if namespace_operation_exists(operation) and get_model(model):
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


def get_user(user_identifier: str, raise_exception: bool = True) -> User:
    """Try to find a user based on the identifier.

    Searches in User.lookup_fields
    """
    return get_object(User, user_identifier, raise_exception=raise_exception)


def get_group(group_identifier: str, raise_exception: bool = True) -> Group:
    """Try to find a group based on the identifier.

    :param: group_identifier

    :return: group object

    :raises: NotFound if no object found.
    """
    return get_object(
        Group,
        group_identifier,
        lookup_fields=["id", "name"],
        raise_exception=raise_exception,
    )
