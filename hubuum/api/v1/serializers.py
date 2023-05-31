# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false
"""Versioned (v1) serializers of the hubuum models."""
import hashlib
from typing import Any, Dict, List, cast

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from hubuum.exceptions import Conflict
from hubuum.models.auth import User
from hubuum.models.core import (
    Attachment,
    AttachmentManager,
    Extension,
    ExtensionData,
    ExtensionsModel,
)
from hubuum.models.permissions import (
    Namespace,
    NamespacedHubuumModelWithExtensions,
    Permission,
)
from hubuum.models.resources import (
    Host,
    HostType,
    Jack,
    Person,
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

    def run_validation(self, data: Dict[str, Any] = empty) -> Dict[str, Any]:
        """Run the validation of the input."""
        if not isinstance(data, dict):  # type: ignore as we have user input.
            raise ValidationError(
                code="expected_dict",
                detail={"typeerror": "API expected a dictionary."},
            )

        provided_keys = data.keys()
        items = cast(Dict[str, Any], self.fields.items())

        for fieldname, field in items:
            if field.read_only and fieldname in provided_keys:
                raise ValidationError(
                    code="write_on_read_only_field",
                    detail={  # pylint: disable=undefined-loop-variable
                        fieldname: (f"'{fieldname}' is a read-only field.")
                    },
                )

        extra_keys = set(provided_keys) - set(cast(List[str], self.fields.keys()))
        if extra_keys:
            raise ValidationError(
                code="write_on_non_existent_field",
                detail={  # pylint: disable=undefined-loop-variable
                    "extra_keys": f"{extra_keys} do not exist."
                },
            )

        return cast(Dict[str, Any], super().run_validation(data))


# run_validation type mismatch. From DRF there is no typing, so we get the following:
# Base classes for class "PermissionSerializer" define method "run_validation"
# in incompatible way
# Parameter 2 type mismatch: base parameter is type "Type[empty]", override parameter
# is type "Dict[str, Any]"
# "Type[type]" is incompatible with "Type[Dict[str, Any]]"
# PylancereportIncompatibleMethodOverride
# serializers.py(416, 9): Base class "Serializer" provides type
#  "(self: Self@Serializer, data: Type[empty] = empty) ->
#   (empty | Unknown | OrderedDict[Unknown, Unknown] | None)", which is overridden
# serializers.py(49, 9): Base class "ErrorOnBadFieldMixin" overrides with type
#  "(self: Self@ErrorOnBadFieldMixin, data: Dict[str, Any] = empty) -> Dict[str, Any]""
class HubuumMetaSerializer(ErrorOnBadFieldMixin, serializers.ModelSerializer):  # type: ignore
    """General Hubuum Serializer."""

    def __init__(self, *args: Any, **kwargs: Any):
        """For methods that are subclasses of ExtensionsModel, enable relevant fields."""
        super().__init__(*args, **kwargs)

        if "request" not in self.context:
            return

        # Generating the openAPI specification can cause self.context["request"] to be None
        # This is a very weird corner case.
        if not self.context["request"]:
            return

        if not self.context["request"].method == "GET":
            return

        if issubclass(self.Meta.model, ExtensionsModel):
            self.fields["extensions"] = serializers.SerializerMethodField()
            self.fields["extension_data"] = serializers.SerializerMethodField()
            self.fields["extension_urls"] = serializers.SerializerMethodField()
        return

    def get_extension_urls(
        self, obj: NamespacedHubuumModelWithExtensions
    ) -> Dict[str, str]:
        """Deliver the endpoint for the URL for this specific object."""
        return obj.extension_urls()

    def get_extension_data(
        self, obj: NamespacedHubuumModelWithExtensions
    ) -> Dict[str, Any]:
        """Display extension data."""
        return obj.extension_data()

    def get_extensions(self, obj: NamespacedHubuumModelWithExtensions) -> List[str]:
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

    def create(self, validated_data: Dict[str, Any]) -> User:
        """Ensure the password is hashed on user creation."""
        validated_data["password"] = make_password(validated_data.get("password"))
        return cast(Dict[str, Any], super().create(validated_data))

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

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the data offered applies to the correct model.

        This doesn't even get triggered unless we have a working extension object.
        """
        require_interpolation = True  # This should fetch the default for the field

        model = None
        if self.partial and self.instance and isinstance(self.instance, Extension):
            require_interpolation = self.instance.require_interpolation
            url = self.instance.url
            model = self.instance.model

        url = ""
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

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
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


class AttachmentManagerSerializer(HubuumMetaSerializer):
    """Serialize an AttachmentManager object."""

    class Meta:
        """How to serialize the object."""

        model = AttachmentManager
        fields = "__all__"

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the the limits are sane."""
        _per_object_total_size_limit = 0
        _per_object_individual_size_limit = 0

        if self.instance and isinstance(self.instance, AttachmentManager):
            obj = self.instance
            _per_object_total_size_limit = int(obj.per_object_total_size_limit)
            _per_object_individual_size_limit = int(
                obj.per_object_individual_size_limit
            )

        per_object_total_size_limit = attrs.get(
            "per_object_total_size_limit",
            _per_object_total_size_limit,
        )
        per_object_individual_size_limit = attrs.get(
            "per_object_individual_size_limit", _per_object_individual_size_limit
        )

        if per_object_total_size_limit and per_object_individual_size_limit:
            if per_object_total_size_limit < per_object_individual_size_limit:
                # The extra paranthese make the string concateation explicit.
                raise ValidationError(
                    """per_object_total_size_limit should be greater than or equal to
                        per_object_individual_size_limit."""
                )
        return attrs


class AttachmentSerializer(HubuumMetaSerializer):
    """Serialize an Attachment object."""

    class Meta:
        """How to serialize the object."""

        model = Attachment
        fields = "__all__"

    def validate_attachment(self, file: UploadedFile) -> UploadedFile:
        """Validate attachment uniqueness."""
        # Calculate the sha256 hash and size of the uploaded file
        file_contents = file.read()
        sha256 = hashlib.sha256(file_contents).hexdigest()

        # Check if a file with the same sha256 hash already exists in the database
        if Attachment.objects.filter(sha256=sha256).exists():
            raise Conflict("Already uploaded.")

        # Reset file pointer to the beginning of the file after reading
        file.seek(0)

        return file


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


# run_validation type mismatch. See the comment for HubuumMetaSerializer.
class PermissionSerializer(ErrorOnBadFieldMixin, serializers.ModelSerializer):  # type: ignore
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
