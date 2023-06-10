"""Permissions module for hubuum."""
from typing import Dict, List, cast

from django.contrib.auth.models import AbstractUser
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import (
    SAFE_METHODS,
    DjangoObjectPermissions,
    IsAuthenticated,
)
from rest_framework.request import Request
from rest_framework.views import APIView
from typing_extensions import Literal

from hubuum.typing import typed_user_from_request


class CustomObjectPermissions(DjangoObjectPermissions):
    """Map permissions towards CRUD."""

    perms_map: Dict[str, List[str]] = {
        "GET": ["%(app_label)s.read_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.read_%(model_name)s"],
        "HEAD": ["%(app_label)s.read_%(model_name)s"],
        "POST": ["%(app_label)s.create_%(model_name)s"],
        "PUT": ["%(app_label)s.update_%(model_name)s"],
        "PATCH": ["%(app_label)s.update_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


def is_super_or_admin(user: AbstractUser) -> bool:
    """Check to see if a user is superuser or admin (staff)."""
    return user.is_staff or user.is_superuser


class IsAuthenticatedAndReadOnly(IsAuthenticated):
    """Allow read-only access if authenticated."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check super (IsAuthenticated) and read-only methods (SAFE_METHODS)."""
        if not super().has_permission(request, view):
            return False

        return request.method in SAFE_METHODS

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> Literal[True]:
        """Check super (IsAuthenticated) and read-only methods (SAFE_METHODS)."""
        #        if not super().has_object_permission(request, view, obj):
        #            return False
        return request.method in SAFE_METHODS


class IsSuperOrAdminOrReadOnly(IsAuthenticatedAndReadOnly):
    """Permit super or admin users, else read only."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if we're super/admin otherwise authenticated readonly."""
        if is_super_or_admin(typed_user_from_request(request)):
            return True
        return super().has_permission(request, view)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> Literal[True]:
        """Check if we're super/admin otherwise authenticated readonly."""
        if is_super_or_admin(typed_user_from_request(request)):
            return True
        return super().has_object_permission(request, view, obj)


# A thing here. Everyone can read all namespaces. For multi-tenant installations we probably need:
# 1. Tenant specific admin groups
# 2. Limit visibility to a tenant's namespace / scope.
class NameSpace(IsSuperOrAdminOrReadOnly):
    """Namespace access.

    Write access:
        - super or admin users
        - users in groups with has_namespace for the namespace set

    Read access:
        - super or admin users
        - users in groups with has_read for the namespace set
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if superuser or admin by delegation, then check user, otherwise false."""
        # First check if we are superuser or asking for read-only (listing), if so, return true.
        user = typed_user_from_request(request)
        if user.is_anonymous:
            return False

        if super().has_permission(request, view):
            return True

        # POST needs special treatment as we don't have an object to work on.
        # The lack of an object means we can't delegate to has_object_permission, as it will
        # never get called...
        # Instead we check if we are creating a namespace (has_namespace) or creating an object
        # in a namespace (has_create).
        # Views operating on namespaces themselves set the attribute "namespace_write_permission"
        # to "has_namespace", and if they don't want to allow post (Detail views), they can
        # explicitly set namespace_post to False.
        #
        # If we are creating a namespace:
        #  - name is the namespace identifier itself.
        #
        # If we are populating into a namespace:
        #  - The identifier for the object that is to be created is not relevant to us.
        #  - namespace is the identifier for the namespace the object is to be placed in.
        if request.method == "POST":
            write_perm = "has_create"

            if hasattr(view, "namespace_post"):
                if not view.namespace_post:
                    raise MethodNotAllowed(method=request.method)

            # This breaks typing as it's not statically possible to resolve the attribute
            # at this point. This ends up propagating through the rest of this code block.
            if hasattr(view, "namespace_write_permission"):
                write_perm = cast(str, view.namespace_write_permission)

            if write_perm == "has_namespace":
                name = cast(str, request.data["name"])
                # We are creating a new namespace as a normal user.
                # We need to create a permission object for the namespace, and that requires us
                # to have a group identifier to allocate the permissions towards.
            else:
                name = cast(str, request.data["namespace"])

            user = typed_user_from_request(request)
            return user.has_namespace(name, write_perm)

        return True

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> Literal[True]:
        """Check for object-specific access."""
        # We can't user the super method, as it allows read-only for everyone,
        # which we don't want.
        # if request.user.is_anonymous:
        #    return False

        if is_super_or_admin(typed_user_from_request(request)):
            return True

        perms_map = {
            "GET": "has_read",
            "OPTIONS": "has_read",
            "HEAD": "has_read",
            "POST": "has_create",
            "PUT": "has_update",
            "PATCH": "has_update",
            "DELETE": "has_delete",
        }

        perms_map_namespace = {
            "GET": "has_read",
            "OPTIONS": "has_read",
            "HEAD": "has_read",
            "POST": "has_create",
            "PUT": "has_namespace",
            "PATCH": "has_namespace",
            "DELETE": "has_namespace",
        }

        if hasattr(view, "namespace_write_permission"):
            perm = perms_map_namespace[request.method]
        else:
            perm = perms_map[request.method]

        user = typed_user_from_request(request)
        if hasattr(obj, "namespace"):
            return user.namespaced_can(perm, cast(int, obj.namespace))

        return user.namespaced_can(perm, obj)
