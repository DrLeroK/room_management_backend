import os
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
    ContactInquiry,
    GalleryCategory,
    GalleryItem,
    HotelBankDetails,
    HotelProfile,
    Partner,
    Testimonial,
)
from apps.core.models import Notification
from apps.guests.models import Guest, IdentificationType
from apps.payments.models import Payment, PaymentStatus, PaymentType
from apps.rooms.models import Amenity, Room, RoomStatus, RoomType
from apps.users.models import User, UserRole


class Command(BaseCommand):
    help = "Seeds database with realistic hotel room types, rooms, guests, bookings, payments, landing page CMS content, testimonials, gallery, partners, and user accounts for all roles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force seeding even if database already contains users or rooms (overrides Zero-Data-Loss guard).",
        )

    def handle(self, *args, **options):
        force_seed = options.get("force", False) or os.environ.get("FORCE_SEED", "").lower() in ("true", "1")

        # Zero-Data-Loss Guard: Only run seed once on initial deployment!
        has_users = User.objects.filter(role__in=[UserRole.ADMIN, UserRole.OWNER, UserRole.MANAGER]).exists()
        has_rooms = Room.objects.exists()

        if (has_users or has_rooms) and not force_seed:
            self.stdout.write(
                self.style.SUCCESS(
                    "ℹ️ [Zero-Data-Loss Guard] Database has already been initialized (Users or Rooms exist).\n"
                    "🔒 Skipping database seed execution to preserve live production data on redeployment.\n"
                    "   (To re-seed in development, pass --force or set FORCE_SEED=true)"
                )
            )
            return

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
        profile_data = {
            "name": "StayCraft Luxury Hotel & Spa",
            "tagline": "Refined Ethiopian Hospitality & Modern Luxury",
            "about_us": "StayCraft Hotel offers world-class bedroom accommodations, gourmet dining, restorative spa treatments, and executive conference spaces located in the heart of Addis Ababa.",
            "address": "Bole Road, Near Friendship Business Center, Addis Ababa, Ethiopia",
            "contact_phone": "+251 911 223 344",
            "contact_email": "reservations@staycrafthotel.com",
            "hero_image": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1600&q=80",
            "facebook_url": "https://facebook.com/staycrafthotel",
            "instagram_url": "https://instagram.com/staycrafthotel",
            "twitter_url": "https://twitter.com/staycrafthotel",
        }
        profile, created = HotelProfile.objects.get_or_create(id=1, defaults=profile_data)
        if not created:
            for k, v in profile_data.items():
                setattr(profile, k, v)
            profile.save()
        self.stdout.write(self.style.SUCCESS("Seeded Hotel Profile content with hero image."))

        # 2. Seed Testimonials with genuine guest avatars
        testimonials_data = [
            {
                "guest_name": "Solomon Haile",
                "guest_title": "Business Executive",
                "rating": 5,
                "comment": "The Executive King Suite was exceptionally clean, comfortable, and quiet. Fast Wi-Fi and seamless online booking with instant SMS confirmation!",
                "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
                "display_order": 1,
            },
            {
                "guest_name": "Elena Rostova",
                "guest_title": "Travel Journalist & Photographer",
                "rating": 5,
                "comment": "Stunning balcony view, polite front desk receptionists, and delicious breakfast buffet. Will definitely return to StayCraft next time I visit Ethiopia!",
                "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=300&q=80",
                "display_order": 2,
            },
            {
                "guest_name": "Marcus Vance",
                "guest_title": "Corporate Consultant",
                "rating": 5,
                "comment": "Loved the quick receptionist check-in experience and modern room key card access. Top tier 5-star service in Addis Ababa.",
                "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
                "display_order": 3,
            },
            {
                "guest_name": "Bethel Tsegaye",
                "guest_title": "Diplomatic Attaché",
                "rating": 5,
                "comment": "Exquisite hospitality, reliable security, and top-of-the-line amenities. The presidential penthouse surpassed every expectation.",
                "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=300&q=80",
                "display_order": 4,
            },
        ]
        for t_data in testimonials_data:
            t_obj, t_created = Testimonial.objects.get_or_create(guest_name=t_data["guest_name"], defaults=t_data)
            if not t_created:
                for k, v in t_data.items():
                    setattr(t_obj, k, v)
                t_obj.save()
        self.stdout.write(self.style.SUCCESS("Seeded Testimonials with realistic photos."))

        # 3. Seed Gallery Categories & Items with High-Resolution Photos
        cat_bed, _ = GalleryCategory.objects.get_or_create(
            name="Bedrooms & Suites", defaults={"slug": "bedrooms", "display_order": 1}
        )
        cat_dine, _ = GalleryCategory.objects.get_or_create(
            name="Dining & Lounge", defaults={"slug": "dining", "display_order": 2}
        )
        cat_spa, _ = GalleryCategory.objects.get_or_create(
            name="Spa & Fitness", defaults={"slug": "spa", "display_order": 3}
        )
        cat_arch, _ = GalleryCategory.objects.get_or_create(
            name="Architecture & Grounds", defaults={"slug": "architecture", "display_order": 4}
        )

        gallery_items_data = [
            {
                "title": "Executive King Bedroom",
                "category": cat_bed,
                "caption": "Spacious master bedroom with plush king mattress, ambient lighting, and panoramic city views.",
                "image": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
                "display_order": 1,
            },
            {
                "title": "Presidential Penthouse Suite",
                "category": cat_bed,
                "caption": "Top-floor panoramic city terrace view with private jacuzzi and lounge parlor.",
                "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
                "display_order": 2,
            },
            {
                "title": "Deluxe Double Bedroom",
                "category": cat_bed,
                "caption": "Contemporary elegance featuring premium queen bedding and ergonomic executive workstation.",
                "image": "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
                "display_order": 3,
            },
            {
                "title": "Gourmet Restaurant & Bar",
                "category": cat_dine,
                "caption": "International & traditional Ethiopian gourmet cuisine prepared by award-winning chefs.",
                "image": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1200&q=80",
                "display_order": 4,
            },
            {
                "title": "Rooftop Sunset Lounge & Cocktail Bar",
                "category": cat_dine,
                "caption": "Artisanal cocktails, fine wine selection, and sweeping skyline sunset views.",
                "image": "https://images.unsplash.com/photo-1572116469696-31de0f17cc34?auto=format&fit=crop&w=1200&q=80",
                "display_order": 5,
            },
            {
                "title": "Luxury Spa & Hydro-Massage Bath",
                "category": cat_spa,
                "caption": "Holistic relaxation treatments, herbal steam baths, and therapeutic massages.",
                "image": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=1200&q=80",
                "display_order": 6,
            },
            {
                "title": "Skyline Heated Infinity Pool",
                "category": cat_spa,
                "caption": "Heated swimming pool with private cabanas and deck loungers.",
                "image": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",
                "display_order": 7,
            },
            {
                "title": "Grand Hotel Lobby & Reception",
                "category": cat_arch,
                "caption": "Welcoming marble atrium, gold-accented chandeliers, and 24/7 concierge desk.",
                "image": "https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=1200&q=80",
                "display_order": 8,
            },
        ]
        for g_data in gallery_items_data:
            g_obj, g_created = GalleryItem.objects.get_or_create(title=g_data["title"], defaults=g_data)
            if not g_created:
                for k, v in g_data.items():
                    setattr(g_obj, k, v)
                g_obj.save()
        self.stdout.write(self.style.SUCCESS("Seeded Gallery Categories & Items with luxury photography."))

        # 3b. Seed Multiple Bank Accounts for Payments
        banks_data = [
            {
                "bank_name": "Commercial Bank of Ethiopia (CBE)",
                "account_name": "StayCraft Hotel PLC",
                "account_number": "1000123456789",
                "branch_name": "Finfine Main Branch",
                "swift_code": "CBETETAA",
                "instructions": "Transfer total reservation amount via CBE Mobile or CBE Birr. Upload screenshot of successful transaction debit.",
                "is_active": True,
                "display_order": 1,
            },
            {
                "bank_name": "Telebirr SuperApp",
                "account_name": "StayCraft Hotel & Resort",
                "account_number": "0911223344",
                "branch_name": "Ethio Telecom Digital",
                "instructions": "Send payment to Merchant / Account 0911223344 on Telebirr app. Attach receipt screenshot.",
                "is_active": True,
                "display_order": 2,
            },
            {
                "bank_name": "Awash Bank",
                "account_name": "StayCraft Hospitality Services",
                "account_number": "01304123456700",
                "branch_name": "Bole Medhanialem Branch",
                "swift_code": "AWINETA",
                "instructions": "Transfer via Awash Online or Mobile Banking. Ensure transaction description specifies your booking reference.",
                "is_active": True,
                "display_order": 3,
            },
            {
                "bank_name": "Bank of Abyssinia (BOA)",
                "account_name": "StayCraft Hotel Operations",
                "account_number": "20938491",
                "branch_name": "Bole Atlas Branch",
                "swift_code": "ABYSETAA",
                "instructions": "Transfer via BOA mobile banking app. Front desk verifies within 15 minutes.",
                "is_active": True,
                "display_order": 4,
            },
        ]
        for idx, b_data in enumerate(banks_data, start=1):
            b_obj = HotelBankDetails.objects.filter(id=idx).first()
            if not b_obj:
                b_obj = HotelBankDetails.objects.filter(bank_name=b_data["bank_name"]).first()
            if b_obj:
                for k, v in b_data.items():
                    setattr(b_obj, k, v)
                b_obj.save()
            else:
                HotelBankDetails.objects.create(**b_data)
        self.stdout.write(self.style.SUCCESS("Seeded Hotel Bank Accounts (CBE, Telebirr, Awash, BOA)."))

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

        # 7. Seed Room Types with Luxury Unsplash Photos & ETB Pricing
        room_types_data = [
            {
                "name": "Standard Single Bedroom",
                "code": "STD_SGL",
                "description": "Cozy, soundproof room designed for solo travelers with ergonomic executive desk, smart TV, and premium single bedding.",
                "base_price_per_night": 1500.00,
                "max_occupancy": 1,
                "image": "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Deluxe Double Bedroom",
                "code": "DLX_DBL",
                "description": "Spacious room featuring a plush queen-sized bed, seating area, ambient smart lighting, and city street view.",
                "base_price_per_night": 2800.00,
                "max_occupancy": 2,
                "image": "https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Executive King Suite",
                "code": "EXEC_KNG",
                "description": "Luxury suite with orthopedic King bed, private balcony, marble bathroom, mini bar, espresso station, and jacuzzi.",
                "base_price_per_night": 4500.00,
                "max_occupancy": 2,
                "image": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Family Suite Bedroom",
                "code": "FAM_STE",
                "description": "Two connected bedrooms with two queen beds, extra wardrobe, expansive living lounge, and dining nook.",
                "base_price_per_night": 6800.00,
                "max_occupancy": 4,
                "image": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Presidential Penthouse",
                "code": "PRES_PENT",
                "description": "Top floor grand suite with private terrace, heated jacuzzi, panoramic Addis Ababa skyline views, VIP chauffeur, and dedicated butler.",
                "base_price_per_night": 15000.00,
                "max_occupancy": 4,
                "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
            },
        ]

        room_type_objs = {}
        for rt_data in room_types_data:
            obj, created = RoomType.objects.get_or_create(code=rt_data["code"], defaults=rt_data)
            if not created:
                for k, v in rt_data.items():
                    setattr(obj, k, v)
                obj.save()
            room_type_objs[rt_data["code"]] = obj
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(room_type_objs)} room types with genuine photos & ETB prices.")
        )

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

        # 11. Seed In-App Notifications for Reception and Manager Dashboards
        notif_items = [
            {
                "title": "Welcome to StayCraft Management System",
                "message": "System running with Zero-Trust RBAC, real-time live board, and multi-bank payment verifications.",
                "notification_type": "SYSTEM",
                "target_role": "MANAGER",
                "link": "/manager",
            },
            {
                "title": "New Online Booking #BK-998822 Submitted",
                "message": "Guest Sarah Connor uploaded bank transfer proof for Room 204. Pending verification.",
                "notification_type": "BOOKING",
                "target_role": "RECEPTIONIST",
                "link": "/reception/payments",
            },
            {
                "title": "New Guest Inquiry: Airport Shuttle Pickup",
                "message": "From Dawit Bekele (dawit@example.com): Inquiring about VIP airport pickup schedule for upcoming stay.",
                "notification_type": "SYSTEM",
                "target_role": "RECEPTIONIST",
                "link": "/manager/inquiries",
            },
        ]
        for n_data in notif_items:
            Notification.objects.get_or_create(title=n_data["title"], defaults=n_data)
        self.stdout.write(self.style.SUCCESS("Seeded sample in-app notifications."))

        # 12. Seed Guest Inquiries
        inquiry_items = [
            {
                "name": "Dawit Bekele",
                "email": "dawit@example.com",
                "phone": "+251911887766",
                "subject": "Airport Shuttle Pickup Request",
                "message": "Hello, I will be landing at Bole International Airport on Ethiopian Airlines flight ET 500 at 7:30 PM. Does the hotel provide an executive airport pickup shuttle?",
                "status": ContactInquiry.StatusChoices.NEW,
            },
            {
                "name": "Emily Chen",
                "email": "emily.chen@globaltech.org",
                "phone": "+14155552671",
                "subject": "Conference Room & Executive Catering Inquiry",
                "message": "We are hosting an East African tech symposium for 25 executives next month and would like to reserve meeting facilities along with 10 executive suites.",
                "status": ContactInquiry.StatusChoices.IN_PROGRESS,
            },
        ]
        for inq in inquiry_items:
            ContactInquiry.objects.get_or_create(email=inq["email"], subject=inq["subject"], defaults=inq)
        self.stdout.write(self.style.SUCCESS("Seeded sample guest inquiries."))

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded bookings, check-ins, check-outs, CMS landing page content, notifications, and payment verifications."
            )
        )
        self.stdout.write(self.style.SUCCESS("Bedroom Management Database is ready!"))
