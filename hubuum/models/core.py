# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false
"""Core models for hubuum."""

import hashlib
from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from django.db import models
from django.db.models import JSONField
from jsonschema import Draft7Validator, validate
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError as SchemaValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from hubuum.exceptions import UnsupportedAttachmentModelError


def model_is_open(model: str) -> bool:
    """Check if the model is an open model."""
    return model in models_that_are_open()


def models_that_are_open() -> Tuple[str]:
    """Return a list of models open to all authenticated users."""
    return ("user", "group")


def class_supports_attachments(model: str) -> bool:
    """Check if a model supports attachments."""


class HubuumModel(models.Model):
    """Base model for Hubuum Objects."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    class Meta:
        """Meta data for the class."""

        abstract = True

    def get_auto_id(self) -> int:
        """Get the auto ID of the object."""
        return cast(int, self.id)


class NamespacedHubuumModel(HubuumModel):
    """Base model for a namespaced Hubuum Objects.

    Adds the following fields:
        namespace: The namespace the object belongs to.

    Inherits from HubuumModel, which and adds the following fields:
        created_at: The date and time the object was created.
        updated_at: The date and time the object was last updated.
    """

    # When we delete a namespace, do we want *all* the objects to disappear?
    # That'd be harsh. But, well... What is the realistic option?
    namespace: int = models.ForeignKey(
        "Namespace",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )

    class Meta:
        """Meta data for the class."""

        abstract = True


class AttachmentManager(HubuumModel):
    """Managing what models may have attachments and what constraints are imposed."""

    hubuum_class = models.ForeignKey("HubuumClass", on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False, null=False)
    per_object_count_limit = models.PositiveIntegerField(default=0, null=False)
    per_object_individual_size_limit = models.PositiveIntegerField(
        default=0, null=False
    )
    per_object_total_size_limit = models.PositiveIntegerField(default=0, null=False)

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

    def __str__(self) -> str:
        """Stringify the object, used to represent the object towards users."""
        return str(self.get_auto_id())


class Attachment(NamespacedHubuumModel):
    """A model for the attachments data for objects."""

    attachment = models.FileField(unique=True)
    hubuum_class = models.ForeignKey("HubuumClass", on_delete=models.CASCADE)
    hubuum_object = models.ForeignKey("HubuumObject", on_delete=models.CASCADE)
    sha256 = models.CharField(max_length=64, unique=True, editable=False)
    size = models.PositiveIntegerField(editable=False)
    original_filename = models.CharField(max_length=255, editable=False)

    class Meta:
        """Meta for the model."""

        ordering = ["id"]

    def generate_sha256_filename(self, sha256_hash: str):
        """Generate a custom filename for the uploaded file using its sha256 hash."""
        return f"attachments/file/{sha256_hash}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override the save method to compute the sha256 hash and size of the uploaded file."""
        file_contents = self.attachment.read()
        self.sha256 = hashlib.sha256(file_contents).hexdigest()
        self.size = self.attachment.size
        self.original_filename = self.attachment.name
        self.attachment.name = self.generate_sha256_filename(self.sha256)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Stringify the object, used to represent the object towards users."""
        return str(self.get_auto_id())


class AttachmentModel(models.Model):
    """A model that supports attachments."""

    class Meta:
        """Meta for the model."""

        abstract = True

    def attachments_are_enabled(self) -> bool:
        """Check if the model is ready to receive attachments."""
        return AttachmentManager.objects.filter(
            hubuum_class=self.hubuum_class, enabled=True
        ).exists()

    def attachments(self) -> List[Attachment]:
        """List all attachments registered to the object."""
        if not self.attachments_are_enabled():
            raise UnsupportedAttachmentModelError(
                f"Attachments are not enabled for {self.hubuum_class.name}."
            )

        return Attachment.objects.filter(
            hubuum_class=self.hubuum_class, hubuum_object=self
        )

    def attachment_count(self) -> int:
        """Return the number of attachments registered to the object."""
        return self.attachments().count()

    def attachment_size(self) -> int:
        """Return the total size of all attachments registered to the object."""
        return sum(attachment.size for attachment in self.attachments())

    def attachment_individual_size_limit(self) -> int:
        """Return the max size of an attachment for the object."""
        return AttachmentManager.objects.get(
            hubuum_class=self.hubuum_class, enabled=True
        ).per_object_individual_size_limit

    def attachment_total_size_limit(self) -> int:
        """Return the size limit of attachments for the object."""
        return AttachmentManager.objects.get(
            hubuum_class=self.hubuum_class, enabled=True
        ).per_object_total_size_limit

    def attachment_count_limit(self) -> int:
        """Return the count limit of attachments for the object."""
        return AttachmentManager.objects.get(
            hubuum_class=self.hubuum_class, enabled=True
        ).per_object_count_limit


class HubuumClass(NamespacedHubuumModel):
    """A user-created 'class'/'model'.

    :param name: The name of the class.
    :param json_schema: The JSON schema of the class (optional)
    :param validate_schema: A boolean indicating if the schema should be validated (optional).
    :param namespace: The namespace the class belongs to.

    The idea with namespaces for classes is that access to the entire structure may be limited
    to a specific set of users who can perform actions on this namespace.

    :raises: rest_framework.exceptions.ValidationError if the proposed schema is not valid.

    :return: A HubuumClass instance.
    """

    name = models.CharField(max_length=200, null=False, unique=True)
    json_schema = JSONField(blank=True, null=True)
    validate_schema = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return a string representation of the HubuumClass instance.

        :return: A string representation of the HubuumClass instance.
        """
        return f"{self.name}"

    def get_object(self, identifier: str) -> Optional["HubuumObject"]:
        """Retrieve a HubuumObject instance based on its name or primary key.

        Tries to find the object first by its name, and if not found, by its primary
        key (if `identifier` is a digit-only string). If the object is not found,
        returns None.

        :param identifier: The name or primary key of the object.
        :return: The found HubuumObject instance, or None if not found.
        """
        try:
            return HubuumObject.objects.get(name=identifier, hubuum_class=self)
        except HubuumObject.DoesNotExist:
            if identifier.isdigit():
                try:
                    return HubuumObject.objects.get(pk=identifier, hubuum_class=self)
                except HubuumObject.DoesNotExist:
                    pass

        return None

    def validate_schema_correctness(self, schema: Dict[str, Any]) -> bool:
        """Validate that a given JSON schema is well-formed."""
        try:
            Draft7Validator.check_schema(schema)
        except SchemaError as e:
            raise DRFValidationError(
                f"The proposed schema is not valid: {str(e)}"
            ) from e

    def validate_additive_schema_change(self, new_schema: Dict[str, Any]) -> bool:
        """Validate that a proposed schema change is additive.

        :param new_schema: The proposed new JSON schema.

        :return: A boolean indicating if the proposed schema is additive.

        :raises: rest_framework.exceptions.ValidationError if the proposed schema
                is not a valid JSON schema, or if the proposed schema change is
                not additive.
        """
        # First, we need to check if the new schema is a valid JSON schema.
        self.validate_schema_correctness(new_schema)

        old_schema: Dict[str, Any] = self.json_schema

        # If there's no old schema, any valid new schema is considered additive.
        # However, this should only be called on update, so this should never happen.
        # if not old_schema:
        #    return True

        def check_subset(old: Dict[str, Any], new: Dict[str, Any]) -> bool:
            for key, old_val in old.items():
                if key not in new:
                    return False
                new_val = new[key]
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    if not check_subset(old_val, new_val):
                        return False
            return True

        if check_subset(old_schema, new_schema):
            # This means every key in the old schema is present in the new schema.
            # Therefore the new schema is considered an additive change.
            return True
        else:
            raise DRFValidationError("Schema changes must be additive.")

    def get_transitive_paths(
        self, target_class: str, max_depth: int = 0
    ) -> List[List["ClassLink"]]:
        """Produce all possible paths that can lead from self to target_class.

        Each path is represented as a list of ClassLinks.
        """
        queue = deque(
            [([], self, set([self]))]
        )  # queue elements are: (path, class, visited classes)
        paths = []

        # Get the HubuumClass object for the target class.
        target_class = HubuumClass.objects.get(name=target_class)

        while queue:
            path, node, visited = queue.popleft()
            if max_depth and len(path) >= max_depth:
                break
            link_types = ClassLink.objects.filter(source_class=node)
            for link_type in link_types:
                if link_type.target_class in visited:
                    continue  # Avoid cycles.
                new_visited = visited.copy()
                new_visited.add(link_type.target_class)
                new_path = path + [link_type]
                if link_type.target_class == target_class:
                    paths.append(new_path)
                else:
                    queue.append((new_path, link_type.target_class, new_visited))

        return paths


class HubuumObject(NamespacedHubuumModel, AttachmentModel):
    """A user-created object.

    :param name: The name of the object.
    :param hubuum_class: The class of the object.
    :param json_data: The data of the object.
    :param namespace: The namespace the object belongs to.

    :raises: rest_framework.exceptions.ValidationError if the instance data is invalid.

    :return: A HubuumObject instance.

    """

    name = models.CharField(max_length=200, null=False)
    hubuum_class = models.ForeignKey(HubuumClass, null=False, on_delete=models.CASCADE)
    json_data = JSONField()

    class Meta:
        """Define the HubuumObjects model's meta data."""

        unique_together = ["name", "hubuum_class"]

    def __str__(self) -> str:
        """Return a string representation of the HubuumObject instance.

        :return: A string representation of the HubuumObject instance.
        """
        return f"{self.name} [{self.hubuum_class.name}]"

    def has_schema(self) -> bool:
        """Determine if a JSON schema exists for the HubuumObject instance.

        :return: A boolean indicating if a JSON schema exists.
        """
        return bool(self.hubuum_class.json_schema)

    def validation_required(self) -> bool:
        """Determine if validation is required for the HubuumObject instance.

        :return: A boolean indicating if validation is required.
        """
        return self.hubuum_class.validate_schema

    def validate_json(self) -> bool:
        """Validate the HubuumObject instance against its schema if validation is required.

        :return: A boolean indicating if the instance data is valid.

        :raises: rest_framework.exceptions.ValidationError if the instance data is not valid.
        """
        if self.validation_required() and self.has_schema():
            schema = self.hubuum_class.json_schema
            try:
                validate(instance=self.json_data, schema=schema)
                return True
            except SchemaValidationError as exc:
                raise DRFValidationError(
                    f"Data is not valid according to schema: {str(exc)}"
                ) from exc
        else:
            # If validation is not required, we consider the instance valid by default.
            return True

    def find_transitive_links(
        self, target_class: HubuumClass, max_depth: int = 0
    ) -> List[Dict[str, Union["HubuumObject", List["ObjectLink"]]]]:
        """Find all paths from self to any object of target_class."""
        # Get the possible paths and early exit if there's no possible link to the target_class.
        possible_paths = self.hubuum_class.get_transitive_paths(
            target_class, max_depth=max_depth
        )
        if not possible_paths:
            return []

        def traverse(
            possible_path: List[ClassLink], current_path: List[HubuumObject]
        ) -> List[List[HubuumObject]]:
            """Traverse the possible paths and collect links that meet the path requirements."""
            # First, we check the possible ClassLinks for the current node.
            # These are the class-based links.
            traversed_path = []
            if not possible_path:
                return [current_path]

            for link_type in possible_path:
                object_links = current_path[-1].outbound_links.filter(
                    link_type=link_type
                )
                for link in object_links:
                    traversed_path.extend(
                        traverse(possible_path[1:], current_path + [link.target])
                    )

            return traversed_path

        # Traverse the possible paths and collect the links that meet the path requirements.
        paths = []
        for possible_path in possible_paths:
            object_paths = traverse(possible_path, [self])

            # If we reached the end of the path and the last node's class is the target class,
            # then we successfully found a path.
            for objects in object_paths:
                paths.append({"object": objects[-1], "path": objects})

        return paths

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the HubuumObject instance.

        Validates the instance data if validation is required.
        """
        self.validate_json()
        super().save(*args, **kwargs)


class ClassLink(NamespacedHubuumModel):
    """A user-created link type between two classes."""

    source_class = models.ForeignKey(
        HubuumClass, related_name="source_links", on_delete=models.CASCADE
    )
    target_class = models.ForeignKey(
        HubuumClass, related_name="target_links", on_delete=models.CASCADE
    )
    max_links = models.IntegerField()

    class Meta:
        """Define the ClassLink model's meta data."""

        unique_together = ["source_class", "target_class"]

    def __str__(self) -> str:
        """Return a string representation of the ClassLink instance."""
        return (
            f"{self.source_class.name} <-> {self.target_class.name} ({self.max_links})"
        )


class ObjectLink(NamespacedHubuumModel):
    """ObjectLink model represents a user-defined link between two objects.

    The model inherits from NamespacedHubuumModel, which includes fields:
        namespace: The namespace the object belongs to.
        created_at: The date and time the object was created.
        updated_at: The date and time the object was last updated.

    Fields:
    - source: The source object of the link.
    - target: The target object of the link.
    - link_type: A ForeignKey to the ClassLink model which defines the type of the link.
    """

    source = models.ForeignKey(
        "HubuumObject",
        on_delete=models.CASCADE,
        related_name="outbound_links",
    )
    target = models.ForeignKey(
        "HubuumObject",
        on_delete=models.CASCADE,
        related_name="inbound_links",
    )
    link_type = models.ForeignKey(
        "ClassLink",
        on_delete=models.CASCADE,
        related_name="links",
    )

    class Meta:
        """Define the ObjectLink model's meta data."""

        unique_together = ["source", "target"]

    def __str__(self) -> str:
        """Return a string representation of the ObjectLink instance."""
        return f"{self.source} <-> {self.target}"
