import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.guests.models import Guest
from apps.rooms.models import Room


class BookingStatus(models.TextChoices):
    PENDING_PAYMENT_VERIFICATION = "PENDING_PAYMENT_VERIFICATION", "Pending Payment Verification"
    CONFIRMED = "CONFIRMED", "Confirmed / Reserved"
    CHECKED_IN = "CHECKED_IN", "Checked In"
    CHECKED_OUT = "CHECKED_OUT", "Checked Out"
    CANCELLED = "CANCELLED", "Cancelled"
    NO_SHOW = "NO_SHOW", "No Show"


class BookingSource(models.TextChoices):
    ONLINE = "ONLINE", "Online Portal"
    WALK_IN = "WALK_IN", "Reception Walk-in"
    PHONE = "PHONE", "Phone Reservation"


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    CARD = "CARD", "Credit/Debit Card"
    ONLINE_TRANSFER = "ONLINE_TRANSFER", "Bank / Online Transfer"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"


def generate_booking_reference():
    return f"BK-{uuid.uuid4().hex[:8].upper()}"


class Booking(TimeStampedModel):
    booking_reference = models.CharField(max_length=30, unique=True, default=generate_booking_reference, db_index=True)
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="bookings")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="bookings")
    booking_source = models.CharField(max_length=20, choices=BookingSource.choices, default=BookingSource.ONLINE)
    status = models.CharField(
        max_length=30, choices=BookingStatus.choices, default=BookingStatus.PENDING_PAYMENT_VERIFICATION, db_index=True
    )
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    adults_count = models.PositiveIntegerField(default=1)
    children_count = models.PositiveIntegerField(default=0)
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    special_requests = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking_reference} - Room {self.room.room_number} ({self.guest.full_name}) [{self.status}]"

    @property
    def total_nights(self):
        delta = (self.check_out_date - self.check_in_date).days
        return delta if delta > 0 else 1

    def save(self, *args, **kwargs):
        if not self.nightly_rate and self.room:
            self.nightly_rate = self.room.effective_price_per_night
        if not self.total_amount:
            self.total_amount = self.nightly_rate * self.total_nights
        super().save(*args, **kwargs)


class CheckInRecord(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="check_in_record")
    receptionist_name = models.CharField(max_length=100, default="Staff Receptionist")
    actual_check_in_time = models.DateTimeField(auto_now_add=True)
    money_received = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    key_card_number = models.CharField(max_length=50, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Check-in for {self.booking.booking_reference} at {self.actual_check_in_time}"


class CheckOutRecord(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="check_out_record")
    receptionist_name = models.CharField(max_length=100, default="Staff Receptionist")
    actual_check_out_time = models.DateTimeField(auto_now_add=True)
    additional_charges = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    additional_charges_notes = models.TextField(blank=True, default="")
    final_amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)]
    )
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    room_inspected = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Check-out for {self.booking.booking_reference} at {self.actual_check_out_time}"
