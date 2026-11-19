"""
End-to-End (E2E) User Flow: Online Booking Lifecycle
Tests complete journey from online guest booking through receptionist verification to guest lookup.
"""

from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework import status

from apps.bookings.models import BookingStatus
from apps.payments.models import Payment, PaymentStatus
from apps.rooms.models import Room, RoomStatus


@pytest.mark.e2e
class TestOnlineBookingLifecycleE2E:
    def test_full_online_booking_workflow(self, api_client, receptionist_client, sample_room):
        # Create additional rooms so total_available > 2 (clearing last-room buffer)
        for i in range(2, 5):
            Room.objects.create(
                room_number=f"10{i}",
                floor=1,
                room_type=sample_room.room_type,
                status=RoomStatus.AVAILABLE,
            )

        today = date.today() + timedelta(days=10)
        checkout = today + timedelta(days=3)

        # ---------------------------------------------------------------------
        # Step 1: Unauthenticated Guest searches for available rooms
        # ---------------------------------------------------------------------
        search_url = reverse("public-room-availability")
        search_res = api_client.get(
            search_url,
            {
                "check_in_date": today.strftime("%Y-%m-%d"),
                "check_out_date": checkout.strftime("%Y-%m-%d"),
                "guests_count": 1,
            },
        )
        assert search_res.status_code == status.HTTP_200_OK
        assert search_res.data["available_count"] >= 1

        # ---------------------------------------------------------------------
        # Step 2: Guest submits online booking with transaction reference
        # ---------------------------------------------------------------------
        book_url = reverse("online-book")
        booking_payload = {
            "guest_first_name": "Solomon",
            "guest_last_name": "Kebede",
            "guest_phone_number": "+251911445566",
            "guest_email": "solomon@example.com",
            "room_id": sample_room.id,
            "check_in_date": today.strftime("%Y-%m-%d"),
            "check_out_date": checkout.strftime("%Y-%m-%d"),
            "transaction_reference": "CBE-TRANSFER-TX10099",
            "special_requests": "Quiet floor preferred",
        }
        book_res = api_client.post(book_url, booking_payload, format="json")
        assert book_res.status_code == status.HTTP_201_CREATED
        booking_id = book_res.data["booking"]["id"]
        booking_ref = book_res.data["booking"]["booking_reference"]
        assert book_res.data["booking"]["status"] == BookingStatus.PENDING_PAYMENT_VERIFICATION

        # ---------------------------------------------------------------------
        # Step 3: Receptionist checks live board & inspects verification queue
        # ---------------------------------------------------------------------
        liveboard_url = reverse("reception-live-board")
        board_res = receptionist_client.get(liveboard_url)
        assert board_res.status_code == status.HTTP_200_OK
        pending_queue = board_res.data["pending_payment_verifications"]
        assert any(item["booking_reference"] == booking_ref for item in pending_queue)

        # ---------------------------------------------------------------------
        # Step 4: Receptionist verifies & approves bank transfer payment
        # ---------------------------------------------------------------------
        payment = Payment.objects.get(booking_id=booking_id)
        verify_url = reverse("reception-verify-payment")
        verify_res = receptionist_client.post(
            verify_url,
            {"payment_id": payment.id, "action": "APPROVE", "notes": "Verified on CBE corporate mobile banking app"},
            format="json",
        )
        assert verify_res.status_code == status.HTTP_200_OK
        assert verify_res.data["booking"]["status"] == BookingStatus.CONFIRMED
        assert verify_res.data["payment"]["status"] == PaymentStatus.SUCCESS

        # ---------------------------------------------------------------------
        # Step 5: Guest queries reservation via public phone lookup
        # ---------------------------------------------------------------------
        lookup_url = reverse("online-lookup")
        lookup_res = api_client.get(lookup_url, {"phone_number": "+251911445566", "booking_reference": booking_ref})
        assert lookup_res.status_code == status.HTTP_200_OK
        assert lookup_res.data["count"] == 1
        assert lookup_res.data["bookings"][0]["status"] == BookingStatus.CONFIRMED
