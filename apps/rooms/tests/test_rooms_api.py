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
        # Create extra single rooms so total hotel rooms > 2 (clearing last-room buffer threshold)
        single_type = RoomType.objects.create(
            name="Single Room", code="SGL", base_price_per_night=Decimal("80.00"), max_occupancy=1
        )
        Room.objects.create(room_number="101", floor=1, room_type=single_type, status=RoomStatus.AVAILABLE)
        Room.objects.create(room_number="102", floor=1, room_type=single_type, status=RoomStatus.AVAILABLE)

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

    def test_unauthenticated_guest_can_list_rooms_and_types(self):
        self.client.logout()
        res_rooms = self.client.get(reverse("room-list"))
        self.assertEqual(res_rooms.status_code, status.HTTP_200_OK)

        res_types = self.client.get(reverse("room-type-list"))
        self.assertEqual(res_types.status_code, status.HTTP_200_OK)

    def test_room_hold_lifecycle(self):
        self.client.logout()
        url = reverse("room-hold-list")
        check_in = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
        check_out = (date.today() + timedelta(days=12)).strftime("%Y-%m-%d")

        # Create hold
        payload = {
            "room": self.room.id,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "session_id": "session-test-123",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["session_id"], "session-test-123")

        # Second hold from different session on same room/dates should fail
        payload2 = {
            "room": self.room.id,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "session_id": "session-test-456",
        }
        res2 = self.client.post(url, payload2, format="json")
        self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)

        # Release hold
        release_url = reverse("room-hold-release-hold")
        res_release = self.client.post(release_url, {"session_id": "session-test-123"}, format="json")
        self.assertEqual(res_release.status_code, status.HTTP_200_OK)
        self.assertTrue(res_release.data["released"])

