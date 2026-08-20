from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LandingPageView, HotelProfileView, HotelBankDetailsView, PublicBankDetailsView,
    TestimonialViewSet, GalleryCategoryViewSet, GalleryItemViewSet, PartnerViewSet,
    FAQViewSet, ContactInquiryView, ContactInquiryDetailView, ContactInquiryStatsView
)

router = DefaultRouter()
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')
router.register(r'gallery-categories', GalleryCategoryViewSet, basename='gallery-category')
router.register(r'gallery', GalleryItemViewSet, basename='gallery')
router.register(r'partners', PartnerViewSet, basename='partner')
router.register(r'faqs', FAQViewSet, basename='faq')

urlpatterns = [
    path('landing-page/', LandingPageView.as_view(), name='landing-page'),
    path('profile/', HotelProfileView.as_view(), name='hotel-profile'),
    
    # Bank Details endpoints
    path('bank-details/', HotelBankDetailsView.as_view(), name='hotel-bank-details'),
    path('public-bank-details/', PublicBankDetailsView.as_view(), name='public-bank-details'),
    
    # Contact Inquiry endpoints
    path('contact-inquiry/', ContactInquiryView.as_view(), name='contact-inquiry'),
    path('contact-inquiry/<int:inquiry_id>/', ContactInquiryDetailView.as_view(), name='contact-inquiry-detail'),
    path('contact-inquiry/stats/', ContactInquiryStatsView.as_view(), name='contact-inquiry-stats'),
    
    path('', include(router.urls)),
]
