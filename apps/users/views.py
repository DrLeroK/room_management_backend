from rest_framework import viewsets, filters, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema

from .models import UserRole
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    CustomTokenObtainPairSerializer, ChangePasswordSerializer
)
from .permissions import IsManagerRole, IsOwnerRole, IsAdminRole, IsSelfOrAdmin

User = get_user_model()

from apps.core.throttling import LoginRateThrottle, BruteForceLockoutThrottle

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint returning SimpleJWT access & refresh tokens along with complete user profile payload.
    Enforces DB-backed rate limiting & brute-force lockout protection (5 failed attempts -> 15 min lockout).
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle, BruteForceLockoutThrottle]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')

        # Pre-check if client/account is already locked out
        throttle = BruteForceLockoutThrottle()
        if not throttle.allow_request(request, self):
            return Response({
                'detail': 'Account temporarily locked due to multiple failed login attempts. Please try again in 15 minutes.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
                BruteForceLockoutThrottle.reset_failed_login(request, username)
            return response
        except Exception as exc:
            failed_count = BruteForceLockoutThrottle.record_failed_login(request, username)
            remaining = max(0, BruteForceLockoutThrottle.MAX_FAILED_ATTEMPTS - failed_count)

            if remaining == 0:
                return Response({
                    'detail': 'Account temporarily locked due to 5 consecutive failed login attempts. Please try again in 15 minutes.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            return Response({
                'detail': f"Invalid username or password. ({remaining} attempt(s) remaining before temporary 15-minute lockout)."
            }, status=status.HTTP_401_UNAUTHORIZED)


class UserProfileView(APIView):
    """
    Get or update profile details of the currently authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """
    Endpoint for authenticated users to change their account password.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={200: dict})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': ['Incorrect current password.']}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    Staff & User Management ViewSet (Managers, Owners, Admins).
    Supports listing, filtering by role, searching by name/email/username, staff creation, updates, and status toggles.
    """
    queryset = User.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'employee_id']
    ordering_fields = ['role', 'username', 'date_joined']

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'toggle_active']:
            return [IsOwnerRole()]
        elif self.action in ['update', 'partial_update']:
            return [IsManagerRole()]
        return [IsManagerRole()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')

        if role:
            queryset = queryset.filter(role=role.upper())
        if is_active is not None:
            if is_active.lower() in ['true', '1']:
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ['false', '0']:
                queryset = queryset.filter(is_active=False)

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerRole])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        status_str = "activated" if user.is_active else "deactivated"
        return Response({
            'message': f"User '{user.username}' has been successfully {status_str}.",
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
