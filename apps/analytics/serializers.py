from rest_framework import serializers

class DailyAnalyticsQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False, help_text="Target date YYYY-MM-DD (defaults to today)")

class WeeklyAnalyticsQuerySerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, help_text="Start date of week YYYY-MM-DD (defaults to Monday of current week)")
