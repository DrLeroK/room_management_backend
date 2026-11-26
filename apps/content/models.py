from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class HotelProfile(TimeStampedModel):
    name = models.CharField(max_length=200, default="StayCraft Hotel & Bedroom Resort")
    tagline = models.CharField(max_length=255, default="Luxury, Comfort, & Elegance in Every Stay")
    about_us = models.TextField(
        default="StayCraft Hotel offers world-class bedroom accommodations, gourmet dining, and executive amenities located in the heart of the city."
    )
    hero_image = models.ImageField(upload_to="hotel_content/hero/", null=True, blank=True)
    address = models.CharField(max_length=255, default="Bole Road, Addis Ababa, Ethiopia")
    contact_phone = models.CharField(max_length=50, default="+251 911 000 000")
    contact_email = models.EmailField(default="info@staycrafthotel.com")
    facebook_url = models.URLField(blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    twitter_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    google_maps_embed = models.TextField(blank=True, default="")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class HotelBankDetails(TimeStampedModel):
    bank_name = models.CharField(max_length=200, default="Commercial Bank of Ethiopia (CBE)")
    account_name = models.CharField(max_length=200, default="StayCraft Hotel & Bedroom Resort")
    account_number = models.CharField(max_length=50, default="1000123456789")
    branch_name = models.CharField(max_length=150, blank=True, default="")
    swift_code = models.CharField(max_length=50, default="CBETETAA", blank=True)
    qr_code = models.ImageField(upload_to="hotel_content/bank_qrs/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    instructions = models.TextField(
        blank=True,
        default="Transfer total stay amount to the account above and upload the receipt/screenshot during online booking.",
    )

    class Meta:
        ordering = ["display_order", "bank_name"]
        verbose_name_plural = "Hotel Bank Details"

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.account_name})"


class Testimonial(TimeStampedModel):
    __test__ = False

    guest_name = models.CharField(max_length=100)
    guest_title = models.CharField(max_length=100, blank=True, default="Verified Guest")
    avatar = models.ImageField(upload_to="hotel_content/testimonials/", null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_featured = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"Review by {self.guest_name} ({self.rating} Stars)"


class GalleryCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Gallery Categories"

    def __str__(self):
        return self.name


class GalleryItem(TimeStampedModel):
    title = models.CharField(max_length=150)
    category = models.ForeignKey(
        GalleryCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    image = models.ImageField(upload_to="hotel_content/gallery/")
    caption = models.CharField(max_length=255, blank=True, default="")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.title


class Partner(TimeStampedModel):
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to="hotel_content/partners/", null=True, blank=True)
    website_url = models.URLField(blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=100, default="Corporate Partner")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class FAQ(TimeStampedModel):
    category = models.CharField(max_length=100, default="General")
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "category"]

    def __str__(self):
        return self.question


class ContactInquiry(TimeStampedModel):
    class StatusChoices(models.TextChoices):
        NEW = "NEW", "New"
        READ = "READ", "Read"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, default="")
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.NEW, db_index=True)
    is_resolved = models.BooleanField(default=False)
    response_notes = models.TextField(blank=True, default="")
    assigned_to = models.CharField(max_length=100, blank=True, default="")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Inquiry from {self.name}: {self.subject} [{self.get_status_display()}]"
