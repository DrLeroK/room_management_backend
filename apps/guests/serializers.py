from rest_framework import serializers
from .models import Guest

class GuestSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Guest
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone_number', 'email', 'identification_type',
            'identification_number', 'address', 'notes',
            'created_at', 'updated_at'
        ]

class GuestLookupSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
