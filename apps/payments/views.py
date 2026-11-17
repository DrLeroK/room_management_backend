from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsReceptionistRole

from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff payment ledger view. Restricted to receptionists, managers, and owners.
    """

    permission_classes = [IsAuthenticated, IsReceptionistRole]
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["transaction_id", "booking__booking_reference", "recorded_by"]
    ordering_fields = ["payment_date", "amount"]
