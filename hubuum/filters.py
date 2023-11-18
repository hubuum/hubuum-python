# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false

"""Filters for hubuum permissions."""
from typing import List, Tuple

from django.contrib.auth.models import Group
from django.db.models import (
    ForeignKey,
    ManyToManyField,
    Model,
    OneToOneField,
    Q,
    QuerySet,
)
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from hubuum.models.core import (
    Attachment,
    AttachmentManager,
    HubuumClass,
    HubuumObject,
    model_is_open,
)
from hubuum.models.iam import Namespace, Permission, User
from hubuum.models.resources import (
    Host,
    HostType,
    Jack,
    Person,
    PurchaseOrder,
    Room,
    Vendor,
)
from hubuum.typing import typed_user_from_request

_key_lookups = ["exact"]  # in?
_boolean_lookups = _key_lookups
_many_to_many_lookups = _key_lookups
_many_to_one_lookups = _key_lookups

_textual_lookups = [
    "contains",
    "icontains",
    "endswith",
    "iendswith",
    "startswith",
    "istartswith",
    "exact",
    "iexact",
    "regex",
    "iregex",
]
_numeric_lookups = ["exact", "gt", "gte", "lt", "lte", "range"]
_date_lookups = [
    "day",
    "month",
    "quarter",
    "year",
    "exact",
    "week_day",
    "iso_week_day",
    "iso_year",
]
_date_lookups.extend(_numeric_lookups)

_hubuum_fields = {
    "id": _key_lookups,
    "created_at": _date_lookups,
    "updated_at": _date_lookups,
}


class RaiseBadRequestOnBadFilter(filters.FilterSet):
    """Mixin to throw 400 Bad request on bad filters.

    Bad filters are defined as any filter that tries to use a field that is not
    defined in the filter set, or any filter that tries to use a lookup that is
    not defined for the field.
    """

    base_fields = [
        # Pagination related fields
        "page_size",
        "page",
        "limit",
        # Ordering related fields
        "ordering",
        # JSON related fields, using JSONFieldLookupFilter
        # This could / should be validated via a field lookup on json_data
        # for the model, but it should suffice.
        "json_data_lookup",
    ]

    def filter_queryset(self, queryset: QuerySet[Model]) -> QuerySet[Model]:
        """Validate the lookups and fields in the request.

        :param queryset: The queryset to filter.
        :return: The filtered queryset.
        :raises ValidationError: If an invalid field or lookup is found in the request.
        """
        self._validate_fields_and_lookups()
        return super().filter_queryset(queryset)

    def _validate_fields_and_lookups(self) -> None:
        """Validate that fields and lookups in the request are valid for filtering."""
        for field in self.request.GET:  # type: ignore
            field_name, lookup = self._get_field_and_lookup(field)
            self._validate_field(field_name)
            self._validate_lookup(field_name, lookup)

    def _get_field_and_lookup(self, field: str) -> Tuple[str, str]:
        """Split the field from the request into field_name and lookup."""
        if "__" in field:
            return field.split("__", 1)
        return field, None

    def _validate_field(self, field_name: str) -> None:
        """Check if the field name is valid."""
        if not self._is_valid_field(field_name):
            raise ValidationError(f"Invalid field for filtering: {field_name}")

    def _validate_lookup(self, field_name: str, lookup: str) -> None:
        """Check if the lookup is valid for the field."""
        if (
            lookup
            and field_name in self.Meta.fields  # pylint: disable=no-member
            and lookup not in self.Meta.fields[field_name]  # pylint: disable=no-member
        ):
            raise ValidationError(f"Invalid lookup ({lookup}) for field ({field_name})")

    def _is_valid_field(self, field_name: str) -> bool:
        """Check if the field name is valid for filtering."""
        return (
            field_name in self.base_fields
            or field_name in self.Meta.fields  # pylint: disable=no-member
            or field_name in self._get_relational_fields()
        )

    def _get_relational_fields(self) -> List[str]:
        """Get the names of a model's related fields."""
        return [
            field.name
            for field in self.Meta.model._meta.get_fields()  # pylint: disable=no-member
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField))
        ]

    class Meta:
        """Meta class."""

        abstract = True


class JSONFieldLookupFilter(filters.CharFilter):
    """Class to allow filtering on JSON fields.

    :param field_name: The field name to filter on. Must be a JSON field.
    """

    def filter(  # noqa: A003 (builtin-attribute-shadowing), this has to be named filter
        self, qs: QuerySet[Model], value: str
    ) -> QuerySet[Model]:
        """Filter the queryset based on a JSON key, value, and optional lookup type.

        :param qs: The queryset to filter.
        :param value: The input value containing the key, value, and optional lookup type.

        :return: The filtered queryset.

        :raises ValidationError: If an invalid lookup type for the value is provided.
        """
        if not value:
            return qs

        try:
            key, val = value.split("=")
        except ValueError as ex:
            raise ValidationError(
                "Filtering requires both a key and a value, separated by '='"
            ) from ex

        try:
            val = float(val)
        except ValueError:
            pass

        if isinstance(val, (float, int)):
            val_type = "numeric"
            allowed_lookups = _numeric_lookups
        else:  # Assume string
            val_type = "text"
            allowed_lookups = _textual_lookups

        parts = key.split("__")
        if len(parts) > 1 and parts[-1] in _numeric_lookups + _textual_lookups:
            lookup_type = parts[-1]
        else:
            lookup_type = "exact"
            key = f"{key}__exact"

        if lookup_type not in allowed_lookups:
            valid_lookups = ", ".join(allowed_lookups)
            allowed_string = f"Allowed types for {val_type} are {valid_lookups}."
            raise ValidationError(
                f"Invalid lookup type '{lookup_type}'. {allowed_string}"
            )

        json_lookup = Q(**{f"{self.field_name}__{key}": val})
        return qs.filter(json_lookup)


class NamespacePermissionFilter(RaiseBadRequestOnBadFilter):
    """Return viewable objects for a user.

    This filter returns (request.)user-visible objects of a model in question.
    """

    def filter_queryset(self, queryset: QuerySet[Model]) -> QuerySet[Model]:
        """Perform the filtering."""
        queryset = super().filter_queryset(queryset)
        user = typed_user_from_request(self.request)
        # model = queryset.model._meta.model_name
        #        permission = self.perm_format % {
        #            "app_label": queryset.model._meta.app_label,
        #            "model_name": queryset.model._meta.model_name,
        #        }

        #    Find all namespaces we can perform the given operation in.

        #        print("List of {}".format(model))
        model_name = queryset.model._meta.model_name  # pylint: disable=protected-access
        if user.is_admin() or model_is_open(model_name):
            return queryset

        res = Permission.objects.filter(
            has_read=True, group__in=user.groups.all()
        ).values_list("namespace", flat=True)
        # print(res)
        # print(queryset)
        if model_name == "namespace":
            filtered = queryset.filter(pk__in=res)
        else:
            filtered = queryset.filter(namespace__in=res)
        return filtered


class HubuumClassFilterSet(NamespacePermissionFilter):
    """Filterset class for HubuumClass."""

    json_schema_lookup = JSONFieldLookupFilter(field_name="json_schema")

    class Meta:
        """Metadata for the class."""

        model = HubuumClass
        fields = {
            "name": _textual_lookups,
            "validate_schema": _boolean_lookups,
        }
        fields.update(_hubuum_fields)


class HubuumObjectFilterSet(NamespacePermissionFilter):
    """Filterset class for HubuumClass."""

    json_data_lookup = JSONFieldLookupFilter(field_name="json_data")

    class Meta:
        """Metadata for the class."""

        model = HubuumObject
        fields = {
            "name": _textual_lookups,
            "hubuum_class": _key_lookups,
        }
        fields.update(_hubuum_fields)


class NamespaceFilterSet(NamespacePermissionFilter):
    """FilterSet class for Namespace."""

    class Meta:
        """Metadata for the class."""

        model = Namespace
        fields = {
            "name": _textual_lookups,
            "description": _textual_lookups,
        }
        fields.update(_hubuum_fields)


class UserFilterSet(RaiseBadRequestOnBadFilter):
    """FilterSet class for User."""

    class Meta:
        """Metadata for the class."""

        model = User
        fields = {
            "id": _numeric_lookups,
            "username": _textual_lookups,
            "email": _textual_lookups,
            "is_active": ["exact"],
            "is_staff": ["exact"],
            "is_superuser": ["exact"],
            "last_login": _date_lookups,
            "groups": _many_to_many_lookups,
        }


class GroupFilterSet(RaiseBadRequestOnBadFilter):
    """FilterSet class for Group."""

    class Meta:
        """Metadata for the class."""

        model = Group
        fields = {
            "id": _numeric_lookups,
            "name": _textual_lookups,
            "user": _many_to_many_lookups,
            "permissions": _many_to_many_lookups,
        }


class PermissionFilterSet(RaiseBadRequestOnBadFilter):
    """FilterSet class for Permission."""

    class Meta:
        """Metadata for the class."""

        model = Permission
        fields = {
            "has_create": _boolean_lookups,
            "has_read": _boolean_lookups,
            "has_update": _boolean_lookups,
            "has_delete": _boolean_lookups,
            "has_namespace": _boolean_lookups,
        }
        fields.update(_hubuum_fields)


class AttachmentManagerFilterSet(RaiseBadRequestOnBadFilter):
    """FilterSet class for AttachmentManagers."""

    class Meta:
        """Metadata for the class."""

        model = AttachmentManager
        fields = {
            "hubuum_class": _textual_lookups,
            "enabled": _boolean_lookups,
            "per_object_count_limit": _numeric_lookups,
            "per_object_individual_size_limit": _numeric_lookups,
            "per_object_total_size_limit": _numeric_lookups,
        }


class AttachmentFilterSet(NamespacePermissionFilter):
    """FilterSet for the Attachment model."""

    class Meta:
        """Meta class for AttachmentFilterSet."""

        model = Attachment
        fields = {
            "hubuum_class": _key_lookups,
            "hubuum_object": _key_lookups,
            "sha256": _textual_lookups,
            "size": _numeric_lookups,
            "original_filename": _textual_lookups,
        }
        fields.update(_hubuum_fields)


class HostFilterSet(NamespacePermissionFilter):
    """FilterSet class for Host."""

    class Meta:
        """Metadata for the class."""

        model = Host
        fields = {
            "name": _textual_lookups,
            "fqdn": _textual_lookups,
            "serial": _textual_lookups,
            "registration_date": _date_lookups,
        }
        fields.update(_hubuum_fields)


class HostTypeFilterSet(NamespacePermissionFilter):
    """FilterSet class for HostType."""

    class Meta:
        """Metadata for the class."""

        model = HostType
        fields = {"name": _textual_lookups, "description": _textual_lookups}
        fields.update(_hubuum_fields)


class JackFilterSet(NamespacePermissionFilter):
    """FilterSet class for Jack."""

    class Meta:
        """Metadata for the class."""

        model = Jack
        fields = {
            "name": _textual_lookups,
            "building": _textual_lookups,
        }
        fields.update(_hubuum_fields)


class PersonFilterSet(NamespacePermissionFilter):
    """FilterSet class for Person."""

    class Meta:
        """Metadata for the class."""

        model = Person
        fields = {
            "username": _textual_lookups,
            "section": _textual_lookups,
            "department": _textual_lookups,
            "email": _textual_lookups,
            "office_phone": _textual_lookups,
            "mobile_phone": _textual_lookups,
        }
        fields.update(_hubuum_fields)


class PurchaseOrderFilterSet(NamespacePermissionFilter):
    """FilterSet class for PurchaseOrder."""

    class Meta:
        """Metadata for the class."""

        model = PurchaseOrder
        fields = {
            "order_date": _date_lookups,
            "po_number": _textual_lookups,
        }
        fields.update(_hubuum_fields)


class RoomFilterSet(NamespacePermissionFilter):
    """FilterSet class for Room."""

    class Meta:
        """Metadata for the class."""

        model = Room
        fields = {
            "room_id": _textual_lookups,
            "building": _textual_lookups,
            "floor": _textual_lookups,
        }
        fields.update(_hubuum_fields)


class VendorFilterSet(NamespacePermissionFilter):
    """FilterSet class for Vendor."""

    class Meta:
        """Metadata for the class."""

        model = Vendor
        fields = {
            "vendor_name": _textual_lookups,
            "vendor_url": _textual_lookups,
            "vendor_credentials": _textual_lookups,
            "contact_name": _textual_lookups,
            "contact_email": _textual_lookups,
            "contact_phone": _textual_lookups,
        }
        fields.update(_hubuum_fields)
