"""Signals for the hubuum app."""

import logging
import os

import structlog
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from hubuum.models.core import Attachment

user_logger = structlog.getLogger("hubuum.auth")
object_logger = structlog.getLogger("hubuum.signals.object")
migration_logger = structlog.getLogger("hubuum.migration")


def _log_user_event(
    sender, user, event, level=logging.INFO, **kwargs
):  # pylint: disable=unused-argument
    """Log user events."""
    user_label = None
    if user:
        user_label = user.id

    user_logger.bind(id=user_label).log(level, event)


def _identifier(instance):
    """Return an identifier for an instance."""
    if hasattr(instance, "id"):
        return instance.id
    return str(instance)


@receiver(post_save)
def log_object_creation(sender, instance, created, **kwargs):
    """Log object creation."""
    identifier = _identifier(instance)
    model_name = sender.__name__
    if created:
        if model_name == "Migration":
            migration_logger.bind(model=model_name, id=identifier).debug("created")
        else:
            object_logger.bind(model=sender.__name__, id=identifier).info("created")
    else:
        object_logger.bind(model=sender.__name__, id=identifier).info("updated")


@receiver(post_delete)
def log_object_deletion(sender, instance, **kwargs):
    """Log object deletion."""
    object_logger.bind(model=sender.__name__, id=_identifier(instance)).info("deleted")


@receiver(user_logged_in)
def log_user_login(sender, user, **kwargs):
    """Log user logins."""
    _log_user_event(sender, user, "login")


@receiver(user_login_failed)
def log_user_login_failed(sender, user=None, **kwargs):
    """Log user login failures."""
    _log_user_event(sender, user, "failure", level=logging.ERROR)


@receiver(user_logged_out)
def log_user_logout(sender, user, **kwargs):
    """Log logouts."""
    _log_user_event(sender, user, "logout")


# Remove files from the filesystem when a Attachment object is deleted.
@receiver(post_delete, sender=Attachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
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
        if os.path.isfile(instance.attachment.path):
            os.remove(instance.attachment.path)
