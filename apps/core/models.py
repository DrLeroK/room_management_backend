from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    `created_at` and `updated_at` fields.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NotificationType(models.TextChoices):
    BOOKING_SUBMITTED = "BOOKING_SUBMITTED", "Booking Submitted"
    PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED", "Payment Verified"
    PAYMENT_REJECTED = "PAYMENT_REJECTED", "Payment Rejected"
    CHECK_IN = "CHECK_IN", "Guest Check-In"
    CHECK_OUT = "CHECK_OUT", "Guest Check-Out"
    ROOM_STATUS = "ROOM_STATUS", "Room Status Change"
    SYSTEM = "SYSTEM", "System Alert"


class Notification(models.Model):
    """
    In-app notification system supporting user-targeted or role-broadcast notifications.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="Direct user recipient, or null if targeted by role",
    )
    target_role = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text="Role allowed to see this notification (RECEPTIONIST, MANAGER, OWNER, ADMIN), or blank for all staff",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    link = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Target URL/path to navigate to when clicked",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.notification_type}] {self.title} (Read: {self.is_read})"


class AuditAction(models.TextChoices):
    AUTH_LOGIN = "AUTH_LOGIN", "User Login"
    AUTH_LOGOUT = "AUTH_LOGOUT", "User Logout"
    AUTH_FAILED = "AUTH_FAILED", "Failed Login"
    BOOKING_CREATED = "BOOKING_CREATED", "Booking Created"
    BOOKING_CHECK_IN = "BOOKING_CHECK_IN", "Guest Check-In"
    BOOKING_CHECK_OUT = "BOOKING_CHECK_OUT", "Guest Check-Out"
    BOOKING_EXTENDED = "BOOKING_EXTENDED", "Stay Extended"
    BOOKING_CANCELLED = "BOOKING_CANCELLED", "Booking Cancelled"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED", "Payment Verified"
    PAYMENT_REJECTED = "PAYMENT_REJECTED", "Payment Rejected"
    USER_CREATED = "USER_CREATED", "User Created"
    USER_UPDATED = "USER_UPDATED", "User Updated"
    USER_DEACTIVATED = "USER_DEACTIVATED", "User Deactivated"
    ROOM_UPDATED = "ROOM_UPDATED", "Room Updated"
    SETTING_CHANGED = "SETTING_CHANGED", "Setting Changed"


class AuditLog(models.Model):
    """
    Append-only security and operational audit trail.
    Viewable exclusively by Platform Administrators and Hotel Owners.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action, or null if system/anonymous",
    )
    actor_email = models.CharField(max_length=255, blank=True, default="")
    actor_role = models.CharField(max_length=50, blank=True, default="")
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Type of object affected (e.g., Booking, Payment, Room, User, Settings)",
    )
    entity_id = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField()
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} | {self.actor_email or 'System'} | {self.action} on {self.entity_type} {self.entity_id}"
