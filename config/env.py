"""Utilities for configuring Django settings from environment variables."""

import os


def _as_bool(val: str | None, default: bool = False) -> bool:
    """
    Convert a textual value to a boolean.

    Treats the following (case-insensitive, with surrounding whitespace ignored)
    as truthy: "1", "true", "yes", "on". If `val` is `None`, returns `default`.

    Examples:
        >>> _as_bool("true")
        True
        >>> _as_bool(" Yes ")
        True
        >>> _as_bool("0")
        False
        >>> _as_bool(None, default=True)
        True

    Args:
        val: The value to interpret (e.g., from `os.getenv(...)`).
        default: Value to return when `val` is `None`.

    Returns:
        bool: The interpreted boolean.
    """
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def configure_django_settings() -> None:
    """
    Set the `DJANGO_SETTINGS_MODULE` env var if it isn't already set.

    If `DJANGO_SETTINGS_MODULE` is present, the function does nothing.
    Otherwise, it selects:
      - `"config.settings.dev"` when the `DEBUG` environment variable is truthy,
      - `"config.settings.prod"` otherwise.

    The `DEBUG` value is interpreted via `_as_bool(os.getenv("DEBUG"), default=True)`,
    meaning that a missing `DEBUG` defaults to the development settings.

    Returns:
        None
    """
    if "DJANGO_SETTINGS_MODULE" in os.environ:
        return

    default_settings = (
        "config.settings.dev"
        if _as_bool(os.getenv("DEBUG"), default=True)
        else "config.settings.prod"
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)
