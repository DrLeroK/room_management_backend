from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.bookings.models import BookingSource, BookingStatus
from apps.bookings.services import (
    check_room_availability,
    create_online_booking,
    process_checkout,
    process_walk_in_checkin,
    verify_online_payment,
)
from apps.payments.models import PaymentStatus
from apps.rooms.models import Room, RoomStatus, RoomType


class BookingServicesTest(TestCase):
    def setUp(self):
        self.room_type = RoomType.objects.create(
            name="Standard Double", code="STD_DBL", base_price_per_night=Decimal("80.00"), max_occupancy=2
        )
        self.room = Room.objects.create(
            room_number="105", floor=1, room_type=self.room_type, status=RoomStatus.AVAILABLE
        )
        self.guest_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "+1234567890",
            "email": "john@example.com",
        }
        self.today = date.today()

    def test_create_online_booking_with_transfer_reference_sets_pending_verification(self):
        check_in = self.today + timedelta(days=2)
        check_out = self.today + timedelta(days=5)

        booking = create_online_booking(
            guest_data=self.guest_data,
            room_id=self.room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            transaction_reference="CBE-TXN-123456",
        )
        self.assertEqual(booking.status, BookingStatus.PENDING_PAYMENT_VERIFICATION)

        payment = booking.payments.first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, PaymentStatus.PENDING_VERIFICATION)
        self.assertEqual(payment.transaction_reference, "CBE-TXN-123456")

        # Ensure room is held / unavailable for others during pending verification
        is_avail = check_room_availability(self.room.id, check_in, check_out)
        self.assertFalse(is_avail)

    def test_verify_online_payment_approval_service(self):
        check_in = self.today + timedelta(days=3)
        check_out = self.today + timedelta(days=5)

        booking = create_online_booking(
            guest_data=self.guest_data,
            room_id=self.room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            transaction_reference="CBE-TXN-778899",
        )
        payment = booking.payments.first()

        res = verify_online_payment(
            payment_id=payment.id,
            action="APPROVE",
            receptionist_name="Helen Receptionist",
            notes="Bank receipt checked on CBE app.",
        )

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.status, BookingStatus.CONFIRMED)
        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(res["sms_info"]["status"], "SENT")
        self.assertIn("+1234567890", res["sms_info"]["recipient"])
        self.assertIn("105", res["sms_info"]["message"])

    def test_verify_online_payment_rejection_service(self):
        check_in = self.today + timedelta(days=3)
        check_out = self.today + timedelta(days=5)

        booking = create_online_booking(
            guest_data=self.guest_data,
            room_id=self.room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            transaction_reference="FAKE-TXN-000",
        )
        payment = booking.payments.first()

        res = verify_online_payment(
            payment_id=payment.id, action="REJECT", receptionist_name="Helen Receptionist", notes="Invalid screenshot."
        )

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.status, BookingStatus.CANCELLED)
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(res["sms_info"]["status"], "REJECTED_NOTICE_SENT")

        # Room should be available again
        is_avail = check_room_availability(self.room.id, check_in, check_out)
        self.assertTrue(is_avail)

    def test_process_walk_in_checkin(self):
        check_in = self.today
        check_out = self.today + timedelta(days=2)

        booking = process_walk_in_checkin(
            guest_data=self.guest_data,
            room_id=self.room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            money_received=Decimal("160.00"),
            payment_method="CASH",
            deposit_amount=Decimal("20.00"),
            receptionist_name="Receptionist Sarah",
        )

        self.assertEqual(booking.status, BookingStatus.CHECKED_IN)
        self.assertEqual(booking.booking_source, BookingSource.WALK_IN)

        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)

    def test_process_checkout(self):
        check_in = self.today
        check_out = self.today + timedelta(days=1)

        booking = process_walk_in_checkin(
            guest_data=self.guest_data,
            room_id=self.room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            money_received=Decimal("80.00"),
            payment_method="CARD",
        )

        checked_out_booking = process_checkout(
            booking_id=booking.id,
            additional_charges=Decimal("10.00"),
            additional_charges_notes="Snacks",
            final_amount_paid=Decimal("10.00"),
            payment_method="CASH",
        )

        self.assertEqual(checked_out_booking.status, BookingStatus.CHECKED_OUT)

        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.DIRTY_CLEANING)
