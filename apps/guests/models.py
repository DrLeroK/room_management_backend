from django.db import models

from apps.core.models import TimeStampedModel


class IdentificationType(models.TextChoices):
    PASSPORT = "PASSPORT", "Passport"
    NATIONAL_ID = "NATIONAL_ID", "National ID Card"
    DRIVERS_LICENSE = "DRIVERS_LICENSE", "Driver License"
    OTHER = "OTHER", "Other"


class Guest(TimeStampedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=30, db_index=True)
    email = models.EmailField(blank=True, default="")
    identification_type = models.CharField(
        max_length=30, choices=IdentificationType.choices, default=IdentificationType.NATIONAL_ID
    )
    identification_number = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    def save(self, *args, **kwargs):
        if self.phone_number:
            from apps.core.validators import normalize_ethiopian_phone

            self.phone_number = normalize_ethiopian_phone(self.phone_number)
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
