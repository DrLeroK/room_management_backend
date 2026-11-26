from rest_framework import serializers

from apps.core.models import AuditLog, Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source="get_notification_type_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "notification_type_display",
            "target_role",
            "link",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "read_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_name",
            "actor_email",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "description",
            "changes",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            name = obj.actor.get_full_name()
            return name if name else obj.actor.username
        return obj.actor_email or "System"
