"""Versioned (v1) views for the hubuum models."""
# from ipaddress import ip_address

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.exceptions import (  # NotAuthenticated,
    MethodNotAllowed,
    NotFound,
    ParseError,
    ValidationError,
)
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import Response

from hubuum.exceptions import Conflict
from hubuum.filters import (
    ExtensionDataFilterSet,
    ExtensionFilterSet,
    GroupFilterSet,
    HostFilterSet,
    HostTypeFilterSet,
    JackFilterSet,
    NamespaceFilterSet,
    PermissionFilterSet,
    PersonFilterSet,
    PurchaseDocumentsFilterSet,
    PurchaseOrderFilterSet,
    RoomFilterSet,
    UserFilterSet,
    VendorFilterSet,
)
from hubuum.models.auth import User, get_group, get_user
from hubuum.models.base import (
    Extension,
    ExtensionData,
    Host,
    HostType,
    Jack,
    Namespace,
    Permission,
    Person,
    PurchaseDocuments,
    PurchaseOrder,
    Room,
    Vendor,
)
from hubuum.permissions import (
    IsSuperOrAdminOrReadOnly,
    NameSpace,
    fully_qualified_operations,
)

from .serializers import (
    ExtensionDataSerializer,
    ExtensionSerializer,
    GroupSerializer,
    HostSerializer,
    HostTypeSerializer,
    JackSerializer,
    NamespaceSerializer,
    PermissionSerializer,
    PersonSerializer,
    PurchaseDocumentsSerializer,
    PurchaseOrderSerializer,
    RoomSerializer,
    UserSerializer,
    VendorSerializer,
)


class MultipleFieldLookupORMixin:  # pylint: disable=too-few-public-methods
    """A mixin to allow us to look up objects beyond just the primary key.

    Set lookup_fields in the class to select what fields, in the given order,
    that are used for the lookup. The value is the parameter passed at all times.

    Example: We are passed "foo" as the value to look up (using the key 'lookup_value'),
    and the class has the following set:

    lookup_fields = ("id", "username", "email")

    Applying this mixin will make the class attempt to:
      1. Try to find object where id=foo (the default behaviour)
      2. If no match was found, try to find an object where username=foo
      3. If still no match, try to find an object where email=foo

    If no matches are found, return 404.
    """

    def get_object(self):
        """Perform the actual lookup based on the model's lookup_fields.

        raises: 404 if not found.
        return: object
        """
        #        if self.request.user.is_anonymous:
        #            raise NotAuthenticated()

        queryset = self.get_queryset()
        obj = None
        value = self.kwargs["val"]
        for field in self.lookup_fields:
            try:
                # https://stackoverflow.com/questions/9122169/calling-filter-with-a-variable-for-field-name
                # No, just no.
                obj = queryset.get(**{field: value})
                if obj:
                    break

            # If we didn't get a hit, or an error, keep trying.
            # If we don't get a hit at all, we'll raise 404.
            except Exception:  # nosec pylint: disable=broad-except
                pass

        if obj is None:
            raise NotFound()

        # As we overload get_object, we need to manually check permissions.
        self.check_object_permissions(self.request, obj)
        return obj


class HubuumList(generics.ListCreateAPIView):
    """Get: List objects. Post: Add object."""

    permission_classes = (NameSpace,)


# NOTE: Order for the inheritance here is vital.
class HubuumDetail(MultipleFieldLookupORMixin, generics.RetrieveUpdateDestroyAPIView):
    """Get, Patch, or Destroy an object."""

    permission_classes = (NameSpace,)
    lookup_fields = ("id",)


class UserList(HubuumList):
    """Get: List users. Post: Add user."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsSuperOrAdminOrReadOnly,)
    filterset_class = UserFilterSet


class UserDetail(HubuumDetail):
    """Get, Patch, or Destroy a user."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_fields = ("id", "username", "email")
    permission_classes = (IsSuperOrAdminOrReadOnly,)


class GroupList(HubuumList):
    """Get: List groups. Post: Add group."""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (IsSuperOrAdminOrReadOnly,)
    filterset_class = GroupFilterSet


class GroupDetail(HubuumDetail):
    """Get, Patch, or Destroy a group."""

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
        tags=["LISTVIEW"],
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
        tags=["LISTVIEW"],
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

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    filterset_class = PermissionFilterSet


class PermissionDetail(HubuumDetail):
    """Get, Patch, or Destroy a permission."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class ExtensionList(HubuumList):
    """Get: List extensions. Post: Add extension."""

    queryset = Extension.objects.all()
    serializer_class = ExtensionSerializer
    filterset_class = ExtensionFilterSet


class ExtensionDetail(HubuumDetail):
    """Get, Patch, or Destroy an extension."""

    queryset = Extension.objects.all()
    serializer_class = ExtensionSerializer
    lookup_fields = ("id", "name")


class ExtensionDataList(HubuumList):
    """Get: List extensiondata. Post: Add extensiondata."""

    queryset = ExtensionData.objects.all()
    serializer_class = ExtensionDataSerializer
    filterset_class = ExtensionDataFilterSet

    def post(self, request, *args, **kwargs):
        """Handle posting duplicates as a patch."""
        extension = request.data["extension"]
        object_id = request.data["object_id"]
        model_name = request.data["content_type"]
        content_type = ContentType.objects.get(model=model_name).id

        existing_object_entry = ExtensionData.objects.filter(
            extension=extension, object_id=object_id, content_type=content_type
        ).first()

        if existing_object_entry:
            existing_object_entry.json_data = request.data["json_data"]
            existing_object_entry.save()
            return Response(
                ExtensionDataSerializer(existing_object_entry).data,
                status=status.HTTP_201_CREATED,
            )

        return super().post(request, *args, **kwargs)


class ExtensionDataDetail(HubuumDetail):
    """Get, Patch, or Destroy an extensiondata object."""

    queryset = ExtensionData.objects.all()
    serializer_class = ExtensionDataSerializer


class HostList(HubuumList):
    """Get: List hosts. Post: Add host."""

    queryset = Host.objects.all().order_by("id")
    serializer_class = HostSerializer
    filterset_class = HostFilterSet


class HostDetail(HubuumDetail):
    """Get, Patch, or Destroy a host."""

    queryset = Host.objects.all()
    serializer_class = HostSerializer
    lookup_fields = ("id", "name", "fqdn")


class NamespaceList(HubuumList):
    """Get: List Namespaces. Post: Add Namespace."""

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

    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer
    lookup_fields = ("id", "name")
    permission_classes = (NameSpace,)
    namespace_write_permission = "has_namespace"
    namespace_post = False


class NamespaceMembers(
    MultipleFieldLookupORMixin,
    generics.RetrieveAPIView,
):
    """List groups that can access a namespace."""

    permission_classes = (NameSpace,)
    lookup_fields = ("id", "name")
    serializer_class = GroupSerializer
    queryset = Namespace.objects.all()
    schema = AutoSchema(
        tags=["LISTVIEW"],
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
    MultipleFieldLookupORMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    """Modify groups that can access a namespace."""

    permission_classes = (NameSpace,)
    lookup_fields = ("id", "name")
    serializer_class = PermissionSerializer
    queryset = Namespace.objects.all()
    schema = AutoSchema(
        tags=["LISTVIEW"],
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


class HostTypeList(HubuumList):
    """Get: List hosttypes. Post: Add hosttype."""

    queryset = HostType.objects.all().order_by("name")
    serializer_class = HostTypeSerializer
    filterset_class = HostTypeFilterSet


class HostTypeDetail(HubuumDetail):
    """Get, Patch, or Destroy a hosttype."""

    queryset = HostType.objects.all()
    serializer_class = HostTypeSerializer


class RoomList(HubuumList):
    """Get: List rooms. Post: Add room."""

    queryset = Room.objects.all().order_by("id")
    serializer_class = RoomSerializer
    filterset_class = RoomFilterSet


class RoomDetail(HubuumDetail):
    """Get, Patch, or Destroy a room."""

    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class JackList(HubuumList):
    """Get: List jacks. Post: Add jack."""

    queryset = Jack.objects.all().order_by("name")
    serializer_class = JackSerializer
    filterset_class = JackFilterSet


class JackDetail(HubuumDetail):
    """Get, Patch, or Destroy a jack."""

    queryset = Jack.objects.all()
    serializer_class = JackSerializer


class PersonList(HubuumList):
    """Get: List persons. Post: Add person."""

    queryset = Person.objects.all().order_by("id")
    serializer_class = PersonSerializer
    filterset_class = PersonFilterSet


class PersonDetail(HubuumDetail):
    """Get, Patch, or Destroy a person."""

    queryset = Person.objects.all()
    serializer_class = PersonSerializer


class VendorList(HubuumList):
    """Get: List vendors. Post: Add vendor."""

    queryset = Vendor.objects.all().order_by("vendor_name")
    serializer_class = VendorSerializer
    filterset_class = VendorFilterSet


class VendorDetail(HubuumDetail):
    """Get, Patch, or Destroy a vendor."""

    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer


class PurchaseOrderList(HubuumList):
    """Get: List purchaseorders. Post: Add purchaseorder."""

    queryset = PurchaseOrder.objects.all().order_by("id")
    serializer_class = PurchaseOrderSerializer
    filterset_class = PurchaseOrderFilterSet


class PurchaseOrderDetail(HubuumDetail):
    """Get, Patch, or Destroy a purchaseorder."""

    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer


class PurchaseDocumentList(HubuumList):
    """Get: List purchasedocuments. Post: Add purchasedocument."""

    queryset = PurchaseDocuments.objects.all().order_by("id")
    serializer_class = PurchaseDocumentsSerializer
    filterset_class = PurchaseDocumentsFilterSet


class PurchaseDocumentDetail(HubuumDetail):
    """Get, Patch, or Destroy a purchasedocument."""

    queryset = PurchaseDocuments.objects.all()
    serializer_class = PurchaseDocumentsSerializer
