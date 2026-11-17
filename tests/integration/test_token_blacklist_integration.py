import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestTokenBlacklistIntegration:
    def test_logout_endpoint_blacklists_refresh_token(self, api_client):
        user = User.objects.create_user(
            username="logout_user",
            email="logout@staycraft.com",
            password="StrongPassword123!",
            role=UserRole.RECEPTIONIST,
        )

        refresh = RefreshToken.for_user(user)
        refresh_str = str(refresh)

        # Confirm token is initially outstanding and not blacklisted
        outstanding = OutstandingToken.objects.get(token=refresh_str)
        assert not BlacklistedToken.objects.filter(token=outstanding).exists()

        response = api_client.post(
            "/api/v1/users/logout/",
            {"refresh": refresh_str},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "revoked" in response.data["message"].lower()
        assert BlacklistedToken.objects.filter(token=outstanding).exists()

    def test_blacklisted_token_cannot_be_used_for_refresh(self, api_client):
        user = User.objects.create_user(
            username="refresh_user",
            email="refresh@staycraft.com",
            password="StrongPassword123!",
            role=UserRole.RECEPTIONIST,
        )

        refresh = RefreshToken.for_user(user)
        refresh_str = str(refresh)

        # Logout to blacklist
        api_client.post("/api/v1/users/logout/", {"refresh": refresh_str}, format="json")

        # Attempt to refresh
        refresh_response = api_client.post(
            "/api/v1/users/token/refresh/",
            {"refresh": refresh_str},
            format="json",
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "token_not_valid" in str(refresh_response.data)

    def test_token_rotation_blacklists_previous_refresh_token(self, api_client):
        user = User.objects.create_user(
            username="rotation_user",
            email="rotation@staycraft.com",
            password="StrongPassword123!",
            role=UserRole.RECEPTIONIST,
        )

        refresh = RefreshToken.for_user(user)
        initial_refresh_str = str(refresh)

        # Perform token refresh
        response = api_client.post(
            "/api/v1/users/token/refresh/",
            {"refresh": initial_refresh_str},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        new_refresh_str = response.data.get("refresh")
        assert new_refresh_str is not None
        assert new_refresh_str != initial_refresh_str

        # The old refresh token must now be blacklisted
        initial_outstanding = OutstandingToken.objects.get(token=initial_refresh_str)
        assert BlacklistedToken.objects.filter(token=initial_outstanding).exists()

        # Re-attempting to refresh using old token must fail
        reuse_response = api_client.post(
            "/api/v1/users/token/refresh/",
            {"refresh": initial_refresh_str},
            format="json",
        )
        assert reuse_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_invalid_or_already_blacklisted_token_returns_400(self, api_client):
        response = api_client.post(
            "/api/v1/users/logout/",
            {"refresh": "completely-invalid-malformed-token"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data
