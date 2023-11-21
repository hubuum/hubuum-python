"""Validators for Hubuum.

This package is NOT allowed to import anything from internally in hubuum, except tools.
"""

import re
from typing import Type

import validators
from django.db.models import Model
from rest_framework.exceptions import ValidationError

from hubuum.models.core import HubuumClass
from hubuum.tools import get_model

url_interpolation_regexp = re.compile("{(.*?)}")


# We use Model here as some of our classes (like Attachment) inherit directly
# from django.db.models.Model, and not from HubuumModel.
def _get_model(model: str) -> Type[Model]:
    """Get the model class from a string."""
    # Ensuring the caller is using the correct type.
    # https://peps.python.org/pep-0484/ makes it very clear that
    # "no type checking happens at runtime". Eventually we will clear this up
    # by ensuring that the caller is using the correct type.
    if not isinstance(model, str):
        raise ValidationError({"model": "The model name must be a string."})

    model = get_model(model)
    if not model:
        raise ValidationError({"model": "No such model"})

    return model


def validate_is_existing_hubuum_class(name: str) -> bool:
    """Validate that a HubuumClass exists."""
    return HubuumClass.objects.filter(name=name).exists()


def validate_url(url: str) -> bool:
    """Validate that the URL field is valid.

    Requirements:
     - Has a supported protocol (http/https)
     - Is a well-formed URL
    """
    clean_url = re.sub(url_interpolation_regexp, "", url)

    if not validators.url(clean_url):  # type: ignore (pylance and documentation mismatch)
        raise ValidationError({"url": f"{url} is malformed."})

    return True
