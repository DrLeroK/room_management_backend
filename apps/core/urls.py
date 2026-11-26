from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.views import AuditLogViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", include(router.urls)),
]
