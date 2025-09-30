"""
ASGI config for the project.

This module exposes the ASGI callable as a module-level variable named ``application``.
It is used by ASGI-compatible servers to serve your Django project, enabling support
for asynchronous features such as WebSockets.
"""

from django.core.asgi import get_asgi_application

from config.env import configure_django_settings

configure_django_settings()

application = get_asgi_application()
