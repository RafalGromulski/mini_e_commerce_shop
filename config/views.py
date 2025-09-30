"""
Project-level views.

Currently, includes:
- HealthCheckView: simple monitoring endpoint for load balancers and ops.
"""

from __future__ import annotations

import logging
from types import ModuleType
from typing import Any, cast

from django.conf import settings
from django.db import connection as db_connection
from django.db.utils import OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    import redis as _redis
except ImportError:
    _redis = None  # type: ignore[assignment]

# Redis module if available, otherwise None. Kept broad for optional dependency.
redis: ModuleType | None = _redis

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health-check endpoint for monitoring and load balancers.

    Returns a JSON payload indicating the status of core services:

    Fields:
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

    # Explicitly public: no auth, allow any requester.
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes: list[Any] = []

    def get(
        self: "HealthCheckView",
        request: Request,
        *args: object,
        **kwargs: object,
    ) -> Response:
        """
        Perform health checks for the database and (optionally) Redis, and return
        their status in a JSON response.

        The Redis check is only attempted when both:
          - The `redis` package is importable, and
          - `settings.CELERY_BROKER_URL` is defined.

        Behavior can be tuned via settings:
          - `HEALTH_REDIS_REQUIRED` (bool, default False): if True and Redis is
            unreachable, overall `status` becomes "error".
          - `HEALTH_REDIS_TIMEOUT` (float seconds, default 0.5): socket timeouts
            for the Redis ping.
        """
        result: dict[str, Any] = {
            "status": "ok",
            "database": False,
            "redis": None,  # None = not configured
        }

        # --- Database check ---
        try:
            # Open a cursor, run a trivial query, then close immediately.
            with db_connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            result["database"] = True
        except OperationalError as e:
            logger.warning("DB health check failed: %s", e)
            result["status"] = "error"
            result["database"] = False

        broker_url = cast(str | None, getattr(settings, "CELERY_BROKER_URL", None))
        require_redis: bool = bool(getattr(settings, "HEALTH_REDIS_REQUIRED", False))
        redis_timeout: float = float(getattr(settings, "HEALTH_REDIS_TIMEOUT", 0.5))

        # --- Redis check (optional) ---
        if redis is not None and broker_url:
            try:
                r = cast(Any, redis).Redis.from_url(
                    broker_url,
                    socket_connect_timeout=redis_timeout,
                    socket_timeout=redis_timeout,
                    health_check_interval=0,  # explicit; we just ping once
                )
                r.ping()
                result["redis"] = True
            except Exception as e:  # noqa: BLE001 — health endpoint should never crash
                logger.warning("Redis health check failed: %s", e)
                result["redis"] = False
                if require_redis:
                    result["status"] = "error"

        return Response(result)
