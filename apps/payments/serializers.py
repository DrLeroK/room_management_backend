from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_proof_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'booking', 'amount',
            'payment_type', 'payment_type_display',
            'payment_method', 'payment_method_display',
            'status', 'status_display', 'payment_proof', 'payment_proof_url',
            'transaction_reference', 'verified_at', 'verified_by',
            'verification_notes', 'recorded_by', 'payment_date', 'notes',
            'created_at', 'updated_at'
        ]

    def get_payment_proof_url(self, obj):
        if obj.payment_proof:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.payment_proof.url)
            return obj.payment_proof.url
        return None


class VerifyPaymentRequestSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    receptionist_name = serializers.CharField(required=False, default='Receptionist')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
