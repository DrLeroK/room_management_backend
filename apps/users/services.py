import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)
User = get_user_model()


def send_password_reset_email(user, frontend_url=None):
    """
    Generates a secure, cryptographically signed one-time token
    and sends a password reset email to the user.
    """
    token = default_token_generator.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

    base_url = frontend_url or getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{base_url.rstrip('/')}/reset-password?uid={uidb64}&token={token}"

    subject = "StayCraft Hotel - Password Reset Request"
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"We received a request to reset your password for your StayCraft Hotel staff account.\n\n"
        f"Please click the link below to set a new password:\n"
        f"{reset_url}\n\n"
        f"If you did not request a password reset, please ignore this email or contact hotel administration.\n\n"
        f"Best regards,\n"
        f"StayCraft Hotel Management System"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@staycrafthotel.com")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"[PASSWORD RESET] Reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"[PASSWORD RESET ERROR] Failed to send email to {user.email}: {e}")
        return False


def verify_and_reset_password(uidb64, token, new_password):
    """
    Decodes the user ID, verifies the one-time token, validates the strong password,
    and updates the user's password.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise ValidationError({"detail": "Invalid password reset link or user does not exist."})

    if not default_token_generator.check_token(user, token):
        raise ValidationError({"detail": "The password reset token is invalid or has expired."})

    # Validate strong password rules
    validate_password(new_password, user=user)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    logger.info(f"[PASSWORD RESET SUCCESS] Password reset completed for user {user.username}")
    return user


def terminate_user_sessions_and_tokens(user):
    """
    Terminates all active sessions and blacklists all outstanding tokens
    for the specified user (e.g., upon deactivation or security compromise).
    """
    revoked_count = 0
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        outstanding_tokens = OutstandingToken.objects.filter(user=user)
        for token in outstanding_tokens:
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            if created:
                revoked_count += 1
        logger.info(
            f"[SESSION TERMINATION] Blacklisted {revoked_count} outstanding tokens for user {user.username} (ID: {user.pk})."
        )
    except Exception as e:
        logger.error(
            f"[SESSION TERMINATION ERROR] Failed to blacklist tokens for user {user.username}: {e}"
        )

    # Flush Django sessions (if any active sessions exist in the session store)
    try:
        from django.contrib.sessions.models import Session

        sessions_deleted = 0
        user_id_str = str(user.pk)
        for session in Session.objects.all():
            try:
                data = session.get_decoded()
                if data.get("_auth_user_id") == user_id_str:
                    session.delete()
                    sessions_deleted += 1
            except Exception:
                continue
        if sessions_deleted:
            logger.info(
                f"[SESSION TERMINATION] Deleted {sessions_deleted} active Django sessions for user {user.username}."
            )
    except Exception as e:
        logger.error(
            f"[SESSION TERMINATION ERROR] Failed to clear Django sessions for user {user.username}: {e}"
        )

    return revoked_count
