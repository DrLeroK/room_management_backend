from django.contrib import admin
from .models import Room, RoomType, Amenity

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon', 'created_at')
    search_fields = ('name', 'code')

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'base_price_per_night', 'max_occupancy', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'floor', 'room_type', 'status', 'effective_price_per_night', 'is_active')
    list_filter = ('status', 'floor', 'room_type', 'is_active')
    search_fields = ('room_number', 'notes')
    filter_horizontal = ('amenities',)
