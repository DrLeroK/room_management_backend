from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.content.models import (
    FAQ,
    ContactInquiry,
    GalleryCategory,
    GalleryItem,
    HotelProfile,
    Partner,
    Testimonial,
)
from apps.users.models import User, UserRole


class ContentAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager_test", password="Password123!", role=UserRole.MANAGER)
        self.client.force_authenticate(user=self.user)

        self.profile = HotelProfile.objects.create(
            name="StayCraft Grand Hotel",
            tagline="Experience Luxury Redefined",
            about_us="A premier destination for relaxation and luxury stay.",
        )
        self.category = GalleryCategory.objects.create(name="Bedrooms", slug="bedrooms")
        self.gallery_item = GalleryItem.objects.create(
            title="Executive Suite Bedroom", category=self.category, caption="Spacious king bed with ocean view"
        )
        self.testimonial = Testimonial.objects.create(
            guest_name="Abebe Bikila",
            guest_title="Marathon Champion",
            rating=5,
            comment="Outstanding room service and high quality bedroom.",
        )
        self.partner = Partner.objects.create(
            name="Ethiopian Airlines", category="Airline Partner", website_url="https://ethiopianairlines.com"
        )
        self.faq = FAQ.objects.create(
            category="Check-In", question="What is check-in time?", answer="Check-in starts at 2:00 PM."
        )

    def test_landing_page_composite_api(self):
        url = reverse("landing-page")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("hotel_profile", response.data)
        self.assertIn("testimonials", response.data)
        self.assertIn("gallery", response.data)
        self.assertIn("partners", response.data)
        self.assertIn("faqs", response.data)
        self.assertIn("bank_transfer_details", response.data)
        self.assertEqual(response.data["hotel_profile"]["name"], "StayCraft Grand Hotel")
        self.assertEqual(len(response.data["testimonials"]), 1)
        self.assertEqual(len(response.data["gallery"]), 1)

    def test_hotel_profile_api(self):
        url = reverse("hotel-profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "StayCraft Grand Hotel")

        # Update profile via PUT
        update_payload = {"name": "StayCraft Luxury Hotel"}
        put_response = self.client.put(url, data=update_payload, format="json")
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)
        self.assertEqual(put_response.data["name"], "StayCraft Luxury Hotel")

    def test_testimonials_api(self):
        url = reverse("testimonial-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_gallery_api(self):
        url = reverse("gallery-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Executive Suite Bedroom")

    def test_partners_api(self):
        url = reverse("partner-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_faqs_api(self):
        url = reverse("faq-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_contact_inquiry_submission(self):
        url = reverse("contact-inquiry")
        payload = {
            "name": "Haile Gebrselassie",
            "email": "haile@example.com",
            "phone": "+251911223344",
            "subject": "Conference Room Booking Inquiry",
            "message": "Hello, I would like to inquire about booking 5 executive bedrooms for next month.",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContactInquiry.objects.count(), 1)
        self.assertEqual(ContactInquiry.objects.first().name, "Haile Gebrselassie")
