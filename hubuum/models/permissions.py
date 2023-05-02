"""Namespace models."""

from django.contrib.auth.models import Group
from django.db import models
from rest_framework.exceptions import NotFound

from hubuum.models.core import (
    AttachmentModel,
    ExtensionsModel,
    HubuumModel,
    NamespacedHubuumModel,
)
from hubuum.permissions import fully_qualified_operations


class NamespacedHubuumModelWithExtensions(
    NamespacedHubuumModel, AttachmentModel, ExtensionsModel
):
    """An abstract model that provides Namespaces and Extensions."""

    class Meta:
        """Meta data for the class."""

        abstract = True


class Namespace(HubuumModel):
    """The namespace ('domain') of an object."""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    def get_permissions_for_group(self, group: Group, raise_exception=True):
        """Try to find a permission object for the given group.

        param: group (Group instance)
        param: raise_exception (True)

        returns:
            success (Permission): Permission object
            failure (None): None

        raises:
            exception: NotFound if raise_exception is True and no permission object is found
        """
        try:
            obj = Permission.objects.get(namespace=self, group=group)
            return obj
        except Permission.DoesNotExist as exc:
            if raise_exception:
                raise NotFound() from exc

        return None

    def grant_all(self, group):
        """Grant all permissions to the namespace to the given group."""
        create = {}
        create["namespace"] = self
        create["group"] = group
        for perm in fully_qualified_operations():
            create[perm] = True
        Permission.objects.update_or_create(**create)
        return True

    def groups_that_can(self, perm):
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

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return self.name


class Permission(HubuumModel):
    """Permissions in Hubuum.

    - Permissions are set by group.
    - Objects belong to a namespace.
    - Every namespace has zero or more groups with permissions for the namespace.

    The permission `has_namespace` allows for the group to create new namespaces scoped
    under the current one.
    """

    # If the namespace the permission points to goes away, clear the entry.
    namespace = models.ForeignKey(
        "Namespace", related_name="p_namespace", on_delete=models.CASCADE
    )
    # If the group the permission uses goes away, clear the entry.
    group = models.ForeignKey(
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

    def __str__(self):
        """Stringify the object, used to represent the object towards users."""
        return str(self.id)
