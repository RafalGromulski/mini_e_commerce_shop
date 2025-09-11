"""Expose the project's Celery application as `celery_app`.

- Celery CLI: `celery -A config worker -l info` imports this package and finds `celery_app`.
- Django startup: importing this package loads the Celery app so that `@shared_task`
  decorators bind to this application.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
