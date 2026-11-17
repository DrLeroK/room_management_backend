"""
Unit tests for database cache throttling key generation and lockout logic.
"""

import pytest
from rest_framework.test import APIRequestFactory

from apps.core.throttling import BruteForceLockoutThrottle, LoginRateThrottle


@pytest.mark.unit
class TestThrottlingLogic:
    def test_brute_force_cache_key_generation(self):
        factory = APIRequestFactory()
        request = factory.post("/api/v1/users/login/", {"username": "JohnDoe"})
        throttle = BruteForceLockoutThrottle()

        key = throttle.get_cache_key(request, None)
        assert "127.0.0.1" in key
        assert "johndoe" in key

    def test_brute_force_lockout_wait_duration(self):
        throttle = BruteForceLockoutThrottle()
        assert throttle.wait() == 900  # 15 minutes in seconds

    def test_login_rate_throttle_key(self):
        factory = APIRequestFactory()
        request = factory.post("/api/v1/users/login/", {"username": "JohnDoe"})
        throttle = LoginRateThrottle()

        key = throttle.get_cache_key(request, None)
        assert "throttle_login_127.0.0.1" in key
