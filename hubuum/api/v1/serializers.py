# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false
"""Versioned (v1) serializers of the hubuum models."""

import hashlib
from typing import Any, Dict, List, cast

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from hubuum.exceptions import Conflict
from hubuum.models.core import (
    Attachment,
    AttachmentManager,
    ClassLink,
    HubuumClass,
    HubuumObject,
    ObjectLink,
)
from hubuum.models.iam import Namespace, Permission, User


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Catch some possible OpenAPI issues."""
        super().__init__(*args, **kwargs)

        if "request" not in self.context:
            return

        # Generating the openAPI specification can cause self.context["request"] to be None
        # This is a very weird corner case.
        if not self.context["request"]:
            return

        if not self.context["request"].method == "GET":
            return

        return

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
            _per_object_individual_size_limit = int(obj.per_object_individual_size_limit)

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


class HubuumClassSerializer(HubuumMetaSerializer):
    """Serialize a HubuumClass object."""

    class Meta:
        """How to serialize the object."""

        model = HubuumClass
        fields = [
            "name",
            "updated_at",
            "created_at",
            "json_schema",
            "validate_schema",
            "namespace",
        ]

    def update(self, instance: HubuumClass, validated_data: Dict[str, Any]):
        """Update the HubuumClass instance with the proposed schema if validation succeeds."""
        # Validating the schema to be additive implies validating
        # that the schema in itself is valid
        if "json_schema" in validated_data:
            instance.validate_additive_schema_change(validated_data["json_schema"])

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance

    def create(self, validated_data: Dict[str, Any]):
        """Create a new HubuumClass instance with the proposed schema if validation succeeds."""
        instance = HubuumClass(**validated_data)
        proposed_schema = validated_data.get("json_schema", None)

        # Proposed_schema may be false or empty, so we need to check for None
        if proposed_schema is not None:
            instance.validate_schema_correctness(proposed_schema)

        instance.save()
        return instance


class HubuumObjectSerializer(HubuumMetaSerializer):
    """Serialize a HubuumObject object."""

    # Make the hubuum_class field read-only so that it's not required during initial validation
    # hubuum_class = serializers.PrimaryKeyRelatedField(read_only=True)

    hubuum_class = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        """How to serialize the object."""

        model = HubuumObject
        fields = [
            "id",
            "name",
            "updated_at",
            "created_at",
            "json_data",
            "namespace",
            "hubuum_class",
        ]


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


class ClassLinkSerializer(HubuumMetaSerializer):
    """Serialize a ClassLink object."""

    source_class = serializers.SlugRelatedField(
        slug_field="name",
        read_only=True,
    )
    target_class = serializers.SlugRelatedField(
        slug_field="name",
        read_only=True,
    )

    class Meta:
        """How to serialize the object."""

        model = ClassLink
        fields = [
            "source_class",
            "target_class",
            "max_links",
            "namespace",
            "created_at",
            "updated_at",
        ]


class ObjectLinkSerializer(serializers.ModelSerializer):  # type: ignore
    """Serializer for the ObjectLink model."""

    source = serializers.SlugRelatedField(slug_field="name", queryset=HubuumObject.objects.all())
    target = serializers.SlugRelatedField(slug_field="name", queryset=HubuumObject.objects.all())

    path = serializers.SerializerMethodField(required=False)

    class Meta:
        """How to serialize the object."""

        model = ObjectLink
        fields = ["source", "target", "path"]

    def get_path(self, obj: ObjectLink):
        """Get the path to the object."""
        return getattr(obj, "path", None)


class PathSerializer(serializers.Serializer):  # type: ignore
    """Serialize a path to an object."""

    object = HubuumObjectSerializer(read_only=True)  # noqa: A003 (redefine object)
    path = serializers.SerializerMethodField()

    def get_path(self, objects: Dict[str, Any]):
        """Display the path to the object as a name of classes we pass through."""
        return HubuumObjectSerializer(objects["path"], many=True).data
