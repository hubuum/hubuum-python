"""Dynamic class constructs for Hubuum."""

# Meta is a bit bugged: https://github.com/microsoft/pylance-release/issues/3814
# pyright: reportIncompatibleVariableOverride=false


from collections import deque
from typing import Any, Dict, List, Union

from django.db import models
from django.db.models import JSONField
from jsonschema import Draft7Validator, validate
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError as SchemaValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from hubuum.models.core import NamespacedHubuumModel


class HubuumClass(NamespacedHubuumModel):
    """A user-created 'class'/'model'."""

    name = models.CharField(max_length=200, null=False, unique=True)
    json_schema = JSONField(blank=True, null=True)
    validate_schema = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return a string representation of the HubuumClass instance.

        :return: A string representation of the HubuumClass instance.
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


class HubuumObject(NamespacedHubuumModel):
    """A user-created object."""

    name = models.CharField(max_length=200, null=False)
    dynamic_class = models.ForeignKey(HubuumClass, null=False, on_delete=models.CASCADE)
    json_data = JSONField()

    class Meta:
        """Define the HubuumObjects model's meta data."""

        unique_together = ["name", "dynamic_class"]

    def __str__(self) -> str:
        """Return a string representation of the HubuumObject instance.

        :return: A string representation of the HubuumObject instance.
        """
        return f"{self.name} [{self.dynamic_class.name}]"

    def has_schema(self) -> bool:
        """Determine if a JSON schema exists for the HubuumObject instance.

        :return: A boolean indicating if a JSON schema exists.
        """
        return bool(self.dynamic_class.json_schema)

    def validation_required(self) -> bool:
        """Determine if validation is required for the HubuumObject instance.

        :return: A boolean indicating if validation is required.
        """
        return self.dynamic_class.validate_schema

    def validate_json(self) -> bool:
        """Validate the HubuumObject instance against its schema if validation is required.

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

    def find_transitive_links(
        self, target_class: HubuumClass, max_depth: int = 0
    ) -> List[Dict[str, Union["HubuumObject", List["ObjectLink"]]]]:
        """Find all paths from self to any object of target_class."""
        # Get the possible paths and early exit if there's no possible link to the target_class.
        possible_paths = self.dynamic_class.get_transitive_paths(
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
