from rest_framework import permissions
from .models import UserRole

class IsAdminRole(permissions.BasePermission):
    """
    Permission check for System Administrator role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsOwnerRole(permissions.BasePermission):
    """
    Permission check for Hotel Owner or Admin roles.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_owner_role)


class IsManagerRole(permissions.BasePermission):
    """
    Permission check for Hotel Manager, Owner, or Admin roles.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_manager_role)


class IsReceptionistRole(permissions.BasePermission):
    """
    Permission check for Receptionist, Manager, Owner, or Admin roles.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_receptionist_role)


class IsSelfOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing users to modify their own object or Admins/Owners/Managers to modify any.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_manager_role:
            return True
        return obj.id == request.user.id
