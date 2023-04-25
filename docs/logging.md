# Logging

## Standard Logging

By default, Hubuum logs to the console. This is the recommended way to run Hubuum in production, as per the [12-factor app](https://12factor.net/logs) methodology.

To control the logging level, set the `HUBUUM_LOGGING_LEVEL` environment variable to one of the following values:

- `critical`
- `error`
- `warning`
- `info`
- `debug`

One may also set the logging level for specific sources. The following environment variables are available:

- `HUBUUM_LOGGING_LEVEL_DJANGO`: Sets the logging level for Django. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_API`: Sets the logging level for the API. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_SIGNALS`: Sets the logging level for signals. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_REQUEST`: Sets the logging level for requests. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_MANUAL`: Sets the logging level for manual logs. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_AUTH`: Sets the logging level for authentication. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.

## Sentry

Hubuum can be configured to send logs to [Sentry](https://sentry.io/). To do this, set the `SENTRY_DSN` environment variable to the DSN for your Sentry project.


## Development

During development, hubuum produces colored output. To disable this, set the `HUBUUM_LOGGING_PRODUCTION` environment variable to `True`.

