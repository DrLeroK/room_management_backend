from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User, UserRole


class BruteForceLockoutTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="test_user", password="StrongPass2026!", email="test@example.com", role=UserRole.RECEPTIONIST
        )

    def test_brute_force_lockout_after_5_failed_attempts(self):
        url = reverse("token_obtain_pair")

        # 1 to 4 failed login attempts
        for attempt in range(1, 5):
            response = self.client.post(url, {"username": "test_user", "password": "WrongPassword123!"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn("remaining", response.data["detail"])

        # 5th failed login attempt -> Triggers lockout
        response5 = self.client.post(url, {"username": "test_user", "password": "WrongPassword123!"}, format="json")
        self.assertEqual(response5.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("locked", response5.data["detail"])

        # Subsequent attempt with CORRECT password is also blocked due to active 15-minute lockout
        blocked_response = self.client.post(
            url, {"username": "test_user", "password": "StrongPass2026!"}, format="json"
        )
        self.assertEqual(blocked_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_successful_login_resets_failed_counter(self):
        url = reverse("token_obtain_pair")

        # 2 failed attempts
        self.client.post(url, {"username": "test_user", "password": "WrongPassword!"}, format="json")
        self.client.post(url, {"username": "test_user", "password": "WrongPassword!"}, format="json")

        # Successful login
        success_response = self.client.post(
            url, {"username": "test_user", "password": "StrongPass2026!"}, format="json"
        )
        self.assertEqual(success_response.status_code, status.HTTP_200_OK)

        # Counter should be reset; single failed attempt should now report 4 attempts remaining
        fail_response = self.client.post(url, {"username": "test_user", "password": "WrongPassword!"}, format="json")
        self.assertEqual(fail_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("4 attempt(s) remaining", fail_response.data["detail"])
