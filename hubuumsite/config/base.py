"""Configuration parser for Hubuum."""

import random
from typing import Any, Dict, Union

from .abstract import HubuumAbstractConfig
from .database import HubuumDatabaseConfig
from .logging import HubuumLoggingConfig
from .request import HubuumRequestConfig
from .sentry import HubuumSentryConfig


# A configuration class for the environment that is used in this project.
class HubuumBaseConfig(HubuumAbstractConfig):
    """A configuration class for Hubuum.

    Args: Dict[str, Any]: The environment variables.
    """

    # List of accepted environment variables and their defaults.
    # These are keys without the prefix listed above.
    VALID_KEYS: Dict[str, Union[None, int, str, bool]] = {
        "SECRET_KEY": None,
        # Used by tox during testing
        "TESTING_PARALLEL": 2,
        "DEVELOPMENT_MODE": True,
    }

    def __init__(self, env: Dict[str, Any]):  # pylint: disable=super-init-not-called
        """Initialize the configuration class."""
        self._prefix = HubuumAbstractConfig.ROOT_PREFIX
        self._config = self.get_prefixed_pairs(self._prefix, env)

        # If we have a secret key, we are in production.
        if self.fq_key("SECRET_KEY") in env:
            env[self.fq_key("LOGGING_PRODUCTION")] = True
            self._config[self.fq_key("PRODUCTION")] = True
            self._config[self.fq_key("DEVELOPMENT_MODE")] = False
        else:
            self._config[self.fq_key("DEVELOPMENT_MODE")] = True
            self._config[self.fq_key("SECRET_KEY")] = self.create_secret_key()

        self.database = HubuumDatabaseConfig("DATABASE", env)
        self.requests = HubuumRequestConfig("REQUESTS", env)
        self.logging = HubuumLoggingConfig("LOGGING", env)
        self.sentry = HubuumSentryConfig("SENTRY", env)

        self.validate()

    def create_secret_key(self) -> str:
        """Create a random secret key."""
        chars = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVXYZ"
            "0123456789"
            "#()^[]-_*%&=+/"
        )
        return "".join([random.SystemRandom().choice(chars) for _ in range(50)])

    def validate(self) -> None:
        """Validate the configuration."""
        try:
            int(self.get("TESTING_PARALLEL"))
        except ValueError as exc:
            if self.get("TESTING_PARALLEL") != "auto":
                raise ValueError(
                    (
                        f"Invalid value for TESTING_PARALLEL: {self.get('TESTING_PARALLEL')}. "
                        "Supported values: int or 'auto'"
                    )
                ) from exc

        if not len(self.get("SECRET_KEY")) == 50:
            raise ValueError(
                (
                    f"Invalid value for SECRET_KEY: {self.get('SECRET_KEY')}."
                    "Supported values: 50 character string"
                )
            )

    def get_secret_key(self) -> str:
        """Get the secret key."""
        return self.get("SECRET_KEY")

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.get("DEVELOPMENT_MODE") is True

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.is_development() is False

    def show_config(self) -> None:
        """Print the configuration."""
        self.show()
        self.database.show()
        self.logging.show()
        self.sentry.show()
        self.requests.show()
