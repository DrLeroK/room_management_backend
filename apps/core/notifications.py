import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_online_booking_submitted_email(booking, payment=None):
    """
    Dispatched when a guest submits an online booking with payment proof:
    1. Alert email sent to Hotel Staff / Reception with booking details & verification CTA.
    2. Acknowledgment email sent to Guest (if email provided) confirming receipt of proof.
    """
    guest = booking.guest
    room = booking.room
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@staycrafthotel.com")
    staff_notification_email = getattr(
        settings, "HOTEL_NOTIFICATION_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "staff@staycrafthotel.com")
    )

    proof_info = "Screenshot Attached" if (payment and payment.payment_proof) else "No file uploaded"
    tx_ref = payment.transaction_reference if payment else "N/A"

    # 1. Staff Notification Email
    staff_subject = (
        f"🔔 [NEW ONLINE BOOKING] #{booking.booking_reference} - {guest.full_name} (Payment Proof Submitted)"
    )
    staff_message = (
        f"A new online reservation with payment proof has been submitted!\n\n"
        f"--- RESERVATION DETAILS ---\n"
        f"Booking Reference : {booking.booking_reference}\n"
        f"Guest Name        : {guest.full_name}\n"
        f"Guest Phone       : {guest.phone_number}\n"
        f"Guest Email       : {guest.email or 'Not provided'}\n"
        f"Room Assigned     : Room {room.room_number} ({room.room_type.name})\n"
        f"Stay Dates        : {booking.check_in_date} to {booking.check_out_date} ({booking.total_nights} nights)\n"
        f"Total Amount      : {booking.total_amount:.2f} ETB\n"
        f"Tx Reference      : {tx_ref}\n"
        f"Payment Proof     : {proof_info}\n\n"
        f"Please log in to the Reception Dashboard to review and verify this transaction.\n\n"
        f"StayCraft Hotel Management System"
    )

    try:
        send_mail(
            subject=staff_subject,
            message=staff_message,
            from_email=from_email,
            recipient_list=[staff_notification_email],
            fail_silently=False,
        )
        logger.info(f"[NOTIFICATION] Staff alert email dispatched for booking {booking.booking_reference}")
    except Exception as e:
        logger.error(f"[NOTIFICATION ERROR] Failed to send staff alert email: {e}")

    # 2. Guest Acknowledgment Email
    if guest.email:
        guest_subject = f"StayCraft Hotel - We Received Your Booking Request (#{booking.booking_reference})"
        guest_message = (
            f"Dear {guest.full_name},\n\n"
            f"Thank you for choosing StayCraft Hotel! We have successfully received your booking request and payment transfer details.\n\n"
            f"--- RESERVATION SUMMARY ---\n"
            f"Booking Reference : {booking.booking_reference}\n"
            f"Room              : Room {room.room_number} ({room.room_type.name})\n"
            f"Check-In Date     : {booking.check_in_date}\n"
            f"Check-Out Date    : {booking.check_out_date}\n"
            f"Total Amount      : {booking.total_amount:.2f} ETB\n"
            f"Status            : Pending Staff Verification\n\n"
            f"Our front desk staff is reviewing your payment transfer proof. Once approved, you will receive a formal confirmation.\n"
            f"You can also check the status of your reservation at any time using your phone number ({guest.phone_number}) on our website.\n\n"
            f"Warm regards,\n"
            f"StayCraft Hotel Front Desk"
        )

        try:
            send_mail(
                subject=guest_subject,
                message=guest_message,
                from_email=from_email,
                recipient_list=[guest.email],
                fail_silently=False,
            )
            logger.info(f"[NOTIFICATION] Guest acknowledgment email dispatched to {guest.email}")
        except Exception as e:
            logger.error(f"[NOTIFICATION ERROR] Failed to send guest email: {e}")


def send_payment_verification_email(booking, payment):
    """
    Dispatched when a staff member approves an online booking payment proof.
    """
    guest = booking.guest
    if not guest.email:
        return

    room = booking.room
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@staycrafthotel.com")
    subject = f"✅ StayCraft Hotel - Booking Confirmed! (#{booking.booking_reference})"
    message = (
        f"Dear {guest.full_name},\n\n"
        f"Great news! Your payment of {payment.amount:.2f} ETB for Booking #{booking.booking_reference} has been verified and confirmed.\n\n"
        f"--- CONFIRMED RESERVATION ---\n"
        f"Room          : Room {room.room_number} ({room.room_type.name})\n"
        f"Check-In Date : {booking.check_in_date} (Check-in from 14:00)\n"
        f"Check-Out Date: {booking.check_out_date} (Check-out by 11:00)\n"
        f"Total Paid    : {payment.amount:.2f} ETB\n\n"
        f"We look forward to welcoming you to StayCraft Hotel!\n\n"
        f"Warm regards,\n"
        f"StayCraft Hotel Management"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[guest.email],
            fail_silently=False,
        )
        logger.info(f"[NOTIFICATION] Payment approval email sent to {guest.email}")
    except Exception as e:
        logger.error(f"[NOTIFICATION ERROR] Failed to send payment approval email: {e}")


def send_payment_rejection_email(booking, payment, reason=""):
    """
    Dispatched when a staff member rejects an online booking payment proof.
    """
    guest = booking.guest
    if not guest.email:
        return

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@staycrafthotel.com")
    reason_text = f"\nReason: {reason}\n" if reason else ""
    subject = f"⚠️ StayCraft Hotel - Update Regarding Booking #{booking.booking_reference}"
    message = (
        f"Dear {guest.full_name},\n\n"
        f"We are contacting you regarding your reservation #{booking.booking_reference}.\n"
        f"Unfortunately, our reception team could not verify your uploaded payment proof.{reason_text}\n"
        f"Please contact hotel reception directly or submit a valid payment screenshot on our website to secure your room.\n\n"
        f"Warm regards,\n"
        f"StayCraft Hotel Front Desk"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[guest.email],
            fail_silently=False,
        )
        logger.info(f"[NOTIFICATION] Payment rejection email sent to {guest.email}")
    except Exception as e:
        logger.error(f"[NOTIFICATION ERROR] Failed to send payment rejection email: {e}")


def create_in_app_notification(
    title,
    message,
    notification_type="SYSTEM",
    target_role="",
    recipient=None,
    link="",
):
    """
    Creates an in-app notification for a specific user or role broadcast.
    """
    try:
        from apps.core.models import Notification

        return Notification.objects.create(
            recipient=recipient,
            target_role=target_role,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )
    except Exception as exc:
        logger.error(f"[NOTIFICATION ERROR] Failed to create in-app notification: {exc}")
        return None
