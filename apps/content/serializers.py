from rest_framework import serializers

from .models import (
    FAQ,
    ContactInquiry,
    GalleryCategory,
    GalleryItem,
    HotelBankDetails,
    HotelProfile,
    Partner,
    Testimonial,
)


def resolve_media_url(file_field, request=None):
    if not file_field:
        return None
    url = str(file_field.url).strip()
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url


class HotelProfileSerializer(serializers.ModelSerializer):
    hero_image_url = serializers.SerializerMethodField()

    class Meta:
        model = HotelProfile
        fields = [
            "id",
            "name",
            "tagline",
            "about_us",
            "hero_image",
            "hero_image_url",
            "address",
            "contact_phone",
            "contact_email",
            "facebook_url",
            "instagram_url",
            "twitter_url",
            "linkedin_url",
            "google_maps_embed",
        ]

    def get_hero_image_url(self, obj):
        return resolve_media_url(obj.hero_image, self.context.get("request"))


class HotelBankDetailsSerializer(serializers.ModelSerializer):
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = HotelBankDetails
        fields = [
            "id",
            "bank_name",
            "account_name",
            "account_number",
            "branch_name",
            "swift_code",
            "qr_code",
            "qr_code_url",
            "is_active",
            "display_order",
            "instructions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_qr_code_url(self, obj):
        return resolve_media_url(obj.qr_code, self.context.get("request"))


class TestimonialSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Testimonial
        fields = [
            "id",
            "guest_name",
            "guest_title",
            "avatar",
            "avatar_url",
            "rating",
            "comment",
            "is_featured",
            "is_active",
            "display_order",
            "created_at",
        ]

    def get_avatar_url(self, obj):
        return resolve_media_url(obj.avatar, self.context.get("request"))


class GalleryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryCategory
        fields = ["id", "name", "slug", "display_order"]


class GalleryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GalleryItem
        fields = [
            "id",
            "title",
            "category",
            "category_name",
            "image",
            "image_url",
            "caption",
            "is_featured",
            "is_active",
            "display_order",
            "created_at",
        ]

    def get_image_url(self, obj):
        return resolve_media_url(obj.image, self.context.get("request"))


class PartnerSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "logo",
            "logo_url",
            "website_url",
            "description",
            "category",
            "is_active",
            "display_order",
        ]

    def get_logo_url(self, obj):
        return resolve_media_url(obj.logo, self.context.get("request"))


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "category", "question", "answer", "is_active", "display_order"]


class ContactInquirySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ContactInquiry
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "status",
            "status_display",
            "is_resolved",
            "response_notes",
            "assigned_to",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status_display", "created_at", "updated_at"]
