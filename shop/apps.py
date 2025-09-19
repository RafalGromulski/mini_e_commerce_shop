"""App configuration for the Shop application.

- Registers Django signal handlers on startup.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ShopConfig(AppConfig):
    """Django app config for the Shop app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"
    verbose_name = _("Shop")

    def ready(self) -> None:
        # Import signal handlers so they get registered by Django.
        from . import signals  # noqa: F401
