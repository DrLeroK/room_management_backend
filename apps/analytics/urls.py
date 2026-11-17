from django.urls import path

from .views import (
    DailyAnalyticsView,
    DashboardSummaryView,
    ExportBookingsView,
    ExportGuestsView,
    ExportPaymentsView,
    WeeklyAnalyticsView,
)

urlpatterns = [
    # Analytics endpoints
    path("daily/", DailyAnalyticsView.as_view(), name="analytics-daily"),
    path("weekly/", WeeklyAnalyticsView.as_view(), name="analytics-weekly"),
    path("summary/", DashboardSummaryView.as_view(), name="analytics-summary"),
    # Export endpoints
    path("export/bookings/", ExportBookingsView.as_view(), name="export-bookings"),
    path("export/payments/", ExportPaymentsView.as_view(), name="export-payments"),
    path("export/guests/", ExportGuestsView.as_view(), name="export-guests"),
]
