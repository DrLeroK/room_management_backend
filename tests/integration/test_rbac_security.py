"""
Integration tests for Zero-Trust RBAC security matrix.
Verifies permissions across Anonymous, Receptionist, Manager, and Owner roles.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.integration
class TestRBACSecurityMatrix:
    # -------------------------------------------------------------------------
    # 1. Anonymous Access Restrictions (Zero-Trust)
    # -------------------------------------------------------------------------
    def test_anonymous_cannot_access_payment_ledger(self, api_client):
        url = reverse("payment-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_access_guest_records(self, api_client):
        url = reverse("guest-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_access_analytics(self, api_client):
        url = reverse("analytics-daily")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_cannot_trigger_exports(self, api_client):
        url = reverse("export-bookings")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # -------------------------------------------------------------------------
    # 2. Receptionist Privileges & Boundaries
    # -------------------------------------------------------------------------
    def test_receptionist_can_access_live_board_and_rooms(self, receptionist_client, sample_room):
        url = reverse("reception-live-board")
        response = receptionist_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        rooms_url = reverse("room-list")
        response_rooms = receptionist_client.get(rooms_url)
        assert response_rooms.status_code == status.HTTP_200_OK

    def test_receptionist_cannot_access_financial_analytics(self, receptionist_client):
        url = reverse("analytics-daily")
        response = receptionist_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_receptionist_cannot_export_database(self, receptionist_client):
        url = reverse("export-payments")
        response = receptionist_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_receptionist_cannot_delete_rooms(self, receptionist_client, sample_room):
        url = reverse("room-detail", kwargs={"pk": sample_room.pk})
        response = receptionist_client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # -------------------------------------------------------------------------
    # 3. Manager & Owner Privileges
    # -------------------------------------------------------------------------
    def test_manager_can_access_analytics_and_exports(self, manager_client):
        daily_url = reverse("analytics-daily")
        response = manager_client.get(daily_url)
        assert response.status_code == status.HTTP_200_OK

        export_url = reverse("export-bookings")
        export_res = manager_client.get(export_url)
        assert export_res.status_code == status.HTTP_200_OK
        assert export_res["Content-Type"] == "text/csv"

    def test_owner_can_access_bank_details_update(self, owner_client):
        url = reverse("hotel-bank-details")
        response = owner_client.get(url)
        assert response.status_code == status.HTTP_200_OK
