from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.conf import settings
from .models import Booking, BookingStatus, CheckInRecord, CheckOutRecord
from .serializers import (
    BookingSerializer, OnlineBookingCreateSerializer, WalkInCheckInSerializer,
    ReservationCheckInSerializer, CheckOutRequestSerializer, ExtendStaySerializer
)
from .services import (
    create_online_booking, process_walk_in_checkin,
    process_booking_checkin, process_checkout, verify_online_payment,
    extend_booking_stay
)
from apps.payments.serializers import PaymentSerializer, VerifyPaymentRequestSerializer
from apps.rooms.models import Room, RoomStatus
from apps.rooms.serializers import RoomSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.content.models import HotelBankDetails
from apps.content.serializers import HotelBankDetailsSerializer


class BookingViewSet(viewsets.ModelViewSet):
    """
    Staff management viewset for querying and maintaining bookings.
    """
    queryset = Booking.objects.select_related('guest', 'room', 'room__room_type') \
                              .prefetch_related('payments', 'check_in_record', 'check_out_record').all()
    serializer_class = BookingSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['booking_reference', 'guest__first_name', 'guest__last_name', 'guest__phone_number', 'room__room_number']
    ordering_fields = ['created_at', 'check_in_date', 'check_out_date']

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        phone_param = self.request.query_params.get('phone_number')
        room_number = self.request.query_params.get('room_number')

        if status_param:
            qs = qs.filter(status=status_param.upper())
        if phone_param:
            qs = qs.filter(guest__phone_number__icontains=phone_param.strip())
        if room_number:
            qs = qs.filter(room__room_number=room_number)
        return qs


class HotelBankDetailsView(APIView):
    """
    Public endpoint providing hotel bank account details for online payment transfers.
    """
    def get(self, request):
        return Response(settings.HOTEL_BANK_DETAILS, status=status.HTTP_200_OK)


class OnlineBookingView(APIView):
    """
    Public API endpoint for online guests to reserve a room and upload bank transfer screenshot proof.
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @extend_schema(request=OnlineBookingCreateSerializer, responses={201: BookingSerializer})
    def post(self, request):
        serializer = OnlineBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = create_online_booking(
            guest_data=data['parsed_guest'],
            room_id=data['room_id'],
            check_in_date=data['check_in_date'],
            check_out_date=data['check_out_date'],
            payment_proof=data.get('payment_proof'),
            transaction_reference=data.get('transaction_reference', ''),
            adults_count=data.get('adults_count', 1),
            children_count=data.get('children_count', 0),
            special_requests=data.get('special_requests', '')
        )

        context_serializer = BookingSerializer(booking, context={'request': request})
        msg = "Online booking submitted! Payment screenshot received and pending staff verification." if (data.get('payment_proof') or data.get('transaction_reference')) else "Booking created successfully!"

        return Response({
            'message': msg,
            'booking': context_serializer.data
        }, status=status.HTTP_201_CREATED)


class GuestBookingLookupView(APIView):
    """
    Public API endpoint for guests to check latest details of their booking using phone number.
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(name='phone_number', description='Guest phone number', required=True, type=str),
            OpenApiParameter(name='booking_reference', description='Optional booking reference code', required=False, type=str),
        ],
        responses={200: BookingSerializer(many=True)}
    )
    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        booking_ref = request.query_params.get('booking_reference')

        if not phone_number:
            return Response({'error': 'phone_number parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        bookings = Booking.objects.filter(guest__phone_number__icontains=phone_number.strip())
        if booking_ref:
            bookings = bookings.filter(booking_reference__iexact=booking_ref.strip())

        bookings = bookings.select_related('guest', 'room', 'room__room_type') \
                           .prefetch_related('payments', 'check_in_record', 'check_out_record')

        serializer = BookingSerializer(bookings, many=True, context={'request': request})
        return Response({
            'query_phone': phone_number,
            'count': bookings.count(),
            'bookings': serializer.data
        }, status=status.HTTP_200_OK)


class VerifyPaymentView(APIView):
    """
    Staff / Receptionist endpoint to inspect bank transfer payment proof screenshot,
    verify/approve or reject the payment, and automatically dispatch SMS notification to the guest's phone.
    """
    @extend_schema(request=VerifyPaymentRequestSerializer)
    def post(self, request):
        serializer = VerifyPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = verify_online_payment(
            payment_id=data['payment_id'],
            action=data['action'],
            receptionist_name=data.get('receptionist_name', 'Receptionist'),
            notes=data.get('notes', '')
        )

        booking_serializer = BookingSerializer(result['booking'], context={'request': request})
        payment_serializer = PaymentSerializer(result['payment'], context={'request': request})

        return Response({
            'message': result['message'],
            'action': result['action'],
            'booking': booking_serializer.data,
            'payment': payment_serializer.data,
            'sms_notification_sent': result['sms_info']
        }, status=status.HTTP_200_OK)


class WalkInCheckInView(APIView):
    """
    Receptionist endpoint to process immediate walk-in guest check-in.
    """
    @extend_schema(request=WalkInCheckInSerializer, responses={201: BookingSerializer})
    def post(self, request):
        serializer = WalkInCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = process_walk_in_checkin(
            guest_data=data['guest'],
            room_id=data['room_id'],
            check_in_date=data['check_in_date'],
            check_out_date=data['check_out_date'],
            money_received=data['money_received'],
            payment_method=data['payment_method'],
            deposit_amount=data.get('deposit_amount', 0),
            receptionist_name=data.get('receptionist_name', 'Receptionist'),
            key_card_number=data.get('key_card_number', ''),
            notes=data.get('notes', '')
        )

        return Response({
            'message': 'Walk-in check-in processed successfully!',
            'booking': BookingSerializer(booking, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class ReservationCheckInView(APIView):
    """
    Receptionist endpoint to check in an existing online/phone reservation.
    """
    @extend_schema(request=ReservationCheckInSerializer, responses={200: BookingSerializer})
    def post(self, request):
        serializer = ReservationCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = process_booking_checkin(
            booking_id=data['booking_id'],
            money_received=data['money_received'],
            payment_method=data['payment_method'],
            deposit_amount=data.get('deposit_amount', 0),
            receptionist_name=data.get('receptionist_name', 'Receptionist'),
            key_card_number=data.get('key_card_number', ''),
            notes=data.get('notes', '')
        )

        return Response({
            'message': f'Reservation {booking.booking_reference} checked in successfully!',
            'booking': BookingSerializer(booking, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class CheckOutView(APIView):
    """
    Receptionist endpoint to record guest departure and check-out.
    """
    @extend_schema(request=CheckOutRequestSerializer, responses={200: BookingSerializer})
    def post(self, request):
        serializer = CheckOutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = process_checkout(
            booking_id=data['booking_id'],
            additional_charges=data.get('additional_charges', 0),
            additional_charges_notes=data.get('additional_charges_notes', ''),
            final_amount_paid=data.get('final_amount_paid', 0),
            payment_method=data.get('payment_method', 'CASH'),
            room_inspected=data.get('room_inspected', True),
            receptionist_name=data.get('receptionist_name', 'Receptionist'),
            notes=data.get('notes', '')
        )

        return Response({
            'message': f'Check-out for booking {booking.booking_reference} completed successfully!',
            'booking': BookingSerializer(booking, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class ExtendStayView(APIView):
    """
    Receptionist / Staff endpoint to extend departure date of an active checked-in stay.
    Recalculates total price, logs additional payment if collected, and verifies room availability.
    """
    @extend_schema(request=ExtendStaySerializer, responses={200: BookingSerializer})
    def post(self, request):
        serializer = ExtendStaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = extend_booking_stay(
            booking_id=data['booking_id'],
            new_check_out_date=data['new_check_out_date'],
            money_received=data.get('money_received', 0),
            payment_method=data.get('payment_method', 'CASH'),
            receptionist_name=data.get('receptionist_name', 'Receptionist'),
            notes=data.get('notes', '')
        )

        booking_data = BookingSerializer(result['booking'], context={'request': request}).data
        return Response({
            'message': f"Stay for booking {result['booking'].booking_reference} extended by {result['extension_days']} night(s) until {result['new_check_out_date']}.",
            'extension_days': result['extension_days'],
            'additional_amount': result['additional_amount'],
            'old_check_out_date': result['old_check_out_date'],
            'new_check_out_date': result['new_check_out_date'],
            'booking': booking_data
        }, status=status.HTTP_200_OK)


class ReceptionLiveBoardView(APIView):
    """
    Receptionist real-time live dashboard: returns room status summary,
    active stay records, expected arrivals & departures today, and pending payment verification queue.
    """
    def get(self, request):
        today = timezone.now().date()
        
        rooms = Room.objects.select_related('room_type').all()
        
        summary = {
            'total_rooms': rooms.count(),
            'available_count': rooms.filter(status=RoomStatus.AVAILABLE).count(),
            'occupied_count': rooms.filter(status=RoomStatus.OCCUPIED).count(),
            'cleaning_count': rooms.filter(status=RoomStatus.DIRTY_CLEANING).count(),
            'maintenance_count': rooms.filter(status=RoomStatus.MAINTENANCE).count(),
            'pending_payment_verification_count': Booking.objects.filter(status=BookingStatus.PENDING_PAYMENT_VERIFICATION).count(),
        }

        # Active checked in bookings
        active_bookings = Booking.objects.filter(status=BookingStatus.CHECKED_IN) \
            .select_related('guest', 'room')

        # Arrivals expected today
        arrivals_today = Booking.objects.filter(check_in_date=today, status=BookingStatus.CONFIRMED) \
            .select_related('guest', 'room')

        # Departures expected today
        departures_today = Booking.objects.filter(check_out_date=today, status=BookingStatus.CHECKED_IN) \
            .select_related('guest', 'room')

        # Pending payment verifications queue
        pending_verifications = Booking.objects.filter(status=BookingStatus.PENDING_PAYMENT_VERIFICATION) \
            .select_related('guest', 'room') \
            .prefetch_related('payments')

        return Response({
            'date': today,
            'summary': summary,
            'active_stay_count': active_bookings.count(),
            'expected_arrivals_today': BookingSerializer(arrivals_today, many=True, context={'request': request}).data,
            'expected_departures_today': BookingSerializer(departures_today, many=True, context={'request': request}).data,
            'pending_payment_verifications': BookingSerializer(pending_verifications, many=True, context={'request': request}).data,
            'rooms_live_state': RoomSerializer(rooms, many=True, context={'request': request}).data
        }, status=status.HTTP_200_OK)

class HotelBankDetailsView(APIView):
    """
    Public endpoint providing hotel bank account details for online payment transfers.
    """
    def get(self, request):
        bank_details, created = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(bank_details)
        return Response(serializer.data, status=status.HTTP_200_OK)