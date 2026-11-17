"""
Integration tests for system health probe endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.integration
class TestHealthCheckEndpoint:
    def test_health_check_returns_200_and_components(self, api_client, db):
        url = reverse("health-check")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"
        assert response.data["components"]["database"] == "healthy"
        assert response.data["components"]["cache"] == "healthy"

    def test_api_health_alias_endpoint(self, api_client, db):
        url = reverse("api-health-check")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"
