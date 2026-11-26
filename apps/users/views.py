from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.audit import record_audit_log
from apps.core.throttling import BruteForceLockoutThrottle, LoginRateThrottle

from .models import UserRole
from .permissions import IsManagerRole, IsOwnerRole
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from .services import (
    send_password_reset_email,
    terminate_user_sessions_and_tokens,
    verify_and_reset_password,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint returning SimpleJWT access & refresh tokens along with complete user profile payload.
    Enforces DB-backed rate limiting & brute-force lockout protection (5 failed attempts -> 15 min lockout).
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle, BruteForceLockoutThrottle]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "")

        # Pre-check if client/account is already locked out
        throttle = BruteForceLockoutThrottle()
        if not throttle.allow_request(request, self):
            return Response(
                {
                    "detail": "Account temporarily locked due to multiple failed login attempts. Please try again in 15 minutes."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
                BruteForceLockoutThrottle.reset_failed_login(request, username)
                user_obj = User.objects.filter(username=username).first()
                if user_obj:
                    record_audit_log(
                        action="AUTH_LOGIN",
                        entity_type="Auth",
                        entity_id=str(user_obj.id),
                        description=f"User '{user_obj.username}' ({user_obj.role}) logged in successfully",
                        actor=user_obj,
                        request=request,
                    )
            return response
        except Exception:
            failed_count = BruteForceLockoutThrottle.record_failed_login(request, username)
            record_audit_log(
                action="AUTH_FAILED",
                entity_type="Auth",
                entity_id=username,
                description=f"Failed login attempt for username '{username}'",
                request=request,
            )
            remaining = max(0, BruteForceLockoutThrottle.MAX_FAILED_ATTEMPTS - failed_count)

            if remaining == 0:
                return Response(
                    {
                        "detail": "Account temporarily locked due to 5 consecutive failed login attempts. Please try again in 15 minutes."
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            return Response(
                {
                    "detail": f"Invalid username or password. ({remaining} attempt(s) remaining before temporary 15-minute lockout)."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )


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
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["Incorrect current password."]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    Staff & User Management ViewSet (Managers, Owners, Admins).
    Supports listing, filtering by role, searching by name/email/username, staff creation, updates, and status toggles.
    """

    queryset = User.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "email", "first_name", "last_name", "phone_number", "employee_id"]
    ordering_fields = ["role", "username", "date_joined"]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsOwnerRole()]
        elif self.action in ["create", "update", "partial_update", "toggle_active"]:
            return [IsManagerRole()]
        return [IsManagerRole()]

    def perform_create(self, serializer):
        user = self.request.user
        target_role = serializer.validated_data.get("role", UserRole.RECEPTIONIST)
        if user.role == UserRole.MANAGER and target_role in [UserRole.OWNER, UserRole.ADMIN]:
            raise PermissionDenied("Managers are only permitted to create Receptionist or Manager accounts.")
        new_user = serializer.save()
        record_audit_log(
            action="USER_CREATED",
            entity_type="User",
            entity_id=str(new_user.id),
            description=f"Staff account '{new_user.username}' ({new_user.role}) created by {user.username}",
            actor=user,
            request=self.request,
            changes={"role": new_user.role, "email": new_user.email},
        )

    def perform_update(self, serializer):
        previous_active = serializer.instance.is_active
        updated_user = serializer.save()
        if previous_active and not updated_user.is_active:
            terminate_user_sessions_and_tokens(updated_user)

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get("role")
        is_active = self.request.query_params.get("is_active")

        if role:
            queryset = queryset.filter(role=role.upper())
        if is_active is not None:
            if is_active.lower() in ["true", "1"]:
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ["false", "0"]:
                queryset = queryset.filter(is_active=False)

        return queryset

    @action(detail=True, methods=["post"], permission_classes=[IsManagerRole])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        # Managers cannot deactivate Owners or Admins
        if request.user.role == UserRole.MANAGER and user.role in [UserRole.OWNER, UserRole.ADMIN]:
            raise PermissionDenied("Managers cannot modify the status of Owner or Admin accounts.")
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        if not user.is_active:
            terminate_user_sessions_and_tokens(user)
        status_str = "activated" if user.is_active else "deactivated"
        record_audit_log(
            action="USER_UPDATED" if user.is_active else "USER_DEACTIVATED",
            entity_type="User",
            entity_id=str(user.id),
            description=f"User account '{user.username}' was {status_str} by {request.user.username}",
            actor=request.user,
            request=request,
            changes={"is_active": user.is_active},
        )
        return Response(
            {
                "message": f"User '{user.username}' has been successfully {status_str}.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Invalidates and blacklists the client's refresh token on the server,
    preventing any future access token renewals with this token.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=LogoutSerializer, responses={200: dict, 400: dict})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data["refresh"]
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Successfully logged out and session revoked."},
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"detail": f"Token is invalid or already blacklisted: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PasswordResetRequestView(APIView):
    """
    Public endpoint for staff to request a password reset email link.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        # Find active user with this email
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            send_password_reset_email(user)

        # Always return generic success message to prevent user enumeration
        return Response(
            {
                "message": "If an active account exists with this email address, a password reset link has been dispatched."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Public endpoint to confirm password reset using token and set a new strong password.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_and_reset_password(
            uidb64=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )

        return Response(
            {"message": "Password has been successfully reset. You can now sign in with your new password."},
            status=status.HTTP_200_OK,
        )
