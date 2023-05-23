"""Configuration for the scope HUBUUM_REQUESTS."""

from typing import Dict, Union

from .abstract import (
    HubuumAbstractConfig,
    valid_logging_levels,
    validator_valid_logging_level,
)


class HubuumRequestConfig(HubuumAbstractConfig):
    """A configuration class for requests."""

    VALID_KEYS: Dict[str, Union[str, int]] = {
        "THRESHOLD_SLOW": 1000,
        "THRESHOLD_VERY_SLOW": 5000,
        "LOG_LEVEL_SLOW": "WARNING",
        "LOG_LEVEL_VERY_SLOW": "ERROR",
    }

    def validate(self) -> None:
        """Validate the request escalation settings."""
        for key in ["THRESHOLD_SLOW", "THRESHOLD_VERY_SLOW"]:
            value = self.get(key)
            try:
                value = int(value)
            except ValueError as exc:
                raise ValueError(
                    (f"Invalid value for {key}: {value}. Supported values: int")
                ) from exc

        slow_threshold = self.get("THRESHOLD_SLOW")
        very_slow_threshold = self.get("THRESHOLD_VERY_SLOW")

        if slow_threshold > very_slow_threshold:
            slow = self.fq_key("THRESHOLD_SLOW")
            very_slow = self.fq_key("THRESHOLD_VERY_SLOW")
            raise ValueError(f"{slow} must be smaller than {very_slow}.")

        for key in ["REQUESTS_LOG_LEVEL_SLOW", "REQUESTS_LOG_LEVEL_VERY_SLOW"]:
            if not validator_valid_logging_level(self.get(key)):
                level_string = ",".join(valid_logging_levels())
                raise ValueError(
                    (
                        f"Invalid logging level for slow requests: {self.get(key)}. "
                        f"Supported levels: {level_string}"
                    )
                )
