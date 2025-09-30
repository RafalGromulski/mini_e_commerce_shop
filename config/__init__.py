"""Expose project's Celery app as `celery_app` for Django and Celery CLI.

- Celery CLI: `celery -A config worker -l info` imports this package and finds `celery_app`.
- Django startup: importing this package loads the Celery app so that `@shared_task`
  decorators bind to this application.
"""

import os

if os.getenv("DJANGO_SKIP_CELERY_IMPORT") != "1":
    from .celery import app as celery_app

__all__ = ("celery_app",)
