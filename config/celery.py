"""Celery application factory for distributed tasks"""

from __future__ import annotations

from celery import Celery

from config.env import configure_django_settings

configure_django_settings()

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
