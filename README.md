# 🏨 StayCraft — Enterprise Hotel & Room Management System (Backend API)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.15-red?style=for-the-badge&logo=django)](https://www.django-rest-framework.org/)
[![JWT](https://img.shields.io/badge/Auth-SimpleJWT-black?style=for-the-badge&logo=jsonwebtokens)](https://django-rest-framework-simplejwt.readthedocs.io/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  An enterprise-grade, high-performance Django REST Framework API for Hotel & Room Management, Multi-Role Access Control, Stay Extensions, Non-Redis DB Brute-Force Shield, Bank Transfer Verification, and Daily Front-Desk Operations.
</p>

</div>

---

## 📖 Overview

**StayCraft Backend** is a robust RESTful service built with Django and Django REST Framework. It powers all core domain operations of the StayCraft Hotel platform, including room inventory management, multi-role staff access control, online guest bookings with bank transfer screenshot proof, receptionist front desk workflows, automated SMS notifications, and financial reporting.

---

## ✨ Features & Module Architecture

### 👥 1. User Management & Role-Based Access Control (`apps/users`)
- **Custom User Model**: Extended Django user model supporting phone numbers, employee IDs, role designations, and active status.
- **4 System Roles**:
  - **`ADMIN`**: System Administrator with complete administrative rights.
  - **`OWNER`**: Hotel Owner accessing financial KPIs, pricing control, staff creation, and status toggles.
  - **`MANAGER`**: Hotel Manager supervising room inventory, front desk operations, and staff reporting.
  - **`RECEPTIONIST`**: Front Desk Receptionist handling check-ins, check-outs, stay extensions, and payment proof verifications.
- **JWT Authentication (`/api/v1/users/login/`)**: Authenticates staff and returns SimpleJWT access and refresh tokens.
- **Staff Administration API (`/api/v1/users/`)**: Allows Managers and Owners to list, create, filter, and toggle active status (`/toggle-active/`) of staff accounts.

### 🛡️ 2. Security, Rate Limiting & Brute-Force Lockout (`apps/core/throttling.py`)
- **Non-Redis Database Cache Throttling**: Utilizes `django.core.cache.backends.db.DatabaseCache` (`django_cache_table`) for reliable rate limiting without requiring external Redis servers.
- **Brute-Force Lockout (`BruteForceLockoutThrottle`)**: Tracks failed login attempts per IP/username. Automatically locks out accounts for **15 minutes** after **5 consecutive failed attempts** (`HTTP 429 Too Many Requests`). Successful logins immediately reset the counter.
- **Sensitive Action Protection**: Limits unauthenticated bookings and contact form submissions (15 requests/min).

### 🏨 3. Room Inventory & Amenities (`apps/rooms`)
- **Room Management**: Models rooms with room numbers, room types, daily rates, capacity, bed types, and operational states (*Available, Occupied, Cleaning, Maintenance*).
- **Amenities Engine**: Categorized room amenities (*Wi-Fi, Jacuzzi, Ocean View, Breakfast*) linked to room types.

### 💳 4. Booking & Stay Extension Engine (`apps/bookings`)
- **Online Booking with Proof Upload (`/api/v1/bookings/online-book/`)**: Online guests reserve rooms by uploading bank transfer screenshot proofs or transaction reference numbers.
- **Staff Payment Proof Verification (`/api/v1/bookings/reception/verify-payment/`)**: Receptionists review screenshots and approve or reject payments:
  - **On APPROVE**: Booking marked `CONFIRMED`, payment logged as `SUCCESS`, and an SMS confirmation is dispatched to the guest's phone number.
  - **On REJECT**: Booking set to `CANCELLED`, room freed for search, and SMS rejection notice sent.
- **Stay Extension Service (`/api/v1/bookings/reception/extend-stay/`)**: Atomic stay extensions validating future room availability, recalculating total cost, and logging an `EXTEND_STAY` payment record.
- **Walk-In & Reservation Check-In**: Immediate check-in with security deposit logging and key card assignment.
- **Check-Out Processing**: Log departures, calculate extra charges (mini-bar, damage fee), and update room state to `DIRTY_CLEANING`.
- **Front Desk Live Board API**: Real-time status breakdown showing occupied rooms, expected arrivals/departures, and pending verification queue.

### 💳 5. Payment Ledgers (`apps/payments`)
- **Multi-Category Payments**: Tracks financial transactions across payment types (`ONLINE_BANK_TRANSFER`, `WALK_IN_CHECK_IN`, `CHECK_OUT_FINAL`, `EXTEND_STAY`).
- **Hotel Bank Account API (`/api/v1/bookings/hotel-bank-details/`)**: Returns official hotel bank details for online guest transfers.

### 🌐 6. Hotel Landing Page CMS (`apps/content`)
- **Composite API (`/api/v1/content/landing-page/`)**: Fast single endpoint supplying hero info, featured rooms, testimonials, photo gallery, partners/sponsors, FAQs, and bank details to the frontend.
- **CMS Management**: Dynamic models for Testimonials, Gallery Photos with categories, Corporate Partners, and FAQs.

### 📊 7. Analytics & Revenue KPIs (`apps/analytics`)
- Calculates real-time total revenue, occupancy rate percentage, Average Daily Rate (ADR), and Revenue Per Available Room (RevPAR).

---

## 🔑 Pre-Seeded System Accounts

Execute `python manage.py seed_db` to populate test accounts:

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `admin` | `admin12345` | `ADMIN` | System Administrator / Superuser |
| `owner` | `owner12345` | `OWNER` | Hotel Owner |
| `manager` | `manager12345` | `MANAGER` | Hotel Manager |
| `receptionist1` | `receptionist12345` | `RECEPTIONIST` | Senior Receptionist (Helen Tesfaye) |
| `receptionist2` | `receptionist12345` | `RECEPTIONIST` | Front Desk Receptionist (Yared Alemu) |

---

## 🛠️ Tech Stack

- **Framework**: Django 6.0 & Django REST Framework 3.15
- **Authentication**: SimpleJWT (JSON Web Tokens)
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Cache & Throttling**: Database-backed cache (`django_cache_table`)
- **Testing**: Pytest & Pytest-Django (39/39 passing tests)
- **Documentation**: OpenAPI 3.0, Swagger UI & ReDoc

---

## 📁 Directory Structure

```
room_management_backend/
├── apps/
│   ├── analytics/                # Revenue totals, occupancy % & RevPAR KPIs
│   ├── bookings/                 # Bookings, check-in, check-out, extend stay service
│   ├── content/                  # CMS (Testimonials, Gallery, Partners, FAQs)
│   ├── core/                     # Database-backed rate limiting & exceptions
│   ├── guests/                   # Guest profiles & phone lookups
│   ├── payments/                 # Payment ledger (Extend Stay, Check-in, Online)
│   ├── rooms/                    # Room inventory, types & amenities
│   └── users/                    # Custom User model & 4-role access control
├── config/                       # Settings, URLs, pytest.ini & WSGI/ASGI
├── manage.py                     # Django management script
└── requirements.txt              # Backend dependencies
```

---

## 🚀 How to Clone & Run from GitHub

### 1. Clone the Repository
```bash
git clone https://github.com/DrLeroK/room_management_backend.git
cd room_management_backend
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Linux/macOS)
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run Database Migrations
```bash
python manage.py migrate
```

### 4. Create Database Cache Table (Required for Throttling)
```bash
python manage.py createcachetable
```

### 5. Seed Database with Demo Data
```bash
python manage.py seed_db
```

### 6. Run Test Suite
Verify that all 39 automated tests pass:
```bash
pytest
```

### 7. Start Development Server
```bash
python manage.py runserver 8000
```

Access API endpoints and documentation at:
- **API Base URL**: `http://localhost:8000/api/v1/`
- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`



## FRONTEND REPO

- YOU CAN FIND THE FRONTEND FOR THIS BACKEND IN A REPO - https://github.com/DrLeroK/booking-and-room-management-fr.git

---

## 🤝 Contributing

- Fork the repository
- Create your feature branch (git checkout -b feature/amazing-feature)
- Commit your changes (git commit -m 'Add some amazing feature')
- Push to the branch (git push origin feature/amazing-feature)
- Open a Pull Request

# 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.