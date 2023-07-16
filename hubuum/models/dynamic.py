"""Dynamic class constructs for Hubuum."""

# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false


from typing import Any, Dict

from django.db import models
from django.db.models import JSONField
from jsonschema import Draft7Validator, validate
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError as SchemaValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from hubuum.models.core import NamespacedHubuumModel


class DynamicClass(NamespacedHubuumModel):
    """A user-created 'class'/'model'."""

    name = models.CharField(max_length=200, null=False, unique=True)
    json_schema = JSONField(blank=True, null=True)
    validate_schema = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return a string representation of the DynamicClass instance.

        :return: A string representation of the DynamicClass instance.
        """
        return f"{self.name}"

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


class DynamicObject(NamespacedHubuumModel):
    """A user-created object."""

    name = models.CharField(max_length=200, null=False, unique=True)
    dynamic_class = models.ForeignKey(
        DynamicClass, null=False, on_delete=models.CASCADE
    )
    json_data = JSONField()

    def __str__(self) -> str:
        """Return a string representation of the DynamicObject instance.

        :return: A string representation of the DynamicObject instance.
        """
        return f"{self.name} [{self.dynamic_class.name}]"

    def has_schema(self) -> bool:
        """Determine if a JSON schema exists for the DynamicObject instance.

        :return: A boolean indicating if a JSON schema exists.
        """
        return bool(self.dynamic_class.json_schema)

    def validation_required(self) -> bool:
        """Determine if validation is required for the DynamicObject instance.

        :return: A boolean indicating if validation is required.
        """
        return self.dynamic_class.validate_schema

    def validate_json(self) -> bool:
        """Validate the DynamicObject instance against its schema if validation is required.

        :return: A boolean indicating if the instance data is valid.

        :raises: rest_framework.exceptions.ValidationError if the instance data is not valid.
        """
        if self.validation_required() and self.has_schema():
            schema = self.dynamic_class.json_schema
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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the DynamicObject instance.

        Validates the instance data if validation is required.
        """
        self.validate_json()
        super().save(*args, **kwargs)
