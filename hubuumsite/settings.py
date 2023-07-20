"""Django settings for hubuum project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict

import structlog
from structlog_sentry import SentryProcessor

import hubuum.log
from hubuumsite.config.base import HubuumBaseConfig

config = HubuumBaseConfig(os.environ)
# config.show_config()

DEBUG = config.is_development()
SECRET_KEY = config.get_secret_key()

# Manage slow requests and their escalations. These values are
# in milliseconds, and are used in the logging_http middleware.
REQUESTS_THRESHOLD_SLOW = config.requests.get("THRESHOLD_SLOW")
REQUESTS_LOG_LEVEL_SLOW = config.requests.get_log_level("LOG_LEVEL_SLOW")

REQUESTS_THRESHOLD_VERY_SLOW = config.requests.get("THRESHOLD_VERY_SLOW")
REQUESTS_LOG_LEVEL_VERY_SLOW = config.requests.get_log_level("LOG_LEVEL_VERY_SLOW")

# from rest_framework.settings import api_settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/
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
    "hubuum.middleware.context.ContextMiddleware",
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

REST_FRAMEWORK: Dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("knox.auth.TokenAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_PAGINATION_CLASS": "hubuum.pagination.HubuumFlexiblePagination",
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # this is default
)

REST_KNOX: Dict[str, Any] = {
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
        "ENGINE": config.database.get("ENGINE"),
        "NAME": config.database.get("NAME"),
        "USER": config.database.get("USER"),
        "PASSWORD": config.database.get("PASSWORD"),
        "HOST": config.database.get("HOST"),
        "PORT": config.database.get("PORT"),
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
        SentryProcessor(event_level=config.sentry.get_log_level("SENTRY_LEVEL")),
        # This sets either consolelogger or jsonlogger as the output type,
        # depending on if we're running in prod or testing production logging.
        config.logging.get_logging_output_type(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": True,
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
            "level": config.logging.level_for_source("DJANGO"),
        },
        "hubuum.internal": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("INTERNAL"),
        },
        "hubuum.api.object": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("API"),
            "propagate": False,
        },
        "hubuum.signals.object": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("SIGNALS"),
            "propagate": False,
        },
        "hubuum.request": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("REQUEST"),
            "propagate": False,
        },
        "hubuum.response": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("RESPONSE"),
            "propagate": False,
        },
        "hubuum.auth": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("AUTH"),
            "propagate": False,
        },
        "hubuum.migration": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("MIGRATION"),
            "propagate": False,
        },
        "hubuum.manual": {
            "handlers": ["console"],
            "level": config.logging.level_for_source("MANUAL"),
            "propagate": False,
        },
    },
}
