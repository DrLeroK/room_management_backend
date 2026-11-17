"""
Global Pytest fixtures and testing helpers for StayCraft Backend.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.guests.models import Guest
from apps.rooms.models import Room, RoomStatus, RoomType
from apps.users.models import UserRole

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="test_admin", email="admin@staycraft.com", password="password123", role=UserRole.ADMIN
    )


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(
        username="test_owner", email="owner@staycraft.com", password="password123", role=UserRole.OWNER
    )


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        username="test_manager", email="manager@staycraft.com", password="password123", role=UserRole.MANAGER
    )


@pytest.fixture
def receptionist_user(db):
    return User.objects.create_user(
        username="test_receptionist",
        email="receptionist@staycraft.com",
        password="password123",
        role=UserRole.RECEPTIONIST,
    )


@pytest.fixture
def receptionist_client(receptionist_user):
    client = APIClient()
    client.force_authenticate(user=receptionist_user)
    return client


@pytest.fixture
def manager_client(manager_user):
    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


@pytest.fixture
def owner_client(owner_user):
    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def sample_room_type(db):
    return RoomType.objects.create(
        name="Deluxe King Room",
        code="DLX-KNG",
        base_price_per_night=Decimal("200.00"),
        max_occupancy=2,
        description="Spacious king bed suite",
    )


@pytest.fixture
def sample_room(sample_room_type):
    return Room.objects.create(room_number="101", floor=1, room_type=sample_room_type, status=RoomStatus.AVAILABLE)


@pytest.fixture
def sample_guest(db):
    return Guest.objects.create(
        first_name="Helen", last_name="Tesfaye", phone_number="+251911223344", email="helen@example.com"
    )
