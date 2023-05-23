# Hubuum Django App Environment Variables

This document provides an overview of the environment variables that can be set to influence the behavior of the Hubuum Django app.

!!! note
    Hubuum validates all environment variables prefixed with HUBUUM_. Any unexpected environment variables under that prefix will be reported and the application will exit.


## Core options

- `HUBUUM_SECRET_KEY`: Setting this sets the [secret key](https://docs.djangoproject.com/en/4.2/ref/settings/#std-setting-SECRET_KEY) for the Django framework. If you do not set this yourself, a random key will be generated on startup. Setting this environment variable will put the application into production mode.

## Database Access

Currently supported engines are "django.db.backends.postgresql" and "django.db.backends.sqlite3". If "django.db.backends.sqlite3" is chosen, the only other option used is `HUBUUM_DATABASE_NAME`.

- `HUBUUM_DATABASE_ENGINE`: Sets the database engine. Defaults to "django.db.backends.postgresql".
- `HUBUUM_DATABASE_NAME`: Sets the name of the database. Defaults to "hubuum".
- `HUBUUM_DATABASE_USER`: Sets the database user. Defaults to "hubuum".
- `HUBUUM_DATABASE_PASSWORD`: Sets the password for the database user. Defaults to `None`. Must be set if `HUBUUM_DATABASE_ENGINE` is "django.db.backends.postgresql".
- `HUBUUM_DATABASE_HOST`: Sets the database host. Defaults to "localhost".
- `HUBUUM_DATABASE_PORT`: Sets the port for the database. Defaults to 5432.

## Logging

For detailed information on logging, see the [logging documentation](logging.md). Loggers that take log values as input accept the following values: DEBUG, INFO, WARNING, ERROR, CRITICAL. 

### Core logging options

- `HUBUUM_LOGGING_LEVEL`: Sets the default logging level for all sources. Defaults to "CRITICAL".
- `HUBUUM_LOGGING_PRODUCTION`: Determines if logging is in production mode or not. In production we get no colored output and the JSON layout is compact. Defaults to `False`. Note that if `HUBUUM_SECRET_KEY` was set above, this defaults to `True`, but may be overridden explicitly. 

### Individual loggers 

These are all loggers for different purposes. TThey default to the level of `HUBUUM_LOGGING_LEVEL`. They are all prefixed with `HUBUUM_LOGGING_LEVEL_`.

| Source       | Description                                                 | Events                            | Fields                                                    |
| ------------ | ----------------------------------------------------------- | --------------------------------- | --------------------------------------------------------- |
| `AUTH`       | Authentication events                                       | login, logout, failure            | id                                                        |
| `API`        | API actions such as direct object manipulation              | created, deleted, updated         | id, model, user                                           |
| `DJANGO`     | Structlog default Django request loggers                    | request_started, request_finished | request, user_agent / request, code                       |
| `INTERNAL`   | Internal events in Hubuum                                   | Undefined                         | Any                                                       |
| `MANUAL`     | Manual log events                                           | manual                            | Any                                                       |
| `MIGRATIONS` | On startup database migrations, logged at the `DEBUG` level | created                           | id, model                                                 |
| `REQUESTS`   | Request responses                                           | response                          | content, method, run\_time\_ms, status_code, status_label |
| `SIGNALS`    | Other signals, such as object manipulation                  | created, deleted, updated         | id, model                                                 |

Why both `API` and `SIGNAL`? `API` gives us user information, as it is gathered from the View itself, but this will only log the direct effect of the requested API call. Ie, deleting a Host will be quite similar between the two loggers:

````json
2023-05-23T10:56:53.420831Z [info ] deleted [hubuum.api.object] instance=1 model=Host user=tmp
2023-05-23T10:56:53.422447Z [info ] deleted [hubuum.signals.object] id=1 model=Host
````

However, if one deletes a Namespace, which causes a cascade on the items within, it looks quite different:

````json
2023-05-23T10:56:53.356191Z [info ] deleted [hubuum.api.object] instance=1 model=Namespace user=superuser
2023-05-23T10:56:53.363781Z [info ] deleted [hubuum.signals.object] id=1 model=Permission
2023-05-23T10:56:53.364163Z [info ] deleted [hubuum.signals.object] id=1 model=Host
2023-05-23T10:56:53.364577Z [info ] deleted [hubuum.signals.object] id=1 model=Namespace
````

Here, the `API` logger only sees the direct effect, the deletion of the Namespace itself, whilst `SIGNAL` also notifies us about the cascaded objects. To get a quick overview of the logging output, one can run a test with logging set to debug:

````bash
HUBUUM_LOGGING_LEVEL=DEBUG pytest hubuum/api/v1/tests/test_20_hosts.py -vv -s
````

### Sentry support

Hubuum supports [Sentry](https://sentry.io) for log tracking. See their guide for [python](https://docs.sentry.io/platforms/python/) for details. The following environment variables can be used to configure Sentry:

- `HUBUUM_SENTRY_DSN`: Sets the Sentry DSN for log tracking. Defaults to an empty string. If this is set, Sentry will be enabled.
- `HUBUUM_SENTRY_LEVEL`: Sets the Sentry logging level. Defaults to `ERROR`.
- `HUBUUM_SENTRY_TRACES_SAMPLE_RATE`: Set the sample rate used. This number from 0 (0%) and 1 (100%) of the events passed to sentry. Defaults to `1.0` (100%).
- `HUBUUM_SENTRY_PII`: Send personal identifiable information (PII). Default is `False`.
- `HUBUUM_SENTRY_ENVIRONMENT`: Set the environment label used, defaults to `production`.

## Request handling

Hubuum supports logging slow and very slow requests. This manipulates the events logged by the `REQUEST` logger.

 - `HUBUUM_REQUEST_THRESHOLD_SLOW`: The amount of time, in milliseconds, a request can take before it is considered slow. Defaults to `1000` (1s).
 - `HUBUUM_REQUEST_THRESHOLD_VERY_SLOW`: The amount of time, in milliseconds, a request can take before it is considered very slow. Defaults to `5000` (5s).
 - `HUBUUM_REQUEST_LOG_LEVEL_SLOW`: The log level a slow request gets escalated to, defaults to `WARNING`.
 - `HUBUUM_REQUEST_LOG_LEVEL_VERY_SLOW`: The log level a very slow request gets escalated to, defaults to `ERROR`.

In addition to escalating the `log_level`, the following fields are added to the event: 
 - `original_log_level`: This is the original log level of the event.
 - One of `slow_response` or `very_slow_response` is set to `True`.

With the default setup, this can look something like this:

````json
2023-05-23T11:38:27.353445Z [warning ] response [hubuum.request] content=... method=GET original_log_level=10 path=/api/v1/resources/hosts/ run_time_ms=1438.51 slow_response=True status_code=200 status_label=OK
2023-05-23T11:38:33.020905Z [error   ] response [hubuum.request] content=... method=GET original_log_level=10 path=/api/v1/resources/hosts/ run_time_ms=5664.79 status_code=200 status_label=OK very_slow_response=True
````