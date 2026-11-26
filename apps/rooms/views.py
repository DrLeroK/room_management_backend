from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.services import check_room_availability, find_available_rooms
from apps.core.audit import record_audit_log
from apps.core.notifications import create_in_app_notification
from apps.users.permissions import IsManagerRole, IsReceptionistRole

from .models import Amenity, Room, RoomHold, RoomType
from .serializers import (
    AmenitySerializer,
    RoomAvailabilitySearchSerializer,
    RoomHoldSerializer,
    RoomSerializer,
    RoomStatusUpdateSerializer,
    RoomTypeSerializer,
)


class AmenityViewSet(viewsets.ModelViewSet):
    """
    Hotel Amenities viewset. Read access for receptionists, write access for managers.
    """

    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class RoomTypeViewSet(viewsets.ModelViewSet):
    """
    Staff / Owner viewset for managing Room Types and pricing rules.
    Public can view types and pricing; write access restricted to managers.
    """

    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "description"]
    ordering_fields = ["base_price_per_night", "max_occupancy", "name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class RoomViewSet(viewsets.ModelViewSet):
    """
    Staff / Receptionist viewset for managing individual rooms and operational statuses.
    """

    permission_classes = [IsAuthenticated, IsReceptionistRole]
    queryset = Room.objects.select_related("room_type").prefetch_related("amenities").all()
    serializer_class = RoomSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["room_number", "room_type__name", "notes"]
    ordering_fields = ["room_number", "floor", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        floor_param = self.request.query_params.get("floor")
        room_type_id = self.request.query_params.get("room_type")

        if status_param:
            qs = qs.filter(status=status_param.upper())
        if floor_param:
            qs = qs.filter(floor=floor_param)
        if room_type_id:
            qs = qs.filter(room_type_id=room_type_id)
        return qs

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        # Only managers/owners can delete rooms or create new rooms
        if self.action in ["create", "destroy"]:
            return [IsAuthenticated(), IsManagerRole()]
        return [IsAuthenticated(), IsReceptionistRole()]

    @extend_schema(request=RoomStatusUpdateSerializer)
    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        """
        Manually toggle room status (e.g. MAINTENANCE, DIRTY_CLEANING, AVAILABLE).
        """
        room = self.get_object()
        serializer = RoomStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        old_status = room.status
        room.status = new_status
        if notes:
            room.notes = f"{room.notes}\n[Status Change]: {notes}".strip()
        room.save(update_fields=["status", "notes", "updated_at"])

        record_audit_log(
            action="ROOM_UPDATED",
            entity_type="Room",
            entity_id=room.room_number,
            description=f"Room {room.room_number} status updated from {old_status} to {new_status} by {request.user.username}",
            actor=request.user,
            request=request,
            changes={"previous_status": old_status, "new_status": new_status, "notes": notes},
        )
        if new_status in ["MAINTENANCE", "AVAILABLE", "DIRTY_CLEANING"]:
            create_in_app_notification(
                title=f"Room {room.room_number}: {new_status.replace('_', ' ').title()}",
                message=f"Room {room.room_number} status was updated to {new_status} by {request.user.username}.",
                notification_type="ROOM_STATUS",
                target_role="RECEPTIONIST",
                link="/reception/rooms",
            )

        return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)


class PublicRoomAvailabilityView(APIView):
    """
    Public endpoint for guests to check room existence, real-time availability, and rates.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="check_in_date", description="Check-in date (YYYY-MM-DD)", required=True, type=str),
            OpenApiParameter(name="check_out_date", description="Check-out date (YYYY-MM-DD)", required=True, type=str),
            OpenApiParameter(name="guests_count", description="Number of guests", required=False, type=int, default=1),
            OpenApiParameter(name="room_type_id", description="Filter by room type ID", required=False, type=int),
        ],
        responses={200: RoomSerializer(many=True)},
    )
    def get(self, request):
        query_serializer = RoomAvailabilitySearchSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        params = query_serializer.validated_data
        raw_available_rooms = find_available_rooms(
            check_in_date=params["check_in_date"],
            check_out_date=params["check_out_date"],
            guests_count=params.get("guests_count", 1),
            room_type_id=params.get("room_type_id"),
            is_online_search=False,
        )

        online_available_rooms = find_available_rooms(
            check_in_date=params["check_in_date"],
            check_out_date=params["check_out_date"],
            guests_count=params.get("guests_count", 1),
            room_type_id=params.get("room_type_id"),
            is_online_search=True,
        )

        sales_closed_by_last_room_rule = raw_available_rooms.exists() and not online_available_rooms.exists()

        serializer = RoomSerializer(online_available_rooms, many=True)
        response_payload = {
            "search_criteria": {
                "check_in_date": params["check_in_date"],
                "check_out_date": params["check_out_date"],
                "guests_count": params.get("guests_count", 1),
                "room_type_id": params.get("room_type_id"),
            },
            "available_count": online_available_rooms.count(),
            "online_sales_closed": sales_closed_by_last_room_rule,
            "rooms": serializer.data,
        }
        if sales_closed_by_last_room_rule:
            response_payload["notice"] = (
                "Online bookings are closed for the last remaining rooms. "
                "These rooms are reserved exclusively for direct front desk reservations. "
                "Please contact reception directly."
            )

        return Response(response_payload, status=status.HTTP_200_OK)


class RoomHoldViewSet(viewsets.GenericViewSet):
    """
    Public endpoint to place and release 10-minute temporary holds on rooms
    during guest checkout, preventing double-booking while guest completes payment.
    """

    permission_classes = [AllowAny]
    queryset = RoomHold.objects.all()
    serializer_class = RoomHoldSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.validated_data["room"]
        check_in_date = serializer.validated_data["check_in_date"]
        check_out_date = serializer.validated_data["check_out_date"]
        session_id = serializer.validated_data["session_id"]

        # Check real-time availability ignoring any existing hold for this same session
        if not check_room_availability(room.id, check_in_date, check_out_date, exclude_session_id=session_id):
            return Response(
                {"error": f"Room {room.room_number} is no longer available for the selected dates."},
                status=status.HTTP_409_CONFLICT,
            )

        # Clear existing holds by this session
        RoomHold.objects.filter(session_id=session_id).delete()

        # Hold for 10 minutes
        hold = RoomHold.objects.create(
            room=room,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            session_id=session_id,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        return Response(RoomHoldSerializer(hold).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="release")
    def release_hold(self, request):
        session_id = request.data.get("session_id")
        hold_id = request.data.get("hold_id")
        if session_id:
            count, _ = RoomHold.objects.filter(session_id=session_id).delete()
            return Response({"released": True, "count": count}, status=status.HTTP_200_OK)
        if hold_id:
            count, _ = RoomHold.objects.filter(id=hold_id).delete()
            return Response({"released": True, "count": count}, status=status.HTTP_200_OK)
        return Response({"error": "session_id or hold_id is required."}, status=status.HTTP_400_BAD_REQUEST)

