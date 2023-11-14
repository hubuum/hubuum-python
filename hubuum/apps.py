# pyright: reportUnusedImport=false
"""A basic app config for hubuum."""

from django.apps import AppConfig
from django.conf import settings

from hubuum import config

SKIP_SETTINGS = ["SECRET_KEY", "BASE_DIR"]


class HubuumApiConfig(AppConfig):
    """The hubuum app."""

    name = "hubuum"

    def ready(self):
        """Initialize core services."""
        import hubuum.signals  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel

        for setting in dir(settings):
            if setting.isupper():
                if setting not in SKIP_SETTINGS:
                    config[setting] = getattr(settings, setting)
