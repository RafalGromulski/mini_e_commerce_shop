"""
WSGI config for the project.

This module exposes the WSGI callable as a module-level variable named ``application``.
It is used by WSGI-compatible web servers to serve your Django project.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/
"""

# import os

from django.core.wsgi import get_wsgi_application

import config.settings  # noqa: F401

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
