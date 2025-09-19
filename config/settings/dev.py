"""
Development settings for the Django project.

This module extends the shared base settings (`base.py`) with configuration
suitable for local development:

- Debug mode enabled.
- Emails printed to console.
"""

from .base import *  # noqa: F403, F401

# ---------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------
DEBUG = True

# ---------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Optionally, loosen logging noise locally:
LOGGING["root"]["level"] = "INFO"  # noqa: F405
