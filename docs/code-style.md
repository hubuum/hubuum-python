# Code Style

## General

* [Black](https://black.readthedocs.io/en/stable/) is the code style used for this project. It is enforced by the CI.
* [isort](https://pycqa.github.io/isort/) is used to sort imports, also enforced by the CI.
* [flake8](https://flake8.pycqa.org/en/latest/) is used to enforce the code style.
* [pylint](https://pylint.org/) is used to check code quality. Anything below 10/10 is considered a failure.
* [coverage](https://coverage.readthedocs.io/en/latest/) is used to check code coverage. Anything below 100% is considered a failure.

## Checking Code Style

* `tox -e format` will run black, isort, and pylint on the codebase.
* `tox -e flake8` will run flake8 with the required extensions on the codebase.

## Checking Code Coverage

* `tox -e coverage` will run coverage on the codebase. Afterwards, `coverage report -m` can be used to see the coverage report.

## External resources

Coveralls and Codiga are used to check code coverage and code quality respectively for pull requests. Both have to pass without errors (ie, no decrease in coverage or code quality) for a pull request to be merged. The following links can be used to view the current status of the project:

* [Coveralls.io](https://coveralls.io/github/hubuum/hubuum?branch=main)
* [Codiga.io](https://app.codiga.io/hub/project/35582/hubuum)
  