import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import UserRole
from apps.users.serializers import LogoutSerializer
from apps.users.services import terminate_user_sessions_and_tokens

User = get_user_model()


@pytest.mark.django_db
class TestTokenSecurityUnit:
    def test_logout_serializer_valid_payload(self):
        serializer = LogoutSerializer(data={"refresh": "dummy-refresh-token-string"})
        assert serializer.is_valid()
        assert serializer.validated_data["refresh"] == "dummy-refresh-token-string"

    def test_logout_serializer_missing_refresh(self):
        serializer = LogoutSerializer(data={})
        assert not serializer.is_valid()
        assert "refresh" in serializer.errors

    def test_terminate_user_sessions_and_tokens_blacklists_all_tokens(self, db):
        user = User.objects.create_user(
            username="security_user",
            email="security@staycraft.com",
            password="StrongPassword123!",
            role=UserRole.RECEPTIONIST,
        )

        token1 = RefreshToken.for_user(user)
        token2 = RefreshToken.for_user(user)
        str(token1)
        str(token2)

        outstanding = OutstandingToken.objects.filter(user=user)
        assert outstanding.count() >= 2

        revoked_count = terminate_user_sessions_and_tokens(user)
        assert revoked_count >= 2

        blacklisted = BlacklistedToken.objects.filter(token__user=user)
        assert blacklisted.count() == outstanding.count()

    def test_terminate_user_sessions_and_tokens_flushes_django_sessions(self, db):
        user = User.objects.create_user(
            username="session_user",
            email="session_user@staycraft.com",
            password="StrongPassword123!",
            role=UserRole.RECEPTIONIST,
        )

        # Create simulated Django session
        s = SessionStore()
        s["_auth_user_id"] = str(user.pk)
        s["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        s.save()
        session_key = s.session_key

        assert Session.objects.filter(session_key=session_key).exists()

        terminate_user_sessions_and_tokens(user)

        assert not Session.objects.filter(session_key=session_key).exists()
