from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
from .serializers import DailyAnalyticsQuerySerializer, WeeklyAnalyticsQuerySerializer
from .services import get_daily_analytics, get_weekly_analytics, get_dashboard_summary
from .export_services import (
    export_bookings_to_csv,
    export_payments_to_csv,
    export_guests_to_csv
)
from drf_spectacular.utils import extend_schema, OpenApiParameter

class DailyAnalyticsView(APIView):
    """
    Returns daily room occupancy, revenue breakdown, check-in/out counts, and key performance indicators.
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(name='date', description='Target date (YYYY-MM-DD)', required=False, type=str)
        ]
    )
    def get(self, request):
        serializer = DailyAnalyticsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data.get('date')

        res = get_daily_analytics(target_date)
        return Response(res, status=status.HTTP_200_OK)


class WeeklyAnalyticsView(APIView):
    """
    Returns 7-day weekly breakdown, total revenue, weekly check-in/out counts,
    average occupancy rate, and room type performance.
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(name='start_date', description='Week start date (YYYY-MM-DD)', required=False, type=str)
        ]
    )
    def get(self, request):
        serializer = WeeklyAnalyticsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        start_date = serializer.validated_data.get('start_date')

        res = get_weekly_analytics(start_date)
        return Response(res, status=status.HTTP_200_OK)


class DashboardSummaryView(APIView):
    """
    Returns summary overview metrics for high-level management dashboard.
    """
    def get(self, request):
        res = get_dashboard_summary()
        return Response(res, status=status.HTTP_200_OK)


# ============ EXPORT VIEWS ============

class ExportBookingsView(APIView):
    """
    Export bookings data to CSV file.
    """
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        csv_data = export_bookings_to_csv(start_date, end_date, status_filter)
        
        response = HttpResponse(csv_data, content_type='text/csv')
        filename = f"bookings_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ExportPaymentsView(APIView):
    """
    Export payments data to CSV file.
    """
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        csv_data = export_payments_to_csv(start_date, end_date, status_filter)
        
        response = HttpResponse(csv_data, content_type='text/csv')
        filename = f"payments_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ExportGuestsView(APIView):
    """
    Export guest data to CSV file.
    """
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        csv_data = export_guests_to_csv(start_date, end_date)
        
        response = HttpResponse(csv_data, content_type='text/csv')
        filename = f"guests_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
