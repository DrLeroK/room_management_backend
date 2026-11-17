import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import (
    Booking,
    BookingSource,
    BookingStatus,
    CheckInRecord,
    CheckOutRecord,
    PaymentMethod,
)
from apps.content.models import (
    FAQ,
    GalleryCategory,
    GalleryItem,
    HotelProfile,
    Partner,
    Testimonial,
)
from apps.guests.models import Guest, IdentificationType
from apps.payments.models import Payment, PaymentStatus, PaymentType
from apps.rooms.models import Amenity, Room, RoomStatus, RoomType
from apps.users.models import User, UserRole


class Command(BaseCommand):
    help = "Seeds database with realistic hotel room types, rooms, guests, bookings, payments, landing page CMS content, testimonials, gallery, partners, and user accounts for all roles."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding Bedroom Management database..."))

        # Seed Accounts for all 4 System Roles with Strong Passwords
        users_to_seed = [
            {
                "username": "admin",
                "email": "admin@staycraft.com",
                "password": "Admin@StayCraft2026!",
                "role": UserRole.ADMIN,
                "first_name": "System",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
                "phone_number": "+251911000001",
                "employee_id": "EMP-ADM-001",
            },
            {
                "username": "owner",
                "email": "owner@staycraft.com",
                "password": "Owner@StayCraft2026!",
                "role": UserRole.OWNER,
                "first_name": "Tewodros",
                "last_name": "Kassahun",
                "is_staff": True,
                "phone_number": "+251911000002",
                "employee_id": "EMP-OWN-001",
            },
            {
                "username": "manager",
                "email": "manager@staycraft.com",
                "password": "Manager@StayCraft2026!",
                "role": UserRole.MANAGER,
                "first_name": "Bethlehem",
                "last_name": "Tadesse",
                "is_staff": True,
                "phone_number": "+251911000003",
                "employee_id": "EMP-MGR-001",
            },
            {
                "username": "receptionist1",
                "email": "reception1@staycraft.com",
                "password": "Reception@StayCraft2026!",
                "role": UserRole.RECEPTIONIST,
                "first_name": "Helen",
                "last_name": "Tesfaye",
                "is_staff": True,
                "phone_number": "+251911000004",
                "employee_id": "EMP-REC-001",
            },
            {
                "username": "receptionist2",
                "email": "reception2@staycraft.com",
                "password": "Reception@StayCraft2026!",
                "role": UserRole.RECEPTIONIST,
                "first_name": "Yared",
                "last_name": "Alemu",
                "is_staff": True,
                "phone_number": "+251911000005",
                "employee_id": "EMP-REC-002",
            },
        ]

        for u_data in users_to_seed:
            password = u_data.pop("password")
            user_obj, created = User.objects.get_or_create(username=u_data["username"], defaults=u_data)
            user_obj.set_password(password)
            for k, v in u_data.items():
                setattr(user_obj, k, v)
            user_obj.is_active = True
            user_obj.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded accounts for all 4 roles: ADMIN, OWNER, MANAGER, RECEPTIONIST with strong passwords."
            )
        )

        # 1. Seed Hotel Profile
        profile, _ = HotelProfile.objects.get_or_create(
            id=1,
            defaults={
                "name": "StayCraft Hotel & Bedroom Resort",
                "tagline": "Luxury, Comfort, & Elegance in Every Stay",
                "about_us": "StayCraft Hotel offers world-class bedroom accommodations, gourmet dining, spa treatments, and executive conference spaces located in the heart of Addis Ababa.",
                "address": "Bole Road, Near Friendship Mall, Addis Ababa, Ethiopia",
                "contact_phone": "+251 911 223 344",
                "contact_email": "reservations@staycrafthotel.com",
                "facebook_url": "https://facebook.com/staycrafthotel",
                "instagram_url": "https://instagram.com/staycrafthotel",
                "twitter_url": "https://twitter.com/staycrafthotel",
            },
        )
        self.stdout.write(self.style.SUCCESS("Seeded Hotel Profile content."))

        # 2. Seed Testimonials
        testimonials_data = [
            {
                "guest_name": "Solomon Haile",
                "guest_title": "Business Traveler",
                "rating": 5,
                "comment": "The Executive King Suite was exceptionally clean and comfortable. Fast Wi-Fi and seamless online booking with instant SMS confirmation!",
                "display_order": 1,
            },
            {
                "guest_name": "Elena Rostova",
                "guest_title": "Tourist & Photographer",
                "rating": 5,
                "comment": "Stunning balcony view, polite front desk receptionists, and delicious breakfast buffet. Will definitely return to StayCraft!",
                "display_order": 2,
            },
            {
                "guest_name": "Marcus Vance",
                "guest_title": "Corporate Executive",
                "rating": 5,
                "comment": "Loved the quick receptionist check-in experience and modern room key card access. Top tier service in Addis Ababa.",
                "display_order": 3,
            },
        ]
        for t_data in testimonials_data:
            Testimonial.objects.get_or_create(guest_name=t_data["guest_name"], defaults=t_data)
        self.stdout.write(self.style.SUCCESS("Seeded Testimonials."))

        # 3. Seed Gallery Categories & Items
        cat_bed, _ = GalleryCategory.objects.get_or_create(
            name="Bedrooms & Suites", defaults={"slug": "bedrooms", "display_order": 1}
        )
        cat_dine, _ = GalleryCategory.objects.get_or_create(
            name="Dining & Lounge", defaults={"slug": "dining", "display_order": 2}
        )
        cat_spa, _ = GalleryCategory.objects.get_or_create(
            name="Spa & Fitness", defaults={"slug": "spa", "display_order": 3}
        )

        gallery_items_data = [
            {
                "title": "Executive King Bedroom",
                "category": cat_bed,
                "caption": "Spacious suite with king mattress and ambient lighting.",
                "display_order": 1,
            },
            {
                "title": "Penthouse Ocean View Terrace",
                "category": cat_bed,
                "caption": "Top-floor panoramic city terrace view.",
                "display_order": 2,
            },
            {
                "title": "Gourmet Restaurant & Bar",
                "category": cat_dine,
                "caption": "International & local cuisine prepared by master chefs.",
                "display_order": 3,
            },
            {
                "title": "Luxury Spa & Heated Bath",
                "category": cat_spa,
                "caption": "Relaxation massage center and hydro-tub.",
                "display_order": 4,
            },
        ]
        for g_data in gallery_items_data:
            GalleryItem.objects.get_or_create(title=g_data["title"], defaults=g_data)
        self.stdout.write(self.style.SUCCESS("Seeded Gallery Categories & Items."))

        # 4. Seed Partners & Sponsors
        partners_data = [
            {
                "name": "Ethiopian Airlines",
                "category": "Airline Partner",
                "description": "Official airline transfer partner for StayCraft guests.",
                "website_url": "https://ethiopianairlines.com",
                "display_order": 1,
            },
            {
                "name": "Commercial Bank of Ethiopia (CBE)",
                "category": "Financial Partner",
                "description": "Instant digital bank transfer integration partner.",
                "website_url": "https://combanketh.et",
                "display_order": 2,
            },
            {
                "name": "Booking.com",
                "category": "Travel Partner",
                "description": "Global hotel reservation distribution partner.",
                "website_url": "https://booking.com",
                "display_order": 3,
            },
            {
                "name": "TripAdvisor",
                "category": "Review Partner",
                "description": "Certificate of Excellence Award 2025 winner.",
                "website_url": "https://tripadvisor.com",
                "display_order": 4,
            },
        ]
        for p_data in partners_data:
            Partner.objects.get_or_create(name=p_data["name"], defaults=p_data)
        self.stdout.write(self.style.SUCCESS("Seeded Partners & Sponsors."))

        # 5. Seed FAQs
        faqs_data = [
            {
                "category": "Booking & Payment",
                "question": "How do I confirm my online room reservation via bank transfer?",
                "answer": "Search available dates, select a room, transfer total cost to CBE Account 1000123456789, and upload your payment receipt screenshot. Reception will verify and send you an SMS confirmation.",
                "display_order": 1,
            },
            {
                "category": "Check-In & Policy",
                "question": "What are the check-in and check-out times?",
                "answer": "Standard check-in starts at 2:00 PM, and check-out is by 11:00 AM. Early check-in or late check-out can be requested at reception.",
                "display_order": 2,
            },
            {
                "category": "Amenities & Services",
                "question": "Is high-speed Wi-Fi and breakfast included?",
                "answer": "Yes, all rooms include complimentary high-speed Wi-Fi (100Mbps) and daily breakfast buffet.",
                "display_order": 3,
            },
        ]
        for f_data in faqs_data:
            FAQ.objects.get_or_create(question=f_data["question"], defaults=f_data)
        self.stdout.write(self.style.SUCCESS("Seeded FAQs."))

        # 6. Seed Amenities
        amenities_data = [
            {
                "name": "High-Speed Wi-Fi",
                "code": "WIFI",
                "icon": "fa-wifi",
                "description": "100Mbps dedicated fiber Internet",
            },
            {
                "name": "Air Conditioning",
                "code": "AC",
                "icon": "fa-snowflake",
                "description": "Climate-controlled quiet AC",
            },
            {"name": "King Size Bed", "code": "KING_BED", "icon": "fa-bed", "description": "Orthopedic mattress"},
            {"name": 'Smart TV 55"', "code": "SMART_TV", "icon": "fa-tv", "description": "Netflix & Prime Enabled"},
            {
                "name": "Ocean View Balcony",
                "code": "OCEAN_VIEW",
                "icon": "fa-water",
                "description": "Panoramic sea view balcony",
            },
            {
                "name": "Mini Bar & Fridge",
                "code": "MINI_BAR",
                "icon": "fa-glass-martini",
                "description": "Stocked beverages & snacks",
            },
            {"name": "Jacuzzi Bath", "code": "JACUZZI", "icon": "fa-bath", "description": "Hydro-massage bathtub"},
            {
                "name": "Complimentary Breakfast",
                "code": "BREAKFAST",
                "icon": "fa-utensils",
                "description": "Daily buffet breakfast",
            },
        ]

        amenities_objs = []
        for item in amenities_data:
            obj, _ = Amenity.objects.get_or_create(code=item["code"], defaults=item)
            amenities_objs.append(obj)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(amenities_objs)} amenities."))

        # 7. Seed Room Types
        room_types_data = [
            {
                "name": "Standard Single Bedroom",
                "code": "STD_SGL",
                "description": "Cozy room ideal for solo travelers with ergonomic desk and single bed.",
                "base_price_per_night": 50.00,
                "max_occupancy": 1,
            },
            {
                "name": "Deluxe Double Bedroom",
                "code": "DLX_DBL",
                "description": "Spacious room featuring a queen bed, seating area, and street view.",
                "base_price_per_night": 85.00,
                "max_occupancy": 2,
            },
            {
                "name": "Executive King Suite",
                "code": "EXEC_KNG",
                "description": "Luxury suite with King bed, ocean view balcony, mini bar, and jacuzzi.",
                "base_price_per_night": 150.00,
                "max_occupancy": 2,
            },
            {
                "name": "Family Suite Bedroom",
                "code": "FAM_STE",
                "description": "Two connected bedrooms with two queen beds, extra wardrobe, and living area.",
                "base_price_per_night": 210.00,
                "max_occupancy": 4,
            },
            {
                "name": "Presidential Penthouse",
                "code": "PRES_PENT",
                "description": "Top floor suite with private terrace, hot tub, panoramic ocean view, and butler service.",
                "base_price_per_night": 450.00,
                "max_occupancy": 4,
            },
        ]

        room_type_objs = {}
        for rt_data in room_types_data:
            obj, _ = RoomType.objects.get_or_create(code=rt_data["code"], defaults=rt_data)
            room_type_objs[rt_data["code"]] = obj
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(room_type_objs)} room types."))

        # 8. Seed Rooms across 3 Floors
        rooms_list = [
            # Floor 1
            {"room_number": "101", "floor": 1, "type_code": "STD_SGL", "status": RoomStatus.AVAILABLE},
            {"room_number": "102", "floor": 1, "type_code": "STD_SGL", "status": RoomStatus.OCCUPIED},
            {"room_number": "103", "floor": 1, "type_code": "DLX_DBL", "status": RoomStatus.AVAILABLE},
            {"room_number": "104", "floor": 1, "type_code": "DLX_DBL", "status": RoomStatus.DIRTY_CLEANING},
            {
                "room_number": "105",
                "floor": 1,
                "type_code": "DLX_DBL",
                "status": RoomStatus.MAINTENANCE,
                "notes": "AC unit fan replacement",
            },
            # Floor 2
            {"room_number": "201", "floor": 2, "type_code": "DLX_DBL", "status": RoomStatus.OCCUPIED},
            {"room_number": "202", "floor": 2, "type_code": "EXEC_KNG", "status": RoomStatus.OCCUPIED},
            {"room_number": "203", "floor": 2, "type_code": "EXEC_KNG", "status": RoomStatus.AVAILABLE},
            {"room_number": "204", "floor": 2, "type_code": "FAM_STE", "status": RoomStatus.AVAILABLE},
            {"room_number": "205", "floor": 2, "type_code": "FAM_STE", "status": RoomStatus.OCCUPIED},
            # Floor 3
            {"room_number": "301", "floor": 3, "type_code": "EXEC_KNG", "status": RoomStatus.AVAILABLE},
            {"room_number": "302", "floor": 3, "type_code": "PRES_PENT", "status": RoomStatus.AVAILABLE},
        ]

        created_rooms = []
        for r_data in rooms_list:
            rt_code = r_data.pop("type_code")
            r_data["room_type"] = room_type_objs[rt_code]
            notes = r_data.pop("notes", "")
            room_obj, created = Room.objects.get_or_create(
                room_number=r_data["room_number"], defaults={**r_data, "notes": notes}
            )
            room_obj.amenities.set(amenities_objs[: random.randint(3, 7)])
            created_rooms.append(room_obj)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_rooms)} hotel bedrooms."))

        # 9. Seed Guests
        guests_data = [
            {
                "first_name": "Latera",
                "last_name": "Dereje",
                "phone_number": "+251911223344",
                "email": "latera@example.com",
                "identification_type": IdentificationType.PASSPORT,
                "identification_number": "P982341",
            },
            {
                "first_name": "Abebe",
                "last_name": "Bikila",
                "phone_number": "+251912345678",
                "email": "abebe@example.com",
                "identification_type": IdentificationType.NATIONAL_ID,
                "identification_number": "ID-88231",
            },
            {
                "first_name": "Sarah",
                "last_name": "Connor",
                "phone_number": "+15550192834",
                "email": "sarah.c@example.com",
                "identification_type": IdentificationType.PASSPORT,
                "identification_number": "US-776123",
            },
            {
                "first_name": "Michael",
                "last_name": "Scott",
                "phone_number": "+15559876543",
                "email": "mscott@dundermifflin.com",
                "identification_type": IdentificationType.DRIVERS_LICENSE,
                "identification_number": "DL-44812",
            },
            {
                "first_name": "Bruce",
                "last_name": "Wayne",
                "phone_number": "+15550000007",
                "email": "bruce@wayne.com",
                "identification_type": IdentificationType.PASSPORT,
                "identification_number": "P-007007",
            },
            {
                "first_name": "Diana",
                "last_name": "Prince",
                "phone_number": "+15559998877",
                "email": "diana@amazon.org",
                "identification_type": IdentificationType.NATIONAL_ID,
                "identification_number": "ID-100200",
            },
        ]

        created_guests = []
        for g_data in guests_data:
            guest_obj, _ = Guest.objects.get_or_create(phone_number=g_data["phone_number"], defaults=g_data)
            created_guests.append(guest_obj)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_guests)} guest records."))

        # 10. Seed Past & Current Bookings, Check-ins, Check-outs and Payments
        today = timezone.now().date()

        # Past Completed Stay
        room_101 = Room.objects.get(room_number="101")
        b_past1 = Booking.objects.create(
            guest=created_guests[1],
            room=room_101,
            booking_source=BookingSource.WALK_IN,
            status=BookingStatus.CHECKED_OUT,
            check_in_date=today - timedelta(days=4),
            check_out_date=today - timedelta(days=1),
            nightly_rate=room_101.effective_price_per_night,
            total_amount=room_101.effective_price_per_night * 3,
        )
        CheckInRecord.objects.create(
            booking=b_past1,
            receptionist_name="Helen Tesfaye",
            actual_check_in_time=timezone.now() - timedelta(days=4),
            money_received=150.00,
            payment_method=PaymentMethod.CASH,
            key_card_number="KC-101-A",
        )
        Payment.objects.create(
            booking=b_past1,
            amount=150.00,
            payment_type=PaymentType.CHECKIN_PAYMENT,
            payment_method=PaymentMethod.CASH,
            status=PaymentStatus.SUCCESS,
            recorded_by="Helen Tesfaye",
            payment_date=timezone.now() - timedelta(days=4),
        )
        CheckOutRecord.objects.create(
            booking=b_past1,
            receptionist_name="Helen Tesfaye",
            actual_check_out_time=timezone.now() - timedelta(days=1),
            additional_charges=15.00,
            additional_charges_notes="Mini bar water and juice",
            final_amount_paid=15.00,
            payment_method=PaymentMethod.CASH,
            room_inspected=True,
        )
        Payment.objects.create(
            booking=b_past1,
            amount=15.00,
            payment_type=PaymentType.ADDITIONAL_CHARGE,
            payment_method=PaymentMethod.CASH,
            status=PaymentStatus.SUCCESS,
            recorded_by="Helen Tesfaye",
            payment_date=timezone.now() - timedelta(days=1),
        )

        # Active Checked-in Stay
        room_102 = Room.objects.get(room_number="102")
        b_active1 = Booking.objects.create(
            guest=created_guests[3],
            room=room_102,
            booking_source=BookingSource.WALK_IN,
            status=BookingStatus.CHECKED_IN,
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=2),
            nightly_rate=room_102.effective_price_per_night,
            total_amount=room_102.effective_price_per_night * 3,
        )
        CheckInRecord.objects.create(
            booking=b_active1,
            receptionist_name="Yared Alemu",
            actual_check_in_time=timezone.now() - timedelta(days=1),
            money_received=150.00,
            deposit_amount=20.00,
            payment_method=PaymentMethod.CARD,
            key_card_number="KC-102-B",
        )
        Payment.objects.create(
            booking=b_active1,
            amount=170.00,
            payment_type=PaymentType.CHECKIN_PAYMENT,
            payment_method=PaymentMethod.CARD,
            status=PaymentStatus.SUCCESS,
            recorded_by="Yared Alemu",
            payment_date=timezone.now() - timedelta(days=1),
        )

        # Online Booking PENDING PAYMENT VERIFICATION
        room_204 = Room.objects.get(room_number="204")
        b_pending = Booking.objects.create(
            guest=created_guests[2],
            room=room_204,
            booking_source=BookingSource.ONLINE,
            status=BookingStatus.PENDING_PAYMENT_VERIFICATION,
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=5),
            nightly_rate=room_204.effective_price_per_night,
            total_amount=room_204.effective_price_per_night * 3,
            special_requests="Transferred 630 ETB via CBE Birr.",
        )
        Payment.objects.create(
            booking=b_pending,
            amount=room_204.effective_price_per_night * 3,
            payment_type=PaymentType.ONLINE_PREPAYMENT,
            payment_method=PaymentMethod.ONLINE_TRANSFER,
            status=PaymentStatus.PENDING_VERIFICATION,
            transaction_reference="CBE-BIRR-TXN-998822",
            recorded_by="Online Guest",
            notes="Bank transfer screenshot uploaded by guest. Waiting receptionist verification.",
        )

        # Verified Online Reservation
        room_203 = Room.objects.get(room_number="203")
        b_verified = Booking.objects.create(
            guest=created_guests[0],
            room=room_203,
            booking_source=BookingSource.ONLINE,
            status=BookingStatus.CONFIRMED,
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            nightly_rate=room_203.effective_price_per_night,
            total_amount=room_203.effective_price_per_night * 2,
            special_requests="Late arrival around 8 PM. High floor preferred.",
        )
        Payment.objects.create(
            booking=b_verified,
            amount=room_203.effective_price_per_night * 2,
            payment_type=PaymentType.ONLINE_PREPAYMENT,
            payment_method=PaymentMethod.ONLINE_TRANSFER,
            status=PaymentStatus.SUCCESS,
            transaction_reference="CBE-TXN-771122",
            verified_at=timezone.now(),
            verified_by="Yared Receptionist",
            verification_notes="Verified receipt with CBE Mobile app.",
            recorded_by="Online Guest",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded bookings, check-ins, check-outs, CMS landing page content, and payment verifications."
            )
        )
        self.stdout.write(self.style.SUCCESS("Bedroom Management Database is ready!"))
