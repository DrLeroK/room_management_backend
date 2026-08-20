from django.contrib import admin
from .models import Guest

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'email', 'identification_type', 'identification_number', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email', 'identification_number')
    list_filter = ('identification_type', 'created_at')
