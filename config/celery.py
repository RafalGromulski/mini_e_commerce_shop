"""Celery application factory for distributed tasks"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app: Celery = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    broker_connection_retry_on_startup=True,
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_track_started=True,
)

app.autodiscover_tasks()
