import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestUserDeactivationE2E:
    def test_complete_user_deactivation_lockout_workflow(self, api_client, manager_user):
        # 1. Create a staff user
        password = "SecurePassword123!"
        staff_user = User.objects.create_user(
            username="receptionist_john",
            email="john@staycraft.com",
            password=password,
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )

        # 2. Staff user logs in via /api/v1/users/login/
        login_response = api_client.post(
            "/api/v1/users/login/",
            {"username": "receptionist_john", "password": password},
            format="json",
        )
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # 3. Staff user can access protected endpoints
        staff_client = APIClient()
        staff_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        me_response = staff_client.get("/api/v1/users/me/")
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.data["username"] == "receptionist_john"

        # 4. Manager logs in and deactivates the staff user
        manager_client = APIClient()
        manager_client.force_authenticate(user=manager_user)

        toggle_response = manager_client.post(
            f"/api/v1/users/{staff_user.id}/toggle_active/",
            format="json",
        )
        assert toggle_response.status_code == status.HTTP_200_OK
        assert toggle_response.data["user"]["is_active"] is False

        # Reload from DB
        staff_user.refresh_from_db()
        assert not staff_user.is_active

        # 5. IMMEDIATE LOCKOUT: Access token must be rejected immediately on next API call
        denied_response = staff_client.get("/api/v1/users/me/")
        assert denied_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in str(denied_response.data).lower()

        # 6. REFRESH LOCKOUT: Refresh token must be blacklisted and rejected
        refresh_response = api_client.post(
            "/api/v1/users/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

        # 7. Verify all outstanding tokens for this user are blacklisted
        outstanding_count = OutstandingToken.objects.filter(user=staff_user).count()
        blacklisted_count = BlacklistedToken.objects.filter(token__user=staff_user).count()
        assert outstanding_count > 0
        assert blacklisted_count == outstanding_count

    def test_deactivation_via_user_update_revokes_tokens(self, api_client, manager_user):
        password = "SecurePassword123!"
        staff = User.objects.create_user(
            username="staff_to_deactivate",
            email="staff_update@staycraft.com",
            password=password,
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )

        login_res = api_client.post(
            "/api/v1/users/login/",
            {"username": "staff_to_deactivate", "password": password},
            format="json",
        )
        access_token = login_res.data["access"]
        refresh_token = login_res.data["refresh"]

        # Deactivate via partial update (PATCH)
        manager_client = APIClient()
        manager_client.force_authenticate(user=manager_user)

        patch_res = manager_client.patch(
            f"/api/v1/users/{staff.id}/",
            {"is_active": False},
            format="json",
        )
        assert patch_res.status_code == status.HTTP_200_OK

        # Verify access token is rejected
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_res = client.get("/api/v1/users/me/")
        assert me_res.status_code == status.HTTP_401_UNAUTHORIZED

        # Verify refresh token is blacklisted
        refresh_res = api_client.post(
            "/api/v1/users/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert refresh_res.status_code == status.HTTP_401_UNAUTHORIZED
