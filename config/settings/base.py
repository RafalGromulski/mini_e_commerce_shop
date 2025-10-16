"""
Base Django settings for the Mini e-commerce Shop API.

This module defines configuration shared across all environments
(dev / staging / production). Environment-specific overrides live in:
`dev.py`, `staging.py`, and `prod.py`.

Notes:
- Environment variables are loaded via `django-environ`.
- Where applicable, helpers are Docker-secrets friendly (e.g., *_FILE vars).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import environ
from celery.schedules import crontab

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
# => parents[2] points to <project_root>
BASE_DIR = Path(__file__).resolve().parents[2]
# Equivalent
# BASE_DIR = Path(__file__).resolve().parent.parent.parent

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


# ---------------------------------------------------------------------
# Secrets helpers / URL builders (Docker secrets friendly)
# ---------------------------------------------------------------------
def read_secret(path: str | None, default: str = "") -> str:
    """
    Read a secret from a file (e.g., `/run/secrets/...`); fall back to `default`.

    Args:
        path: Path to the secret file or None.
        default: Value to return when `path` is missing or unreadable.

    Returns:
        The stripped file contents on success, otherwise `default`.
    """
    if not path:
        return default
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return default


def build_postgres_dict_from_parts() -> dict[str, Any]:
    """
    Build `DATABASES['default']` using discrete DB_* envs + optional `DB_PASSWORD_FILE`.

    Honors:
        - DB_NAME, DB_USER, DB_HOST, DB_PORT
        - DB_CONN_MAX_AGE, DB_CONNECT_TIMEOUT
        - DB_SSL_REQUIRED, DB_SSLMODE
        - DB_PASSWORD_FILE (preferred) or POSTGRES_PASSWORD

    Returns:
        A Django DATABASES configuration dictionary for PostgreSQL.
    """
    name = env("DB_NAME", default="app")
    user = env("DB_USER", default="app")
    host = env("DB_HOST", default="db")
    port = env("DB_PORT", default="5432")
    pwd = read_secret(
        env("DB_PASSWORD_FILE", default=None), default=env("POSTGRES_PASSWORD", default="")
    )
    cfg: dict[str, Any] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": user,
        "PASSWORD": pwd,
        "HOST": host,
        "PORT": port,
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
        "OPTIONS": {"connect_timeout": env.int("DB_CONNECT_TIMEOUT", default=5)},
    }

    if env.bool("DB_SSL_REQUIRED", default=False):
        cfg.setdefault("OPTIONS", {}).update({"sslmode": env("DB_SSLMODE", default="require")})
    return cfg


def build_redis_url(db_env_name: str, default_db: str) -> str:
    """
    Compose a `redis://` URL from REDIS_* envs plus `REDIS_PASSWORD[_FILE]`.

    Args:
        db_env_name: Name of the env var carrying the logical Redis DB index
                     (e.g., "REDIS_DB_BROKER").
        default_db: Fallback DB index string to use when `db_env_name` is unset.

    Returns:
        A `redis://` or `redis://:password@host:port/db` connection URL.
    """
    host = env("REDIS_HOST", default="redis")
    port = env("REDIS_PORT", default="6379")
    db = env(db_env_name, default=default_db)
    pwd = read_secret(
        env("REDIS_PASSWORD_FILE", default=None), default=env("REDIS_PASSWORD", default="")
    )
    if pwd:
        return f"redis://:{quote_plus(pwd)}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


# --- Core / Security ----------------------------------------------------------
DEBUG: bool = env.bool("DEBUG", default=True)

SECRET_KEY: str = read_secret(
    env("DJANGO_SECRET_KEY_FILE", default=None),
    default=env("SECRET_KEY", default="dev-secret-key-change-me"),
)

# IMPORTANT: use list defaults, not strings
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS: list[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[])

if not DEBUG and ALLOWED_HOSTS == ["*"]:
    raise RuntimeError("Set ALLOWED_HOSTS explicitly for non-debug runs.")

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
# Priority:
# 1) DATABASE_URL (convenient in dev)
# 2) DB_* + DB_PASSWORD_FILE (Docker secrets)
# 3) SQLite fallback
if env("DATABASE_URL", default=None):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    if any(
        env(e, default=None)
        for e in [
            "DB_NAME",
            "DB_USER",
            "DB_HOST",
            "DB_PORT",
            "DB_PASSWORD_FILE",
            "POSTGRES_PASSWORD",
        ]
    ):
        DATABASES = {"default": build_postgres_dict_from_parts()}
    else:
        DATABASES = {"default": env.db(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

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
TIME_ZONE = env("TZ", default="Europe/Warsaw")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = Path(env("STATIC_ROOT", default=BASE_DIR / "staticfiles"))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=BASE_DIR / "media"))

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
    "TITLE": env("OPENAPI_TITLE", default="Mini e-commerce shop API project"),
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

# ---------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=None) or build_redis_url(
    "REDIS_DB_BROKER", default_db="0"
)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=None) or build_redis_url(
    "REDIS_DB_BACKEND", default_db="0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = env("CELERY_TASK_DEFAULT_QUEUE", default="default")
CELERY_BEAT_SCHEDULE = {
    # Weekdays at 09:00 — payment reminder for orders due the next day.
    "payment-reminders-daily": {
        "task": "shop.tasks.send_payment_reminders",
        "schedule": crontab(hour=9, minute=0, day_of_week="mon-fri"),
        "options": {"queue": CELERY_TASK_DEFAULT_QUEUE},
        # For local testing:
        # "schedule": timedelta(minutes=1),
    },
}

# ---------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------
if env("CACHE_URL", default=None):
    CACHES: dict[str, Any] = {"default": env.cache("CACHE_URL")}
elif env.bool("USE_REDIS_CACHE", default=False):
    redis_cache_url = build_redis_url("REDIS_DB_CACHE", default_db="1")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_cache_url,
            "TIMEOUT": env.int("CACHE_TIMEOUT", default=300),
            "KEY_PREFIX": env("CACHE_KEY_PREFIX", default="app"),
        }
    }
else:
    CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}

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
# Auto-harden when DEBUG=False. You can still override via env in `prod.py`.
# if not DEBUG:
#     # Require proper secret in non-debug runs
#     if not SECRET_KEY or SECRET_KEY == "dev-secret-key-change-me":
#         raise RuntimeError("SECRET_KEY must be set when DEBUG is False.")

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
