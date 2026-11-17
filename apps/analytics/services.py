from datetime import datetime, timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.bookings.models import (
    Booking,
    BookingSource,
    BookingStatus,
    CheckInRecord,
    CheckOutRecord,
)
from apps.payments.models import Payment, PaymentMethod, PaymentStatus
from apps.rooms.models import Room, RoomStatus, RoomType


def get_daily_analytics(target_date=None):
    """
    Calculates daily performance metrics for a specific date (defaults to today).
    """
    if target_date is None:
        target_date = timezone.now().date()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    total_rooms = Room.objects.filter(is_active=True).count()
    maintenance_rooms = Room.objects.filter(is_active=True, status=RoomStatus.MAINTENANCE).count()
    available_capacity = max(total_rooms - maintenance_rooms, 1)

    # Active bookings on target_date
    active_stay_bookings = Booking.objects.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
        check_in_date__lte=target_date,
        check_out_date__gt=target_date,
    )
    rooms_sold = active_stay_bookings.count()
    occupancy_rate = round((rooms_sold / available_capacity) * 100, 2)

    # Check-ins & Check-outs on target_date
    check_ins_count = CheckInRecord.objects.filter(actual_check_in_time__date=target_date).count()
    check_outs_count = CheckOutRecord.objects.filter(actual_check_out_time__date=target_date).count()

    # Payments received on target_date
    payments_qs = Payment.objects.filter(payment_date__date=target_date, status=PaymentStatus.SUCCESS)
    total_revenue = payments_qs.aggregate(total=Sum("amount"))["total"] or 0.00

    # Revenue by payment method
    revenue_by_method = {}
    for method_choice, method_label in PaymentMethod.choices:
        amount = payments_qs.filter(payment_method=method_choice).aggregate(total=Sum("amount"))["total"] or 0.00
        revenue_by_method[method_choice] = float(amount)

    # Booking source breakdown for bookings created or active on target_date
    source_breakdown = {}
    for source_choice, source_label in BookingSource.choices:
        count = active_stay_bookings.filter(booking_source=source_choice).count()
        source_breakdown[source_choice] = count

    adr = round(float(total_revenue) / rooms_sold, 2) if rooms_sold > 0 else 0.00
    revpar = round(float(total_revenue) / available_capacity, 2) if available_capacity > 0 else 0.00

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "total_rooms": total_rooms,
        "maintenance_rooms": maintenance_rooms,
        "available_capacity": available_capacity,
        "rooms_sold": rooms_sold,
        "occupancy_rate_percentage": occupancy_rate,
        "check_ins_count": check_ins_count,
        "check_outs_count": check_outs_count,
        "total_revenue": float(total_revenue),
        "average_daily_rate_adr": adr,
        "revenue_per_available_room_revpar": revpar,
        "revenue_by_payment_method": revenue_by_method,
        "booking_source_breakdown": source_breakdown,
    }


def get_weekly_analytics(start_date=None):
    """
    Calculates weekly performance metrics starting from start_date (7 days range).
    """
    if start_date is None:
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())  # Start of current week (Monday)
    elif isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

    end_date = start_date + timedelta(days=6)

    daily_reports = []
    total_weekly_revenue = 0.00
    total_weekly_check_ins = 0
    total_weekly_check_outs = 0
    occupancy_rates_list = []

    curr_date = start_date
    while curr_date <= end_date:
        daily_res = get_daily_analytics(curr_date)
        daily_reports.append(daily_res)
        total_weekly_revenue += daily_res["total_revenue"]
        total_weekly_check_ins += daily_res["check_ins_count"]
        total_weekly_check_outs += daily_res["check_outs_count"]
        occupancy_rates_list.append(daily_res["occupancy_rate_percentage"])
        curr_date += timedelta(days=1)

    average_weekly_occupancy = (
        round(sum(occupancy_rates_list) / len(occupancy_rates_list), 2) if occupancy_rates_list else 0.00
    )

    # Popular room types performance in week
    room_types_performance = []
    for rt in RoomType.objects.all():
        rt_bookings = Booking.objects.filter(
            room__room_type=rt, check_in_date__lte=end_date, check_out_date__gte=start_date
        )
        b_count = rt_bookings.count()
        b_revenue = rt_bookings.aggregate(total=Sum("total_amount"))["total"] or 0.00
        room_types_performance.append(
            {
                "room_type_id": rt.id,
                "room_type_name": rt.name,
                "bookings_count": b_count,
                "total_revenue": float(b_revenue),
            }
        )

    return {
        "week_start_date": start_date.strftime("%Y-%m-%d"),
        "week_end_date": end_date.strftime("%Y-%m-%d"),
        "total_weekly_revenue": round(total_weekly_revenue, 2),
        "average_weekly_occupancy_percentage": average_weekly_occupancy,
        "total_weekly_check_ins": total_weekly_check_ins,
        "total_weekly_check_outs": total_weekly_check_outs,
        "room_types_performance": room_types_performance,
        "daily_breakdown": daily_reports,
    }


def get_dashboard_summary():
    """
    Returns summary overview metrics for executive staff dashboard.
    """
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    today_analytics = get_daily_analytics(today)

    week_payments = (
        Payment.objects.filter(
            payment_date__date__gte=start_of_week, payment_date__date__lte=today, status=PaymentStatus.SUCCESS
        ).aggregate(total=Sum("amount"))["total"]
        or 0.00
    )

    month_payments = (
        Payment.objects.filter(
            payment_date__date__gte=start_of_month, payment_date__date__lte=today, status=PaymentStatus.SUCCESS
        ).aggregate(total=Sum("amount"))["total"]
        or 0.00
    )

    return {
        "today_date": today.strftime("%Y-%m-%d"),
        "today_revenue": today_analytics["total_revenue"],
        "today_occupancy_rate": today_analytics["occupancy_rate_percentage"],
        "this_week_revenue": round(float(week_payments), 2),
        "this_month_revenue": round(float(month_payments), 2),
        "rooms_summary": {
            "total": today_analytics["total_rooms"],
            "occupied": today_analytics["rooms_sold"],
            "available": today_analytics["available_capacity"] - today_analytics["rooms_sold"],
            "maintenance": today_analytics["maintenance_rooms"],
        },
    }
