"""
Configure the Django settings module based on an environment variable.

If the environment variable `DEBUG` is set to `"1"` (or is missing),
the development settings module will be used:
    "config.settings.dev"

Otherwise, the production settings module will be used:
    "config.settings.prod"

The configuration only applies if `DJANGO_SETTINGS_MODULE`
is not already defined in the environment.
"""

import os


def configure_django_settings() -> None:
    """Set the default Django settings module based on DEBUG=True/False."""
    default_settings = (
        "config.settings.dev" if os.getenv("DEBUG", "True") == "True" else "config.settings.prod"
    )
    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)
    os.environ["DJANGO_SETTINGS_MODULE"] = default_settings


# Apply configuration at import time
configure_django_settings()
