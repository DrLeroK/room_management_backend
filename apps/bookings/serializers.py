import json
from decimal import Decimal

from rest_framework import serializers

from apps.guests.serializers import GuestSerializer
from apps.payments.serializers import PaymentSerializer
from apps.rooms.serializers import RoomSerializer

from .models import (
    Booking,
    CheckInRecord,
    CheckOutRecord,
    PaymentMethod,
)


class CheckInRecordSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = CheckInRecord
        fields = [
            "id",
            "receptionist_name",
            "actual_check_in_time",
            "money_received",
            "deposit_amount",
            "payment_method",
            "payment_method_display",
            "key_card_number",
            "notes",
            "created_at",
        ]


class CheckOutRecordSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = CheckOutRecord
        fields = [
            "id",
            "receptionist_name",
            "actual_check_out_time",
            "additional_charges",
            "additional_charges_notes",
            "final_amount_paid",
            "payment_method",
            "payment_method_display",
            "room_inspected",
            "notes",
            "created_at",
        ]


class BookingSerializer(serializers.ModelSerializer):
    guest_details = GuestSerializer(source="guest", read_only=True)
    room_details = RoomSerializer(source="room", read_only=True)
    check_in_record = CheckInRecordSerializer(read_only=True)
    check_out_record = CheckOutRecordSerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    booking_source_display = serializers.CharField(source="get_booking_source_display", read_only=True)
    total_nights = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_reference",
            "guest",
            "guest_details",
            "room",
            "room_details",
            "booking_source",
            "booking_source_display",
            "status",
            "status_display",
            "check_in_date",
            "check_out_date",
            "total_nights",
            "adults_count",
            "children_count",
            "nightly_rate",
            "total_amount",
            "special_requests",
            "check_in_record",
            "check_out_record",
            "payments",
            "created_at",
            "updated_at",
        ]


class GuestInputSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    phone_number = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    identification_type = serializers.CharField(required=False, default="NATIONAL_ID")
    identification_number = serializers.CharField(required=False, allow_blank=True, default="")
    address = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_phone_number(self, value):
        from apps.core.validators import normalize_ethiopian_phone

        return normalize_ethiopian_phone(value)


class OnlineBookingCreateSerializer(serializers.Serializer):
    guest = serializers.JSONField(
        required=False, help_text="Guest object or JSON string when uploading multipart form data"
    )
    guest_first_name = serializers.CharField(required=False, write_only=True)
    guest_last_name = serializers.CharField(required=False, write_only=True, default="")
    guest_phone_number = serializers.CharField(required=False, write_only=True)
    guest_email = serializers.CharField(required=False, write_only=True, default="")

    room_id = serializers.IntegerField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    payment_proof = serializers.ImageField(required=False, allow_null=True)
    transaction_reference = serializers.CharField(required=False, allow_blank=True, default="")
    adults_count = serializers.IntegerField(default=1, min_value=1)
    children_count = serializers.IntegerField(default=0, min_value=0)
    special_requests = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_guest_phone_number(self, value):
        from apps.core.validators import normalize_ethiopian_phone

        return normalize_ethiopian_phone(value)

    def validate(self, data):
        if data["check_in_date"] >= data["check_out_date"]:
            raise serializers.ValidationError({"check_out_date": "Check-out date must be after check-in date."})

        # Parse guest data either from JSONField or individual form parameters
        guest_raw = data.get("guest")
        if guest_raw:
            if isinstance(guest_raw, str):
                try:
                    guest_dict = json.loads(guest_raw)
                except Exception:
                    raise serializers.ValidationError({"guest": "Invalid JSON format for guest object."})
            elif isinstance(guest_raw, dict):
                guest_dict = guest_raw
            else:
                guest_dict = {}
        else:
            guest_dict = {
                "first_name": data.get("guest_first_name"),
                "last_name": data.get("guest_last_name", ""),
                "phone_number": data.get("guest_phone_number"),
                "email": data.get("guest_email", ""),
            }

        if not guest_dict.get("first_name") or not guest_dict.get("phone_number"):
            raise serializers.ValidationError({"guest": "Guest first_name and phone_number are required."})

        from apps.core.validators import normalize_ethiopian_phone

        guest_dict["phone_number"] = normalize_ethiopian_phone(guest_dict["phone_number"])
        data["parsed_guest"] = guest_dict
        return data


class WalkInCheckInSerializer(serializers.Serializer):
    guest = GuestInputSerializer()
    room_id = serializers.IntegerField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    money_received = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    deposit_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=Decimal("0.00"))
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    key_card_number = serializers.CharField(required=False, allow_blank=True, default="")
    receptionist_name = serializers.CharField(required=False, default="Receptionist")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        if data["check_in_date"] >= data["check_out_date"]:
            raise serializers.ValidationError({"check_out_date": "Check-out date must be after check-in date."})
        return data


class ReservationCheckInSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    money_received = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    deposit_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=Decimal("0.00"))
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    key_card_number = serializers.CharField(required=False, allow_blank=True, default="")
    receptionist_name = serializers.CharField(required=False, default="Receptionist")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CheckOutRequestSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    additional_charges = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=Decimal("0.00"))
    additional_charges_notes = serializers.CharField(required=False, allow_blank=True, default="")
    final_amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=Decimal("0.00"))
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    room_inspected = serializers.BooleanField(default=True)
    receptionist_name = serializers.CharField(required=False, default="Receptionist")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ExtendStaySerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    new_check_out_date = serializers.DateField()
    money_received = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=Decimal("0.00"))
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    receptionist_name = serializers.CharField(required=False, default="Receptionist")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
