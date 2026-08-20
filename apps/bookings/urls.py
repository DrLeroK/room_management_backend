from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BookingViewSet, OnlineBookingView, GuestBookingLookupView,
    WalkInCheckInView, ReservationCheckInView, CheckOutView, ExtendStayView,
    ReceptionLiveBoardView, HotelBankDetailsView, VerifyPaymentView
)

router = DefaultRouter()
router.register(r'', BookingViewSet, basename='booking')

urlpatterns = [
    # Public online guest APIs
    path('hotel-bank-details/', HotelBankDetailsView.as_view(), name='hotel-bank-details'),
    path('online-book/', OnlineBookingView.as_view(), name='online-book'),
    path('online-lookup/', GuestBookingLookupView.as_view(), name='online-lookup'),
    
    # Receptionist & Staff verification APIs
    path('reception/verify-payment/', VerifyPaymentView.as_view(), name='reception-verify-payment'),
    path('reception/walk-in-checkin/', WalkInCheckInView.as_view(), name='reception-walk-in-checkin'),
    path('reception/checkin/', ReservationCheckInView.as_view(), name='reception-checkin'),
    path('reception/checkout/', CheckOutView.as_view(), name='reception-checkout'),
    path('reception/extend-stay/', ExtendStayView.as_view(), name='reception-extend-stay'),
    path('reception/live-board/', ReceptionLiveBoardView.as_view(), name='reception-live-board'),

    path('', include(router.urls)),
]
