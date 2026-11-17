"""
Health check endpoints for load balancers, container orchestrators, and monitoring probes.
"""

from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Returns 200 OK if API is responsive, database is connected, and cache is functional.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_healthy = True
        cache_healthy = True
        error_details = {}

        # 1. Probe database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except Exception as e:
            db_healthy = False
            error_details["database"] = str(e)

        # 2. Probe cache (database-backed cache)
        try:
            cache.set("__health_probe__", "ok", 5)
            if cache.get("__health_probe__") != "ok":
                cache_healthy = False
                error_details["cache"] = "Cache read mismatch"
        except Exception as e:
            cache_healthy = False
            error_details["cache"] = str(e)

        overall_status = "ok" if (db_healthy and cache_healthy) else "degraded"
        http_status = status.HTTP_200_OK if overall_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": overall_status,
                "timestamp": timezone.now().isoformat(),
                "components": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "cache": "healthy" if cache_healthy else "unhealthy",
                },
                **({"errors": error_details} if error_details else {}),
            },
            status=http_status,
        )
