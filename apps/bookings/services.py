from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.models import (
    Booking,
    BookingSource,
    BookingStatus,
    CheckInRecord,
    CheckOutRecord,
    PaymentMethod,
)
from apps.bookings.sms_service import (
    send_payment_rejection_sms,
    send_payment_verification_sms,
)
from apps.core.exceptions import ConflictError
from apps.core.notifications import (
    send_online_booking_submitted_email,
    send_payment_rejection_email,
    send_payment_verification_email,
)
from apps.guests.models import Guest
from apps.payments.models import Payment, PaymentStatus, PaymentType
from apps.rooms.models import Room, RoomStatus


def check_room_availability(room_id, check_in_date, check_out_date, exclude_booking_id=None):
    """
    Checks if a room is available for requested stay window.
    Occupied or reserved statuses include CONFIRMED, CHECKED_IN, and PENDING_PAYMENT_VERIFICATION.
    """
    try:
        room = Room.objects.get(id=room_id, is_active=True)
    except Room.DoesNotExist:
        return False

    if room.status == RoomStatus.MAINTENANCE:
        return False

    overlapping_query = Booking.objects.filter(
        room_id=room_id,
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.PENDING_PAYMENT_VERIFICATION],
        check_in_date__lt=check_out_date,
        check_out_date__gt=check_in_date,
    )

    if exclude_booking_id:
        overlapping_query = overlapping_query.exclude(id=exclude_booking_id)

    return not overlapping_query.exists()


def find_available_rooms(check_in_date, check_out_date, guests_count=1, room_type_id=None, is_online_search=False):
    """
    Returns available rooms matching stay dates and capacity.
    Enforces The Last-Room Rule:
    If is_online_search=True, closes online sales when total available rooms <= 2
    or when overall hotel occupancy reaches 98%, reserving the final rooms strictly for Front Desk walk-ins.
    """
    unavailable_room_ids = Booking.objects.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.PENDING_PAYMENT_VERIFICATION],
        check_in_date__lt=check_out_date,
        check_out_date__gt=check_in_date,
    ).values_list("room_id", flat=True)

    queryset = (
        Room.objects.filter(is_active=True, room_type__max_occupancy__gte=guests_count)
        .exclude(status=RoomStatus.MAINTENANCE)
        .exclude(id__in=unavailable_room_ids)
        .select_related("room_type")
        .prefetch_related("amenities")
    )

    if room_type_id:
        queryset = queryset.filter(room_type_id=room_type_id)

    if is_online_search:
        total_active_rooms = Room.objects.filter(is_active=True).exclude(status=RoomStatus.MAINTENANCE).count()
        total_available_overall = (
            Room.objects.filter(is_active=True)
            .exclude(status=RoomStatus.MAINTENANCE)
            .exclude(id__in=unavailable_room_ids)
            .count()
        )

        is_occupancy_98 = (
            total_active_rooms > 0 and ((total_active_rooms - total_available_overall) / total_active_rooms) >= 0.98
        )
        if total_available_overall <= 2 or is_occupancy_98:
            return Room.objects.none()

    return queryset


def get_or_create_guest(guest_data):
    """
    Finds guest by phone number or creates a new guest record.
    """
    phone = guest_data.get("phone_number", "").strip()
    if not phone:
        raise ValidationError({"phone_number": "Phone number is required."})

    guest, created = Guest.objects.get_or_create(
        phone_number=phone,
        defaults={
            "first_name": guest_data.get("first_name", "Guest"),
            "last_name": guest_data.get("last_name", ""),
            "email": guest_data.get("email", ""),
            "identification_type": guest_data.get("identification_type", "NATIONAL_ID"),
            "identification_number": guest_data.get("identification_number", ""),
            "address": guest_data.get("address", ""),
            "notes": guest_data.get("notes", ""),
        },
    )

    if not created and ("first_name" in guest_data or "email" in guest_data):
        if guest_data.get("first_name"):
            guest.first_name = guest_data["first_name"]
        if guest_data.get("last_name"):
            guest.last_name = guest_data["last_name"]
        if guest_data.get("email"):
            guest.email = guest_data["email"]
        if guest_data.get("identification_number"):
            guest.identification_number = guest_data["identification_number"]
        guest.save()

    return guest


def create_online_booking(
    guest_data,
    room_id,
    check_in_date,
    check_out_date,
    payment_proof=None,
    transaction_reference="",
    adults_count=1,
    children_count=0,
    special_requests="",
):
    """
    Creates an online booking for a guest after checking real-time availability.
    If bank transfer screenshot / transaction reference is uploaded, booking status is set to
    PENDING_PAYMENT_VERIFICATION and a Payment record is created for staff verification.
    """
    with transaction.atomic():
        room = Room.objects.select_for_update().get(id=room_id, is_active=True)

        if not check_room_availability(room.id, check_in_date, check_out_date):
            raise ValidationError(
                f"Room {room.room_number} is not available for selected dates ({check_in_date} to {check_out_date})."
            )

        # Enforce The Last-Room Rule: close online bookings when total available <= 2 or occupancy >= 98%
        unavailable_room_ids = Booking.objects.filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.PENDING_PAYMENT_VERIFICATION],
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date,
        ).values_list("room_id", flat=True)

        total_active_rooms = Room.objects.filter(is_active=True).exclude(status=RoomStatus.MAINTENANCE).count()
        total_available = (
            Room.objects.filter(is_active=True)
            .exclude(status=RoomStatus.MAINTENANCE)
            .exclude(id__in=unavailable_room_ids)
            .count()
        )

        is_occupancy_98 = (
            total_active_rooms > 0 and ((total_active_rooms - total_available) / total_active_rooms) >= 0.98
        )

        if total_available <= 2 or is_occupancy_98:
            raise ValidationError(
                {
                    "detail": "Online bookings are closed for the last remaining rooms. Please contact our front desk directly to reserve."
                }
            )

        guest = get_or_create_guest(guest_data)

        nightly_rate = room.effective_price_per_night
        delta_days = (check_out_date - check_in_date).days
        total_nights = delta_days if delta_days > 0 else 1
        total_amount = nightly_rate * total_nights

        booking_status = (
            BookingStatus.PENDING_PAYMENT_VERIFICATION
            if (payment_proof or transaction_reference)
            else BookingStatus.CONFIRMED
        )

        booking = Booking.objects.create(
            guest=guest,
            room=room,
            booking_source=BookingSource.ONLINE,
            status=booking_status,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults_count=adults_count,
            children_count=children_count,
            nightly_rate=nightly_rate,
            total_amount=total_amount,
            special_requests=special_requests,
        )

        payment = None
        if payment_proof or transaction_reference:
            payment = Payment.objects.create(
                booking=booking,
                amount=total_amount,
                payment_type=PaymentType.ONLINE_PREPAYMENT,
                payment_method=PaymentMethod.ONLINE_TRANSFER,
                status=PaymentStatus.PENDING_VERIFICATION,
                payment_proof=payment_proof,
                transaction_reference=transaction_reference,
                recorded_by="Online Guest",
                notes="Bank transfer screenshot uploaded. Pending staff verification.",
            )

        # Dispatch automated email notifications to hotel staff and confirmation receipt to guest
        send_online_booking_submitted_email(booking, payment)

        return booking


def verify_online_payment(payment_id, action, receptionist_name="Receptionist", notes=""):
    """
    Staff / Receptionist endpoint service to verify uploaded bank transfer screenshot:
    - APPROVE: Updates Payment to SUCCESS, Booking to CONFIRMED, and sends SMS & Email confirmation to guest phone/email.
    - REJECT: Updates Payment to FAILED, Booking to CANCELLED, frees room, and sends SMS & Email rejection notice to guest phone/email.
    """
    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("booking", "booking__guest", "booking__room", "booking__room__room_type")
            .get(id=payment_id)
        )
        booking = payment.booking

        action = action.upper()
        if action not in ["APPROVE", "REJECT"]:
            raise ValidationError({"action": "Action must be either APPROVE or REJECT."})

        if action == "APPROVE":
            payment.status = PaymentStatus.SUCCESS
            payment.verified_at = timezone.now()
            payment.verified_by = receptionist_name
            payment.verification_notes = notes
            payment.save()

            booking.status = BookingStatus.CONFIRMED
            booking.save(update_fields=["status", "updated_at"])

            sms_info = send_payment_verification_sms(booking, payment)
            send_payment_verification_email(booking, payment)

            return {
                "message": "Payment approved successfully. Confirmation notifications sent to guest.",
                "action": "APPROVED",
                "booking": booking,
                "payment": payment,
                "sms_info": sms_info,
            }
        else:
            payment.status = PaymentStatus.FAILED
            payment.verified_at = timezone.now()
            payment.verified_by = receptionist_name
            payment.verification_notes = notes
            payment.save()

            booking.status = BookingStatus.CANCELLED
            booking.save(update_fields=["status", "updated_at"])

            # Immediately release room back to available inventory
            if booking.room and booking.room.status == RoomStatus.OCCUPIED:
                booking.room.status = RoomStatus.AVAILABLE
                booking.room.save(update_fields=["status", "updated_at"])

            sms_info = send_payment_rejection_sms(booking, payment, reason=notes)
            send_payment_rejection_email(booking, payment, reason=notes)

            return {
                "message": "Payment rejected and booking unverified. Room has been released back to available inventory.",
                "action": "REJECTED",
                "booking": booking,
                "payment": payment,
                "sms_info": sms_info,
            }


def process_walk_in_checkin(
    guest_data,
    room_id,
    check_in_date,
    check_out_date,
    money_received,
    payment_method,
    deposit_amount=0,
    receptionist_name="Receptionist",
    key_card_number="",
    notes="",
):
    """
    Performs immediate walk-in receptionist check-in:
    - Atomically checks room availability
    - Creates Guest record
    - Creates Booking with status CHECKED_IN
    - Creates CheckInRecord & Payment transactions
    - Updates Room status to OCCUPIED
    """
    with transaction.atomic():
        room = Room.objects.select_for_update().get(id=room_id, is_active=True)

        if not check_room_availability(room.id, check_in_date, check_out_date):
            raise ConflictError(
                f"Conflict: Room {room.room_number} is unavailable for requested stay dates (already reserved or occupied)."
            )

        guest = get_or_create_guest(guest_data)

        nightly_rate = room.effective_price_per_night
        delta_days = (check_out_date - check_in_date).days
        total_nights = delta_days if delta_days > 0 else 1
        total_amount = nightly_rate * total_nights

        booking = Booking.objects.create(
            guest=guest,
            room=room,
            booking_source=BookingSource.WALK_IN,
            status=BookingStatus.CHECKED_IN,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            nightly_rate=nightly_rate,
            total_amount=total_amount,
        )

        CheckInRecord.objects.create(
            booking=booking,
            receptionist_name=receptionist_name,
            money_received=money_received,
            deposit_amount=deposit_amount,
            payment_method=payment_method,
            key_card_number=key_card_number,
            notes=notes,
        )

        room.status = RoomStatus.OCCUPIED
        room.save(update_fields=["status", "updated_at"])

        if money_received > 0:
            Payment.objects.create(
                booking=booking,
                amount=money_received,
                payment_type=PaymentType.CHECKIN_PAYMENT,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Walk-in check-in payment for {booking.booking_reference}",
            )

        if deposit_amount > 0:
            Payment.objects.create(
                booking=booking,
                amount=deposit_amount,
                payment_type=PaymentType.DEPOSIT,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Security deposit received for {booking.booking_reference}",
            )

        return booking


def process_booking_checkin(
    booking_id,
    money_received,
    payment_method,
    deposit_amount=0,
    receptionist_name="Receptionist",
    key_card_number="",
    notes="",
):
    """
    Check-in an existing online/phone reservation (CONFIRMED booking).
    """
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(id=booking_id)

        if booking.status != BookingStatus.CONFIRMED:
            raise ValidationError(
                f"Booking {booking.booking_reference} cannot be checked in because current status is '{booking.status}'."
            )

        booking.status = BookingStatus.CHECKED_IN
        booking.save(update_fields=["status", "updated_at"])

        room = booking.room
        room.status = RoomStatus.OCCUPIED
        room.save(update_fields=["status", "updated_at"])

        CheckInRecord.objects.create(
            booking=booking,
            receptionist_name=receptionist_name,
            money_received=money_received,
            deposit_amount=deposit_amount,
            payment_method=payment_method,
            key_card_number=key_card_number,
            notes=notes,
        )

        if money_received > 0:
            Payment.objects.create(
                booking=booking,
                amount=money_received,
                payment_type=PaymentType.CHECKIN_PAYMENT,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Check-in payment for reservation {booking.booking_reference}",
            )

        if deposit_amount > 0:
            Payment.objects.create(
                booking=booking,
                amount=deposit_amount,
                payment_type=PaymentType.DEPOSIT,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Security deposit for reservation {booking.booking_reference}",
            )

        return booking


def process_checkout(
    booking_id,
    additional_charges=0,
    additional_charges_notes="",
    final_amount_paid=0,
    payment_method="CASH",
    room_inspected=True,
    receptionist_name="Receptionist",
    notes="",
):
    """
    Completes guest stay & performs checkout.
    """
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(id=booking_id)

        if booking.status != BookingStatus.CHECKED_IN:
            raise ValidationError(
                f"Booking {booking.booking_reference} cannot be checked out because status is '{booking.status}'."
            )

        booking.status = BookingStatus.CHECKED_OUT
        booking.save(update_fields=["status", "updated_at"])

        room = booking.room
        room.status = RoomStatus.DIRTY_CLEANING
        room.save(update_fields=["status", "updated_at"])

        CheckOutRecord.objects.create(
            booking=booking,
            receptionist_name=receptionist_name,
            additional_charges=additional_charges,
            additional_charges_notes=additional_charges_notes,
            final_amount_paid=final_amount_paid,
            payment_method=payment_method,
            room_inspected=room_inspected,
            notes=notes,
        )

        if final_amount_paid > 0:
            Payment.objects.create(
                booking=booking,
                amount=final_amount_paid,
                payment_type=PaymentType.CHECKOUT_PAYMENT,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Final payment received at check-out for {booking.booking_reference}",
            )

        if additional_charges > 0 and final_amount_paid == 0:
            Payment.objects.create(
                booking=booking,
                amount=additional_charges,
                payment_type=PaymentType.ADDITIONAL_CHARGE,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Additional charges ({additional_charges_notes}) for {booking.booking_reference}",
            )

        return booking


def extend_booking_stay(
    booking_id,
    new_check_out_date,
    money_received=0,
    payment_method=PaymentMethod.CASH,
    receptionist_name="Receptionist",
    notes="",
):
    """
    Extends departure date for an active checked-in or confirmed booking:
    1. Validates booking state (CHECKED_IN or CONFIRMED).
    2. Validates new_check_out_date > current check_out_date.
    3. Checks room availability for extended window (excluding current booking).
    4. Recalculates total price (additional_amount = extension_days * nightly_rate).
    5. Updates booking.check_out_date and booking.total_amount.
    6. Logs a Payment transaction if money was received.
    """
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related("room", "guest").get(id=booking_id)

        if booking.status not in [BookingStatus.CHECKED_IN, BookingStatus.CONFIRMED]:
            raise ValidationError(
                f"Cannot extend stay for booking {booking.booking_reference} with status '{booking.status}'. Only active stays can be extended."
            )

        current_check_out = booking.check_out_date
        if new_check_out_date <= current_check_out:
            raise ValidationError(
                {
                    "new_check_out_date": f"New check-out date ({new_check_out_date}) must be after current check-out date ({current_check_out})."
                }
            )

        # Check room availability during extension window
        is_available = check_room_availability(
            room_id=booking.room.id,
            check_in_date=current_check_out,
            check_out_date=new_check_out_date,
            exclude_booking_id=booking.id,
        )

        if not is_available:
            raise ValidationError(
                f"Room {booking.room.room_number} is reserved/unavailable between {current_check_out} and {new_check_out_date}. Cannot extend stay."
            )

        extension_days = (new_check_out_date - current_check_out).days
        nightly_rate = booking.nightly_rate or booking.room.effective_price_per_night
        additional_amount = nightly_rate * extension_days

        old_check_out = booking.check_out_date
        booking.check_out_date = new_check_out_date
        booking.total_amount += additional_amount
        booking.save(update_fields=["check_out_date", "total_amount", "updated_at"])

        payment = None
        if money_received > 0:
            payment = Payment.objects.create(
                booking=booking,
                amount=money_received,
                payment_type=PaymentType.EXTEND_STAY,
                payment_method=payment_method,
                status=PaymentStatus.SUCCESS,
                recorded_by=receptionist_name,
                notes=f"Stay extended by {extension_days} night(s) from {old_check_out} to {new_check_out_date}. {notes}".strip(),
            )

        return {
            "booking": booking,
            "extension_days": extension_days,
            "additional_amount": additional_amount,
            "old_check_out_date": old_check_out,
            "new_check_out_date": new_check_out_date,
            "payment": payment,
        }
