"""Versioned (v1) serializers of the hubuum models."""
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

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


class ErrorOnBadFieldMixin:  # pylint: disable=too-few-public-methods
    """Raise validation errors on bad input.

    Django Rest Framework returns 200 OK for patches against both
    read-only fields and non-existent fields... Ie, a quiet failure.
    This mixin changes that behaviour to raise a Validation error which
    again causes the response "400 Bad Request".
    See https://github.com/encode/django-rest-framework/issues/6508
    """

    def run_validation(self, data=empty):
        """Run the validation of the input."""
        if isinstance(data, dict):
            provided_keys = data.keys()
        else:
            provided_keys = data[::2]

        items = self.fields.items()

        for fieldname, field in items:
            if field.read_only and fieldname in provided_keys:
                raise ValidationError(
                    code="write_on_read_only_field",
                    detail={  # pylint: disable=undefined-loop-variable
                        fieldname: (f"'{fieldname}' is a read-only field.")
                    },
                )

        extra_keys = set(provided_keys) - set(self.fields.keys())
        if extra_keys:
            raise ValidationError(
                code="write_on_non_existent_field",
                detail={  # pylint: disable=undefined-loop-variable
                    "extra_keys": f"{extra_keys} do not exist."
                },
            )

        return super().run_validation(data)


class HubuumSerializer(ErrorOnBadFieldMixin, serializers.ModelSerializer):
    """General Hubuum Serializer."""


class UserSerializer(HubuumSerializer):
    """Serialize a User object."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Leave empty if no change needed",
        style={"input_type": "password", "placeholder": "Password"},
    )

    def create(self, validated_data):
        """Ensure the password is hashed on user creation."""
        validated_data["password"] = make_password(validated_data.get("password"))
        return super().create(validated_data)

    class Meta:
        """How to serialize the object."""

        model = User
        fields = "__all__"


class GroupSerializer(HubuumSerializer):
    """Serialize a Group object."""

    class Meta:
        """How to serialize the object."""

        model = Group
        fields = "__all__"


class HostSerializer(HubuumSerializer):
    """Serialize a Host object."""

    # serializers.HyperlinkedModelSerializer
    #    externals = serializers.SerializerMethodField()
    #    _mod_dns = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())

    class Meta:
        """How to serialize the object."""

        model = Host
        fields = "__all__"
        # fields = ['id', 'name', '_mod_dns']


class NamespaceSerializer(HubuumSerializer):
    """Serialize a Namespace object."""

    class Meta:
        """How to serialize the object."""

        model = Namespace
        fields = "__all__"


class PermissionSerializer(HubuumSerializer):
    """Serialize a Permission object."""

    class Meta:
        """How to serialize the object."""

        model = Permission
        fields = "__all__"


class HostTypeSerializer(HubuumSerializer):
    """Serialize a HostType object."""

    class Meta:
        """How to serialize the object."""

        model = HostType
        fields = "__all__"


class JackSerializer(HubuumSerializer):
    """Serialize a Jack object."""

    class Meta:
        """How to serialize the object."""

        model = Jack
        fields = "__all__"


class PersonSerializer(HubuumSerializer):
    """Serialize a Person object."""

    class Meta:
        """How to serialize the object."""

        model = Person
        fields = "__all__"


class RoomSerializer(HubuumSerializer):
    """Serialize a Room object."""

    class Meta:
        """How to serialize the object."""

        model = Room
        fields = "__all__"


class PurchaseDocumentsSerializer(HubuumSerializer):
    """Serialize a PurchaseDocument object."""

    class Meta:
        """How to serialize the object."""

        model = PurchaseDocuments
        fields = "__all__"


class PurchaseOrderSerializer(HubuumSerializer):
    """Serialize a PurchaseOrder object."""

    class Meta:
        """How to serialize the object."""

        model = PurchaseOrder
        fields = "__all__"


class VendorSerializer(HubuumSerializer):
    """Serialize a Vendor object."""

    class Meta:
        """How to serialize the object."""

        model = Vendor
        fields = "__all__"
