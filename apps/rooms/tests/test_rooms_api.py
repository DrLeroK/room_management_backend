from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.rooms.models import Room, RoomStatus, RoomType
from apps.users.models import UserRole

User = get_user_model()


class RoomAPITest(APITestCase):
    def setUp(self):
        self.receptionist = User.objects.create_user(
            username="receptionist_user", role=UserRole.RECEPTIONIST, password="password123"
        )
        self.room_type = RoomType.objects.create(
            name="Executive Suite", code="EXEC", base_price_per_night=Decimal("150.00"), max_occupancy=2
        )
        self.room = Room.objects.create(
            room_number="201", floor=2, room_type=self.room_type, status=RoomStatus.AVAILABLE
        )

    def test_list_rooms(self):
        self.client.force_authenticate(user=self.receptionist)
        url = reverse("room-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_update_room_status(self):
        self.client.force_authenticate(user=self.receptionist)
        url = reverse("room-update-status", kwargs={"pk": self.room.pk})
        payload = {"status": "MAINTENANCE", "notes": "Plumbing repair required"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.MAINTENANCE)

    def test_public_room_availability_api(self):
        # Unauthenticated guest request
        self.client.logout()
        url = reverse("public-room-availability")
        check_in = date.today() + timedelta(days=5)
        check_out = date.today() + timedelta(days=7)
        response = self.client.get(
            url,
            {
                "check_in_date": check_in.strftime("%Y-%m-%d"),
                "check_out_date": check_out.strftime("%Y-%m-%d"),
                "guests_count": 2,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["available_count"], 1)
        self.assertEqual(response.data["rooms"][0]["room_number"], "201")
