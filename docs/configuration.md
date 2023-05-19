# Hubuum Django App Environment Variables

This document provides an overview of the environment variables that can be set to influence the behavior of the Hubuum Django app.

## Logging

For detailed information on logging, see the [logging documentation](logging.md).

- `HUBUUM_LOGGING_LEVEL`: Sets the default logging level for all sources. Defaults to "critical".
- `HUBUUM_LOGGING_LEVEL_DJANGO`: Sets the logging level for the default Django loggers. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_API`: Sets the logging level for API actions such as direct object manipulation through the API. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_SIGNALS`: Sets the logging level for signals. This will include object manipulation of all sorts. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_REQUEST`: Sets the logging level for HTTP requests. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_MANUAL`: Sets the logging level for manual logs. These are explicit logging requests inn the code. Not recommended for production. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_AUTH`: Sets the logging level for authentication events (login/logout/failures). Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_PRODUCTION`: Determines if logging is in production mode or not. In production we get no colored output. Defaults to `False`.

### Sentry support

Hubuum supports [Sentry](https://sentry.io) for log tracking. The following environment variables can be used to configure Sentry:

- `HUBUUM_SENTRY_DSN`: Sets the Sentry DSN for log tracking. Defaults to an empty string. If this is set, Sentry will be enabled.
- `HUBUUM_SENTRY_LEVEL`: Sets the Sentry logging level. Defaults to "critical".

## Database Access

- `HUBUUM_DATABASE_ENGINE`: Sets the database engine. Defaults to "django.db.backends.postgresql".
- `HUBUUM_DATABASE_NAME`: Sets the name of the database. Defaults to "hubuum".
- `HUBUUM_DATABASE_USER`: Sets the database user. Defaults to "hubuum".
- `HUBUUM_DATABASE_PASSWORD`: Sets the password for the database user. Defaults to `None`.
- `HUBUUM_DATABASE_HOST`: Sets the database host. Defaults to "localhost".
- `HUBUUM_DATABASE_PORT`: Sets the port for the database. Defaults to 5432.
