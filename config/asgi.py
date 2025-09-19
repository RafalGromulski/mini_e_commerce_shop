"""
ASGI config for the project.

This module exposes the ASGI callable as a module-level variable named ``application``.
It is used by ASGI-compatible servers to serve your Django project, enabling support
for asynchronous features such as WebSockets.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/asgi/
"""

# import os

from django.core.asgi import get_asgi_application

import config.settings  # noqa: F401

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
