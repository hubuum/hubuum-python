# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false
"""Core models for hubuum."""

import hashlib
from typing import Any, List, Tuple, Union, cast

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from hubuum.tools import get_model
from hubuum.validators import validate_model_can_have_attachments


def model_is_open(model: str) -> bool:
    """Check if the model is an open model."""
    return model in models_that_are_open()


def models_that_are_open() -> Tuple[str]:
    """Return a list of models open to all authenticated users."""
    return ("user", "group")


def model_supports_attachments(model: Union[str, models.Model]) -> bool:
    """Check if a model supports attachments."""
    if isinstance(model, str):
        model = get_model(model)

    return issubclass(model, AttachmentModel)


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

    @classmethod
    def supports_attachments(cls) -> bool:
        """Check if a class supports attachments."""
        return issubclass(cls, AttachmentModel)

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
    """A model for attachments to objects."""

    model: str = models.CharField(
        max_length=255,
        null=False,
        validators=[validate_model_can_have_attachments],
        unique=True,
    )
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
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
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

    attachment_data_objects = GenericRelation(
        Attachment, related_query_name="att_objects"
    )

    class Meta:
        """Meta for the model."""

        abstract = True

    def attachments_are_enabled(self) -> bool:
        """Check if the model is ready to receive attachments."""
        return AttachmentManager.objects.filter(
            model=self.__class__.__name__.lower(), enabled=True
        ).exists()

    def attachments(self) -> List[Attachment]:
        """List all attachments registered to the object."""
        return self.attachment_data_objects.all()

    def attachment_count(self) -> int:
        """Return the number of attachments registered to the object."""
        return self.attachment_data_objects.count()

    def attachment_size(self) -> int:
        """Return the total size of all attachments registered to the object."""
        return sum(attachment.size for attachment in self.attachments())

    def attachment_individual_size_limit(self) -> int:
        """Return the max size of an attachment for the object."""
        return AttachmentManager.objects.get(
            model=self.__class__.__name__.lower(), enabled=True
        ).per_object_individual_size_limit

    def attachment_total_size_limit(self) -> int:
        """Return the size limit of attachments for the object."""
        return AttachmentManager.objects.get(
            model=self.__class__.__name__.lower(), enabled=True
        ).per_object_total_size_limit

    def attachment_count_limit(self) -> int:
        """Return the count limit of attachments for the object."""
        return AttachmentManager.objects.get(
            model=self.__class__.__name__.lower(), enabled=True
        ).per_object_count_limit
