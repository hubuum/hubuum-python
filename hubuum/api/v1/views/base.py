"""Base view classes for Hubuum API v1."""

from typing import List, Type, cast

import structlog
from django.contrib.auth.models import AbstractUser
from django.db.models import Model, QuerySet
from django.http import HttpRequest, HttpResponse
from rest_framework import generics, serializers
from rest_framework.exceptions import NotFound
from rest_framework.schemas.openapi import AutoSchema

from hubuum.models.auth import typed_user
from hubuum.permissions import NameSpace

object_logger = structlog.get_logger("hubuum.api.object")


class LoggingMixin:
    """Mixin to log object modifications (create, update, and delete).

    Also logs the user who performed the action.
    """

    def _log(
        self, operation: str, model: str, user: AbstractUser, instance: Model
    ) -> None:
        """Write the log string."""
        object_logger.info(
            operation,
            model=model,
            user=str(user),
            instance=instance.id,
        )

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:
        """Log creates."""
        super().perform_create(serializer)
        instance = cast(Model, serializer.instance)
        user = typed_user(cast(HttpRequest, self.request))
        if instance:
            self._log("created", instance.__class__.__name__, user, instance)

    def perform_update(self, serializer: serializers.ModelSerializer) -> None:
        """Log updates."""
        super().perform_update(serializer)
        instance = cast(Model, serializer.instance)
        user = typed_user(cast(HttpRequest, self.request))
        if instance:
            self._log("updated", instance.__class__.__name__, user, instance)

    def perform_destroy(self, instance: Model) -> None:
        """Log deletes."""
        user = typed_user(cast(HttpRequest, self.request))
        self._log("deleted", instance.__class__.__name__, user, instance)
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

    def get_object(
        self, lookup_identifier: str = "val", model: Type[Model] = None
    ) -> Model:
        """Perform the actual lookup based on the view's lookup_fields.

        raises: 404 if not found.
        return: object
        """
        if model is None:  # type: ignore
            queryset = cast(QuerySet[Model], self.get_queryset())
            fields = cast(List[str], self.lookup_fields)
        else:
            queryset = model.objects.all()
            fields = ("id",)

        obj = None
        value = cast(str, self.kwargs[lookup_identifier])
        for field in fields:
            try:
                # https://stackoverflow.com/questions/9122169/calling-filter-with-a-variable-for-field-name
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

    def file_response(self, filename: str, original_filename: str) -> HttpResponse:
        """Return a HTTPresponse with the file in question."""
        with open(filename, "rb") as file:
            response = HttpResponse(file, content_type="application/octet-stream")
            response[
                "Content-Disposition"
            ] = f"attachment; filename={original_filename}"
            return response
