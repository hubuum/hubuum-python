"""The HubuumConfig abstract class."""

import logging
from typing import Any, Dict, List, Union

LOGMAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def validator_valid_logging_level(level: str) -> bool:
    """Validate the logging level."""
    return level in LOGMAP


def valid_logging_levels() -> List[str]:
    """Return a string of valid logging levels."""
    return list(LOGMAP.keys())


class HubuumAbstractConfig:
    """Abstract base class for Hubuum configuration."""

    ROOT_PREFIX: str = "HUBUUM"
    VALID_KEYS: Dict[str, Union[None, int, float, str, bool]] = {}

    def __init__(self, prefix: str, env: Dict[str, Any]) -> None:
        """Initialize the configuration class."""
        self._prefix = prefix
        self._config = self.get_prefixed_pairs(prefix, env)
        self.validate()

    def validate(self) -> None:
        """Validate the configuration."""

    def fq_key(self, key: str) -> str:
        """Fully qualify a key."""
        fq_key = ""
        if not key.startswith(HubuumAbstractConfig.ROOT_PREFIX):
            fq_key = f"{HubuumAbstractConfig.ROOT_PREFIX}_"

        if (
            self._prefix not in key
            and not self._prefix == HubuumAbstractConfig.ROOT_PREFIX
        ):
            fq_key = f"{fq_key}{self._prefix.upper()}_"

        return f"{fq_key}{key.upper()}"

    def get_prefixed_pairs(self, prefix: str, env: Dict[str, str]) -> Dict[str, str]:
        """Get all prefixed pairs matching a prefix."""
        prefixed_pairs: Dict[str, str] = {}
        for key, default in self.VALID_KEYS.items():
            fq_key = self.fq_key(f"{prefix}_{key}")
            value = env.get(fq_key, default)

            if "LEVEL" in key and isinstance(value, str):
                value = value.upper()

            if isinstance(value, str):
                if value.lower() == "false":
                    prefixed_pairs[fq_key] = False
                elif value.lower() == "true":
                    prefixed_pairs[fq_key] = True
                else:
                    prefixed_pairs[fq_key] = value
            else:
                prefixed_pairs[fq_key] = value

        return prefixed_pairs

    def get(self, key: str) -> Union[None, int, str]:
        """Get a key, qualifying it if needed."""
        fq_key = self.fq_key(key)

        if fq_key not in self._config:
            cls = self.__class__.__name__
            raise KeyError(f"Invalid key for {cls}: {fq_key}")

        value = self._config.get(fq_key)
        return value

    def get_log_level(self, key: str) -> int:
        """Get a log level."""
        return LOGMAP[self.get(key)]

    def list_valid_keys(self) -> List[str]:
        """Return a list of valid keys."""
        return [self.fq_key(key) for key in self.VALID_KEYS]

    def show(self) -> None:
        """Print the configuration."""
        for key, value in self._config.items():
            print(f"{key}={value}")

    def show_valid_keys(self) -> None:
        """Print the valid keys."""
        print(self.list_valid_keys())
