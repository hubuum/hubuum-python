"""Signals for the hubuum app."""

import logging

import structlog
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

user_logger = structlog.getLogger("hubuum.auth")


def _log_user_event(
    sender, user, event, level=logging.INFO, **kwargs
):  # pylint: disable=unused-argument
    """Log user events."""
    user_label = None
    if user:
        user_label = user.id

    user_logger.bind(id=user_label).log(level, event)


@receiver(user_logged_in)
def log_user_login(sender, user, **kwargs):
    """Log user logins."""
    _log_user_event(sender, user, "login")


@receiver(user_login_failed)
def log_user_login_failed(sender, user=None, **kwargs):
    """Log user login failures."""
    _log_user_event(sender, user, "login failed", level=logging.ERROR)


@receiver(user_logged_out)
def log_user_logout(sender, user, **kwargs):
    """Log logouts."""
    _log_user_event(sender, user, "logout")
