# pyright: reportUnusedImport=false
"""A basic app config for hubuum."""

from django.apps import AppConfig


class HubuumApiConfig(AppConfig):
    """The hubuum app."""

    name = "hubuum"

    def ready(self):
        """Initialize core services."""
        import hubuum.signals  # noqa: F401 pylint: disable=unused-import,import-outside-toplevel
