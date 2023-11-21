"""Attachment views for API v1."""

from typing import Any, Dict, cast

import structlog
from django.core.exceptions import FieldError
from django.urls import resolve
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ParseError, PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema

from hubuum.api.v1.serializers import AttachmentManagerSerializer, AttachmentSerializer
from hubuum.exceptions import (
    AttachmentCountLimitExceededError,
    AttachmentSizeLimitExceededError,
    AttachmentsNotEnabledError,
    AttachmentTooBig,
)
from hubuum.filters import AttachmentFilterSet, AttachmentManagerFilterSet
from hubuum.models.core import Attachment, AttachmentManager, HubuumObject
from hubuum.models.iam import Namespace
from hubuum.typing import typed_query_params_from_request

from .base import HubuumClassAndObjectMixin, HubuumDetail, HubuumList, LoggingMixin

manual_logger = structlog.get_logger("hubuum.manual")


class AttachmentAutoSchema(AutoSchema):
    """Custom AutoSchema for generating unique operation IDs for the Attachment views.

    The generated operation IDs will utilize specific path parameters to ensure uniqueness.
    """

    def get_operation_id(self, path: str, method: str) -> str:
        """Generate a unique operation ID by appending specific path parameters to the base ID.

        :param path: The path of the current route.
        :param method: The HTTP method of the current route.

        :return: The unique operation ID for the route.
        """
        operation_id_base = super().get_operation_id(path, method)

        # Order is relevant, so use a list of tuples and not a dict.
        path_mapping: Dict[str, str] = [
            ("{class}", "Class"),
            ("{instance}", "Instance"),
            ("{instance}/", "Object"),
            ("{attachment}", "Attachment"),
            ("download", "Download"),
        ]

        for path_substr, postfix in path_mapping:
            if path_substr in path:
                operation_id_base += postfix

        return operation_id_base


class AttachmentManagerList(HubuumClassAndObjectMixin, HubuumList):
    """Get: List attachmentmanagers. Post: Add attachmentmanager."""

    schema = AutoSchema(
        tags=["Attachment"],
    )

    queryset = AttachmentManager.objects.all()
    serializer_class = AttachmentManagerSerializer
    filterset_class = AttachmentManagerFilterSet

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Add an attachment manager."""
        # Check if the class is a valid hubuum class, or raise 404.
        hubuum_class = self.get_hubuum_class(request.data.get("class"))

        # Convert the hubuum_class parameter from its name to its ID
        del request.data["class"]
        request.data["hubuum_class"] = hubuum_class.id
        return super().post(request, *args, **kwargs)


class AttachmentManagerDetail(HubuumClassAndObjectMixin, HubuumDetail):
    """Get, Patch, or Destroy an attachment manager.

    AttachmentManager objects are used to configure attachments for a given hubuum class.
    """

    schema = AutoSchema(
        tags=["Attachment"],
    )

    queryset = AttachmentManager.objects.all()
    serializer_class = AttachmentManagerSerializer

    def get_object(self) -> AttachmentManager:
        """Get the attachment manager we're working on."""
        class_identifier = self.kwargs.get("class") or self.request.data.get("class")
        if not class_identifier:
            raise ParseError(detail="No class identifier provided.")

        hubuum_class = self.get_hubuum_class(class_identifier)

        try:
            return AttachmentManager.objects.get(hubuum_class=hubuum_class)
        except AttachmentManager.DoesNotExist as exc:
            raise NotFound(
                detail="No attachment manager found for {hubuum_class}."
            ) from exc


class AttachmentList(HubuumClassAndObjectMixin, generics.CreateAPIView, LoggingMixin):
    """Get: List attachment data for a model. Post: Add attachment data to a model."""

    schema = AttachmentAutoSchema(
        tags=["Attachment"],
    )

    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    filterset_class = AttachmentFilterSet

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Get all attachments for a given model."""
        attachments: Attachment = []

        attachment_filter: Dict[str, str] = {}

        for key, value in typed_query_params_from_request(request).items():
            attachment_filter[key] = value

        if self.kwargs.get("class"):
            cls = self.get_hubuum_class(self.kwargs.get("class"))
            attachment_filter["hubuum_class"] = cls

            if self.kwargs.get("instance"):
                attachment_filter["hubuum_object"] = self.get_hubuum_object(
                    cls, kwargs.get("instance")
                )

        try:
            attachments = self.get_queryset().filter(**attachment_filter)
        except FieldError as exc:
            raise ParseError(detail="Invalid query parameter.") from exc
        except ValueError as exc:
            raise ParseError(detail="Invalid parameter value.") from exc

        return Response(AttachmentSerializer(attachments, many=True).data)


class AttachmentDetail(HubuumClassAndObjectMixin, HubuumDetail):
    """Get, Patch, or Destroy an attachment metadata."""

    parser_classes = (MultiPartParser,)
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    lookup_fields = ["id", "sha256"]

    schema = AttachmentAutoSchema(
        tags=["Attachment"],
    )

    def _ensure_size_limits(self, instance: HubuumObject, request: Request) -> bool:
        """Ensure adding the attachment won't exceed size limits."""
        attachment = cast(
            Attachment,
            request.data.get(
                "attachment", ParseError(detail="No attachment provided.")
            ),
        )
        size = len(cast(bytes, attachment.read()))
        attachment.seek(0)

        max_attachments = instance.attachment_count_limit()
        max_attachment_size = instance.attachment_individual_size_limit()
        max_total_size = instance.attachment_total_size_limit()

        # Check limits
        if max_attachments and instance.attachment_count() >= max_attachments:
            raise AttachmentCountLimitExceededError()

        if max_attachment_size and size > max_attachment_size:
            raise AttachmentTooBig()

        if max_total_size and size + instance.attachment_size() > max_total_size:
            raise AttachmentSizeLimitExceededError()

        return True

    def _get_attachment(
        self, request: Request, *args: Any, **kwargs: Any
    ) -> Attachment:
        """Get an attachment object, or raise 404."""
        # This view is called by the URL pattern that includes the part:
        # /data/<class>/... as such there is now way to get here and have
        # the model kwarg be None.
        attachment_id = self.kwargs.get("attachment")

        cls = self.get_hubuum_class(self.kwargs.get("class"))
        obj = self.get_hubuum_object(cls, self.kwargs.get("instance"))

        attachment = None
        for field in self.lookup_fields:
            try:
                attachment = Attachment.objects.get(
                    hubuum_class=cls,
                    hubuum_object=obj,
                    **{field: attachment_id},
                )
            except (Attachment.DoesNotExist, ValueError):
                pass

        if attachment:
            self.check_object_permissions(request, attachment)
        else:
            raise NotFound(detail="Attachment not found.")

        return attachment

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
            except FileNotFoundError as exc:
                manual_logger.error(
                    event="attachment_file",
                    file_status="missing",
                    text=f"File belonging to attachment {obj.id} was not found.",
                )
                raise NotFound(detail="File not found.") from exc

        # It was not a download request, so return the serialized metadata object.
        return Response(AttachmentSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Add an attachment metadata."""
        # This view is called by the URL pattern that includes the part:
        # /data/<model>/... as such there is now way to get here and have
        # the model kwarg be None.
        cls = self.get_hubuum_class(self.kwargs.get("class"))
        obj = self.get_hubuum_object(cls, self.kwargs.get("instance"))

        if not obj:
            raise NotFound(detail="Object not found.")

        if not obj.attachments_are_enabled():
            raise AttachmentsNotEnabledError()

        if not self.check_object_permissions(request, obj):
            PermissionDenied("No permission to add attachments to this object.")

        # Note that the validator requires hubuum_class and hubuum_object to be
        # present in the request data, but we got them from the URL, so we
        # have to manually add them back into the request data.
        request.data["hubuum_object"] = cast(int, obj.id)
        request.data["hubuum_class"] = cast(int, cls.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self._ensure_size_limits(obj, request)

        namespace = Namespace.objects.get(id=request.data.get("namespace"))

        # Create and save an Attachment object
        attachment_data = Attachment(
            namespace=namespace,
            attachment=request.data.get("attachment"),
            hubuum_class=cls,
            hubuum_object=obj,
        )
        attachment_data.save()

        return Response(
            {
                "detail": "Attachment uploaded successfully.",
                "id": attachment_data.id,
                "sha256": attachment_data.sha256,
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Delete an attachment."""
        obj = self._get_attachment(request, *args, **kwargs)
        self.check_object_permissions(request, obj)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
