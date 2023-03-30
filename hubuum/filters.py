"""Filters for hubuum permissions."""
from django.contrib.auth.models import Group
from django_filters import rest_framework as filters

from hubuum.models.auth import User
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
    model_is_open,
)

_key_lookups = ["exact"]  # in?
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
_namespace_fields = {"namespace": _key_lookups}
_namespace_fields.update(_hubuum_fields)


class JSONFieldExactFilter(filters.CharFilter):
    """Filter for JSON fields, needs testing."""


class NamespacePermissionFilter(filters.FilterSet):
    """Return viewable objects for a user.

    This filter returns (request.)user-visible objects of a model in question.
    """

    def filter_queryset(self, queryset):
        """Perform the filtering."""
        queryset = super().filter_queryset(queryset)
        user = self.request.user
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


#        return get_objects_for_user(user, permission, queryset, **self.shortcut_kwargs)


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


class UserFilterSet(filters.FilterSet):
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


class GroupFilterSet(filters.FilterSet):
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


class PermissionFilterSet(filters.FilterSet):
    """FilterSet class for Permission."""

    class Meta:
        """Metadata for the class."""

        model = Permission
        fields = {
            "namespace": _key_lookups,
            "group": _key_lookups,
            "has_create": ["exact"],
            "has_read": ["exact"],
            "has_update": ["exact"],
            "has_delete": ["exact"],
            "has_namespace": ["exact"],
        }
        fields.update(_hubuum_fields)


class ExtensionFilterSet(NamespacePermissionFilter):
    """FilterSet class for Extension."""

    class Meta:
        """Metadata for the class."""

        model = Extension
        fields = {
            "name": _textual_lookups,
            "model": _textual_lookups,
            "url": _textual_lookups,
            "require_interpolation": ["exact"],
            "header": _textual_lookups,
            "cache_time": _numeric_lookups,
        }
        fields.update(_namespace_fields)


class ExtensionDataFilterSet(NamespacePermissionFilter):
    """FilterSet class for ExtensionData."""

    json_data = JSONFieldExactFilter()

    class Meta:
        """Metadata for the class."""

        model = ExtensionData
        fields = {
            "extension": _key_lookups,
            "content_type": ["exact"],
            "object_id": _numeric_lookups,
            #            "json_data": _textual_lookups,
        }
        fields.update(_namespace_fields)


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
            "room": _key_lookups,
            "jack": _key_lookups,
            "purchase_order": _key_lookups,
            "person": _key_lookups,
        }


class HostTypeFilterSet(NamespacePermissionFilter):
    """FilterSet class for HostType."""

    class Meta:
        """Metadata for the class."""

        model = HostType
        fields = {"name": _textual_lookups, "description": _textual_lookups}
        fields.update(_namespace_fields)


class JackFilterSet(NamespacePermissionFilter):
    """FilterSet class for Jack."""

    class Meta:
        """Metadata for the class."""

        model = Jack
        fields = {
            "name": _textual_lookups,
            "building": _textual_lookups,
            "room": _key_lookups,
        }
        fields.update(_namespace_fields)


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
            "room": _key_lookups,
        }
        fields.update(_namespace_fields)


class PurchaseDocumentsFilterSet(NamespacePermissionFilter):
    """FilterSet class for PurchaseDocuments."""

    class Meta:
        """Metadata for the class."""

        # It would be neat to have the binary field "document"
        # be matchable to a hash...
        model = PurchaseDocuments
        fields = {
            "document_id": _numeric_lookups,
            "purchase_order": _key_lookups,
        }
        fields.update(_namespace_fields)


class PurchaseOrderFilterSet(NamespacePermissionFilter):
    """FilterSet class for PurchaseOrder."""

    class Meta:
        """Metadata for the class."""

        model = PurchaseOrder
        fields = {
            "vendor": _key_lookups,
            "order_date": _date_lookups,
            "po_number": _textual_lookups,
        }
        fields.update(_namespace_fields)


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
        fields.update(_namespace_fields)


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
        fields.update(_namespace_fields)
