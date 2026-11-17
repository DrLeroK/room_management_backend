import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def send_payment_verification_sms(booking, payment):
    """
    Simulates sending an SMS text message to the guest's phone number upon payment approval.
    Details include:
    - Guest name
    - Verified payment amount
    - Booking reference code
    - Assigned bedroom number and room type
    - Check-in & check-out dates
    """
    guest = booking.guest
    room = booking.room
    phone_number = guest.phone_number

    message = (
        f"Hello {guest.full_name}, your bank transfer payment of ${payment.amount:.2f} "
        f"for Booking {booking.booking_reference} has been VERIFIED! "
        f"Your Bedroom #{room.room_number} ({room.room_type.name}) is reserved for stay from "
        f"{booking.check_in_date.strftime('%b %d, %Y')} to {booking.check_out_date.strftime('%b %d, %Y')}. "
        f"Thank you for choosing StayCraft Hotel!"
    )

    logger.info(f"[SMS DISPATCH] To: {phone_number} | Message: {message}")

    return {
        "status": "SENT",
        "recipient": phone_number,
        "recipient_name": guest.full_name,
        "booking_reference": booking.booking_reference,
        "room_number": room.room_number,
        "amount_verified": float(payment.amount),
        "message": message,
        "sent_at": timezone.now().isoformat(),
    }


def send_payment_rejection_sms(booking, payment, reason=""):
    """
    Simulates sending an SMS text message notifying the guest of payment proof rejection.
    """
    guest = booking.guest
    phone_number = guest.phone_number

    reason_str = f" Reason: {reason}" if reason else ""
    message = (
        f"Dear {guest.full_name}, your payment screenshot for Booking {booking.booking_reference} "
        f"could not be verified.{reason_str} Please contact hotel reception or re-submit valid payment proof."
    )

    logger.info(f"[SMS REJECTION NOTICE] To: {phone_number} | Message: {message}")

    return {
        "status": "REJECTED_NOTICE_SENT",
        "recipient": phone_number,
        "recipient_name": guest.full_name,
        "booking_reference": booking.booking_reference,
        "message": message,
        "sent_at": timezone.now().isoformat(),
    }
