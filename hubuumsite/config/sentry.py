"""Configuration for the scope HUBUUM_SENTRY."""

from typing import Dict, Union

import sentry_sdk

from .abstract import (
    HubuumAbstractConfig,
    valid_logging_levels,
    validator_valid_logging_level,
)

DEFAULT_SENTRY_LEVEL = "ERROR"


class HubuumSentryConfig(HubuumAbstractConfig):
    """A configuration class for Sentry."""

    VALID_KEYS: Dict[str, Union[None, str, int, float]] = {
        "DSN": None,
        "LEVEL": DEFAULT_SENTRY_LEVEL,
        "TRACES_SAMPLE_RATE": 1.0,
        "PII": False,
        "ENVIRONMENT": "production",
    }

    def validate(self) -> None:
        """Validate the Sentry configuration."""
        if not validator_valid_logging_level(self.get("LEVEL")):
            level_string = ",".join(valid_logging_levels())
            raise ValueError(
                (
                    f"Invalid Sentry logging level: {self.get('LEVEL')}."
                    f"Supported levels: {level_string}"
                )
            )

    def init(self) -> None:
        """Initialize Sentry."""
        if self.get("DSN"):
            sentry_sdk.init(
                dsn=self.get("DSN"),
                send_default_pii=self.get("PII"),
                traces_sample_rate=self.get("TRACES_SAMPLE_RATE"),
                environment=self.get("ENVIRONMENT"),
            )
