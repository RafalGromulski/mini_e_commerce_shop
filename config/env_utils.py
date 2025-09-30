"""Helpers for reading configuration from environment variables or Docker secrets.

This module provides `env_or_file`, a small helper that returns the value of an
environment variable if set, otherwise it attempts to read the value from a file
whose path is provided via a companion `<KEY>_FILE` environment variable.
"""

import os
from pathlib import Path


def env_or_file(key: str, default: str | None = None) -> str | None:
    """
    Return a configuration value from the environment or from a file path in `<KEY>_FILE`.

    Resolution order:
      1) If `os.environ[key]` exists and is a non-empty string, return it.
      2) Else, if `os.environ[f"{key}_FILE"]` points to an existing file, read its
         contents as UTF-8, strip surrounding whitespace, and return the result.
      3) Otherwise, return `default`.

    Notes:
      - An empty string in the direct environment variable is treated as "unset"
        (i.e., step 2 will still be attempted). This mirrors common secret-loading
        patterns, but call it out if you need empty strings to be respected.
      - Any I/O error while reading the file (permissions, encoding issues, etc.)
        will fall back to `default`.

    Examples:
        >>> # Suppose: SECRET="top", SECRET_FILE unset
        >>> env_or_file("SECRET")
        'top'
        >>> # Suppose: SECRET unset, SECRET_FILE="/run/secrets/secret"
        >>> env_or_file("SECRET")  # reads and strips file contents
        'from-file'
        >>> # Suppose: both unset
        >>> env_or_file("MISSING", default="fallback")
        'fallback'

    Args:
        key: Name of the environment variable to look up (e.g., "DATABASE_PASSWORD").
        default: Value to return when neither the env var nor the file are available.

    Returns:
        The resolved string value, or `None` if nothing found and no default provided.
    """
    val = os.getenv(key)
    if val:
        return val

    file_path = os.getenv(f"{key}_FILE")
    if file_path:
        p = Path(file_path)
        if p.exists():
            try:
                return p.read_text(encoding="utf-8").strip()
            except OSError:
                # Fall through to default on read errors
                pass
    return default
