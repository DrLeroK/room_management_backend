from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status

from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import create_online_booking
from apps.payments.models import Payment, PaymentStatus
from apps.rooms.models import Room, RoomStatus, RoomType


@pytest.mark.django_db
class TestOfflineSyncAndRejectionIntegration:
    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.room_type = RoomType.objects.create(
            name="Executive Suite",
            code="EXEC-STE",
            base_price_per_night=Decimal("250.00"),
            max_occupancy=2,
        )
        # Create 10 rooms so Last-Room Rule doesn't trigger for basic tests
        self.rooms = [
            Room.objects.create(
                room_number=f"40{i}",
                floor=4,
                room_type=self.room_type,
                status=RoomStatus.AVAILABLE,
            )
            for i in range(1, 10)
        ]
        self.target_room = self.rooms[0]
        self.check_in = date.today() + timedelta(days=1)
        self.check_out = date.today() + timedelta(days=3)

    def test_walk_in_idempotency_prevents_duplicate_sync(self, receptionist_client):
        payload = {
            "room_id": self.target_room.id,
            "check_in_date": self.check_in.strftime("%Y-%m-%d"),
            "check_out_date": self.check_out.strftime("%Y-%m-%d"),
            "money_received": "500.00",
            "payment_method": "CASH",
            "deposit_amount": "50.00",
            "guest": {
                "first_name": "Abebe",
                "last_name": "Bikila",
                "phone_number": "+251911001122",
                "email": "abebe@example.com",
            },
        }

        idemp_header = "sync_unique_uuid_9999"

        # First sync transmission
        res1 = receptionist_client.post(
            "/api/v1/bookings/reception/walk-in-checkin/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=idemp_header,
        )
        assert res1.status_code == status.HTTP_201_CREATED
        initial_booking_id = res1.data["booking"]["id"]
        total_bookings_count = Booking.objects.count()

        # Second sync transmission (e.g. tablet reconnected and retried)
        res2 = receptionist_client.post(
            "/api/v1/bookings/reception/walk-in-checkin/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=idemp_header,
        )
        assert res2.status_code == status.HTTP_201_CREATED
        assert res2.data["booking"]["id"] == initial_booking_id
        # Confirm no duplicate booking record was created in the database
        assert Booking.objects.count() == total_bookings_count

    def test_walk_in_concurrent_conflict_returns_409(self, receptionist_client):
        # Online guest books the room first
        create_online_booking(
            guest_data={
                "first_name": "Online",
                "last_name": "Winner",
                "phone_number": "+251912334455",
            },
            room_id=self.target_room.id,
            check_in_date=self.check_in,
            check_out_date=self.check_out,
        )

        # Offline desk reconnects later and attempts to claim the same room
        offline_payload = {
            "room_id": self.target_room.id,
            "check_in_date": self.check_in.strftime("%Y-%m-%d"),
            "check_out_date": self.check_out.strftime("%Y-%m-%d"),
            "money_received": "500.00",
            "payment_method": "CASH",
            "guest": {
                "first_name": "Offline",
                "last_name": "Guest",
                "phone_number": "+251933445566",
            },
        }

        res = receptionist_client.post(
            "/api/v1/bookings/reception/walk-in-checkin/",
            offline_payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="sync_offline_conflict_test",
        )
        assert res.status_code == status.HTTP_409_CONFLICT
        assert "unavailable" in str(res.data).lower() or "conflict" in str(res.data).lower()

    def test_reception_reject_payment_unverifies_booking_and_releases_room(self, receptionist_client):
        # Create an online booking with pending payment proof
        booking = create_online_booking(
            guest_data={
                "first_name": "Pending",
                "last_name": "Guest",
                "phone_number": "+251922334455",
                "email": "pending@example.com",
            },
            room_id=self.target_room.id,
            check_in_date=self.check_in,
            check_out_date=self.check_out,
            transaction_reference="FT261116FAKE01",
        )

        payment = Payment.objects.get(booking=booking)
        assert payment.status == PaymentStatus.PENDING_VERIFICATION
        assert booking.status == BookingStatus.PENDING_PAYMENT_VERIFICATION

        # Receptionist un-verifies / rejects payment due to invalid screenshot
        reject_payload = {
            "payment_id": payment.id,
            "action": "REJECT",
            "receptionist_name": "Front Desk Lead",
            "notes": "Called guest. Screenshot transfer proof is illegible/unconfirmed by bank.",
        }

        response = receptionist_client.post(
            "/api/v1/bookings/reception/verify-payment/",
            reject_payload,
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify booking is CANCELLED and payment is FAILED
        booking.refresh_from_db()
        payment.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED
        assert payment.status == PaymentStatus.FAILED

        # Verify Room is released back to AVAILABLE
        self.target_room.refresh_from_db()
        assert self.target_room.status == RoomStatus.AVAILABLE
