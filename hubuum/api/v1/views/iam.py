"""IAM views for the API v1."""

from django.contrib.auth.models import Group
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotFound,
    ParseError,
    ValidationError,
)
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import Response

from hubuum.api.v1.serializers import (
    GroupSerializer,
    NamespaceSerializer,
    PermissionSerializer,
    UserSerializer,
)
from hubuum.exceptions import Conflict
from hubuum.filters import (
    GroupFilterSet,
    NamespaceFilterSet,
    PermissionFilterSet,
    UserFilterSet,
)
from hubuum.models.auth import User, get_group, get_user
from hubuum.models.permissions import Namespace, Permission
from hubuum.permissions import (
    IsSuperOrAdminOrReadOnly,
    NameSpace,
    fully_qualified_operations,
)

from .base import HubuumDetail, HubuumList, LoggingMixin, MultipleFieldLookupORMixin


class UserList(HubuumList):
    """Get: List users. Post: Add user."""

    schema = AutoSchema(
        tags=["User"],
    )

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsSuperOrAdminOrReadOnly,)
    filterset_class = UserFilterSet


class UserDetail(HubuumDetail):
    """Get, Patch, or Destroy a user."""

    schema = AutoSchema(
        tags=["User"],
    )

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_fields = ("id", "username", "email")
    permission_classes = (IsSuperOrAdminOrReadOnly,)


class GroupList(HubuumList):
    """Get: List groups. Post: Add group."""

    schema = AutoSchema(
        tags=["Group"],
    )

    queryset = Group.objects.all().order_by("id")
    serializer_class = GroupSerializer
    permission_classes = (IsSuperOrAdminOrReadOnly,)
    filterset_class = GroupFilterSet


class GroupDetail(HubuumDetail):
    """Get, Patch, or Destroy a group."""

    schema = AutoSchema(
        tags=["Group"],
    )

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    lookup_fields = ("id", "name")
    permission_classes = (IsSuperOrAdminOrReadOnly,)


class GroupMembers(
    MultipleFieldLookupORMixin,
    generics.RetrieveAPIView,
):
    """List group members."""

    permission_classes = (IsSuperOrAdminOrReadOnly,)
    lookup_fields = ("id", "name")
    serializer_class = UserSerializer
    queryset = Group.objects.all()
    schema = AutoSchema(
        tags=["Group"],
        component_name="Group memberships",
        operation_id_base="Groupmemberships",
    )

    def get(self, request, *args, **kwargs):
        """Get all users in the group."""
        group_object = self.get_object()
        users = User.objects.filter(groups=group_object)

        return Response(UserSerializer(users, many=True).data)


class GroupMembersUser(
    MultipleFieldLookupORMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    """Modify users in groups."""

    permission_classes = (IsSuperOrAdminOrReadOnly,)
    lookup_fields = ("id", "name")
    serializer_class = UserSerializer
    queryset = Group.objects.all()
    schema = AutoSchema(
        tags=["Group", "User"],
        component_name="Group memberships users",
        operation_id_base="Groupmembershipsusers",
    )

    def get(self, request, *args, **kwargs):
        """Get user in group."""
        group = self.get_object()

        user = get_user(kwargs["userid"])
        if user:
            if user.groups.filter(id=group.id).exists():
                return Response(UserSerializer(user).data)

        raise NotFound()

    def patch(self, request, *args, **kwargs):
        """Disallow patch."""
        raise MethodNotAllowed(request.method)

    def post(self, request, *args, **kwargs):
        """Add a user to a group."""
        group = self.get_object()
        user = get_user(kwargs["userid"])

        if user.groups.filter(id=group.id).exists():
            return Response(
                f"User {user.id} is already a member of group {group.id}",
                status=status.HTTP_200_OK,
            )

        user.groups.add(group)
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        """Delete a user from a group."""
        group = self.get_object()
        user = get_user(kwargs["userid"])

        if user.groups.filter(id=group.id).exists():
            user.groups.remove(group)
            user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionList(HubuumList):
    """Get: List permissions. Post: Add permission."""

    schema = AutoSchema(
        tags=["Permission"],
    )

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    filterset_class = PermissionFilterSet


class PermissionDetail(HubuumDetail):
    """Get, Patch, or Destroy a permission."""

    schema = AutoSchema(
        tags=["Permission"],
    )

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class NamespaceList(HubuumList):
    """Get: List Namespaces. Post: Add Namespace."""

    schema = AutoSchema(
        tags=["Namespace"],
    )

    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer
    permission_classes = (NameSpace,)
    namespace_write_permission = "has_namespace"
    filterset_class = NamespaceFilterSet

    def post(self, request, *args, **kwargs):
        """Process creation of new namespaces."""
        user = request.user
        group = None
        if "group" in request.data:
            # We want to pop the group since it's not part of the model.
            # As such, validation will fail if it present.
            group = Group.objects.get(id=request.data.pop("group"))
            if not user.is_member_of(group):
                raise ValidationError(
                    """The user is not a member of the group that was requested to have
                    permissions for the created object."""
                )
        else:
            if user.has_only_one_group():
                group = user.groups.all().first()

        if not user.is_admin() and group is None:
            raise ValidationError(
                """No group parameter provided, and no singular default available.
                All user-owned namespace-enabled objects are required to have an initial group
                with permissions to the object set upon creation."""
            )

        #        if not user.is_admin():
        #            print(user.has_only_one_group())
        #            print(user.groups.all())

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            new_namespace = serializer.save()

        if group is not None:
            new_namespace.grant_all(group)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NamespaceDetail(HubuumDetail):
    """Get, Patch, or Destroy a namespace."""

    schema = AutoSchema(
        tags=["Namespace"],
    )

    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer
    lookup_fields = ("id", "name")
    permission_classes = (NameSpace,)
    namespace_write_permission = "has_namespace"
    namespace_post = False


class NamespaceMembers(
    LoggingMixin,
    MultipleFieldLookupORMixin,
    generics.RetrieveAPIView,
):
    """List groups that can access a namespace."""

    permission_classes = (NameSpace,)
    lookup_fields = ("id", "name")
    serializer_class = GroupSerializer
    queryset = Namespace.objects.all()
    schema = AutoSchema(
        tags=["Namespace"],
        component_name="Namespace members",
        operation_id_base="NamespaceMember",
    )

    def get(self, request, *args, **kwargs):
        """Get all groups that have access to a given namespace."""
        namespace = self.get_object()

        qs = Permission.objects.filter(namespace=namespace.id).values("group")
        groups = Group.objects.filter(id__in=qs)

        return Response(GroupSerializer(groups, many=True).data)


class NamespaceMembersGroup(
    LoggingMixin,
    MultipleFieldLookupORMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    """Modify groups that can access a namespace."""

    permission_classes = (NameSpace,)
    lookup_fields = ("id", "name")
    serializer_class = PermissionSerializer
    queryset = Namespace.objects.all()
    schema = AutoSchema(
        tags=["Namespace", "Group"],
        component_name="Namespace group permissions",
        operation_id_base="NamespaceMembersGroup",
    )

    def get(self, request, *args, **kwargs):
        """Get a group that has access to a namespace."""
        namespace = self.get_object()
        group = get_group(kwargs["groupid"])
        permission = namespace.get_permissions_for_group(group)

        return Response(PermissionSerializer(permission).data)

    # TODO: Should be used to update a groups permissions for the namespace.
    def patch(self, request, *args, **kwargs):
        """Patch the permissions of an existing group for a namespace."""
        namespace = self.get_object()
        group = get_group(kwargs["groupid"])
        instance = namespace.get_permissions_for_group(group)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, *args, **kwargs):
        """Put associates a group with a namespace.

        /namespace/<namespaceid>/groups/<groupid>
            {
                has_read = 1,
                has_delete = 0,
                has_create = 0,
                has_update = 0,
                has_namespace = 0,
            }

        Transparently creates a permission object.
        """
        namespace = self.get_object()
        group = get_group(kwargs["groupid"])
        instance = namespace.get_permissions_for_group(group, raise_exception=False)

        if set(request.data.keys()).isdisjoint(fully_qualified_operations()):
            raise ParseError(
                detail=f"Missing at least one of '{fully_qualified_operations()}'"
            )

        if instance:
            raise Conflict()

        params = {"namespace": namespace.id, "group": group.id, **request.data}
        serializer = self.get_serializer(data=params, partial=False)
        serializer.is_valid(raise_exception=True)

        create = serializer.data
        create["namespace"] = namespace
        create["group"] = group
        create["has_read"] = True

        Permission.objects.create(**create)
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        """Delete disassociates a group with a namespace.

        Transparently deletes the permission object.
        """
        namespace = self.get_object()
        group = get_group(kwargs["groupid"])
        permission = namespace.get_permissions_for_group(group)

        permission.delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)
