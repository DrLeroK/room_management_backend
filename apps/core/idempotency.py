import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

IDEMPOTENCY_CACHE_PREFIX = "idemp_"
IDEMPOTENCY_TIMEOUT_SECONDS = 86400  # 24 hours


def get_idempotency_key(request):
    """Extracts idempotency key from HTTP headers."""
    return request.headers.get("X-Idempotency-Key") or request.META.get("HTTP_X_IDEMPOTENCY_KEY")


def get_cached_idempotency_response(idempotency_key):
    """Retrieves cached response if the idempotency key was previously processed."""
    if not idempotency_key:
        return None
    cache_key = f"{IDEMPOTENCY_CACHE_PREFIX}{idempotency_key}"
    return cache.get(cache_key)


def set_cached_idempotency_response(idempotency_key, response_data, status_code):
    """Caches response for an idempotency key for 24 hours."""
    if not idempotency_key:
        return
    cache_key = f"{IDEMPOTENCY_CACHE_PREFIX}{idempotency_key}"
    cache.set(
        cache_key,
        {"data": response_data, "status_code": status_code},
        timeout=IDEMPOTENCY_TIMEOUT_SECONDS,
    )
    logger.info(f"[IDEMPOTENCY] Cached response for key: {idempotency_key}")
