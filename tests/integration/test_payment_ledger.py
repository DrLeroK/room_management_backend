"""
Integration tests for payment ledger endpoints and transaction recording.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.bookings.models import Booking, BookingSource, BookingStatus
from apps.payments.models import Payment, PaymentStatus, PaymentType


@pytest.mark.integration
class TestPaymentLedgerAPI:
    def test_receptionist_can_list_payments(self, receptionist_client, sample_guest, sample_room):
        booking = Booking.objects.create(
            guest=sample_guest,
            room=sample_room,
            booking_source=BookingSource.ONLINE,
            status=BookingStatus.CONFIRMED,
            check_in_date="2026-11-01",
            check_out_date="2026-11-03",
            nightly_rate=Decimal("200.00"),
            total_amount=Decimal("400.00"),
        )
        Payment.objects.create(
            booking=booking,
            amount=Decimal("400.00"),
            payment_type=PaymentType.ONLINE_PREPAYMENT,
            status=PaymentStatus.SUCCESS,
            transaction_reference="CBE-TX-998811",
        )

        url = reverse("payment-list")
        response = receptionist_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1
