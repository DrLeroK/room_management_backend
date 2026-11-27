from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import AuditLog, Notification
from apps.core.pagination import StandardResultsSetPagination
from apps.core.serializers import AuditLogSerializer, NotificationSerializer
from apps.users.permissions import IsOwnerRole


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for in-app notifications.
    Staff members can view notifications targeted to them or their role, and mark as read.
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Notification.objects.none()

        role = getattr(user, "role", "")
        # Filter for direct recipient, matching role, or general staff (blank target_role)
        return Notification.objects.filter(Q(recipient=user) | Q(target_role=role) | Q(target_role="")).order_by(
            "-created_at"
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        unread_count = self.get_queryset().filter(is_read=False).count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["unread_count"] = unread_count
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "unread_count": unread_count,
                "results": serializer.data,
            }
        )

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
        unread_count = self.get_queryset().filter(is_read=False).count()
        serializer = self.get_serializer(notification)
        return Response(
            {
                "notification": serializer.data,
                "unread_count": unread_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        now = timezone.now()
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=now)
        return Response(
            {
                "detail": f"{updated_count} notification(s) marked as read.",
                "unread_count": 0,
            },
            status=status.HTTP_200_OK,
        )


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for system audit logs.
    Strictly restricted to Hotel Owners and Platform Administrators.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsOwnerRole]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = AuditLog.objects.all().select_related("actor").order_by("-created_at")

        action_param = self.request.query_params.get("action")
        if action_param:
            queryset = queryset.filter(action=action_param)

        entity_param = self.request.query_params.get("entity_type")
        if entity_param:
            queryset = queryset.filter(entity_type=entity_param)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search)
                | Q(actor_email__icontains=search)
                | Q(entity_id__icontains=search)
                | Q(ip_address__icontains=search)
            )

        start_date = self.request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        end_date = self.request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset
