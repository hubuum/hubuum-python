"""Test the configuration management system."""

import os
import sys
from unittest.mock import patch

import pytest
import structlog
from django.test import TestCase

from hubuumsite.config.abstract import HubuumAbstractConfig, valid_logging_levels
from hubuumsite.config.base import HubuumBaseConfig
from hubuumsite.config.database import HubuumDatabaseConfig
from hubuumsite.config.logging import HubuumLoggingConfig
from hubuumsite.config.request import HubuumRequestConfig
from hubuumsite.config.sentry import HubuumSentryConfig


class HubuumBaseConfigTestCase(TestCase):
    """Test the basic parts of the configuration management system."""

    def _create_config(self, **kwargs: str) -> HubuumBaseConfig:
        """Create a configuration object with a password."""
        kwargs["HUBUUM_DATABASE_PASSWORD"] = "!"
        return HubuumBaseConfig(kwargs)

    def test_valid_logging_levels(self) -> None:
        """Test the valid logging levels."""
        self.assertListEqual(
            valid_logging_levels(), ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
        )

    def test_empty_configuration(self) -> None:
        """Test without any configuration. Defaults to postgres."""
        config = HubuumBaseConfig({})
        self.assertIsNotNone(config)
        self.assertIsInstance(config, HubuumBaseConfig)
        self.assertIsInstance(config.logging, HubuumLoggingConfig)
        self.assertIsInstance(config.database, HubuumDatabaseConfig)
        self.assertIsInstance(config.sentry, HubuumSentryConfig)
        self.assertIsInstance(config.requests, HubuumRequestConfig)
        self.assertEqual(config.database.get("ENGINE"), "django.db.backends.postgresql")

    def test_production_vs_developement(self) -> None:
        """Test the mode of operation."""
        key = "-1cljr3%p2_(s66!@&ld5du2rb*&4$@$q1myr=s=a63efl##0&"

        # Test production mode.
        config = self._create_config(HUBUUM_SECRET_KEY=key)
        self.assertEqual(config.get("SECRET_KEY"), key)
        self.assertFalse(config.is_development())
        self.assertTrue(config.is_production())

        # Test development mode. We get a generated key.
        config = self._create_config()
        self.assertEqual(len(config.get("SECRET_KEY")), 50)
        self.assertTrue(config.is_development())
        self.assertFalse(config.is_production())

    def test_almost_empty_sqlite_configuration(self) -> None:
        """Test only setting the database engine to sqlite."""
        config = self._create_config(
            HUBUUM_DATABASE_ENGINE="django.db.backends.sqlite3"
        )
        self.assertIsNotNone(config)
        self.assertEqual(config.database.get("ENGINE"), "django.db.backends.sqlite3")
        self.assertEqual(config.database.get("NAME"), "hubuum")

        self.assertEqual(len(config.get("SECRET_KEY")), 50)

    def test_wrong_values(self) -> None:
        """Test trying to set some keys to wrong values.."""
        with pytest.raises(ValueError):
            self._create_config(HUBUUM_DATABASE_ENGINE="not_a_database")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_SECRET_KEY="not_long_enough")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_TESTING_PARALLEL="not_a_number")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_SENTRY_LEVEL="sentrydebug")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_LOGGING_LEVEL="defaultdebug")

        for source in HubuumLoggingConfig.SOURCES:
            with pytest.raises(ValueError):
                self._create_config(**{f"HUBUUM_LOGGING_LEVEL_{source}": "invalid"})

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_LOGGING_LEVEL_API="apidebug")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_LOGGING_PRODUCTION="notabool")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_REQUESTS_THRESHOLD_SLOW="notanumber")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_REQUESTS_THRESHOLD_VERY_SLOW="notanumber")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_REQUESTS_LOG_LEVEL_SLOW="notaloglevel")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_REQUESTS_LOG_LEVEL_VERY_SLOW="notaloglevel")

    def test_initializing_sentry(self) -> None:
        """Test that we can initialize sentry when DSN is set."""
        # No DSN set, no call.
        with patch("sentry_sdk.init") as mock_init:
            config = self._create_config()
            config.sentry.init()
            mock_init.assert_not_called()

        # DSN set, call.
        dsn = "https://sentry.io"
        with patch("sentry_sdk.init") as mock_init:
            config = self._create_config(HUBUUM_SENTRY_DSN=dsn)
            config.sentry.init()
            mock_init.assert_called_once_with(
                dsn=dsn,
                send_default_pii=config.sentry.get("PII"),
                traces_sample_rate=config.sentry.get("TRACES_SAMPLE_RATE"),
                environment=config.sentry.get("ENVIRONMENT"),
            )

    def test_logging_output_types(self) -> None:
        """Test the logging output types for structlog."""
        # Default is JSON
        config = self._create_config()
        logging_type = config.logging.get_logging_output()[-1]
        self.assertIsInstance(logging_type, structlog.dev.ConsoleRenderer)

        # Explicitly set to JSON
        config = self._create_config(HUBUUM_LOGGING_PRODUCTION=False)
        logging_type = config.logging.get_logging_output()[-1]
        self.assertIsInstance(logging_type, structlog.dev.ConsoleRenderer)

        # Explicitly set to produciton
        config = self._create_config(HUBUUM_LOGGING_PRODUCTION=True)
        logging_type = config.logging.get_logging_output()[-1]
        self.assertIsInstance(logging_type, structlog.processors.JSONRenderer)

    def test_testing_parallel(self) -> None:
        """Test that we can set the testing parallelization."""
        config = self._create_config(HUBUUM_TESTING_PARALLEL=2)
        self.assertEqual(config.get("TESTING_PARALLEL"), 2)
        config = self._create_config(HUBUUM_TESTING_PARALLEL="auto")
        self.assertEqual(config.get("TESTING_PARALLEL"), "auto")

        with pytest.raises(ValueError):
            self._create_config(HUBUUM_TESTING_PARALLEL="nope")

    def test_request_thresholds(self) -> None:
        """Test that thresholds make sense."""
        config = self._create_config(
            HUBUUM_REQUESTS_THRESHOLD_SLOW=1,
            HUBUUM_REQUESTS_THRESHOLD_VERY_SLOW=2,
        )
        self.assertEqual(config.requests.get("THRESHOLD_SLOW"), 1)
        self.assertEqual(config.requests.get("THRESHOLD_VERY_SLOW"), 2)

        # Check that the slow threshold is smaller than the very slow threshold.
        with pytest.raises(ValueError):
            self._create_config(
                HUBUUM_REQUESTS_THRESHOLD_SLOW=5,
                HUBUUM_REQUESTS_THRESHOLD_VERY_SLOW=1,
            )

    def test_show_methods(self) -> None:
        """Test that we can call the show methods."""
        config = self._create_config()
        with open(os.devnull, "w", encoding="utf-8") as null_stdout:
            sys.stdout = null_stdout
            config.show()
            config.show_config()
            config.show_valid_keys()
            sys.stdout = sys.__stdout__

    def test_invalid_key(self) -> None:
        """Test trying to get an invalid key."""
        config = self._create_config()
        with pytest.raises(KeyError):
            config.get("not_a_key")

    def test_list_valid_keys(self) -> None:
        """Test listing the valid keys."""
        config = self._create_config()
        self.assertListEqual(
            config.list_valid_keys(),
            [
                "HUBUUM_SECRET_KEY",
                "HUBUUM_TESTING_PARALLEL",
                "HUBUUM_DEVELOPMENT_MODE",
            ],
        )
        self.assertListEqual(
            config.database.list_valid_keys(),
            [
                "HUBUUM_DATABASE_HOST",
                "HUBUUM_DATABASE_PORT",
                "HUBUUM_DATABASE_NAME",
                "HUBUUM_DATABASE_USER",
                "HUBUUM_DATABASE_PASSWORD",
                "HUBUUM_DATABASE_ENGINE",
            ],
        )
        self.assertListEqual(
            config.requests.list_valid_keys(),
            [
                "HUBUUM_REQUESTS_THRESHOLD_SLOW",
                "HUBUUM_REQUESTS_THRESHOLD_VERY_SLOW",
                "HUBUUM_REQUESTS_LOG_LEVEL_SLOW",
                "HUBUUM_REQUESTS_LOG_LEVEL_VERY_SLOW",
            ],
        )

        self.assertListEqual(
            config.logging.list_valid_keys(),
            [
                "HUBUUM_LOGGING_LEVEL",
                "HUBUUM_LOGGING_PRODUCTION",
                "HUBUUM_LOGGING_BODY_LENGTH",
                "HUBUUM_LOGGING_COLLAPSE_REQUEST_ID",
                "HUBUUM_LOGGING_LEVEL_API",
                "HUBUUM_LOGGING_LEVEL_AUTH",
                "HUBUUM_LOGGING_LEVEL_OBJECT",
                "HUBUUM_LOGGING_LEVEL_HTTP",
                "HUBUUM_LOGGING_LEVEL_SIGNAL",
                "HUBUUM_LOGGING_LEVEL_INTERNAL",
                "HUBUUM_LOGGING_LEVEL_MANUAL",
                "HUBUUM_LOGGING_LEVEL_DJANGO",
                "HUBUUM_LOGGING_LEVEL_MIGRATION",
            ],
        )

        self.assertListEqual(
            config.sentry.list_valid_keys(),
            [
                "HUBUUM_SENTRY_DSN",
                "HUBUUM_SENTRY_LEVEL",
                "HUBUUM_SENTRY_TRACES_SAMPLE_RATE",
                "HUBUUM_SENTRY_PII",
                "HUBUUM_SENTRY_ENVIRONMENT",
            ],
        )

    def test_get_prefixed_pairs_creating_booleans(self):
        # Define the environment
        env = {
            "HUBUUM_PREFIX_KEY1": "false",
            "HUBUUM_PREFIX_KEY2": "true",
            "HUBUUM_PREFIX_KEY3": "value",
        }

        self.obj = HubuumAbstractConfig("PREFIX", env)

        # Set VALID_KEYS in your object
        self.obj.VALID_KEYS = {"KEY1": None, "KEY2": None, "KEY3": None}

        # Run your function
        result = self.obj.get_prefixed_pairs("PREFIX", env)

        # Assert that the values are as expected
        self.assertEqual(result["HUBUUM_PREFIX_KEY1"], False)
        self.assertEqual(result["HUBUUM_PREFIX_KEY2"], True)
        self.assertEqual(result["HUBUUM_PREFIX_KEY3"], "value")
