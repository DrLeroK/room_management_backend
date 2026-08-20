from rest_framework.throttling import SimpleRateThrottle, AnonRateThrottle
from django.core.cache import cache

class LoginRateThrottle(SimpleRateThrottle):
    """
    Limits total login attempts per client IP address (10 per minute).
    """
    scope = 'login'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        ident = self.get_ident(request)
        return f"throttle_login_{ident}"


class BruteForceLockoutThrottle(SimpleRateThrottle):
    """
    Database-backed Brute-Force Lockout Protection (No Redis required).
    Tracks failed login attempts per (IP + Username).
    Locks out account for 15 minutes after 5 consecutive failed attempts.
    """
    scope = 'brute_force'
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        username = request.data.get('username', '').strip().lower() if hasattr(request, 'data') else ''
        return f"brute_force_attempts_{ident}_{username}"

    def allow_request(self, request, view):
        self.key = self.get_cache_key(request, view)
        if not self.key:
            return True

        failed_count = cache.get(self.key, 0)
        self.history = failed_count
        if failed_count >= self.MAX_FAILED_ATTEMPTS:
            return False
        return True

    def wait(self):
        return self.LOCKOUT_DURATION_SECONDS

    @classmethod
    def record_failed_login(cls, request, username):
        """
        Increments failed login counter in DB cache and sets 15-min TTL.
        """
        ident = cls().get_ident(request)
        username_clean = (username or '').strip().lower()
        key = f"brute_force_attempts_{ident}_{username_clean}"

        current_count = cache.get(key, 0) + 1
        cache.set(key, current_count, cls.LOCKOUT_DURATION_SECONDS)
        return current_count

    @classmethod
    def reset_failed_login(cls, request, username):
        """
        Resets failed login counter upon successful authentication.
        """
        ident = cls().get_ident(request)
        username_clean = (username or '').strip().lower()
        key = f"brute_force_attempts_{ident}_{username_clean}"
        cache.delete(key)


class SensitiveActionRateThrottle(AnonRateThrottle):
    """
    Limits sensitive actions like public booking submissions and contact form inquiries.
    """
    scope = 'sensitive_action'
