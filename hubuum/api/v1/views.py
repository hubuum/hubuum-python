"""Versioned (v1) views for the hubuum models."""
# from ipaddress import ip_address

from django.contrib.auth.models import Group
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from rest_framework import generics, status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import Response

from hubuum.filters import HubuumObjectPermissionsFilter
from hubuum.models import (
    Host,
    HostType,
    Jack,
    Namespace,
    Permission,
    Person,
    PurchaseDocuments,
    PurchaseOrder,
    Room,
    User,
    Vendor,
)
from hubuum.permissions import (
    IsSuperOrAdminOrReadOnly,
    NameSpaceOrReadOnly,
    fully_qualified_operations,
)
from hubuum.tools import get_group, get_user

from .serializers import (
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
            raise Http404()

        return obj


class HubuumList(generics.ListCreateAPIView):
    """Get: List objects. Post: Add object."""

    permission_classes = (IsSuperOrAdminOrReadOnly,)
    filter_backends = [HubuumObjectPermissionsFilter]


# NOTE: Order for the inheritance here is vital.
class HubuumDetail(MultipleFieldLookupORMixin, generics.RetrieveUpdateDestroyAPIView):
    """Get, Patch, or Destroy an object."""

    permission_classes = (IsSuperOrAdminOrReadOnly,)


class UserList(HubuumList):
    """Get: List users. Post: Add user."""

    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(HubuumDetail):
    """Get, Patch, or Destroy a user."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_fields = ("id", "username", "email")


class GroupList(HubuumList):
    """Get: List groups. Post: Add group."""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class GroupDetail(HubuumDetail):
    """Get, Patch, or Destroy a group."""

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    lookup_fields = ("id", "name")


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

        return HttpResponseNotFound()

    def patch(self, request, *args, **kwargs):
        """Disallow patch."""
        raise MethodNotAllowed(request.method)

    def post(self, request, *args, **kwargs):
        """Add a user to a group."""
        group = self.get_object()

        user = get_user(kwargs["userid"])
        if user:
            if user.groups.filter(id=group.id).exists():
                return Response(
                    f"User {user.id} is already a member of group {group.id}",
                    status=status.HTTP_200_OK,
                )

            user.groups.add(group)
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return HttpResponseNotFound()

    def delete(self, request, *args, **kwargs):
        """Delete a user from a group."""
        group = self.get_object()
        user = get_user(kwargs["userid"])

        if user:
            if user.groups.filter(id=group.id).exists():
                user.groups.remove(group)
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return HttpResponseNotFound()


class PermissionList(HubuumList):
    """Get: List permissions. Post: Add permission."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class PermissionDetail(HubuumDetail):
    """Get, Patch, or Destroy a permission."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class HostList(HubuumList):
    """Get: List hosts. Post: Add host."""

    queryset = Host.objects.all().order_by("id")
    serializer_class = HostSerializer


class HostDetail(HubuumDetail):
    """Get, Patch, or Destroy a host."""

    queryset = Host.objects.all()
    serializer_class = HostSerializer
    lookup_fields = ("id", "name", "fqdn")


class NamespaceList(HubuumList):
    """Get: List Namespaces. Post: Add Namespace."""

    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer
    permission_classes = (NameSpaceOrReadOnly,)


class NamespaceDetail(HubuumDetail):
    """Get, Patch, or Destroy a namespace."""

    queryset = Namespace.objects.all()
    serializer_class = NamespaceSerializer
    lookup_fields = ("id", "name")
    permission_classes = (NameSpaceOrReadOnly,)


class NamespaceMembers(
    MultipleFieldLookupORMixin,
    generics.RetrieveAPIView,
):
    """List groups that can access a namespace."""

    permission_classes = (NameSpaceOrReadOnly,)
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

    permission_classes = (NameSpaceOrReadOnly,)
    lookup_fields = ("id", "name")
    serializer_class = GroupSerializer
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

        if not group:
            return HttpResponse("Group not found.", status=status.HTTP_404_NOT_FOUND)

        if not Permission.objects.filter(namespace=namespace, group=group).exists():
            return HttpResponseNotFound()

        return Response(GroupSerializer(group).data)

    # TODO: Should be used to update a groups permissions for the namespace.
    def patch(self, request, *args, **kwargs):
        """Disallow patch."""
        raise MethodNotAllowed(request.method)

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
        if not group:
            return HttpResponse("Group not found.", status=status.HTTP_404_NOT_FOUND)

        if set(request.data.keys()).isdisjoint(fully_qualified_operations()):
            return HttpResponseBadRequest(
                f"Missing at least one of '{fully_qualified_operations()}'"
            )

        # Check if the object (namespace, group) already exists.
        # If so, they need to patch, not put.
        if Permission.objects.filter(namespace=namespace, group=group).exists():
            return HttpResponse(
                reason=f"{group.name} already has permissions on {namespace.name}",
                status=status.HTTP_409_CONFLICT,
            )

        # We now have some params, so we generated a dict of options to set, and then
        # forcibly add has_read=True to ensure that also gets set.
        params = {}
        for key in fully_qualified_operations():
            if key in request.data:
                params[key] = bool(request.data[key])
                request.data.pop(key)

        # Check for remaining junk in the request data.
        if request.data.keys():
            return HttpResponseBadRequest()

        params["has_read"] = True

        try:
            Permission.objects.create(namespace=namespace, group=group, **params)
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        except Exception:  # pylint: disable=broad-except
            return HttpResponseServerError()

    def delete(self, request, *args, **kwargs):
        """Delete disassociates a group with a namespace.

        Transparently deletes the permission object.
        """
        namespace = self.get_object()
        group = get_group(kwargs["groupid"])
        if not group:
            return HttpResponse("Group not found.", status=status.HTTP_404_NOT_FOUND)

        try:
            Permission.objects.get(namespace=namespace, group=group).delete()
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        except Exception:  # pylint: disable=broad-except
            return HttpResponseServerError()


class HostTypeList(HubuumList):
    """Get: List hosttypes. Post: Add hosttype."""

    queryset = HostType.objects.all().order_by("name")
    serializer_class = HostTypeSerializer


class HostTypeDetail(HubuumDetail):
    """Get, Patch, or Destroy a hosttype."""

    queryset = HostType.objects.all()
    serializer_class = HostTypeSerializer


class RoomList(HubuumList):
    """Get: List rooms. Post: Add room."""

    queryset = Room.objects.all().order_by("id")
    serializer_class = RoomSerializer


class RoomDetail(HubuumDetail):
    """Get, Patch, or Destroy a room."""

    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class JackList(HubuumList):
    """Get: List jacks. Post: Add jack."""

    queryset = Jack.objects.all().order_by("name")
    serializer_class = JackSerializer


class JackDetail(HubuumDetail):
    """Get, Patch, or Destroy a jack."""

    queryset = Jack.objects.all()
    serializer_class = JackSerializer


class PersonList(HubuumList):
    """Get: List persons. Post: Add person."""

    queryset = Person.objects.all().order_by("id")
    serializer_class = PersonSerializer


class PersonDetail(HubuumDetail):
    """Get, Patch, or Destroy a person."""

    queryset = Person.objects.all()
    serializer_class = PersonSerializer


class VendorList(HubuumList):
    """Get: List vendors. Post: Add vendor."""

    queryset = Vendor.objects.all().order_by("vendor_name")
    serializer_class = VendorSerializer


class VendorDetail(HubuumDetail):
    """Get, Patch, or Destroy a vendor."""

    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer


class PurchaseOrderList(HubuumList):
    """Get: List purchaseorders. Post: Add purchaseorder."""

    queryset = PurchaseOrder.objects.all().order_by("id")
    serializer_class = PurchaseOrderSerializer


class PurchaseOrderDetail(HubuumDetail):
    """Get, Patch, or Destroy a purchaseorder."""

    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer


class PurchaseDocumentList(HubuumList):
    """Get: List purchasedocuments. Post: Add purchasedocument."""

    queryset = PurchaseDocuments.objects.all().order_by("id")
    serializer_class = PurchaseDocumentsSerializer


class PurchaseDocumentDetail(HubuumDetail):
    """Get, Patch, or Destroy a purchasedocument."""

    queryset = PurchaseDocuments.objects.all()
    serializer_class = PurchaseDocumentsSerializer
