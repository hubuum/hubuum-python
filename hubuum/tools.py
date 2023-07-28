"""Tools for huubum.

This package is NOT allowed to import anything from internally in hubuum.
"""
from typing import List, Union, cast

from dateutil.parser import isoparse
from django.apps import apps
from django.db.models import Model
from rest_framework.exceptions import NotFound


def is_iso_date(value: str) -> bool:
    """Assert that a value is a valid date."""
    try:
        isoparse(value)
        return True
    except ValueError:
        return False


def get_model(model: Union[str, Model]) -> Union[Model, None]:
    """Return the model from a string. Returns None if it fails.."""
    try:
        return apps.get_model("hubuum", model)
    except LookupError:
        return None


def get_object(
    cls: Model,
    lookup_value: str,
    lookup_fields: List[str] = None,
    raise_exception: bool = True,
) -> Union[object, None]:
    """Get an object from a class.

    A generic way to find objects in a model.
    By default the list of fields searched are in order of precedence:
      - the list passed to the lookup_fields keyword argument
      - the models class attribute 'lookup_fields'
      - the list ["id"]

    param: cls (the model to look into)
    param: lookup_value (value to search for)
    param: lookup_fields=[] (explicitly declare fields to look into)

    return object or None
    """
    obj = None
    fields = ["id"]
    if lookup_fields:
        fields = lookup_fields
    elif hasattr(cls, "lookup_fields"):
        fields = cast(List[str], cls.lookup_fields)

    for field in fields:
        try:
            obj = cast(Model, cls.objects.get(**{field: lookup_value}))
            if obj:
                return obj

        except Exception:  # nosec pylint: disable=broad-except
            pass

    if raise_exception:
        raise NotFound()

    return None
