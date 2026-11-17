from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "booking", "amount", "payment_type", "payment_method", "status", "payment_date")
    list_filter = ("payment_type", "payment_method", "status", "payment_date")
    search_fields = ("transaction_id", "booking__booking_reference", "recorded_by")
