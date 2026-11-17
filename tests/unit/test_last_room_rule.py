from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from apps.bookings.services import create_online_booking, find_available_rooms
from apps.rooms.models import Room, RoomStatus, RoomType


@pytest.mark.django_db
class TestLastRoomRuleUnit:
    @pytest.fixture(autouse=True)
    def setup_rooms(self, db):
        self.room_type = RoomType.objects.create(
            name="Standard Double",
            code="STD-DBL",
            base_price_per_night=Decimal("150.00"),
            max_occupancy=2,
        )
        self.check_in = date.today() + timedelta(days=1)
        self.check_out = date.today() + timedelta(days=3)

    def test_online_search_shows_rooms_when_inventory_abundant(self):
        # Create 5 active rooms
        for i in range(1, 6):
            Room.objects.create(
                room_number=f"10{i}",
                floor=1,
                room_type=self.room_type,
                status=RoomStatus.AVAILABLE,
            )

        online_rooms = find_available_rooms(
            self.check_in, self.check_out, guests_count=1, is_online_search=True
        )
        assert online_rooms.count() == 5

    def test_last_room_rule_hides_last_two_rooms_from_online_search(self):
        # Create exactly 2 active rooms
        r1 = Room.objects.create(
            room_number="201",
            floor=2,
            room_type=self.room_type,
            status=RoomStatus.AVAILABLE,
        )
        r2 = Room.objects.create(
            room_number="202",
            floor=2,
            room_type=self.room_type,
            status=RoomStatus.AVAILABLE,
        )

        # Online search must return 0 rooms (Last-Room Rule triggered)
        online_rooms = find_available_rooms(
            self.check_in, self.check_out, guests_count=1, is_online_search=True
        )
        assert online_rooms.count() == 0

        # Front desk staff search (is_online_search=False) must STILL see both rooms
        staff_rooms = find_available_rooms(
            self.check_in, self.check_out, guests_count=1, is_online_search=False
        )
        assert staff_rooms.count() == 2
        assert set(staff_rooms.values_list("id", flat=True)) == {r1.id, r2.id}

    def test_online_booking_blocked_when_last_rooms_remain(self):
        # Only 2 rooms exist in hotel
        room = Room.objects.create(
            room_number="301",
            floor=3,
            room_type=self.room_type,
            status=RoomStatus.AVAILABLE,
        )
        Room.objects.create(
            room_number="302",
            floor=3,
            room_type=self.room_type,
            status=RoomStatus.AVAILABLE,
        )

        guest_data = {
            "first_name": "Online",
            "last_name": "Guest",
            "phone_number": "+251911998877",
            "email": "online@example.com",
        }

        with pytest.raises(ValidationError) as exc_info:
            create_online_booking(
                guest_data=guest_data,
                room_id=room.id,
                check_in_date=self.check_in,
                check_out_date=self.check_out,
            )

        assert "closed for the last remaining rooms" in str(exc_info.value)
