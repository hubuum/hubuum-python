# Contributing

## How to contribute

### Reporting bugs

If you find a bug in, or have a suggestion for Hubuum, please create an [issue](https://github.com/terjekv/hubuum/issues) on GitHub. Generally speaking it is suggested to create an issue before creating a pull request.

Pull Requests are very welcome. For faster turnaround, please see the [Pull Request Guidelines](#pull-request-guidelines) below.

### Pull Request Guidelines

Before you submit a pull request, please make sure the following is done:

1. Fork the repository and create your branch from `main`.
2. Check that the tests pass and code style is valid by running `tox -e format` and `tox -e flake8`.
3. Check that coverage is 100% by running `tox -e coverage` and then `coverage report -m`.

### Local testing

If you have both postgresql and sqlite available locally, you can run the complete test suite by issuing `tox`. The default environment list is rather large (see `tox -l`). You can also test against only one of them. Ideally you want to set your "default" engine setup by using the same enviroment variables as one uses under production:

- `HUBUUM_DATABASE_ENGINE`: Sets the database engine. Defaults to "django.db.backends.postgresql".
- `HUBUUM_DATABASE_NAME`: Sets the name of the database. Defaults to "hubuum".
- `HUBUUM_DATABASE_USER`: Sets the database user. Defaults to "hubuum".
- `HUBUUM_DATABASE_PASSWORD`: Sets the password for the database user. Defaults to `None`.
- `HUBUUM_DATABASE_HOST`: Sets the database host. Defaults to "localhost".
- `HUBUUM_DATABASE_PORT`: Sets the port for the database. Defaults to 5432.

#### Postgresql

You MUST specify the following variables for postgresql, even when using tox to ask for a postgresql enviroment (ie, `python310-django41-postgres`). The database name and engine will however be automatically set.

- `HUBUUM_DATABASE_USER` 
- `HUBUUM_DATABASE_PASSWORD` 
- `HUBUUM_DATABASE_HOST` 
- `HUBUUM_DATABASE_PORT` 

You can see the available sqlite environments by doing `tox -l | grep postgres`.

You can run the postgresql suite by itself by doing `tox -e $( tox -l | grep postgres | tr '\n' ',' )`.

#### SQLite 

No configuration is required when using Tox and asking for an sqlite environment. The database will be created in `{envtmpdir}/hubuum.db`, typically something like ` .tox/python310-django41-sqlite/tmp`, and it will be deleted after use. The engine will be automaticall set.

You can see the available sqlite environments by doing `tox -l | grep sqlite`.

You can run the SQLite suite by itself by doing `tox -e $( tox -l | grep sqlite | tr '\n' ',' )`.

### Coverage

Coverage (`tox -e coverage && tox -e report`) assumes that the local environment variables are set up to allow for testing. See the sections for postgresql and SQLite above.