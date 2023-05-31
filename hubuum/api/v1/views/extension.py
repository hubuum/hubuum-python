"""Extension-related views for the API v1."""

from typing import Any, cast

from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.request import Request
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import Response

from hubuum.api.v1.serializers import ExtensionDataSerializer, ExtensionSerializer
from hubuum.filters import ExtensionDataFilterSet, ExtensionFilterSet
from hubuum.models.core import Extension, ExtensionData

from .base import HubuumDetail, HubuumList


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


class ExtensionDataList(HubuumList):
    """Get: List extensiondata. Post: Add extensiondata."""

    schema = AutoSchema(
        tags=["Extension"],
    )

    queryset = ExtensionData.objects.all()
    serializer_class = ExtensionDataSerializer
    filterset_class = ExtensionDataFilterSet

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Handle posting duplicates as a patch."""
        extension = cast(str, request.data["extension"])
        object_id = cast(str, request.data["object_id"])
        model_name = cast(str, request.data["content_type"])
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
