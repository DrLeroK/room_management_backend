from datetime import date, timedelta
from io import BytesIO

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

from apps.bookings.services import create_online_booking, verify_online_payment
from apps.payments.models import Payment
from apps.rooms.models import Room, RoomStatus, RoomType


@pytest.mark.django_db
def test_online_booking_dispatches_email_notifications(api_client):
    # Setup Room Type and Room
    rt = RoomType.objects.create(name="Executive Suite", code="EXE", base_price_per_night=150.00, max_occupancy=2)
    room = Room.objects.create(room_number="301", floor=3, room_type=rt)
    for i in range(2, 5):
        Room.objects.create(room_number=f"30{i}", floor=3, room_type=rt, status=RoomStatus.AVAILABLE)

    mail.outbox.clear()

    # Generate a valid PNG image using Pillow
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    proof_file = SimpleUploadedFile("cbe_receipt.png", buf.read(), content_type="image/png")

    today = date.today()
    online_book_url = reverse("online-book")
    payload = {
        "room_id": room.id,
        "check_in_date": (today + timedelta(days=2)).isoformat(),
        "check_out_date": (today + timedelta(days=5)).isoformat(),
        "guest_first_name": "Solomon",
        "guest_last_name": "Kebede",
        "guest_phone_number": "+251911998877",
        "guest_email": "solomon.kebede@example.com",
        "identification_type": "PASSPORT",
        "transaction_reference": "TXN-CBE-987654321",
        "payment_proof": proof_file,
    }

    res = api_client.post(online_book_url, payload, format="multipart")
    assert res.status_code == status.HTTP_201_CREATED, res.data

    # Verify emails were dispatched: 1 to hotel staff + 1 to guest
    assert len(mail.outbox) == 2
    subjects = [m.subject for m in mail.outbox]
    assert any("NEW ONLINE BOOKING" in s for s in subjects)
    assert any("We Received Your Booking Request" in s for s in subjects)


@pytest.mark.django_db
def test_online_booking_approval_dispatches_confirmation_email_and_sms():
    # Setup Room Type and Rooms
    rt = RoomType.objects.create(name="Deluxe Suite", code="DLX", base_price_per_night=180.00, max_occupancy=2)
    room = Room.objects.create(room_number="401", floor=4, room_type=rt, status=RoomStatus.AVAILABLE)
    for i in range(2, 5):
        Room.objects.create(room_number=f"40{i}", floor=4, room_type=rt, status=RoomStatus.AVAILABLE)

    today = date.today()
    booking = create_online_booking(
        guest_data={
            "first_name": "Abebe",
            "last_name": "Bikila",
            "phone_number": "+251911223344",
            "email": "abebe@example.com",
        },
        room_id=room.id,
        check_in_date=today + timedelta(days=3),
        check_out_date=today + timedelta(days=6),
        transaction_reference="TXN-CBE-APPROVED123",
    )

    payment = Payment.objects.get(booking=booking)
    mail.outbox.clear()

    # Staff Approves Payment
    result = verify_online_payment(
        payment_id=payment.id,
        action="APPROVE",
        receptionist_name="Front Desk Manager",
        notes="Bank deposit confirmed via CBE Birr",
    )

    assert result["action"] == "APPROVED"
    assert result["sms_info"]["status"] == "SENT"
    assert result["sms_info"]["recipient"] == "+251911223344"
    assert "VERIFIED" in result["sms_info"]["message"]

    # Verify confirmation email sent to guest
    assert len(mail.outbox) == 1
    confirm_email = mail.outbox[0]
    assert "Booking Confirmed" in confirm_email.subject
    assert "abebe@example.com" in confirm_email.to
    assert booking.booking_reference in confirm_email.body


@pytest.mark.django_db
def test_online_booking_rejection_dispatches_rejection_email_and_sms():
    # Setup Room Type and Rooms
    rt = RoomType.objects.create(name="Executive Suite", code="EXE2", base_price_per_night=150.00, max_occupancy=2)
    room = Room.objects.create(room_number="501", floor=5, room_type=rt, status=RoomStatus.AVAILABLE)
    for i in range(2, 5):
        Room.objects.create(room_number=f"50{i}", floor=5, room_type=rt, status=RoomStatus.AVAILABLE)

    today = date.today()
    booking = create_online_booking(
        guest_data={
            "first_name": "Tigist",
            "last_name": "Assefa",
            "phone_number": "+251922334455",
            "email": "tigist@example.com",
        },
        room_id=room.id,
        check_in_date=today + timedelta(days=2),
        check_out_date=today + timedelta(days=5),
        transaction_reference="TXN-FAKE-REJECT999",
    )

    payment = Payment.objects.get(booking=booking)
    mail.outbox.clear()

    # Staff Rejects Payment
    result = verify_online_payment(
        payment_id=payment.id,
        action="REJECT",
        receptionist_name="Senior Receptionist",
        notes="Transaction reference not found in bank statement",
    )

    assert result["action"] == "REJECTED"
    assert result["sms_info"]["status"] == "REJECTED_NOTICE_SENT"
    assert result["sms_info"]["recipient"] == "+251922334455"
    assert "could not be verified" in result["sms_info"]["message"]

    # Verify rejection email sent to guest
    assert len(mail.outbox) == 1
    reject_email = mail.outbox[0]
    assert "Update Regarding Booking" in reject_email.subject
    assert "tigist@example.com" in reject_email.to
    assert "Transaction reference not found in bank statement" in reject_email.body


@pytest.mark.django_db
def test_in_app_notifications_lifecycle(api_client, receptionist_user, django_user_model):
    from apps.core.notifications import create_in_app_notification

    # Create notifications
    notif1 = create_in_app_notification(
        title="New Booking #BK-101",
        message="Guest Abebe booked Room 101.",
        notification_type="BOOKING_SUBMITTED",
        target_role="RECEPTIONIST",
        link="/reception/payments",
    )
    notif2 = create_in_app_notification(
        title="Payment Approved: #BK-102",
        message="Payment verified by Staff.",
        notification_type="PAYMENT_VERIFIED",
        target_role="RECEPTIONIST",
        link="/reception/bookings",
    )

    api_client.force_authenticate(user=receptionist_user)

    # 1. List notifications
    list_url = "/api/v1/notifications/"
    res = api_client.get(list_url)
    assert res.status_code == status.HTTP_200_OK
    assert res.data["unread_count"] >= 2
    assert any(n["id"] == notif1.id for n in res.data["results"])

    # 2. Mark single notification as read
    mark_read_url = f"/api/v1/notifications/{notif1.id}/mark-read/"
    res_mark = api_client.post(mark_read_url)
    assert res_mark.status_code == status.HTTP_200_OK
    assert res_mark.data["notification"]["is_read"] is True

    notif1.refresh_from_db()
    assert notif1.is_read is True

    # 3. Mark all as read
    mark_all_url = "/api/v1/notifications/mark-all-read/"
    res_all = api_client.post(mark_all_url)
    assert res_all.status_code == status.HTTP_200_OK
    assert res_all.data["unread_count"] == 0

    notif2.refresh_from_db()
    assert notif2.is_read is True


@pytest.mark.django_db
def test_audit_log_security_and_filtering(api_client, receptionist_user, owner_user):
    from apps.core.audit import record_audit_log

    # Record test audit logs
    record_audit_log(
        action="BOOKING_CREATED",
        entity_type="Booking",
        entity_id="BK-9999",
        description="Booking created for testing audit",
        actor=owner_user,
        changes={"amount": 2500.0},
    )
    record_audit_log(
        action="AUTH_LOGIN",
        entity_type="Auth",
        entity_id="1",
        description="Owner logged in",
        actor=owner_user,
    )

    # 1. Receptionist tries to access audit logs -> 403 Forbidden
    api_client.force_authenticate(user=receptionist_user)
    audit_url = "/api/v1/audit-logs/"
    res_rec = api_client.get(audit_url)
    assert res_rec.status_code == status.HTTP_403_FORBIDDEN

    # 2. Owner accesses audit logs -> 200 OK
    api_client.force_authenticate(user=owner_user)
    res_owner = api_client.get(audit_url)
    assert res_owner.status_code == status.HTTP_200_OK
    assert res_owner.data["count"] >= 2

    # 3. Filter by action
    res_filter = api_client.get(f"{audit_url}?action=BOOKING_CREATED")
    assert res_filter.status_code == status.HTTP_200_OK
    for item in res_filter.data["results"]:
        assert item["action"] == "BOOKING_CREATED"

