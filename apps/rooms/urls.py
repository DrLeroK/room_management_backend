from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, RoomTypeViewSet, AmenityViewSet, PublicRoomAvailabilityView

router = DefaultRouter()
router.register(r'types', RoomTypeViewSet, basename='room-type')
router.register(r'amenities', AmenityViewSet, basename='amenity')
router.register(r'', RoomViewSet, basename='room')

urlpatterns = [
    path('public-availability/', PublicRoomAvailabilityView.as_view(), name='public-room-availability'),
    path('', include(router.urls)),
]
