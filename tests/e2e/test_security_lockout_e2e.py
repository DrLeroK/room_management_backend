"""
End-to-End (E2E) Security Flow: Brute-Force Lockout Defense.
Simulates authentication attack and verifies 429 Too Many Requests response after 5 failed attempts.
"""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status


@pytest.mark.e2e
class TestSecurityLockoutE2E:
    def test_brute_force_lockout_on_fifth_failed_login(self, api_client, receptionist_user):
        login_url = reverse("token_obtain_pair")
        cache.clear()

        # Submit 4 incorrect password attempts -> 401 Unauthorized
        for i in range(1, 5):
            res = api_client.post(
                login_url, {"username": receptionist_user.username, "password": f"wrong_pass_{i}"}, format="json"
            )
            assert res.status_code == status.HTTP_401_UNAUTHORIZED

        # 5th attempt must trigger 429 Too Many Requests lockout
        res_5th = api_client.post(
            login_url, {"username": receptionist_user.username, "password": "wrong_pass_5"}, format="json"
        )
        assert res_5th.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "temporarily locked" in res_5th.data["detail"].lower()
