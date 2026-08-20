from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.utils import timezone
from .models import (
    HotelProfile, HotelBankDetails, Testimonial, GalleryCategory,
    GalleryItem, Partner, FAQ, ContactInquiry
)
from .serializers import (
    HotelProfileSerializer, HotelBankDetailsSerializer, TestimonialSerializer, 
    GalleryCategorySerializer, GalleryItemSerializer, PartnerSerializer, 
    FAQSerializer, ContactInquirySerializer
)
from apps.rooms.models import RoomType, Amenity
from apps.rooms.serializers import RoomTypeSerializer, AmenitySerializer
from drf_spectacular.utils import extend_schema

# Import for email notifications (you'll need to implement email sending)
# from django.core.mail import send_mail
# from django.template.loader import render_to_string

class LandingPageView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        profile, _ = HotelProfile.objects.get_or_create(id=1)
        testimonials = Testimonial.objects.filter(is_active=True, is_featured=True)
        gallery_items = GalleryItem.objects.filter(is_active=True).select_related('category')
        partners = Partner.objects.filter(is_active=True)
        faqs = FAQ.objects.filter(is_active=True)
        room_types = RoomType.objects.filter(is_active=True)
        amenities = Amenity.objects.all()

        return Response({
            'hotel_profile': HotelProfileSerializer(profile, context={'request': request}).data,
            'room_types': RoomTypeSerializer(room_types, many=True, context={'request': request}).data,
            'amenities': AmenitySerializer(amenities, many=True, context={'request': request}).data,
            'testimonials': TestimonialSerializer(testimonials, many=True, context={'request': request}).data,
            'gallery': GalleryItemSerializer(gallery_items, many=True, context={'request': request}).data,
            'partners': PartnerSerializer(partners, many=True, context={'request': request}).data,
            'faqs': FAQSerializer(faqs, many=True, context={'request': request}).data,
            'bank_transfer_details': settings.HOTEL_BANK_DETAILS
        }, status=status.HTTP_200_OK)


class HotelProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile, _ = HotelProfile.objects.get_or_create(id=1)
        return Response(HotelProfileSerializer(profile, context={'request': request}).data)

    def put(self, request):
        profile, _ = HotelProfile.objects.get_or_create(id=1)
        serializer = HotelProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class HotelBankDetailsView(APIView):
    """
    Get or update hotel bank details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bank_details, created = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(bank_details)
        return Response(serializer.data)

    def put(self, request):
        # Only allow owners/admins to update
        if not request.user.is_owner_role:
            return Response(
                {'error': 'Only owners and admins can update bank details'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        bank_details, created = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(bank_details, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PublicBankDetailsView(APIView):
    """
    Public endpoint for guests to view bank details for payment.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        bank_details, created = HotelBankDetails.objects.get_or_create(id=1)
        serializer = HotelBankDetailsSerializer(bank_details)
        return Response(serializer.data)


class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonial.objects.filter(is_active=True)
    serializer_class = TestimonialSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['display_order', 'rating', 'created_at']


class GalleryCategoryViewSet(viewsets.ModelViewSet):
    queryset = GalleryCategory.objects.all()
    serializer_class = GalleryCategorySerializer


class GalleryItemViewSet(viewsets.ModelViewSet):
    queryset = GalleryItem.objects.filter(is_active=True).select_related('category')
    serializer_class = GalleryItemSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'caption', 'category__name']
    ordering_fields = ['display_order', 'created_at']


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.filter(is_active=True)
    serializer_class = PartnerSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['display_order', 'name']


class FAQViewSet(viewsets.ModelViewSet):
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['question', 'answer', 'category']
    ordering_fields = ['display_order', 'category']


class ContactInquiryView(APIView):
    """
    Public POST to submit a contact form inquiry. Staff GET to view received messages.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(request=ContactInquirySerializer, responses={201: ContactInquirySerializer})
    def post(self, request):
        serializer = ContactInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save(status=ContactInquiry.StatusChoices.NEW)
        
        # TODO: Send email notification to staff
        # send_staff_notification(inquiry)
        
        # TODO: Send auto-reply to guest
        # send_guest_confirmation(inquiry)
        
        return Response({
            'message': 'Thank you! Your message has been received. Our team will contact you shortly.',
            'inquiry': ContactInquirySerializer(inquiry).data
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        inquiries = ContactInquiry.objects.all()
        
        if status_filter:
            inquiries = inquiries.filter(status=status_filter.upper())
        
        return Response(ContactInquirySerializer(inquiries, many=True).data)


class ContactInquiryDetailView(APIView):
    """
    Staff view to update inquiry status and add response notes.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, inquiry_id):
        try:
            inquiry = ContactInquiry.objects.get(id=inquiry_id)
        except ContactInquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(ContactInquirySerializer(inquiry).data)
    
    def patch(self, request, inquiry_id):
        try:
            inquiry = ContactInquiry.objects.get(id=inquiry_id)
        except ContactInquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ContactInquirySerializer(inquiry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # If status is being changed to RESOLVED, set resolved_at
        if 'status' in request.data and request.data['status'] == 'RESOLVED':
            serializer.validated_data['resolved_at'] = timezone.now()
            serializer.validated_data['is_resolved'] = True
        elif 'status' in request.data and request.data['status'] == 'CLOSED':
            serializer.validated_data['is_resolved'] = True
        
        serializer.save()
        
        # If status is READ, update is_resolved to False
        if 'status' in request.data and request.data['status'] == 'READ':
            inquiry.is_resolved = False
            inquiry.save()
        
        return Response(serializer.data)
    
    
class ContactInquiryStatsView(APIView):
    """
    Staff view to get inquiry statistics.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        total = ContactInquiry.objects.count()
        new = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.NEW).count()
        read = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.READ).count()
        in_progress = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.IN_PROGRESS).count()
        resolved = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.RESOLVED).count()
        closed = ContactInquiry.objects.filter(status=ContactInquiry.StatusChoices.CLOSED).count()
        
        return Response({
            'total': total,
            'new': new,
            'read': read,
            'in_progress': in_progress,
            'resolved': resolved,
            'closed': closed,
            'pending': new + read + in_progress,
        })
