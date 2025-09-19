"""
Project-level views.

Currently, includes:
- HealthCheckView: simple monitoring endpoint for load balancers and ops.
"""

import logging
from types import ModuleType
from typing import Any, Optional, cast

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    import redis as _redis
except ImportError:
    _redis = None  # type: ignore[assignment]

redis: Optional[ModuleType] = _redis

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health-check endpoint for monitoring and load balancers.

    Returns a JSON payload indicating the status of core services:
    - status: "ok" if all required services are healthy, otherwise "error".
    - database: True if the default DB connection works, False if not.
    - redis: True if Redis is reachable, False if unreachable,
      or null if Redis is not configured in settings.

    This endpoint is intentionally public (no auth), so external systems
    like Kubernetes liveness/readiness probes, AWS ALB health checks, or
    monitoring dashboards can call it without credentials.

    Example responses:

        200 OK
        {
            "status": "ok",
            "database": true,
            "redis": true
        }

        200 OK
        {
            "status": "error",
            "database": false,
            "redis": true
        }

        200 OK
        {
            "status": "ok",
            "database": true,
            "redis": null
        }
    """

    authentication_classes: list[Any] = []  # No authentication required
    permission_classes: list[Any] = []  # No permission checks

    @staticmethod
    def get(request: Request) -> Response:
        result: dict[str, Any] = {
            "status": "ok",
            "database": False,
            "redis": None,  # None = not configured
        }

        # --- Database check ---
        try:
            conn = connections["default"]
            conn.cursor()  # open connection
            result["database"] = True
        except OperationalError as e:
            logger.warning("DB health check failed: %s", e)
            result["status"] = "error"
            result["database"] = False

        # --- Redis check ---
        broker_url = cast(Optional[str], getattr(settings, "CELERY_BROKER_URL", None))
        if redis is not None and broker_url:
            try:
                r = cast(Any, redis).Redis.from_url(broker_url)
                r.ping()
                result["redis"] = True
            except Exception as e:
                logger.warning("Redis health check failed: %s", e)
                result["status"] = "error"
                result["redis"] = False

        return Response(result)
