from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "System Administrator"
    OWNER = "OWNER", "Hotel Owner"
    MANAGER = "MANAGER", "Hotel Manager"
    RECEPTIONIST = "RECEPTIONIST", "Receptionist"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.RECEPTIONIST,
        db_index=True,
        help_text="Role determining user permissions across the system",
    )
    phone_number = models.CharField(max_length=30, blank=True, default="")
    employee_id = models.CharField(max_length=30, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["role", "username"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        return f"{display_name} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_owner_role(self):
        return self.role in [UserRole.OWNER, UserRole.ADMIN] or self.is_superuser

    @property
    def is_manager_role(self):
        return self.role in [UserRole.MANAGER, UserRole.OWNER, UserRole.ADMIN] or self.is_superuser

    @property
    def is_receptionist_role(self):
        return (
            self.role in [UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.OWNER, UserRole.ADMIN] or self.is_superuser
        )
