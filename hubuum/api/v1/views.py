"""Versioned (v1) views for the hubuum models."""
# from ipaddress import ip_address
import structlog
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.urls import resolve
from rest_framework import generics, status
from rest_framework.exceptions import (  # NotAuthenticated,
    MethodNotAllowed,
    NotFound,
    ParseError,
    ValidationError,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import Response

from hubuum.exceptions import (
    AttachmentCountLimitExceededError,
    AttachmentSizeLimitExceededError,
    AttachmentsNotEnabledError,
    AttachmentTooBig,
    Conflict,
    UnsupportedAttachmentModelError,
)
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
from hubuum.models.core import (
    Attachment,
    AttachmentManager,
    Extension,
    ExtensionData,
    get_model,
    model_supports_attachments,
)
from hubuum.models.permissions import Namespace, Permission
from hubuum.models.resources import (
    Host,
    HostType,
    Jack,
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
    AttachmentManagerSerializer,
    AttachmentSerializer,
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

object_logger = structlog.get_logger("hubuum.api.object")
manual_logger = structlog.get_logger("hubuum.manual")


class LoggingMixin:
    """Mixin to log object modifications (create, update, and delete).

    Also logs the user who performed the action.
    """

    def _log(self, operation, model, user, instance):
        """Write the log string."""
        object_logger.info(
            operation,
            model=model,
            user=str(user),
            instance=instance.id,
        )

    def perform_create(self, serializer):
        """Log creates."""
        super().perform_create(serializer)
        instance = serializer.instance
        if instance:
            self._log(
                "created", instance.__class__.__name__, self.request.user, instance
            )

    def perform_update(self, serializer):
        """Log updates."""
        super().perform_update(serializer)
        instance = serializer.instance
        if instance:
            self._log(
                "updated", instance.__class__.__name__, self.request.user, instance
            )

    def perform_destroy(self, instance):
        """Log deletes."""
        self._log("deleted", instance.__class__.__name__, self.request.user, instance)
        super().perform_destroy(instance)


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

    def get_object(self, lookup_identifier="val", model=None):
        """Perform the actual lookup based on the model's lookup_fields.

        raises: 404 if not found.
        return: object
        """
        #        if self.request.user.is_anonymous:
        #            raise NotAuthenticated()

        #        queryset = self.get_queryset()
        if model is None:
            queryset = self.get_queryset()
        else:
            queryset = model.objects.all()

        obj = None
        value = self.kwargs[lookup_identifier]
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

        if obj:
            self.check_object_permissions(self.request, obj)
        else:
            raise NotFound()

        return obj


# Hubuum List and Detail Views include near empty get, post, patch, and delete methods
# to allow the schema to be documented with the correct docstrings.
class HubuumList(LoggingMixin, generics.ListCreateAPIView):
    """Get: List objects. Post: Add object."""

    schema = AutoSchema(
        tags=["Resources"],
    )

    permission_classes = (NameSpace,)


# NOTE: Order for the inheritance here is vital.
class HubuumDetail(
    MultipleFieldLookupORMixin, LoggingMixin, generics.RetrieveUpdateDestroyAPIView
):
    """Get, Patch, or Destroy an object."""

    schema = AutoSchema(
        tags=["Resources"],
    )

    permission_classes = (NameSpace,)
    lookup_fields = ("id",)

    def file_response(self, filename, original_filename):
        """Return a HTTPresponse with the file in question."""
        with open(filename, "rb") as file:
            response = HttpResponse(file, content_type="application/octet-stream")
            response[
                "Content-Disposition"
            ] = f"attachment; filename={original_filename}"
            return response


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


class ExtensionList(HubuumList):
    """Get: List extensions. Post: Add extension."""

    schema = AutoSchema(
        tags=["Extension"],
    )

    queryset = Extension.objects.all()
    serializer_class = ExtensionSerializer
    filterset_class = ExtensionFilterSet


class ExtensionDetail(HubuumDetail):
    """Get, Patch, or Destroy an extension."""

    schema = AutoSchema(
        tags=["Extension"],
    )

    queryset = Extension.objects.all()
    serializer_class = ExtensionSerializer
    lookup_fields = ("id", "name")


class AttachmentManagerList(HubuumList):
    """Get: List attachmentmanagers. Post: Add attachmentmanager."""

    schema = AutoSchema(
        tags=["Attachment"],
    )

    queryset = AttachmentManager.objects.all()
    serializer_class = AttachmentManagerSerializer


class AttachmentManagerDetail(HubuumDetail):
    """Get, Patch, or Destroy an attachment."""

    schema = AutoSchema(
        tags=["Attachment"],
    )

    queryset = AttachmentManager.objects.all()
    serializer_class = AttachmentManagerSerializer
    lookup_fields = ("id", "model")


class AttachmentList(generics.CreateAPIView, LoggingMixin):
    """Get: List attachment data for a model. Post: Add attachment data to a model."""

    schema = AutoSchema(
        tags=["Attachment"],
    )

    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer


class AttachmentDetail(HubuumDetail):
    """Get, Patch, or Destroy an attachment metadata."""

    parser_classes = (MultiPartParser,)
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer

    schema = AutoSchema(
        tags=["Attachment"],
    )

    def _get_attachment(self, request, *args, **kwargs):
        """Get an attachment object, or raise 404."""
        model_name = self.kwargs.get("model").lower()
        obj_id = self.kwargs.get("instance")
        attachment_id = self.kwargs.get("attachment")

        model = get_model(model_name)

        if model is None:
            raise NotFound(detail=f"Model {model_name} does not exist.")

        if not model_supports_attachments(model):
            raise UnsupportedAttachmentModelError()

        content_type = ContentType.objects.get_for_model(model)

        # Find the meta object for the attachment, that is the object that
        # has the FileField, but also all the other metadata for the attachment.
        # To do this we use the obj_id from the URL, and check that against the
        # lookup_fields for the view.
        obj = None
        for field in self.lookup_fields:
            try:
                obj = Attachment.objects.get(
                    content_type=content_type,
                    object_id=obj_id,
                    **{field: attachment_id},
                )
            except Attachment.DoesNotExist:
                pass

        if obj:
            self.check_object_permissions(request, obj)
        else:
            raise NotFound(detail="Attachment not found.")

        return obj

    def get(self, request, *args, **kwargs):
        """Get an attachment metadata."""
        obj = self._get_attachment(request, *args, **kwargs)

        download_request = False
        if resolve(request.path).url_name == "download_attachment":
            download_request = True

        # If this is a download request, we return the file itself.
        # If the file itself is missing, we raise a 404 and log the missing
        # file as an error.
        if download_request:
            try:
                return self.file_response(
                    obj.attachment.name,
                    obj.original_filename,
                )
            except FileNotFoundError as exc:  # pragma: no cover, we can't provoke this
                manual_logger.error(
                    "File belonging to attachment {metaobj.id} was not found."
                )
                raise NotFound(detail="File not found.") from exc

        # It was not a download request, so return the serialized metadata object.
        return Response(AttachmentSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Add an attachment metadata."""
        model_name = kwargs["model"]

        model = get_model(model_name)

        if model is None:
            raise NotFound(detail=f"Model {model_name} does not exist.")

        if not model_supports_attachments(model):
            raise UnsupportedAttachmentModelError()

        content_type = ContentType.objects.get_for_model(model)
        obj = self.get_object(model=model, lookup_identifier="instance")

        # Note that the validator requires content_type and object_id to be
        # present in the request data, but we got them from the URL, so we
        # have to manually add them back into the request data.
        request.data["content_type"] = content_type.id
        request.data["object_id"] = obj.id
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not obj.attachments_are_enabled():
            raise AttachmentsNotEnabledError()

        # Get the uploaded file from the request, get its size,
        # and reset the file pointer
        uploaded_file = request.data.get("attachment")
        size = len(uploaded_file.read())
        uploaded_file.seek(0)

        max_attachments = obj.attachment_count_limit()
        max_attachment_size = obj.attachment_individual_size_limit()
        max_total_size = obj.attachment_total_size_limit()

        # Check limits
        if max_attachments and obj.attachment_count() >= max_attachments:
            raise AttachmentCountLimitExceededError()

        if max_attachment_size and size > max_attachment_size:
            raise AttachmentTooBig()

        if max_total_size and size + obj.attachment_size() > max_total_size:
            raise AttachmentSizeLimitExceededError()

        namespace = Namespace.objects.get(id=request.data.get("namespace"))

        # Create and save an Attachment object
        attachment_data = Attachment(
            namespace=namespace,
            attachment=uploaded_file,
            content_type=content_type,
            object_id=obj.id,
        )
        attachment_data.save()

        return Response(
            {
                "detail": "Attachment uploaded successfully.",
                "id": attachment_data.id,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, *args, **kwargs):
        """Delete an attachment"""
        obj = self._get_attachment(request, *args, **kwargs)
        self.check_object_permissions(request, obj)
        obj.delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


class ExtensionDataList(HubuumList):
    """Get: List extensiondata. Post: Add extensiondata."""

    schema = AutoSchema(
        tags=["Extension"],
    )

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

    schema = AutoSchema(
        tags=["Extension"],
    )

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
