"""
Django settings for hubuum project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import logging
import os
from datetime import timedelta
from pathlib import Path

import sentry_sdk
import structlog
from structlog_sentry import SentryProcessor

import hubuum.log

LOGGING_LEVEL = os.environ.get("HUBUUM_LOGGING_LEVEL", "critical").upper()
LOGGING_LEVEL_SOURCE = {}

for source in ["DJANGO", "API", "SIGNALS", "REQUEST", "MANUAL", "MIGRATION", "AUTH"]:
    LOGGING_LEVEL_SOURCE[source] = os.environ.get(
        f"HUBUUM_LOGGING_LEVEL_{source}", LOGGING_LEVEL
    ).upper()

LOGGING_PRODUCTION = os.environ.get("HUBUUM_LOGGING_PRODUCTION", False)

SENTRY_DSN = os.environ.get("HUBUUM_SENTRY_DSN", "")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production,
        traces_sample_rate=1.0,
    )

# from rest_framework.settings import api_settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "_1i4sc7w+h!i6fz=+-@@0kj#61152x6c=a(b61-%1*$5m)xwok"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "django_structlog",
    "knox",
    "hubuum",
]

AUTH_USER_MODEL = "hubuum.User"


MIDDLEWARE = [
    "django_structlog.middlewares.RequestMiddleware",
    "hubuum.middleware.logging_http.LogHttpResponseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hubuumsite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hubuumsite.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("knox.auth.TokenAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_PAGINATION_CLASS": "hubuum.pagination.HubuumFlexiblePagination",
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # this is default
)

REST_KNOX = {
    "TOKEN_TTL": timedelta(hours=24),
    "AUTO_REFRESH": True,
}

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

# DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': BASE_DIR / 'db.sqlite3',
#    }
# }

DATABASES = {
    "default": {
        "ENGINE": os.environ.get(
            "HUBUUM_DATABASE_BACKEND", "django.db.backends.postgresql"
        ),
        "NAME": os.environ.get("HUBUUM_DATABASE_NAME", "hubuum"),
        "USER": os.environ.get("HUBUUM_DATABASE_USER", "hubuum"),
        "PASSWORD": os.environ.get("HUBUUM_DATABASE_PASSWORD"),
        "HOST": os.environ.get("HUBUUM_DATABASE_HOST", "localhost"),
        "PORT": int(os.environ.get("HUBUUM_DATABASE_PORT", 5432)),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

# Deprecated.
# USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"

output_type = structlog.dev.ConsoleRenderer(colors=True)
if LOGGING_PRODUCTION or not DEBUG:
    output_type = structlog.processors.JSONRenderer()

SENTRY_LEVEL = os.environ.get("HUBUUM_SENTRY_LEVEL", "critical").upper()
if SENTRY_LEVEL not in [
    "CRITICAL",
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG",
]:  # pragma: no cover
    raise ValueError("Invalid SENTRY_LEVEL")

# set sentry_level to logger.level depending on the value of SENTRY_LEVEL
if SENTRY_LEVEL == "DEBUG":
    SENTRY_LOG_LEVEL = logging.DEBUG
elif SENTRY_LEVEL == "INFO":
    SENTRY_LOG_LEVEL = logging.INFO
elif SENTRY_LEVEL == "WARNING":
    SENTRY_LOG_LEVEL = logging.WARNING
elif SENTRY_LEVEL == "ERROR":
    SENTRY_LOG_LEVEL = logging.ERROR
elif SENTRY_LEVEL == "CRITICAL":
    SENTRY_LOG_LEVEL = logging.CRITICAL


structlog.configure(
    processors=[
        hubuum.log.filter_sensitive_data,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        SentryProcessor(event_level=SENTRY_LOG_LEVEL),
        output_type,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": "DEBUG",
        },
    },
    "loggers": {
        "django_structlog": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["DJANGO"],
        },
        "hubuum.api.object": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["API"],
            "propagate": False,
        },
        "hubuum.signals.object": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["SIGNALS"],
            "propagate": False,
        },
        "hubuum.request": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["REQUEST"],
            "propagate": False,
        },
        "hubuum.auth": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["AUTH"],
            "propagate": False,
        },
        "hubuum.migration": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["MIGRATION"],
            "propagate": False,
        },
        "hubuum.manual": {
            "handlers": ["console"],
            "level": LOGGING_LEVEL_SOURCE["MANUAL"],
            "propagate": False,
        },
    },
}
