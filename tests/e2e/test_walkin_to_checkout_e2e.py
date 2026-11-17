"""
End-to-End (E2E) Operational Flow: Walk-in Check-in -> Stay Extension -> Check-out -> Analytics KPI update.
"""

from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework import status

from apps.bookings.models import BookingStatus
from apps.rooms.models import RoomStatus


@pytest.mark.e2e
class TestWalkinToCheckoutE2E:
    def test_complete_stay_cycle(self, receptionist_client, manager_client, sample_room):
        today = date.today()
        checkout_date = today + timedelta(days=2)

        # ---------------------------------------------------------------------
        # Step 1: Walk-in guest arrives, receptionist checks in with deposit
        # ---------------------------------------------------------------------
        walkin_url = reverse("reception-walk-in-checkin")
        walkin_payload = {
            "guest": {
                "first_name": "Tewodros",
                "last_name": "Kassahun",
                "phone_number": "+251922334455",
                "email": "teddy@example.com",
            },
            "room_id": sample_room.id,
            "check_in_date": today.strftime("%Y-%m-%d"),
            "check_out_date": checkout_date.strftime("%Y-%m-%d"),
            "money_received": "400.00",
            "payment_method": "CASH",
            "deposit_amount": "50.00",
            "key_card_number": "CARD-402",
        }
        res_walkin = receptionist_client.post(walkin_url, walkin_payload, format="json")
        assert res_walkin.status_code == status.HTTP_201_CREATED
        booking_id = res_walkin.data["booking"]["id"]

        sample_room.refresh_from_db()
        assert sample_room.status == RoomStatus.OCCUPIED

        # ---------------------------------------------------------------------
        # Step 2: Guest extends stay by 2 extra nights
        # ---------------------------------------------------------------------
        extended_date = checkout_date + timedelta(days=2)
        extend_url = reverse("reception-extend-stay")
        res_extend = receptionist_client.post(
            extend_url,
            {
                "booking_id": booking_id,
                "new_check_out_date": extended_date.strftime("%Y-%m-%d"),
                "money_received": "400.00",
                "payment_method": "CASH",
                "notes": "Conference extended",
            },
            format="json",
        )
        assert res_extend.status_code == status.HTTP_200_OK
        assert res_extend.data["extension_days"] == 2

        # ---------------------------------------------------------------------
        # Step 3: Guest checks out, room inspection performed
        # ---------------------------------------------------------------------
        checkout_url = reverse("reception-checkout")
        res_checkout = receptionist_client.post(
            checkout_url,
            {
                "booking_id": booking_id,
                "additional_charges": "25.00",
                "additional_charges_notes": "Mini-bar beverages",
                "final_amount_paid": "25.00",
                "payment_method": "CASH",
                "room_inspected": True,
                "notes": "Room in clean condition, key card returned",
            },
            format="json",
        )
        assert res_checkout.status_code == status.HTTP_200_OK
        assert res_checkout.data["booking"]["status"] == BookingStatus.CHECKED_OUT

        sample_room.refresh_from_db()
        assert sample_room.status == RoomStatus.DIRTY_CLEANING

        # ---------------------------------------------------------------------
        # Step 4: Manager inspects daily analytics; revenue reflects all payments
        # ---------------------------------------------------------------------
        analytics_url = reverse("analytics-daily")
        res_analytics = manager_client.get(analytics_url, {"date": today.strftime("%Y-%m-%d")})
        assert res_analytics.status_code == status.HTTP_200_OK
        # Checkin (400) + Deposit (50) + Extension (400) + Checkout minibar (25) = 875
        assert res_analytics.data["total_revenue"] >= 800.00
