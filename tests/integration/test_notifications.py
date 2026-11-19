from datetime import date, timedelta
from io import BytesIO

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status

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
