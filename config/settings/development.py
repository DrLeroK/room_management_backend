"""
Development settings for StayCraft Backend.
"""

from .base import *

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# Log SQL queries if needed during local debugging
if env.bool("DJANGO_LOG_SQL", default=False):
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "django.db.backends": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
        },
    }

# Development email backend (defaults to SMTP/Mailpit configured in base.py; allows console override)
EMAIL_BACKEND = env("EMAIL_BACKEND", default=EMAIL_BACKEND)
