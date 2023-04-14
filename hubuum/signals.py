"""Signals for the hubuum app."""

import structlog
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

user_logger = structlog.getLogger("hubuum.auth")


@receiver(user_logged_in)
def log_user_login(sender, user, **kwargs):  # pylint: disable=unused-argument
    """Log user logins."""
    user_logger.info(event="login", user=user.id)


@receiver(user_login_failed)
def log_user_login_failed(
    sender, user=None, **kwargs
):  # pylint: disable=unused-argument
    """Log user login failures."""
    if user:  # pragma: no cover, not sure if this can ever happen.
        user_logger.info(event="login failed", user=user.id)
    else:
        user_logger.error(event="login failed", user="", user_unknown=True)


@receiver(user_logged_out)
def log_user_logout(sender, user, **kwargs):  # pylint: disable=unused-argument
    """Log logouts."""
    user_logger.info(event="logout", user=user.id)
