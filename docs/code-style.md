# Code Style

## General

* [Black](https://black.readthedocs.io/en/stable/) is the code style used for this project. It is enforced by the CI.
* [ruff](https://docs.astral.sh/ruff/) is used to sort imports, general formatting, and linting. It is also enforced by the CI.
* [coverage](https://coverage.readthedocs.io/en/latest/) is used to check code coverage. Anything below 100% is considered a failure.

Ruff is used to replace pylint, flake8, and isort. It is also used to run black. It is configured via the `pyproject.toml` file.

## Checking Code Style

* `tox -e lint` will run the current linting tools on the codebase.

## Checking Code Coverage

* `tox -e coverage` will run coverage on the codebase. Afterwards, `coverage report -m` can be used to see the coverage report.

## External resources

Coveralls and Codiga are used to check code coverage and code quality respectively for pull requests. Both have to pass without errors (ie, no decrease in coverage or code quality) for a pull request to be merged. The following links can be used to view the current status of the project:

* [Coveralls.io](https://coveralls.io/github/hubuum/hubuum?branch=main)
* [Codiga.io](https://app.codiga.io/hub/project/35582/hubuum)
  