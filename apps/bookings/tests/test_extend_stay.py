from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking, BookingSource, BookingStatus
from apps.guests.models import Guest
from apps.payments.models import Payment, PaymentType
from apps.rooms.models import Room, RoomStatus, RoomType
from apps.users.models import UserRole

User = get_user_model()


class ExtendStayAPITest(APITestCase):
    def setUp(self):
        self.receptionist = User.objects.create_user(
            username="receptionist_helen", role=UserRole.RECEPTIONIST, password="password123"
        )
        self.client.force_authenticate(user=self.receptionist)

        self.room_type = RoomType.objects.create(name="Deluxe Suite", base_price_per_night=100.00, max_occupancy=2)
        self.room = Room.objects.create(
            room_number="401", room_type=self.room_type, status=RoomStatus.OCCUPIED, floor=4
        )
        self.guest = Guest.objects.create(
            first_name="Abebe", last_name="Bikila", phone_number="+251911002233", email="abebe@example.com"
        )
        self.today = date.today()
        self.booking = Booking.objects.create(
            guest=self.guest,
            room=self.room,
            booking_source=BookingSource.WALK_IN,
            status=BookingStatus.CHECKED_IN,
            check_in_date=self.today - timedelta(days=2),
            check_out_date=self.today + timedelta(days=1),  # 3 nights = $300
            nightly_rate=100.00,
            total_amount=300.00,
        )
        self.url = reverse("reception-extend-stay")

    def test_extend_stay_success(self):
        new_checkout = self.today + timedelta(days=3)  # Extending 2 extra nights (Total 5 nights = $500)

        response = self.client.post(
            self.url,
            {
                "booking_id": self.booking.id,
                "new_check_out_date": new_checkout.strftime("%Y-%m-%d"),
                "money_received": "200.00",
                "payment_method": "CASH",
                "receptionist_name": "Receptionist Helen",
                "notes": "Guest requested stay extension for business meeting",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["extension_days"], 2)
        self.assertEqual(Decimal(str(response.data["additional_amount"])), Decimal("200.00"))

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.check_out_date, new_checkout)
        self.assertEqual(self.booking.total_amount, Decimal("500.00"))

        # Check Payment record logged
        payments = Payment.objects.filter(booking=self.booking, payment_type=PaymentType.EXTEND_STAY)
        self.assertEqual(payments.count(), 1)
        self.assertEqual(payments.first().amount, Decimal("200.00"))

    def test_extend_stay_invalid_date(self):
        # New check-out date is earlier than or equal to current check-out date
        earlier_checkout = self.today
        response = self.client.post(
            self.url,
            {
                "booking_id": self.booking.id,
                "new_check_out_date": earlier_checkout.strftime("%Y-%m-%d"),
                "money_received": "0.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_check_out_date", str(response.data))

    def test_extend_stay_room_conflict(self):
        # Create another confirmed booking for the same room during the extension window
        guest2 = Guest.objects.create(first_name="Sara", last_name="Mamo", phone_number="+251911998877")
        Booking.objects.create(
            guest=guest2,
            room=self.room,
            booking_source=BookingSource.ONLINE,
            status=BookingStatus.CONFIRMED,
            check_in_date=self.today + timedelta(days=2),
            check_out_date=self.today + timedelta(days=5),
            nightly_rate=100.00,
            total_amount=300.00,
        )

        new_checkout = self.today + timedelta(days=4)  # Overlaps with guest2's booking
        response = self.client.post(
            self.url,
            {"booking_id": self.booking.id, "new_check_out_date": new_checkout.strftime("%Y-%m-%d")},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unavailable", str(response.data))
