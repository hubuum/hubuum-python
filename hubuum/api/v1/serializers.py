"""Versioned (v1) serializers of the hubuum models."""
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from hubuum.models.auth import User
from hubuum.models.base import (
    Extension,
    ExtensionData,
    ExtensionsModel,
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
from hubuum.tools import get_model
from hubuum.validators import url_interpolation_fields


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
        if not isinstance(data, dict):
            raise ValidationError(
                code="expected_dict",
                detail={"typeerror": "API expected a dictionary."},
            )

        provided_keys = data.keys()
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


class HubuumMetaSerializer(ErrorOnBadFieldMixin, serializers.ModelSerializer):
    """General Hubuum Serializer."""

    def __init__(self, *args, **kwargs):
        """For methods that are subclasses of ExtensionsModel, enable relevant fields."""
        super().__init__(*args, **kwargs)

        if "request" not in self.context:
            return

        # Generating the openAPI specification can cause self.context["request"] to be None
        # This is a very weird corner case.
        if not self.context["request"]:  # pragma: no cover
            return

        if not self.context["request"].method == "GET":
            return

        if issubclass(self.Meta.model, ExtensionsModel):
            self.fields["extensions"] = serializers.SerializerMethodField()
            self.fields["extension_data"] = serializers.SerializerMethodField()
            self.fields["extension_urls"] = serializers.SerializerMethodField()
        return

    def get_extension_urls(self, obj):
        """Deliver the endpoint for the URL for this specific object."""
        return obj.extension_urls()

    def get_extension_data(self, obj):
        """Display extension data."""
        return obj.extension_data()

    def get_extensions(self, obj):
        """Display active extensions for the object."""
        return sorted(o.name for o in obj.extensions())

    class Meta:
        """Meta class for HubuumMetaSerializer."""

        abstract = True
        model = None


class UserSerializer(HubuumMetaSerializer):
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


class GroupSerializer(HubuumMetaSerializer):
    """Serialize a Group object."""

    class Meta:
        """How to serialize the object."""

        model = Group
        fields = "__all__"


class ExtensionSerializer(HubuumMetaSerializer):
    """Serialize an Extension object."""

    def validate(self, attrs):
        """Validate that the data offered applies to the correct model.

        This doesn't even get triggered unless we have a working extension object.
        """
        require_interpolation = True  # This should fetch the default for the field

        if self.partial and self.instance:
            require_interpolation = self.instance.require_interpolation
            url = self.instance.url
            model = self.instance.model

        if "url" in attrs:
            url = attrs["url"]

        if "model" in attrs:
            model = attrs["model"]

        if "require_interpolation" in attrs:
            require_interpolation = attrs["require_interpolation"]

        fields = url_interpolation_fields(url)
        if require_interpolation and not fields:
            raise ValidationError({"url": "Interpolation required but none found."})

        #            none model is already validated as existing via validate_model.
        #            try:
        #                cls = get_model(attrs["model"])
        #            except ValueError as ex:
        #                raise ValidationError({"model": "No such model."}) from ex

        cls = get_model(model)
        failed_fields = []
        for field in fields:
            if not hasattr(cls, field):
                failed_fields.append(field)

        if failed_fields:
            errorstring = f"{model} does not support interpolating"
            errorstring += f" on the field(s) {failed_fields}."
            raise ValidationError({"url": errorstring})

        return attrs

    class Meta:
        """How to serialize the object."""

        model = Extension
        fields = "__all__"


class ExtensionDataSerializer(HubuumMetaSerializer):
    """Serialize an ExtensionData object."""

    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field="model",
    )

    def validate(self, attrs):
        """Validate that the data offered applies to the correct model.

        This doesn't even get triggered unless we have a working extension object.
        """
        content_type = attrs["content_type"]
        extension = attrs["extension"]
        model_class = content_type.model_class()
        model_name = model_class._meta.model_name  # pylint: disable=protected-access

        if not extension.model == model_name:
            raise ValidationError({"model": "Extension does not apply to this model."})

        super().validate(self)
        return attrs

    class Meta:
        """How to serialize the object."""

        model = ExtensionData
        fields = "__all__"


class HostSerializer(HubuumMetaSerializer):
    """Serialize a Host object."""

    # serializers.HyperlinkedModelSerializer
    #    externals = serializers.SerializerMethodField()
    #    _mod_dns = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())

    class Meta:
        """How to serialize the object."""

        model = Host
        fields = "__all__"
        # fields = ['id', 'name', '_mod_dns']


class NamespaceSerializer(HubuumMetaSerializer):
    """Serialize a Namespace object."""

    class Meta:
        """How to serialize the object."""

        model = Namespace
        fields = "__all__"


class PermissionSerializer(ErrorOnBadFieldMixin, serializers.ModelSerializer):
    """Serialize a Permission object."""

    class Meta:
        """How to serialize the object."""

        model = Permission
        fields = "__all__"


class HostTypeSerializer(HubuumMetaSerializer):
    """Serialize a HostType object."""

    class Meta:
        """How to serialize the object."""

        model = HostType
        fields = "__all__"


class JackSerializer(HubuumMetaSerializer):
    """Serialize a Jack object."""

    class Meta:
        """How to serialize the object."""

        model = Jack
        fields = "__all__"


class PersonSerializer(HubuumMetaSerializer):
    """Serialize a Person object."""

    class Meta:
        """How to serialize the object."""

        model = Person
        fields = "__all__"


class RoomSerializer(HubuumMetaSerializer):
    """Serialize a Room object."""

    class Meta:
        """How to serialize the object."""

        model = Room
        fields = "__all__"


class PurchaseDocumentsSerializer(HubuumMetaSerializer):
    """Serialize a PurchaseDocument object."""

    class Meta:
        """How to serialize the object."""

        model = PurchaseDocuments
        fields = "__all__"


class PurchaseOrderSerializer(HubuumMetaSerializer):
    """Serialize a PurchaseOrder object."""

    class Meta:
        """How to serialize the object."""

        model = PurchaseOrder
        fields = "__all__"


class VendorSerializer(HubuumMetaSerializer):
    """Serialize a Vendor object."""

    class Meta:
        """How to serialize the object."""

        model = Vendor
        fields = "__all__"
