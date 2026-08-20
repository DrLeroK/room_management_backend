from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Guest
from .serializers import GuestSerializer, GuestLookupSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter

class GuestViewSet(viewsets.ModelViewSet):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['first_name', 'last_name', 'phone_number', 'email', 'identification_number']
    ordering_fields = ['created_at', 'first_name', 'last_name']

    @extend_schema(
        parameters=[
            OpenApiParameter(name='phone_number', description='Guest phone number', required=True, type=str)
        ]
    )
    @action(detail=False, methods=['get'], url_path='by-phone')
    def by_phone(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response(
                {"error": "phone_number parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        guests = Guest.objects.filter(phone_number__icontains=phone_number.strip())
        serializer = self.get_serializer(guests, many=True)
        return Response({
            'count': guests.count(),
            'results': serializer.data
        })
