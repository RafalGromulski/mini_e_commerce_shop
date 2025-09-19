"""
Staging settings for the Django project.

This module extends the shared base settings (`base.py`) with configuration
suitable for a staging/pre-production environment:

- Debug disabled.
- SSL redirect + secure cookies on.
- Short HSTS without preload.
- Console email to avoid sending real mail.
"""

from .base import *  # noqa: F403, F401

# ---------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------
DEBUG = False

# ---------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------
# Short HSTS for staging (1 day) and no preload to avoid pinning test domains.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 60 * 60 * 24  # 1 day
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

# ---------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------
# Do not send real emails from staging.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
