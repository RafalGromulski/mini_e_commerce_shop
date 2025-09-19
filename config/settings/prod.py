"""
Production settings for the Django project.

This module extends the shared base settings (`base.py`) with configuration
suitable for a production environment:

- Debug disabled.
- Strong security headers and HTTPS-only cookies.
- HSTS enabled with preload and subdomains.
- Use a real email backend (configure via env).
"""

from .base import *  # noqa: F403, F401

# ---------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------
DEBUG = False

# ---------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------
# If you want to force stricter values than base auto-toggles, set them here:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------
# Configure a real backend for production, e.g. SMTP:
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
