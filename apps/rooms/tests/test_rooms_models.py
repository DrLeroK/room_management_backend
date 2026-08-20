from decimal import Decimal
from django.test import TestCase
from apps.rooms.models import Room, RoomType, Amenity, RoomStatus

class RoomModelTest(TestCase):
    def setUp(self):
        self.amenity_wifi = Amenity.objects.create(
            name="Wi-Fi 6", code="WIFI6", icon="fa-wifi"
        )
        self.deluxe_type = RoomType.objects.create(
            name="Deluxe Suite",
            code="DLX",
            base_price_per_night=Decimal("120.00"),
            max_occupancy=2
        )
        self.room = Room.objects.create(
            room_number="101",
            floor=1,
            room_type=self.deluxe_type,
            status=RoomStatus.AVAILABLE
        )

    def test_effective_price_defaults_to_room_type(self):
        self.assertEqual(self.room.effective_price_per_night, Decimal("120.00"))

    def test_effective_price_uses_override_if_set(self):
        self.room.price_per_night_override = Decimal("140.00")
        self.room.save()
        self.assertEqual(self.room.effective_price_per_night, Decimal("140.00"))

    def test_room_string_representation(self):
        self.assertIn("101", str(self.room))
        self.assertIn("Deluxe Suite", str(self.room))
