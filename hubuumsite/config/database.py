"""Configuration for the scope HUBUUM_DATABASE."""

from typing import Dict, Union

from .abstract import HubuumAbstractConfig


class HubuumDatabaseConfig(HubuumAbstractConfig):
    """A configuration class for the database."""

    SUPPORTED_ENGINES = ["django.db.backends.sqlite3", "django.db.backends.postgresql"]
    DEFAULT_ENGINE = "django.db.backends.postgresql"

    VALID_KEYS: Dict[str, Union[None, int, str]] = {
        "HOST": "localhost",
        "PORT": 5432,
        "NAME": "hubuum",
        "USER": "hubuum",
        "PASSWORD": None,
        "ENGINE": DEFAULT_ENGINE,
    }

    def validate(self) -> None:
        """Validate the database configuration."""
        engine = self.get("ENGINE")
        if engine not in HubuumDatabaseConfig.SUPPORTED_ENGINES:
            raise ValueError(
                (
                    f"Unsupported database engine: {self.get('ENGINE')}."
                    f"Supported engines: {HubuumDatabaseConfig.SUPPORTED_ENGINES}"
                )
            )
