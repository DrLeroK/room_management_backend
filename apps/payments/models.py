import uuid
from django.db import models
from apps.core.models import TimeStampedModel
from apps.bookings.models import Booking, PaymentMethod
from django.core.validators import MinValueValidator

class PaymentType(models.TextChoices):
    DEPOSIT = 'DEPOSIT', 'Security Deposit'
    CHECKIN_PAYMENT = 'CHECKIN_PAYMENT', 'Check-in Payment'
    CHECKOUT_PAYMENT = 'CHECKOUT_PAYMENT', 'Check-out Final Balance'
    ADDITIONAL_CHARGE = 'ADDITIONAL_CHARGE', 'Additional Service Charge'
    EXTEND_STAY = 'EXTEND_STAY', 'Extend Stay Additional Charge'
    ONLINE_PREPAYMENT = 'ONLINE_PREPAYMENT', 'Online Prepayment'

class PaymentStatus(models.TextChoices):
    PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Staff Verification'
    SUCCESS = 'SUCCESS', 'Successful'
    PENDING = 'PENDING', 'Pending'
    FAILED = 'FAILED', 'Failed / Rejected'
    REFUNDED = 'REFUNDED', 'Refunded'

def generate_transaction_id():
    return f"TXN-{uuid.uuid4().hex[:10].upper()}"

class Payment(TimeStampedModel):
    transaction_id = models.CharField(
        max_length=50, 
        unique=True, 
        default=generate_transaction_id,
        db_index=True
    )
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)]
    )
    payment_type = models.CharField(
        max_length=30, 
        choices=PaymentType.choices, 
        default=PaymentType.CHECKIN_PAYMENT
    )
    payment_method = models.CharField(
        max_length=30, 
        choices=PaymentMethod.choices, 
        default=PaymentMethod.CASH
    )
    status = models.CharField(
        max_length=30, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.SUCCESS,
        db_index=True
    )
    recorded_by = models.CharField(max_length=100, default='System Receptionist')
    payment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    payment_proof = models.ImageField(upload_to='payment_proofs/%Y/%m/', null=True, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True, default='')
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=100, blank=True, default='')
    verification_notes = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.transaction_id} - ${self.amount} ({self.get_payment_type_display()}) [{self.get_status_display()}]"
