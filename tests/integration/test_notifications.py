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
