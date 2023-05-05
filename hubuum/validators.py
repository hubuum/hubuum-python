"""Validators for Hubuum.

This package is NOT allowed to import anything from internally in hubuum, except tools.
"""

import re

import validators
from rest_framework.exceptions import ValidationError

from hubuum.tools import get_model

url_interpolation_regexp = re.compile("{(.*?)}")


def _get_model(model):
    """Get the model class from a string."""
    if not isinstance(model, str):
        raise ValidationError({"model": "The model name must be a string."})

    model = get_model(model)
    if not model:
        raise ValidationError({"model": "No such model"})

    return model


def url_interpolation_fields(url):
    """Return the fields to be interpolated in the URL."""
    return re.findall(url_interpolation_regexp, url)


def validate_model_can_have_extensions(model):
    """Validate that the model can have extensions.

    Requirements:
     - Is a Hubuum model.
     - Supports extensions.
    """
    model = _get_model(model)

    if not model.supports_extensions():
        raise ValidationError({"model": "Model does not support extensions."})

    return True


def validate_model_can_have_attachments(model):
    """Validate that the model can have attachments.

    Requirements:
     - Is a Hubuum model.
     - Supports extensions.
    """
    model = _get_model(model)

    if not model.supports_attachments():
        raise ValidationError({"model": "Model does not support attachments."})

    return True


def validate_model(model_name):
    """Validate that the textual name of the model is valid.

    Requirements:
     - Is a string.
     - Resolves as the name of a Hubuum model.

     _get_model will raise a ValidationError if the model is not found.
    """
    _get_model(model_name)
    return True


def validate_url(url):
    """Validate that the URL field is valid.

    Requirements:
     - Has a supported protocol (http/https)
     - Is a well-formed URL
    """
    clean_url = re.sub(url_interpolation_regexp, "", url)

    if not validators.url(clean_url):
        raise ValidationError({"url": f"{url} is malformed."})

    return True
