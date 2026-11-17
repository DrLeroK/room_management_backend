from django.contrib import admin

from .models import (
    FAQ,
    ContactInquiry,
    GalleryCategory,
    GalleryItem,
    HotelProfile,
    Partner,
    Testimonial,
)


@admin.register(HotelProfile)
class HotelProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline", "contact_phone", "contact_email", "updated_at")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("guest_name", "rating", "guest_title", "is_featured", "is_active", "display_order")
    list_filter = ("rating", "is_featured", "is_active")
    search_fields = ("guest_name", "comment")


@admin.register(GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "is_active", "display_order")
    list_filter = ("category", "is_featured", "is_active")
    search_fields = ("title", "caption")


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "website_url", "is_active", "display_order")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_active", "display_order")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer")


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "subject", "is_resolved", "created_at")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
