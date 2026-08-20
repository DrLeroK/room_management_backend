from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'employee_id', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'employee_id')
    ordering = ('role', 'username')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Staff Details', {'fields': ('role', 'phone_number', 'employee_id', 'notes')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Staff Details', {'fields': ('role', 'email', 'first_name', 'last_name', 'phone_number', 'employee_id', 'notes')}),
    )
