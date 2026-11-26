from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AmenityViewSet,
    PublicRoomAvailabilityView,
    RoomHoldViewSet,
    RoomTypeViewSet,
    RoomViewSet,
)

router = DefaultRouter()
router.register(r"types", RoomTypeViewSet, basename="room-type")
router.register(r"amenities", AmenityViewSet, basename="amenity")
router.register(r"holds", RoomHoldViewSet, basename="room-hold")
router.register(r"", RoomViewSet, basename="room")

urlpatterns = [
    path("public-availability/", PublicRoomAvailabilityView.as_view(), name="public-room-availability"),
    path("", include(router.urls)),
]
