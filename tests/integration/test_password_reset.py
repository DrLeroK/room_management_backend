import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status

from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
def test_password_reset_request_and_confirm_flow(api_client):
    # 1. Create a user
    user = User.objects.create_user(
        username="reset_user",
        email="reset_user@staycraft.com",
        password="Initial@Password2026!",
        role=UserRole.RECEPTIONIST,
    )

    # 2. Request password reset
    reset_request_url = reverse("password_reset_request")
    res = api_client.post(reset_request_url, {"email": "reset_user@staycraft.com"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1
    assert "Password Reset Request" in mail.outbox[0].subject

    # 3. Confirm password reset with valid token and new strong password
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    confirm_url = reverse("password_reset_confirm")
    confirm_res = api_client.post(
        confirm_url,
        {
            "uid": uid,
            "token": token,
            "new_password": "NewStrong@Password2026!",
            "new_password_confirm": "NewStrong@Password2026!",
        },
        format="json",
    )
    assert confirm_res.status_code == status.HTTP_200_OK

    # Verify user can login with new password
    user.refresh_from_db()
    assert user.check_password("NewStrong@Password2026!")


@pytest.mark.django_db
def test_password_reset_weak_password_rejected(api_client):
    user = User.objects.create_user(
        username="weak_user",
        email="weak_user@staycraft.com",
        password="Initial@Password2026!",
        role=UserRole.RECEPTIONIST,
    )

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    confirm_url = reverse("password_reset_confirm")
    # Weak password without special char or uppercase
    confirm_res = api_client.post(
        confirm_url,
        {"uid": uid, "token": token, "new_password": "weakpassword123", "new_password_confirm": "weakpassword123"},
        format="json",
    )
    assert confirm_res.status_code == status.HTTP_400_BAD_REQUEST
