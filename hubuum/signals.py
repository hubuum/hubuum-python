"""Signals for the hubuum app."""

import logging
import os
from typing import Any, Dict, cast

import structlog
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models import Model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from hubuum.models.auth import User
from hubuum.models.core import Attachment

user_logger = structlog.getLogger("hubuum.auth")
object_logger = structlog.getLogger("hubuum.signals.object")
migration_logger = structlog.getLogger("hubuum.migration")


def _log_user_event(
    _: Model,
    user: User,
    event: Dict[str, Any],
    level: int = logging.INFO,
    **kwargs: Dict[str, Any]
) -> None:
    """Log user events."""
    user_label = None
    if user:
        user_label = cast(int, user.id)

    user_logger.bind(id=user_label).log(level, event)


def _identifier(instance: object) -> str:
    """Return an identifier for an instance."""
    if hasattr(instance, "id"):
        return cast(int, instance.id)
    return str(instance)


@receiver(post_save)
def log_object_creation(
    sender: Model, instance: object, created: bool, **kwargs: Dict[str, Any]
) -> None:
    """Log object creation."""
    identifier = _identifier(instance)
    model_name = cast(str, sender.__name__)
    if created:
        if model_name == "Migration":
            migration_logger.bind(model=model_name, id=identifier).debug("created")
        else:
            object_logger.bind(model=sender.__name__, id=identifier).info("created")
    else:
        object_logger.bind(model=sender.__name__, id=identifier).info("updated")


@receiver(post_delete)
def log_object_deletion(
    sender: Model, instance: object, **kwargs: Dict[str, Any]
) -> None:
    """Log object deletion."""
    object_logger.bind(model=sender.__name__, id=_identifier(instance)).info("deleted")


@receiver(user_logged_in)
def log_user_login(sender: Model, user: User, **kwargs: Dict[str, Any]) -> None:
    """Log user logins."""
    _log_user_event(sender, user, "login")


@receiver(user_login_failed)
def log_user_login_failed(
    sender: Model, user: User = None, **kwargs: Dict[str, Any]
) -> None:
    """Log user login failures."""
    _log_user_event(sender, user, "failure", level=logging.ERROR)


@receiver(user_logged_out)
def log_user_logout(sender: Model, user: User = None, **kwargs: Dict[str, Any]) -> None:
    """Log logouts."""
    _log_user_event(sender, user, "logout")


# Remove files from the filesystem when a Attachment object is deleted.
@receiver(post_delete, sender=Attachment)
def auto_delete_file_on_delete(
    sender: Attachment, instance: object, **kwargs: Dict[str, Any]
) -> None:
    """Clean up filesystems.

    Deletes the actual attachment when the `Attachment` object is deleted.
    """
    object_logger.bind(
        model=sender.__name__,
        id=_identifier(instance),
        sha256=instance.sha256,
        path=instance.attachment.path,
    ).debug("deleted")
    if instance.attachment:
        path = cast(str, instance.attachment.path)
        if os.path.isfile(path):
            os.remove(path)
