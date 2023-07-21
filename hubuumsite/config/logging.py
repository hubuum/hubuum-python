"""Configuration for the scope HUBUUM_LOGGING."""

from typing import Dict, Union

import structlog

from .abstract import (
    HubuumAbstractConfig,
    valid_logging_levels,
    validator_valid_logging_level,
)

DEFAULT_LOG_LEVEL = "ERROR"


class HubuumLoggingConfig(HubuumAbstractConfig):
    """A configuration class for logging."""

    VALID_KEYS: Dict[str, Union[str, bool]] = {
        "LEVEL": DEFAULT_LOG_LEVEL,
        "PRODUCTION": False,
    }

    SOURCES = [
        "API",
        "AUTH",
        "DJANGO",
        "INTERNAL",
        "MANUAL",
        "MIGRATION",
        "REQUEST",
        "RESPONSE",
        "SIGNALS",
    ]

    # Add the logging levels for the different sources.
    for source in SOURCES:
        VALID_KEYS[f"LEVEL_{source}"] = DEFAULT_LOG_LEVEL

    def __init__(self, prefix: str, env: Dict[str, str]) -> None:
        """Initialize the logging configuration."""
        # Set defaults for the logging sources, based on either the provided overall
        # log level or the default log level.
        self._prefix = prefix
        fq_key = self.fq_key("LEVEL")
        if fq_key in env:
            for source in self.SOURCES:
                # Do not set the default for the Django source, require it to be
                # explicitly set.
                if source == "DJANGO":
                    continue
                self.VALID_KEYS[f"LEVEL_{source}"] = env[fq_key]

        super().__init__(prefix, env)

    def validate(self) -> None:
        """Validate the logging configuration."""
        if not validator_valid_logging_level(self.get("LEVEL")):
            level_string = ",".join(valid_logging_levels())
            raise ValueError(
                (
                    f"Invalid logging level: {self.get('LEVEL')}. "
                    f"Supported levels: {level_string}"
                )
            )

        if not isinstance(self.get("PRODUCTION"), bool):
            raise ValueError(
                (
                    f"Invalid value for PRODUCTION: {self.get('PRODUCTION')}. "
                    "Supported values: True, False"
                )
            )

        for source in self.SOURCES:
            value = self.get(f"LEVEL_{source}")
            if value and isinstance(value, str):
                value = value.upper()

            if not validator_valid_logging_level(value):
                level_string = ",".join(valid_logging_levels())
                fq_source = self.fq_key(f"LEVEL_{source}")
                raise ValueError(
                    (
                        f"Invalid logging level for {fq_source}: {value}. "
                        f"Supported levels: {level_string}"
                    )
                )

    def level_for_source(self, source: str) -> str:
        """Get the logging level for a source."""
        return self.get_log_level(f"LEVEL_{source.upper()}")

    def get_logging_output_type(
        self,
    ) -> Union[structlog.processors.JSONRenderer, structlog.dev.ConsoleRenderer]:
        """Get the logging output type."""
        if self.get("LOGGING_PRODUCTION"):
            return structlog.processors.JSONRenderer()
        return structlog.dev.ConsoleRenderer(colors=True)
