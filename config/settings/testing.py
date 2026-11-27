"""
Testing settings for StayCraft Backend.
Optimized for high-speed automated unit, integration, and E2E test runs.
"""

from .base import *

DEBUG = False

SECRET_KEY = "test-secret-key-staycraft-test-suite"

# Use fast password hasher for test execution speed
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use Database Cache for rate limiting tests if table created, or LocMemCache fallback
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake-test",
    }
}

# In-memory email backend for inspecting outbound confirmation emails
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Fast in-memory storage for test uploads without remote S3/R2 network calls
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
