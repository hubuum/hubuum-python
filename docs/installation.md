# Installation

!!! note

    Hubuum is a work in progress and is not ready for production use.

Currently there are no releases, so...

```bash
$ git clone git@github.com:terjekv/hubuum.git
$ cd hubuum
$ python -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ python manage.py runserver
```

If you want to work on development for Hubuum, you can install the additional development requirements:

```bash
$ pip install -r requirements-dev.txt
```