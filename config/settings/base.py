"""
Base settings for StayCraft Room Management & Booking Backend.
Contains common settings for development, testing, and production environments.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project: BASE_DIR is the root room_management_backend/ directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment parser
env = environ.Env()

# Read .env file if present
environ.Env.read_env(BASE_DIR / ".env")

# Core Security
SECRET_KEY = env("SECRET_KEY", default="django-insecure-staycraft-room-mgmt-dev-secret-key-change-in-prod")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Application definition
INSTALLED_APPS = [
    # Django core apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # Local Domain Apps
    "apps.users.apps.UsersConfig",
    "apps.core.apps.CoreConfig",
    "apps.rooms.apps.RoomsConfig",
    "apps.guests.apps.GuestsConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.content.apps.ContentConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database Configuration (PostgreSQL by default with SQLite fallback)
# Format: postgresql://user:password@hostname:5432/dbname
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "apps.users.validators.StrongPasswordValidator",
        "OPTIONS": {"min_length": 8},
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static Assets
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media Assets & Cloudflare R2 Cloud Object Storage (S3-Compatible API)
# Optional: If configured, images and proofs are uploaded to Cloudflare R2.
# If omitted or empty, automatically falls back to local disk storage (/media/).
R2_ACCOUNT_ID = env("R2_ACCOUNT_ID", default="")
R2_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID", default="")
R2_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY", default="")
R2_BUCKET_NAME = env("R2_BUCKET_NAME", default="")
R2_PUBLIC_DOMAIN = env("R2_PUBLIC_DOMAIN", default="").strip()

USE_R2_STORAGE = bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME)

if USE_R2_STORAGE:
    if "storages" not in INSTALLED_APPS:
        INSTALLED_APPS.append("storages")

    _r2_endpoint = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    _r2_domain = (
        R2_PUBLIC_DOMAIN.replace("https://", "").replace("http://", "").rstrip("/") if R2_PUBLIC_DOMAIN else None
    )

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "access_key": R2_ACCESS_KEY_ID,
                "secret_key": R2_SECRET_ACCESS_KEY,
                "bucket_name": R2_BUCKET_NAME,
                "endpoint_url": _r2_endpoint,
                "custom_domain": _r2_domain,
                "file_overwrite": False,
                "default_acl": None,
                "signature_version": "s3v4",
                "querystring_auth": False,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    if _r2_domain:
        MEDIA_URL = f"https://{_r2_domain}/"
    else:
        MEDIA_URL = f"https://{R2_BUCKET_NAME}.r2.dev/"
    MEDIA_ROOT = BASE_DIR / "media"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# Database-Backed Caching System (Zero-Redis architecture)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
}

# REST Framework Settings (Zero-Trust Security Baseline)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "500/hour",
        "user": "5000/hour",
        "login": "10/minute",
        "brute_force": "5/minute",
        "sensitive_action": "15/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# OpenAPI / Swagger Specification
SPECTACULAR_SETTINGS = {
    "TITLE": "StayCraft Room Management & Booking System API",
    "DESCRIPTION": "Enterprise API for Hotel/Bedroom Inventory Management, Multi-Role Access Control, Front Desk Operations, Bank Transfer Proof Verification, and Financial Analytics.",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Simple JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS & CSRF Settings
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3007",
        "http://127.0.0.1:3007",
    ],
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3007",
        "http://127.0.0.1:3007",
    ],
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# Email Configuration (Supports Local/Docker Mailpit & Google Gmail SMTP)
# ==============================================================================
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)

# Host support: SMTP_HOST or EMAIL_HOST (default localhost)
EMAIL_HOST = env("SMTP_HOST", default=env("EMAIL_HOST", default="localhost"))

# When running inside Docker container with default localhost, resolve to docker service name 'mailpit'
if EMAIL_HOST == "localhost" and (os.path.exists("/.dockerenv") or env.bool("RUNNING_IN_DOCKER", default=False)):
    EMAIL_HOST = "mailpit"

# Port support: SMTP_PORT or EMAIL_PORT (default 1025 for Mailpit, 587 for Gmail TLS)
EMAIL_PORT = env.int("SMTP_PORT", default=env.int("EMAIL_PORT", default=1025))

# Auth credentials: SMTP_USER / EMAIL_HOST_USER, SMTP_PASS / EMAIL_HOST_PASSWORD
EMAIL_HOST_USER = env("SMTP_USER", default=env("EMAIL_HOST_USER", default=""))
EMAIL_HOST_PASSWORD = env("SMTP_PASS", default=env("EMAIL_HOST_PASSWORD", default=""))

# Auto-enable TLS if port is 587 or EMAIL_USE_TLS is True
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=(EMAIL_PORT == 587))
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=(EMAIL_PORT == 465))

# From address: EMAIL_FROM or DEFAULT_FROM_EMAIL
DEFAULT_FROM_EMAIL = env(
    "EMAIL_FROM",
    default=env("DEFAULT_FROM_EMAIL", default="StayCraft Hotel <noreply@staycraft.com>"),
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
HOTEL_NOTIFICATION_EMAIL = env("HOTEL_NOTIFICATION_EMAIL", default="staff@staycrafthotel.com")

# Frontend URL for email password reset links
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3007")
