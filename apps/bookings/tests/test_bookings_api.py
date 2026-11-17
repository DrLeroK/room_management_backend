from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import BookingStatus
from apps.rooms.models import Room, RoomStatus, RoomType
from apps.users.models import User, UserRole


class BookingAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="receptionist_test", password="Password123!", role=UserRole.RECEPTIONIST
        )
        self.client.force_authenticate(user=self.user)

        self.room_type = RoomType.objects.create(
            name="Deluxe Suite", code="DLX", base_price_per_night=Decimal("100.00"), max_occupancy=2
        )
        self.room = Room.objects.create(
            room_number="301", floor=3, room_type=self.room_type, status=RoomStatus.AVAILABLE
        )
        self.today = date.today()

    def test_hotel_bank_details_api(self):
        url = reverse("hotel-bank-details")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("bank_name", response.data)
        self.assertIn("account_number", response.data)

    def test_online_booking_with_bank_transfer_api(self):
        url = reverse("online-book")
        payload = {
            "guest_first_name": "Abebe",
            "guest_last_name": "Bikila",
            "guest_phone_number": "+251912345678",
            "guest_email": "abebe@example.com",
            "room_id": self.room.id,
            "check_in_date": (self.today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "check_out_date": (self.today + timedelta(days=4)).strftime("%Y-%m-%d"),
            "transaction_reference": "CBE-BIRR-TXN-554433",
            "adults_count": 2,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["booking"]["status"], BookingStatus.PENDING_PAYMENT_VERIFICATION)

    def test_verify_online_payment_api(self):
        # Create online booking first
        book_url = reverse("online-book")
        payload = {
            "guest_first_name": "Latera",
            "guest_phone_number": "+251911223344",
            "room_id": self.room.id,
            "check_in_date": (self.today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "check_out_date": (self.today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "transaction_reference": "CBE-TXN-909090",
        }
        res_book = self.client.post(book_url, payload, format="json")
        payment_id = res_book.data["booking"]["payments"][0]["id"]

        # Staff verifies payment
        verify_url = reverse("reception-verify-payment")
        verify_payload = {
            "payment_id": payment_id,
            "action": "APPROVE",
            "receptionist_name": "Helen Receptionist",
            "notes": "Verified transfer of 200 ETB",
        }
        response = self.client.post(verify_url, verify_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "APPROVED")
        self.assertEqual(response.data["booking"]["status"], BookingStatus.CONFIRMED)
        self.assertIn("sms_notification_sent", response.data)
        self.assertEqual(response.data["sms_notification_sent"]["status"], "SENT")

    def test_guest_online_lookup_api(self):
        book_url = reverse("online-book")
        payload = {
            "guest_first_name": "Alex",
            "guest_phone_number": "+1999888777",
            "room_id": self.room.id,
            "check_in_date": (self.today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "check_out_date": (self.today + timedelta(days=3)).strftime("%Y-%m-%d"),
        }
        self.client.post(book_url, payload, format="json")

        lookup_url = reverse("online-lookup")
        response = self.client.get(lookup_url, {"phone_number": "+1999888777"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_walk_in_checkin_api(self):
        url = reverse("reception-walk-in-checkin")
        payload = {
            "guest": {
                "first_name": "Michael",
                "last_name": "Scott",
                "phone_number": "+15559876543",
                "identification_type": "PASSPORT",
                "identification_number": "P-90909",
            },
            "room_id": self.room.id,
            "check_in_date": self.today.strftime("%Y-%m-%d"),
            "check_out_date": (self.today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "money_received": "200.00",
            "deposit_amount": "30.00",
            "payment_method": "CASH",
            "receptionist_name": "Yared",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)

    def test_checkout_api(self):
        walkin_url = reverse("reception-walk-in-checkin")
        payload = {
            "guest": {"first_name": "Dwight", "phone_number": "+1555111222"},
            "room_id": self.room.id,
            "check_in_date": self.today.strftime("%Y-%m-%d"),
            "check_out_date": (self.today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "money_received": "100.00",
            "payment_method": "CASH",
        }
        res_walkin = self.client.post(walkin_url, payload, format="json")
        booking_id = res_walkin.data["booking"]["id"]

        checkout_url = reverse("reception-checkout")
        checkout_payload = {
            "booking_id": booking_id,
            "additional_charges": "15.00",
            "additional_charges_notes": "Mini bar drinks",
            "final_amount_paid": "15.00",
            "payment_method": "CASH",
            "receptionist_name": "Yared",
        }
        res_checkout = self.client.post(checkout_url, checkout_payload, format="json")
        self.assertEqual(res_checkout.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.DIRTY_CLEANING)

    def test_reception_live_board_api(self):
        url = reverse("reception-live-board")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary", response.data)
        self.assertIn("pending_payment_verifications", response.data)
