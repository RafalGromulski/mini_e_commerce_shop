"""
Base Django settings for the E-commerce API project.

This module holds configuration shared by all environments (dev/staging/prod).
Environment-specific overrides live in sibling modules: dev.py, staging.py, prod.py.

Key points:
- Environment-driven config using django-environ (.env for dev).
- SQLite by default; switch to Postgres/MySQL with DATABASE_URL.
- DRF + django-filter + drf-spectacular for REST API and OpenAPI schema.
- Celery/Redis & a sample daily beat task, all env-driven.
- Production security toggles auto-enable when DEBUG=False (see bottom section).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import environ
from celery.schedules import crontab

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
# => parents[2] points to <project_root>
BASE_DIR = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, True),
)

# Load .env if present (prefer <project_root>/.env; fall back to config/.env)
env_file_candidates = [BASE_DIR / ".env", BASE_DIR / "config" / ".env"]
for _env_path in env_file_candidates:
    if _env_path.exists():
        environ.Env.read_env(_env_path)
        break

# --- Core / Security ----------------------------------------------------------
DEBUG: bool = env.bool("DEBUG", default=True)
SECRET_KEY: str = env("SECRET_KEY", default="dev-secret-key-change-me")
# ALLOWED_HOSTS: List[str] = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
ALLOWED_HOSTS: List[str] = env.list("ALLOWED_HOSTS", default="*")
CSRF_TRUSTED_ORIGINS: List[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    # Local apps
    "shop.apps.ShopConfig",
]

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# URL / WSGI / ASGI
# ---------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------
DATABASES = {"default": env.db(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

# ---------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en")
TIME_ZONE = env("TIME_ZONE", default="Europe/Warsaw")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
EMAIL_HOST = env("EMAIL_HOST", default=None)
EMAIL_PORT = env.int("EMAIL_PORT", default=0) or None
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default=None)
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default=None)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

# ---------------------------------------------------------------------
# Django REST Framework (DRF)
# ---------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Session auth is fine for dev/Swagger. Token/JWT can be enabled in prod.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        # "rest_framework.authentication.TokenAuthentication",
        # "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE", default=20),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
}

if not DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = ["rest_framework.renderers.JSONRenderer"]
else:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]

# ---------------------------------------------------------------------
# OpenAPI (drf-spectacular)
# ---------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": env("OPENAPI_TITLE", default="E-commerce API"),
    "DESCRIPTION": "REST API for e-commerce domain.",
    "VERSION": env("OPENAPI_VERSION", default="0.1.0"),
    "SERVERS": [{"url": env("OPENAPI_SERVER_URL", default="http://localhost:8000")}],
    "SERVE_INCLUDE_SCHEMA": env.bool("OPENAPI_SERVE_INCLUDE_SCHEMA", default=DEBUG),
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayRequestDuration": True,
        "persistAuthorization": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    # Example of closing Swagger in prod:
    # "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
}

CELERY_TASK_DEFAULT_QUEUE = env("CELERY_TASK_DEFAULT_QUEUE", default="default")
CELERY_BEAT_SCHEDULE = {
    # Daily payment reminder for orders due tomorrow.
    "payment-reminders-daily": {
        "task": "shop.tasks.send_payment_reminders",
        "schedule": crontab(hour=9, minute=0),
        "options": {"queue": CELERY_TASK_DEFAULT_QUEUE},
    },
}

# --- Cache --------------------------------------------------------------------
CACHES = {
    "default": env.cache("CACHE_URL", default="locmemcache://"),
}

# --- Logging ------------------------------------------------------------------
# Simple console logs by default; tune levels/handlers for production as needed.
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "shop": {"handlers": ["console"], "level": "INFO"},
    },
}

# --- Production security toggles ---------------------------------------------
# Auto-harden when DEBUG=False. You can still override via env in prod.py.
if not DEBUG:
    # Require proper secret in non-debug runs
    if not SECRET_KEY or SECRET_KEY == "dev-secret-key-change-me":
        raise RuntimeError("SECRET_KEY must be set when DEBUG is False.")

    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)  # 30 days
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
