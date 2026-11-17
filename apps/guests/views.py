from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsReceptionistRole

from .models import Guest
from .serializers import GuestSerializer


class GuestViewSet(viewsets.ModelViewSet):
    """
    Staff Guest management viewset. Restricted to receptionists, managers, and owners.
    """

    permission_classes = [IsAuthenticated, IsReceptionistRole]
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "phone_number", "email", "identification_number"]
    ordering_fields = ["created_at", "first_name", "last_name"]

    @extend_schema(
        parameters=[OpenApiParameter(name="phone_number", description="Guest phone number", required=True, type=str)]
    )
    @action(detail=False, methods=["get"], url_path="by-phone")
    def by_phone(self, request):
        phone_number = request.query_params.get("phone_number")
        if not phone_number:
            return Response({"error": "phone_number parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        guests = Guest.objects.filter(phone_number__icontains=phone_number.strip())
        serializer = self.get_serializer(guests, many=True)
        return Response({"count": guests.count(), "results": serializer.data})
