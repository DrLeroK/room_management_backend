from django.contrib import admin

from .models import Booking, CheckInRecord, CheckOutRecord


class CheckInRecordInline(admin.StackedInline):
    model = CheckInRecord
    extra = 0


class CheckOutRecordInline(admin.StackedInline):
    model = CheckOutRecord
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_reference",
        "guest",
        "room",
        "booking_source",
        "status",
        "check_in_date",
        "check_out_date",
        "total_amount",
    )
    list_filter = ("status", "booking_source", "check_in_date", "check_out_date")
    search_fields = (
        "booking_reference",
        "guest__first_name",
        "guest__last_name",
        "guest__phone_number",
        "room__room_number",
    )
    inlines = [CheckInRecordInline, CheckOutRecordInline]


@admin.register(CheckInRecord)
class CheckInRecordAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "receptionist_name",
        "actual_check_in_time",
        "money_received",
        "deposit_amount",
        "payment_method",
    )
    search_fields = ("booking__booking_reference", "receptionist_name", "key_card_number")


@admin.register(CheckOutRecord)
class CheckOutRecordAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "receptionist_name",
        "actual_check_out_time",
        "additional_charges",
        "final_amount_paid",
        "payment_method",
    )
    search_fields = ("booking__booking_reference", "receptionist_name")
