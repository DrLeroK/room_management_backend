import csv
import io
from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone
from django.db import models  # Add this import for aggregation
from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.guests.models import Guest

def export_bookings_to_csv(start_date=None, end_date=None, status=None):
    """Export bookings data to CSV"""
    queryset = Booking.objects.select_related('guest', 'room')
    
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)
    if status:
        queryset = queryset.filter(status=status)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'Booking Reference', 'Guest Name', 'Guest Phone', 'Room Number',
        'Check-in Date', 'Check-out Date', 'Nights', 'Total Amount',
        'Status', 'Booking Source', 'Created At'
    ])
    
    for booking in queryset:
        writer.writerow([
            booking.booking_reference,
            booking.guest.full_name,
            booking.guest.phone_number,
            booking.room.room_number,
            booking.check_in_date.strftime('%Y-%m-%d') if booking.check_in_date else '',
            booking.check_out_date.strftime('%Y-%m-%d') if booking.check_out_date else '',
            booking.total_nights,
            str(booking.total_amount),
            booking.status,
            booking.booking_source,
            booking.created_at.strftime('%Y-%m-%d %H:%M:%S') if booking.created_at else '',
        ])
    
    return output.getvalue()


def export_payments_to_csv(start_date=None, end_date=None, status=None):
    """Export payments data to CSV"""
    queryset = Payment.objects.select_related('booking', 'booking__guest')
    
    if start_date:
        queryset = queryset.filter(payment_date__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(payment_date__date__lte=end_date)
    if status:
        queryset = queryset.filter(status=status)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Transaction ID', 'Guest Name', 'Guest Phone', 'Booking Reference',
        'Amount', 'Payment Type', 'Payment Method', 'Status',
        'Payment Date', 'Verified By', 'Notes'
    ])
    
    for payment in queryset:
        writer.writerow([
            payment.transaction_id,
            payment.booking.guest.full_name if payment.booking and payment.booking.guest else 'N/A',
            payment.booking.guest.phone_number if payment.booking and payment.booking.guest else 'N/A',
            payment.booking.booking_reference if payment.booking else 'N/A',
            str(payment.amount),
            payment.payment_type,
            payment.payment_method,
            payment.status,
            payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else '',
            payment.verified_by or 'N/A',
            payment.notes or '',
        ])
    
    return output.getvalue()


def export_guests_to_csv(start_date=None, end_date=None):
    """Export guest data to CSV"""
    queryset = Guest.objects.all()
    
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Guest ID', 'Full Name', 'Phone Number', 'Email',
        'ID Type', 'ID Number', 'Address', 'Created At',
        'Total Bookings', 'Total Spent'
    ])
    
    for guest in queryset:
        total_bookings = guest.bookings.count()
        total_spent = guest.bookings.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
        
        writer.writerow([
            guest.id,
            guest.full_name,
            guest.phone_number,
            guest.email,
            guest.identification_type,
            guest.identification_number or '',
            guest.address or '',
            guest.created_at.strftime('%Y-%m-%d %H:%M:%S') if guest.created_at else '',
            total_bookings,
            str(total_spent),
        ])
    
    return output.getvalue()
