from rest_framework import serializers
from .models import Room, RoomType, Amenity, RoomStatus

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'code', 'icon', 'description', 'created_at', 'updated_at']


class RoomTypeSerializer(serializers.ModelSerializer):
    active_rooms_count = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'code', 'description', 
            'base_price_per_night', 'max_occupancy', 
            'is_active', 'active_rooms_count', 'created_at', 'updated_at'
        ]

    def get_active_rooms_count(self, obj):
        return obj.rooms.filter(is_active=True).count()


class RoomSerializer(serializers.ModelSerializer):
    room_type_details = RoomTypeSerializer(source='room_type', read_only=True)
    amenities_details = AmenitySerializer(source='amenities', many=True, read_only=True)
    effective_price_per_night = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Room
        fields = [
            'id', 'room_number', 'floor', 'room_type', 'room_type_details',
            'status', 'status_display', 'price_per_night_override',
            'effective_price_per_night', 'amenities', 'amenities_details',
            'is_active', 'notes', 'created_at', 'updated_at'
        ]


class RoomStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['status', 'notes']


class RoomAvailabilitySearchSerializer(serializers.Serializer):
    check_in_date = serializers.DateField(required=True)
    check_out_date = serializers.DateField(required=True)
    guests_count = serializers.IntegerField(required=False, default=1, min_value=1)
    room_type_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        check_in = data.get('check_in_date')
        check_out = data.get('check_out_date')
        if check_in and check_out:
            if check_in >= check_out:
                raise serializers.ValidationError({"check_out_date": "Check-out date must be strictly after check-in date."})
        return data
