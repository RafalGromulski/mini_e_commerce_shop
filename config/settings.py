"""
Django settings for the E-commerce API project.

Key points:
- All sensitive values are loaded from environment variables (.env in dev).
- SQLite by default in development; switch to Postgres/MySQL via DATABASE_URL.
- DRF + django-filter + drf-spectacular for a clean REST API and OpenAPI schema.
- Celery/Redis settings are env-driven; a daily beat task is preconfigured.
- Production security flags auto-enable when DEBUG=False.
"""

from pathlib import Path
from typing import List

import environ
from celery.schedules import crontab

# --- Paths --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment --------------------------------------------------------------
# Define defaults here; override via actual env vars or .env in development.
env = environ.Env(
    DEBUG=(bool, True),
)
# Load .env if present (use real environment in production).
environ.Env.read_env(BASE_DIR / ".env")

# --- Core / Security ----------------------------------------------------------
DEBUG: bool = env.bool("DEBUG", default=True)
SECRET_KEY = "django-insecure-*o6#w)3-dnea#7(fuc)ypss+^k6!2$3loudny7ej01y_k74vzj"
# SECRET_KEY: str = env("SECRET_KEY", default="dev-secret-key-change-me")
ALLOWED_HOSTS: List[str] = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS: List[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[])

if not DEBUG and (not SECRET_KEY or SECRET_KEY == "dev-secret-key-change-me"):
    raise RuntimeError("SECRET_KEY must be set when DEBUG is False.")

# --- Installed apps -----------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "django_filters",
    "drf_spectacular",

    # Local apps
    "shop.apps.ShopConfig",
]

# --- Middleware ---------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# --- Templates ----------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # Add your template dirs here if needed
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

WSGI_APPLICATION = "config.wsgi.application"

# --- Database -----------------------------------------------------------------
# Default: SQLite (dev).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- Password validation ------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / tz ----------------------------------------------------------------
LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

# --- Static & media -----------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Email --------------------------------------------------------------------
# In development we log emails to console; configure SMTP in .env for real mail.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
EMAIL_HOST = env("EMAIL_HOST", default=None)
EMAIL_PORT = env.int("EMAIL_PORT", default=0) or None
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default=None)
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default=None)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

# --- DRF / OpenAPI ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # Session auth is fine for dev / Swagger. Token/JWT can be added later.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Public read endpoints by default; per-view overrides handle stricter rules.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# Name of the Django auth group whose members are treated as "sellers"
SHOP_SELLER_GROUP = env("SHOP_SELLER_GROUP", default="seller")

SPECTACULAR_SETTINGS = {
    "TITLE": "Rafał Gromulski e-commerce API",
    "VERSION": "0.1.0",
}

# --- Celery / Redis -----------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_BEAT_SCHEDULE = {
    # Daily payment reminder for orders due tomorrow.
    "payment-reminders-daily": {
        "task": "shop.tasks.send_payment_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
}

# --- Logging ------------------------------------------------------------------
# Simple console logs in dev; tune levels/handlers for production as needed.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "shop": {"handlers": ["console"], "level": "INFO"},
    },
}

# --- Production security toggles ---------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
