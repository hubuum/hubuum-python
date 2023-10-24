# Testing

`tox` is used as the testing framework. Apart from running the same tests as `python manage.py test`, it will test against multiple permutations of supported python and django versions.

Tox is also used to run linting (`tox -e format` and `tox -e flake8`), as well as coveragev via `tox -e coverage`.

## Running tests

To run the tests, simply run `tox` in the root directory of the project.

Note that you may also use pytest directly, but this will only run the tests against one version python and django. You do however get the option to use `pytest -k` to run a specific test, which is useful for debugging. pytest is also handy as adding `-s` will also show the output of print statements.

A common workflow is to run `pytest -k path/to/test_something.py -s -vv` to run a specific test and see the output of print statements.

## Writing tests

Tests are seperated between core functionality and the API. Core functionality tests are located in `tests/` and API tests are located in `api/v1/tests/`.

### Testing dynamic classes

There is a testing framework in place to make testing dynamic classes easier. See `tests/helpers/populators.py` and `api/v1/tests/helpers/populators.py` for inheritable classes to help set up test classes, objects, and data.
