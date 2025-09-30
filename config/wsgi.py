"""
WSGI config for the project.

This module exposes the WSGI callable as a module-level variable named ``application``.
It is used by WSGI-compatible web servers to serve your Django project.
"""

from django.core.wsgi import get_wsgi_application

from config.env import configure_django_settings

configure_django_settings()

application = get_wsgi_application()
