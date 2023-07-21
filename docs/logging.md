# Logging

## Standard Logging

Hubuum logs to the console as per the [12-factor app](https://12factor.net/logs) methodology.

To control the logging level, set the `HUBUUM_LOGGING_LEVEL` environment variable to one of the following values:

- `critical`
- `error`
- `warning`
- `info`
- `debug`

One may also set the logging level for specific sources. The following environment variables are available:

- `HUBUUM_LOGGING_LEVEL_API`: Sets the logging level for the API. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_AUTH`: Sets the logging level for authentication. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_SIGNALS`: Sets the logging level for signals, typically used for object manipulation. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_RESPONSE`: Sets the logging level for responses. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_REQUEST`: Sets the logging level for requests. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_MANUAL`: Sets the logging level for manual logs. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_MIGRATION`: Sets the logging level for migration logs. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_DJANGO`: Sets the logging level for Django. Defaults to `ERROR`. This logger is not recommended for use.

## Request identifiers

Hubuum applies a request_id to contextually related log entries. This request_id follows events from a request to a response, leading to logs such as these:

```json
2023-07-20T23:13:17.676391Z [debug ] request  [hubuum.request] method=PATCH path=/api/v1/resources/hosts/yes proxy_ip= remote_ip=127.0.0.1 request_id=402cfc7c-f8de-42d6-8f4e-6bbb7dd0b39c request_size=12 user_agent=
2023-07-20T23:13:17.714942Z [info  ] updated  [hubuum.signals.object] id=8 model=Host request_id=402cfc7c-f8de-42d6-8f4e-6bbb7dd0b39c
2023-07-20T23:13:17.715166Z [info  ] updated  [hubuum.api.object] instance=8 model=Host request_id=402cfc7c-f8de-42d6-8f4e-6bbb7dd0b39c user=tmp
2023-07-20T23:13:17.715638Z [debug ] response [hubuum.response] content={...} method=PATCH path=/api/v1/resources/hosts/yes request_id=402cfc7c-f8de-42d6-8f4e-6bbb7dd0b39c run_time_ms=39.25 status_code=200 status_label=OK user=tmp
2023-07-20T23:13:17.735291Z [debug ] request  [hubuum.request] method=DELETE path=/api/v1/iam/namespaces/namespace1 proxy_ip= remote_ip=127.0.0.1 request_id=65b430d5-e8ec-45dd-90de-4fb4732b132b request_size=0 user_agent=
2023-07-20T23:13:17.752319Z [info  ] deleted  [hubuum.api.object] instance=7 model=Namespace request_id=65b430d5-e8ec-45dd-90de-4fb4732b132b user=superuser
2023-07-20T23:13:17.811455Z [info  ] deleted  [hubuum.signals.object] id=4 model=Permission request_id=65b430d5-e8ec-45dd-90de-4fb4732b132b
2023-07-20T23:13:17.815491Z [info  ] deleted  [hubuum.signals.object] id=8 model=Host request_id=65b430d5-e8ec-45dd-90de-4fb4732b132b
2023-07-20T23:13:17.818405Z [info  ] deleted  [hubuum.signals.object] id=7 model=Namespace request_id=65b430d5-e8ec-45dd-90de-4fb4732b132b
2023-07-20T23:13:17.818837Z [debug ] response [hubuum.response] content=[] method=DELETE path=/api/v1/iam/namespaces/namespace1 request_id=65b430d5-e8ec-45dd-90de-4fb4732b132b run_time_ms=83.53 status_code=204 status_label=No Content user=superuser
```

Notice how the request_id also applies to the cascading events caught by the signals logger and caused by the deletion of the namespace "namespace1".

## Sentry

Hubuum can be configured to send logs to [Sentry](https://sentry.io/). To do this, set the `SENTRY_DSN` environment variable to the DSN for your Sentry project.


## Development

During development, hubuum produces colored output. To disable this, set the `HUBUUM_LOGGING_PRODUCTION` environment variable to `True`.

