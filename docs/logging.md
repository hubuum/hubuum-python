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
- `HUBUUM_LOGGING_LEVEL_HTTP`: Sets the logging level for HTTP traffic, typically requests and responses. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_OBJECT`: Sets the logging level for object manipulation. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_SIGNAL`: Sets the logging level for signals, typically used for object manipulation. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_INTERNAL`: Sets the logging level for internal logging, typically used for introspection. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_MANUAL`: Sets the logging level for manual logs. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_MIGRATION`: Sets the logging level for migration logs. Defaults to the value of `HUBUUM_LOGGING_LEVEL`.
- `HUBUUM_LOGGING_LEVEL_DJANGO`: Sets the logging level for Django. Defaults to `ERROR`. This logger is not recommended for use.

## Request identifiers

Hubuum applies a request_id to contextually related log entries. This request_id follows events from a request to a response, leading to logs such as these:

```
2023-07-23T21:16:30.863144Z [info     ]  • request          [hubuum.http] request_id=a07...2f4 method=PATCH remote_ip=127.0.0.1 proxy_ip= user_agent= path=/api/v1/resources/hosts/yes request_size=12 body={"serial":1}
2023-07-23T21:16:30.896036Z [info     ]  • updated          [hubuum.object] request_id=a07...2f4 model=Host id=1
2023-07-23T21:16:30.896433Z [debug    ]  • updated          [hubuum.api] request_id=a07...2f4 model=Host user=tmp instance=1
2023-07-23T21:16:30.896900Z [info     ]  • response         [hubuum.http] request_id=a07...2f4 user=tmp method=PATCH status_code=200 status_label=OK path=/api/v1/resources/hosts/yes content={"id":1,"created_at":"2023-07-23T21:16:30.725568Z","updated_at":"2023-07-23T21:16:30.892566Z","name":"yes","fqdn":"","serial":"1","registration_date":"2023-07-23T21:16:30.725586Z","namespace":1,"type":null,"room":null,"jack":null,"purchase_order":null,"person":null} run_time_ms=33.75
2023-07-23T21:16:30.908318Z [info     ]  • updated          [hubuum.object] request_id=98f...8d2 model=User id=1
2023-07-23T21:16:30.912440Z [info     ]  • created          [hubuum.object] request_id=98f...8d2 model=AuthToken id=2ec...aa0 : superuser
2023-07-23T21:16:30.913254Z [info     ]  • request          [hubuum.http] request_id=98f...8d2 method=DELETE remote_ip=127.0.0.1 proxy_ip= user_agent= path=/api/v1/iam/namespaces/namespace1 request_size=0 body=
2023-07-23T21:16:30.928717Z [debug    ]  • deleted          [hubuum.api] request_id=98f...8d2 model=Namespace user=superuser instance=1
2023-07-23T21:16:30.980427Z [info     ]  • deleted          [hubuum.object] request_id=98f...8d2 model=Permission id=1
2023-07-23T21:16:30.984305Z [info     ]  • deleted          [hubuum.object] request_id=98f...8d2 model=Host id=1
2023-07-23T21:16:30.987523Z [info     ]  • deleted          [hubuum.object] request_id=98f...8d2 model=Namespace id=1
2023-07-23T21:16:30.987982Z [info     ]  • response         [hubuum.http] request_id=98f...8d2 user=superuser method=DELETE status_code=204 status_label=No Content path=/api/v1/iam/namespaces/namespace1 content= run_time_ms=74.71
```

Notice how the request_id also applies to the cascading events caused by the deletion of the namespace "namespace1". Also note that the dots would be colored according to the request_id for the entry.

## Sentry

Hubuum can be configured to send logs to [Sentry](https://sentry.io/). To do this, set the `SENTRY_DSN` environment variable to the DSN for your Sentry project.


## Development

During development, hubuum produces colored output. To disable this, set the `HUBUUM_LOGGING_PRODUCTION` environment variable to `True`.

