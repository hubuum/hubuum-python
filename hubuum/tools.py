"""Tools for huubum.

This package is NOT allowed to import anything from internally in hubuum.
"""


from django.apps import apps
from rest_framework.exceptions import NotFound


def get_model(model):
    """Return the model from a string. Returns None if it fails.."""
    try:
        return apps.get_model("hubuum", model)
    except LookupError:
        return None


def get_object(cls, lookup_value, lookup_fields=None, raise_exception=True):
    """Get a object from a class.

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
        fields = cls.lookup_fields

    for field in fields:
        try:
            obj = cls.objects.get(**{field: lookup_value})
            if obj:
                return obj

        except Exception:  # nosec pylint: disable=broad-except
            pass

    if raise_exception:
        raise NotFound()

    return None
