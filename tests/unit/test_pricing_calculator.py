"""
Unit tests for stay duration and room price calculation logic.
"""

from datetime import date
from decimal import Decimal

import pytest

from apps.rooms.models import Room


@pytest.mark.unit
class TestRoomPricingCalculations:
    def test_room_effective_price_with_custom_rate(self, db, sample_room_type):
        room = Room.objects.create(
            room_number="999", room_type=sample_room_type, price_per_night_override=Decimal("250.00"), floor=9
        )
        assert room.effective_price_per_night == Decimal("250.00")

    def test_room_effective_price_without_custom_rate(self, db, sample_room_type):
        room = Room.objects.create(room_number="998", room_type=sample_room_type, floor=9)
        assert room.effective_price_per_night == Decimal("200.00")

    def test_multi_night_calculation(self):
        nightly_rate = Decimal("150.00")
        check_in = date(2026, 12, 1)
        check_out = date(2026, 12, 5)  # 4 nights
        total_nights = (check_out - check_in).days
        total_price = nightly_rate * total_nights
        assert total_nights == 4
        assert total_price == Decimal("600.00")

    def test_single_day_stay_defaults_to_one_night(self):
        check_in = date(2026, 12, 1)
        check_out = date(2026, 12, 1)
        delta = (check_out - check_in).days
        nights = delta if delta > 0 else 1
        assert nights == 1
