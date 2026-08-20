from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Room, RoomType, Amenity, RoomStatus
from .serializers import (
    RoomSerializer, RoomTypeSerializer, AmenitySerializer,
    RoomStatusUpdateSerializer, RoomAvailabilitySearchSerializer
)
from apps.bookings.services import find_available_rooms
from drf_spectacular.utils import extend_schema, OpenApiParameter

class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']


class RoomTypeViewSet(viewsets.ModelViewSet):
    """
    Staff / Owner viewset for managing Room Types and pricing rules.
    """
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['base_price_per_night', 'max_occupancy', 'name']


class RoomViewSet(viewsets.ModelViewSet):
    """
    Staff / Owner viewset for managing individual rooms.
    """
    queryset = Room.objects.select_related('room_type').prefetch_related('amenities').all()
    serializer_class = RoomSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['room_number', 'room_type__name', 'notes']
    ordering_fields = ['room_number', 'floor', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        floor_param = self.request.query_params.get('floor')
        room_type_id = self.request.query_params.get('room_type')

        if status_param:
            qs = qs.filter(status=status_param.upper())
        if floor_param:
            qs = qs.filter(floor=floor_param)
        if room_type_id:
            qs = qs.filter(room_type_id=room_type_id)
        return qs

    @extend_schema(request=RoomStatusUpdateSerializer)
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Manually toggle room status (e.g. MAINTENANCE, DIRTY_CLEANING, AVAILABLE).
        """
        room = self.get_object()
        serializer = RoomStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        room.status = new_status
        if notes:
            room.notes = f"{room.notes}\n[Status Change]: {notes}".strip()
        room.save(update_fields=['status', 'notes', 'updated_at'])

        return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)


class PublicRoomAvailabilityView(APIView):
    """
    Public endpoint for guests to check room existence, real-time availability, and rates.
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(name='check_in_date', description='Check-in date (YYYY-MM-DD)', required=True, type=str),
            OpenApiParameter(name='check_out_date', description='Check-out date (YYYY-MM-DD)', required=True, type=str),
            OpenApiParameter(name='guests_count', description='Number of guests', required=False, type=int, default=1),
            OpenApiParameter(name='room_type_id', description='Filter by room type ID', required=False, type=int),
        ],
        responses={200: RoomSerializer(many=True)}
    )
    def get(self, request):
        query_serializer = RoomAvailabilitySearchSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        params = query_serializer.validated_data
        available_rooms = find_available_rooms(
            check_in_date=params['check_in_date'],
            check_out_date=params['check_out_date'],
            guests_count=params.get('guests_count', 1),
            room_type_id=params.get('room_type_id')
        )

        serializer = RoomSerializer(available_rooms, many=True)
        return Response({
            'search_criteria': {
                'check_in_date': params['check_in_date'],
                'check_out_date': params['check_out_date'],
                'guests_count': params.get('guests_count', 1),
                'room_type_id': params.get('room_type_id'),
            },
            'available_count': available_rooms.count(),
            'rooms': serializer.data
        }, status=status.HTTP_200_OK)
