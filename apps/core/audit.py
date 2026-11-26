import logging

from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def record_audit_log(
    action,
    entity_type,
    description,
    entity_id="",
    actor=None,
    request=None,
    changes=None,
):
    """
    Safely creates an AuditLog record. Does not raise exceptions to callers if logging fails.
    """
    try:
        ip_address = get_client_ip(request) if request else None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""

        actor_user = actor
        if not actor_user and request and hasattr(request, "user") and request.user.is_authenticated:
            actor_user = request.user

        actor_email = ""
        actor_role = ""
        if actor_user:
            actor_email = getattr(actor_user, "email", "") or getattr(actor_user, "username", "")
            actor_role = getattr(actor_user, "role", "")
        else:
            actor_email = "System / Guest"
            actor_role = "SYSTEM"

        return AuditLog.objects.create(
            actor=actor_user if (actor_user and hasattr(actor_user, "pk") and actor_user.pk) else None,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            description=description,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as exc:
        logger.error(f"[AUDIT LOG ERROR] Failed to record audit log {action} on {entity_type}: {exc}")
        return None
