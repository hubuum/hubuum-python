"""Configuration for the scope HUBUUM_LOGGING."""

from typing import Dict, List, Union

import structlog
from structlog.types import Processor

import hubuum.log

from .abstract import (
    HubuumAbstractConfig,
    valid_logging_levels,
    validator_valid_logging_level,
)

DEFAULT_LOG_LEVEL = "ERROR"


class HubuumLoggingConfig(HubuumAbstractConfig):
    """A configuration class for logging."""

    VALID_KEYS: Dict[str, Union[str, bool]] = {  # type: ignore
        "LEVEL": DEFAULT_LOG_LEVEL,
        "PRODUCTION": False,
        "BODY_LENGTH": 3000,
        "COLLAPSE_REQUEST_ID": True,
    }

    SOURCES = [
        "API",
        "AUTH",
        "OBJECT",
        "HTTP",
        "SIGNAL",
        "INTERNAL",
        "MANUAL",
        "DJANGO",
        "MIGRATION",
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
                # DJANGO and MIGRATION are special cases, and require their log
                # levels to be set explicitly.
                if source == "DJANGO" or source == "MIGRATION":
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

    def get_logging_output(
        self,
    ) -> List[Union[Processor, structlog.dev.ConsoleRenderer, structlog.processors.JSONRenderer]]:
        """Get the logging output type and any additional processors."""
        if self.get("LOGGING_PRODUCTION"):
            return [structlog.processors.JSONRenderer()]
        else:
            # Add development processors if not in production
            # reorder_keys_processor comes first and ensures that request_id is first in the log
            # collapse_request_id shortens the request_id to make the logs more readable
            # RequestColorizer adds a colored bubble to the event message based on the request_id
            processors: List[
                Union[
                    Processor,
                    structlog.dev.ConsoleRenderer,
                    structlog.processors.JSONRenderer,
                ]
            ] = [
                hubuum.log.reorder_keys_processor,
                hubuum.log.RequestColorTracker(),
                structlog.dev.ConsoleRenderer(colors=True, sort_keys=False),
            ]

            if self.get("COLLAPSE_REQUEST_ID"):
                processors.insert(1, hubuum.log.collapse_request_id)

        return processors
