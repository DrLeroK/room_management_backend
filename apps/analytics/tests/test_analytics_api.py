from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.analytics.services import get_daily_analytics, get_weekly_analytics
from apps.bookings.services import process_walk_in_checkin
from apps.rooms.models import Room, RoomStatus, RoomType
from apps.users.models import UserRole

User = get_user_model()


class AnalyticsTest(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="test_manager", email="manager@hotel.com", password="password123", role=UserRole.MANAGER
        )
        self.room_type = RoomType.objects.create(
            name="Executive Suite", code="EXEC", base_price_per_night=Decimal("150.00"), max_occupancy=2
        )
        self.room1 = Room.objects.create(
            room_number="401", floor=4, room_type=self.room_type, status=RoomStatus.AVAILABLE
        )
        self.room2 = Room.objects.create(
            room_number="402", floor=4, room_type=self.room_type, status=RoomStatus.AVAILABLE
        )
        self.today = date.today()

    def test_daily_and_weekly_analytics_service(self):
        # Create a walk in checkin
        process_walk_in_checkin(
            guest_data={"first_name": "Bruce", "phone_number": "+1555000777"},
            room_id=self.room1.id,
            check_in_date=self.today,
            check_out_date=self.today + timedelta(days=2),
            money_received=Decimal("300.00"),
            payment_method="CARD",
            receptionist_name="Test Receptionist",
        )

        daily_data = get_daily_analytics(self.today)
        self.assertEqual(daily_data["rooms_sold"], 1)
        self.assertEqual(daily_data["occupancy_rate_percentage"], 50.0)  # 1 of 2 rooms
        self.assertEqual(daily_data["total_revenue"], 300.00)
        self.assertEqual(daily_data["revenue_by_payment_method"]["CARD"], 300.00)

        weekly_data = get_weekly_analytics(self.today)
        self.assertIn("total_weekly_revenue", weekly_data)
        self.assertEqual(len(weekly_data["daily_breakdown"]), 7)

    def test_analytics_api_endpoints(self):
        self.client.force_authenticate(user=self.manager)
        daily_url = reverse("analytics-daily")
        res_daily = self.client.get(daily_url)
        self.assertEqual(res_daily.status_code, status.HTTP_200_OK)
        self.assertIn("occupancy_rate_percentage", res_daily.data)

        weekly_url = reverse("analytics-weekly")
        res_weekly = self.client.get(weekly_url)
        self.assertEqual(res_weekly.status_code, status.HTTP_200_OK)
        self.assertIn("total_weekly_revenue", res_weekly.data)
