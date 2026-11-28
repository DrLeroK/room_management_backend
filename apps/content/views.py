from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import record_audit_log
from apps.core.notifications import create_in_app_notification
from apps.rooms.models import Amenity, RoomType
from apps.rooms.serializers import AmenitySerializer, RoomTypeSerializer
from apps.users.permissions import IsManagerRole, IsOwnerRole, IsReceptionistRole

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
from .serializers import (
    ContactInquirySerializer,
    FAQSerializer,
    GalleryCategorySerializer,
    GalleryItemSerializer,
    HotelBankDetailsSerializer,
    HotelProfileSerializer,
    PartnerSerializer,
    TestimonialSerializer,
)


class PublicReadAuthMixin:
    """
    Relaxes authentication for public read operations (GET, HEAD, OPTIONS).
    If an expired or stale Bearer token is provided by a public visitor,
    this prevents DRF SimpleJWT from halting with 401 Unauthorized before
    evaluating public AllowAny permissions.
    """

    def get_authenticators(self):
        if (
            self.request
            and self.request.method in ("GET", "HEAD", "OPTIONS")
            and getattr(self, "action", None)
            in [
                "list",
                "retrieve",
                None,
            ]
        ):
            return []
        return super().get_authenticators()


class LandingPageView(PublicReadAuthMixin, APIView):
    """
    Composite API supplying all landing page content to the guest frontend.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        profile, _ = HotelProfile.objects.get_or_create(id=1)
        testimonials = Testimonial.objects.filter(is_active=True, is_featured=True)
        gallery_items = GalleryItem.objects.filter(is_active=True).select_related("category")
        partners = Partner.objects.filter(is_active=True)
        faqs = FAQ.objects.filter(is_active=True)
        room_types = RoomType.objects.filter(is_active=True)
        amenities = Amenity.objects.all()

        active_bank_accounts = HotelBankDetails.objects.filter(is_active=True)
        primary_bank = active_bank_accounts.first()
        if not primary_bank:
            primary_bank, _ = HotelBankDetails.objects.get_or_create(id=1)
        bank_data = HotelBankDetailsSerializer(primary_bank, context={"request": request}).data
        all_banks_data = HotelBankDetailsSerializer(active_bank_accounts, many=True, context={"request": request}).data
        bank_data["accounts"] = all_banks_data

        return Response(
            {
                "hotel_profile": HotelProfileSerializer(profile, context={"request": request}).data,
                "room_types": RoomTypeSerializer(room_types, many=True, context={"request": request}).data,
                "amenities": AmenitySerializer(amenities, many=True, context={"request": request}).data,
                "testimonials": TestimonialSerializer(testimonials, many=True, context={"request": request}).data,
                "gallery": GalleryItemSerializer(gallery_items, many=True, context={"request": request}).data,
                "partners": PartnerSerializer(partners, many=True, context={"request": request}).data,
                "faqs": FAQSerializer(faqs, many=True, context={"request": request}).data,
                "bank_transfer_details": bank_data,
                "bank_accounts": all_banks_data,
            },
            status=status.HTTP_200_OK,
        )


class HotelProfileView(PublicReadAuthMixin, APIView):
    """
    Hotel profile view. Public can read; only Managers/Owners can update.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]

    def get(self, request):
        profile, _ = HotelProfile.objects.get_or_create(id=1)
        return Response(HotelProfileSerializer(profile, context={"request": request}).data)

    def put(self, request):
        profile, _ = HotelProfile.objects.get_or_create(id=1)
        serializer = HotelProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HotelBankDetailsViewSet(PublicReadAuthMixin, viewsets.ModelViewSet):
    """
    ViewSet to manage multiple hotel bank accounts (CBE, Telebirr, Awash, etc.).
    Public can view active accounts; Owner/Admin can create, edit, or delete accounts.
    """

    queryset = HotelBankDetails.objects.all()
    serializer_class = HotelBankDetailsSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["display_order", "bank_name"]

    def get_queryset(self):
        queryset = HotelBankDetails.objects.all()
        # If unauthenticated or guest, only active accounts
        if not (
            self.request.user
            and self.request.user.is_authenticated
            and self.request.user.role in ["ADMIN", "OWNER", "MANAGER", "RECEPTIONIST"]
        ):
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerRole()]

    def perform_create(self, serializer):
        bank = serializer.save()
        record_audit_log(
            action="SETTING_CHANGED",
            entity_type="BankDetails",
            entity_id=str(bank.id),
            description=f"Hotel bank account '{bank.bank_name}' created by {self.request.user.username}",
            actor=self.request.user,
            request=self.request,
            changes={"bank_name": bank.bank_name, "account_number": bank.account_number},
        )

    def perform_update(self, serializer):
        bank = serializer.save()
        record_audit_log(
            action="SETTING_CHANGED",
            entity_type="BankDetails",
            entity_id=str(bank.id),
            description=f"Hotel bank account '{bank.bank_name}' updated by {self.request.user.username}",
            actor=self.request.user,
            request=self.request,
            changes={"bank_name": bank.bank_name, "is_active": bank.is_active},
        )

    def perform_destroy(self, instance):
        bank_name = instance.bank_name
        instance_id = instance.id
        instance.delete()
        record_audit_log(
            action="SETTING_CHANGED",
            entity_type="BankDetails",
            entity_id=str(instance_id),
            description=f"Hotel bank account '{bank_name}' deleted by {self.request.user.username}",
            actor=self.request.user,
            request=self.request,
        )


class HotelBankDetailsView(PublicReadAuthMixin, APIView):
    """
    View to inspect or update hotel bank details. Public GET for transfer info; PUT requires Owner/Admin.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerRole()]

    def get(self, request):
        accounts = HotelBankDetails.objects.filter(is_active=True)
        primary = accounts.first()
        if not primary:
            primary, _ = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(primary, context={"request": request})
        data = serializer.data
        data["accounts"] = HotelBankDetailsSerializer(accounts, many=True, context={"request": request}).data
        return Response(data)

    def put(self, request):
        bank_details, created = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(
            bank_details, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PublicBankDetailsView(PublicReadAuthMixin, APIView):
    """
    Public endpoint for guests to view bank details for payment transfers.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        accounts = HotelBankDetails.objects.filter(is_active=True)
        primary = accounts.first()
        if not primary:
            primary, _ = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(primary, context={"request": request})
        data = serializer.data
        data["accounts"] = HotelBankDetailsSerializer(accounts, many=True, context={"request": request}).data
        return Response(data)


class TestimonialViewSet(PublicReadAuthMixin, viewsets.ModelViewSet):
    queryset = Testimonial.objects.filter(is_active=True)
    serializer_class = TestimonialSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["display_order", "rating", "created_at"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class GalleryCategoryViewSet(PublicReadAuthMixin, viewsets.ModelViewSet):
    queryset = GalleryCategory.objects.all()
    serializer_class = GalleryCategorySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class GalleryItemViewSet(PublicReadAuthMixin, viewsets.ModelViewSet):
    serializer_class = GalleryItemSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "caption", "category__name"]
    ordering_fields = ["display_order", "created_at"]

    def get_queryset(self):
        queryset = GalleryItem.objects.filter(is_active=True).select_related("category")
        category_param = self.request.query_params.get("category")
        if category_param and category_param.lower() != "all":
            if category_param.isdigit():
                queryset = queryset.filter(category_id=int(category_param))
            else:
                queryset = queryset.filter(category__name__iexact=category_param) | queryset.filter(
                    category__slug__iexact=category_param
                )
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class PartnerViewSet(PublicReadAuthMixin, viewsets.ModelViewSet):
    queryset = Partner.objects.filter(is_active=True)
    serializer_class = PartnerSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["display_order", "name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class FAQViewSet(PublicReadAuthMixin, viewsets.ModelViewSet):
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["question", "answer", "category"]
    ordering_fields = ["display_order", "category"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsManagerRole()]


class ContactInquiryView(APIView):
    """
    Public POST to submit a contact inquiry. Staff GET to view received messages.
    """

    def get_authenticators(self):
        if self.request and self.request.method == "POST":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated(), IsReceptionistRole()]

    @extend_schema(request=ContactInquirySerializer, responses={201: ContactInquirySerializer})
    def post(self, request):
        serializer = ContactInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save(status=ContactInquiry.StatusChoices.NEW)

        subject_preview = inquiry.subject.strip() if inquiry.subject else "General Inquiry"
        message_preview = (inquiry.message[:90] + "...") if len(inquiry.message) > 90 else inquiry.message

        create_in_app_notification(
            title=f"New Guest Inquiry: {subject_preview}",
            message=f"From {inquiry.name} ({inquiry.email}): {message_preview}",
            notification_type="SYSTEM",
            target_role="RECEPTIONIST",
            link="/manager/inquiries",
        )
        create_in_app_notification(
            title=f"New Guest Inquiry: {subject_preview}",
            message=f"From {inquiry.name} ({inquiry.email}): {message_preview}",
            notification_type="SYSTEM",
            target_role="MANAGER",
            link="/manager/inquiries",
        )

        record_audit_log(
            action="GUEST_INQUIRY_CREATED",
            entity_type="ContactInquiry",
            entity_id=str(inquiry.id),
            description=f"Guest inquiry from '{inquiry.name}' ({inquiry.email}) received.",
            actor=None,
            request=request,
            changes={"subject": inquiry.subject, "name": inquiry.name, "email": inquiry.email},
        )

        return Response(
            {
                "message": "Thank you! Your message has been received. Our team will contact you shortly.",
                "inquiry": ContactInquirySerializer(inquiry).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        status_filter = request.query_params.get("status")
        inquiries = ContactInquiry.objects.all()

        if status_filter:
            inquiries = inquiries.filter(status=status_filter.upper())

        return Response(ContactInquirySerializer(inquiries, many=True).data)


class ContactInquiryDetailView(APIView):
    """
    Staff view to update inquiry status and add response notes.
    """

    permission_classes = [IsAuthenticated, IsReceptionistRole]

    def get(self, request, inquiry_id):
        try:
            inquiry = ContactInquiry.objects.get(id=inquiry_id)
        except ContactInquiry.DoesNotExist:
            return Response({"error": "Inquiry not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ContactInquirySerializer(inquiry).data)

    def patch(self, request, inquiry_id):
        try:
            inquiry = ContactInquiry.objects.get(id=inquiry_id)
        except ContactInquiry.DoesNotExist:
            return Response({"error": "Inquiry not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ContactInquirySerializer(inquiry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if "status" in request.data and request.data["status"] == "RESOLVED":
            serializer.validated_data["resolved_at"] = timezone.now()
            serializer.validated_data["is_resolved"] = True
        elif "status" in request.data and request.data["status"] == "CLOSED":
            serializer.validated_data["is_resolved"] = True

        serializer.save()

        if "status" in request.data and request.data["status"] == "READ":
            inquiry.is_resolved = False
            inquiry.save()

        return Response(serializer.data)


class ContactInquiryStatsView(APIView):
    """
    Staff view to get inquiry statistics.
    """

    permission_classes = [IsAuthenticated, IsReceptionistRole]

    def get(self, request):
        total = ContactInquiry.objects.count()
        new = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.NEW).count()
        read = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.READ).count()
        in_progress = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.IN_PROGRESS).count()
        resolved = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.RESOLVED).count()
        closed = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.CLOSED).count()

        return Response(
            {
                "total": total,
                "new": new,
                "read": read,
                "in_progress": in_progress,
                "resolved": resolved,
                "closed": closed,
                "pending": new + read + in_progress,
            }
        )
