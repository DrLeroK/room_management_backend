from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class RoomStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    OCCUPIED = "OCCUPIED", "Occupied"
    MAINTENANCE = "MAINTENANCE", "Under Maintenance"
    DIRTY_CLEANING = "DIRTY_CLEANING", "Dirty / Cleaning In Progress"


class Amenity(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=100, blank=True, default="fa-star")
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Amenities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class RoomType(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)  # e.g., Deluxe Suite, Standard Single
    code = models.CharField(max_length=20, unique=True)  # e.g., DLX, SGL, DBL
    description = models.TextField(blank=True, default="")
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    max_occupancy = models.PositiveIntegerField(default=2)
    image = models.ImageField(upload_to="room_types/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["base_price_per_night", "name"]

    def __str__(self):
        return f"{self.name} (${self.base_price_per_night}/night)"


class Room(TimeStampedModel):
    room_number = models.CharField(max_length=20, unique=True, db_index=True)
    floor = models.PositiveIntegerField(default=1)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    status = models.CharField(max_length=20, choices=RoomStatus.choices, default=RoomStatus.AVAILABLE, db_index=True)
    price_per_night_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional custom price override for this specific room. Defaults to room type price if left empty.",
    )
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="rooms")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["floor", "room_number"]

    def __str__(self):
        return f"Room {self.room_number} ({self.room_type.name}) - {self.get_status_display()}"

    @property
    def effective_price_per_night(self):
        if self.price_per_night_override is not None:
            return self.price_per_night_override
        return self.room_type.base_price_per_night


class RoomHold(TimeStampedModel):
    """
    Temporary 10-minute hold placed on a room when an online guest proceeds to checkout/payment.
    Automatically ignored in availability searches once expires_at is in the past.
    """

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="holds")
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    session_id = models.CharField(max_length=100, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["room", "check_in_date", "check_out_date", "expires_at"]),
        ]

    def __str__(self):
        return f"Hold on Room {self.room.room_number} until {self.expires_at} (session: {self.session_id})"

    @property
    def is_expired(self):
        from django.utils import timezone

        return timezone.now() >= self.expires_at
