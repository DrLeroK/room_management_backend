# 🏨 StayCraft — Enterprise Hotel & Room Management System (Backend API)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![DRF](https://img.shields.io/badge/DRF-3.18-red?style=for-the-badge&logo=django)](https://www.django-rest-framework.org/)
[![JWT](https://img.shields.io/badge/Auth-SimpleJWT-black?style=for-the-badge&logo=jsonwebtokens)](https://django-rest-framework-simplejwt.readthedocs.io/)
[![Pytest](https://img.shields.io/badge/Tests-67%20Passed%20(87%25%20Cov)-0A9EDC?style=for-the-badge&logo=pytest)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  An enterprise-grade, deployment-ready Django REST Framework API for Hotel & Room Inventory Management, Role-Based Access Control (RBAC), Bank Transfer Proof Verification, Automated Rate Limiting, and Daily Front-Desk Operations.
</p>

</div>

---

## 📖 Overview

**StayCraft Backend** is a production-hardened RESTful service built with Django and Django REST Framework. It powers all core domain operations of the StayCraft platform, including room inventory management, multi-role staff access control, online guest bookings with bank transfer screenshot proof, receptionist front desk workflows, and financial reporting.

---

## ✨ Features & Module Architecture

### 👥 1. User Management & Zero-Trust RBAC (`apps/users`)
- **Custom User Model**: Extended Django user model supporting phone numbers, employee IDs, role designations, and active status.
- **4 System Roles**:
  - **`ADMIN`**: System Administrator with complete administrative rights.
  - **`OWNER`**: Hotel Owner accessing financial KPIs, pricing control, staff creation, and status toggles.
  - **`MANAGER`**: Hotel Manager supervising room inventory, front desk operations, and staff reporting.
  - **`RECEPTIONIST`**: Front Desk Receptionist handling check-ins, check-outs, stay extensions, and payment proof verifications.
- **JWT Authentication (`/api/v1/users/login/`)**: Authenticates staff and returns SimpleJWT access and refresh tokens.
- **Zero-Trust Security**: Default API policy requires authentication (`IsAuthenticated`). Public endpoints are strictly isolated with explicit `AllowAny`.

### 🛡️ 2. Security, Rate Limiting & Brute-Force Lockout (`apps/core/throttling.py`)
- **Non-Redis Database Cache Throttling**: Utilizes `django.core.cache.backends.db.DatabaseCache` (`django_cache_table`) for reliable rate limiting without requiring external Redis servers.
- **Brute-Force Lockout (`BruteForceLockoutThrottle`)**: Automatically locks out accounts for **15 minutes** after **5 consecutive failed attempts** (`HTTP 429 Too Many Requests`). Successful logins immediately reset the counter.
- **File Upload Security (`apps/core/validators.py`)**: Strict MIME type whitelisting and 5MB size caps for uploaded payment proofs and media.
- **Production Headers**: HSTS (1 year), `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS = 'DENY'`.

### 🏨 3. Room Inventory & Amenities (`apps/rooms`)
- **Room Management**: Models rooms with room numbers, room types, daily rates, custom rate overrides, capacity, bed types, and operational states (*Available, Occupied, Dirty/Cleaning, Maintenance*).
- **Public Availability Engine**: Real-time room availability filtering by stay dates and guest count.

### 💳 4. Booking, Last-Room Protection & Offline Sync (`apps/bookings`)
- **The Last-Room Rule (Online Inventory Protection)**: When hotel occupancy reaches **98%** or only **1–2 rooms remain**, the backend automatically closes public online sales (`online_sales_closed: true`). The remaining rooms are exclusively reserved for front desk walk-ins, eliminating race conditions.
- **Offline Idempotency & Conflict Engine (`apps/core/idempotency.py`)**: Endpoints accept `X-Idempotency-Key` headers. If an offline front-desk client replays actions upon reconnection, requests are deduplicated and return cached responses. If another guest claimed the room in the interim, the backend raises `ConflictError` (`HTTP 409 Conflict`).
- **Payment Proof Verification & Instant Room Release (`/api/v1/bookings/reception/verify-payment/`)**:
  - **APPROVE**: Booking marked `CONFIRMED`, payment logged as `SUCCESS`, and SMS/email confirmation dispatched.
  - **REJECT**: Booking set to `CANCELLED`, payment marked `FAILED`, and **the assigned room is immediately released back to `AVAILABLE` status** for new bookings.
- **Stay Extension Service (`/api/v1/bookings/reception/extend-stay/`)**: Atomic stay extensions validating future room availability, recalculating total cost, and logging an `EXTEND_STAY` payment record.
- **Walk-In Check-In (`/api/v1/bookings/reception/walk-in-checkin/`)**: Immediate front-desk check-in with security deposit logging and key card assignment.
- **Check-Out Processing**: Log departures, calculate extra charges (mini-bar, damage fee), and update room state to `DIRTY_CLEANING`.
- **Front Desk Live Board API**: Real-time status breakdown showing occupied rooms, expected arrivals/departures, and pending verification queue.

### 💳 5. Payment Ledgers (`apps/payments`)
- Multi-category transactions (`ONLINE_PREPAYMENT`, `CHECKIN_PAYMENT`, `CHECKOUT_PAYMENT`, `EXTEND_STAY`, `DEPOSIT`, `ADDITIONAL_CHARGE`).
- Hotel bank account API returning official details for online transfers.

### 🌐 6. Hotel Landing Page CMS (`apps/content`)
- **Composite API (`/api/v1/content/landing-page/`)**: Supplies hero info, featured rooms, testimonials, photo gallery, corporate partners, FAQs, and bank details in a single performant payload.

### 📊 7. Analytics & Revenue KPIs (`apps/analytics`)
- Calculates real-time total revenue, occupancy rate percentage, Average Daily Rate (ADR), RevPAR, and CSV data export for managers.

---

## 📁 Directory Structure

```
room_management_backend/
├── .env.example                               # Full environment variables template
├── .dockerignore                              # Optimized container build exclusions
├── Dockerfile                                 # Multi-stage production container
├── docker-compose.yml                         # Local PostgreSQL + Web orchestration
├── docker-entrypoint.sh                       # DB probe, migrate, cache table, seed, exec
├── render.yaml                                # Render Blueprint specification (Web + DB)
├── .github/workflows/ci-cd.yml                # Parallel GitHub Actions CI/CD pipeline
├── pyproject.toml                             # Ruff linter & formatter configuration
├── pytest.ini                                 # Pytest settings and marker definitions
├── requirements/
│   ├── base.txt                               # Core Django, DRF, PostgreSQL, Pillow
│   ├── production.txt                         # Gunicorn, WhiteNoise
│   └── development.txt                        # Pytest, Factory-Boy, Ruff, Coverage
├── requirements.txt                           # Entrypoint pointing to production requirements
├── config/
│   ├── asgi.py                                # ASGI configuration
│   ├── wsgi.py                                # WSGI configuration
│   ├── urls.py                                # Root URL router + health check
│   └── settings/                              # Modular Split Settings Architecture
│       ├── __init__.py                        # Dynamic environment-based loader
│       ├── base.py                            # Shared configuration & Zero-Trust RBAC
│       ├── development.py                     # Local debug settings
│       ├── production.py                      # WhiteNoise, PostgreSQL, Security headers
│       └── testing.py                         # Fast hashers & in-memory caches
├── apps/
│   ├── analytics/                             # Revenue KPIs, daily/weekly stats, CSV exports
│   ├── bookings/                              # Reservations, check-in/out, stay extensions, Last-Room rule
│   ├── content/                               # Landing page CMS & bank transfer details
│   ├── core/                                  # Health probes, idempotency, exceptions, throttling, notifications
│   ├── guests/                                # Guest profiles & phone lookups
│   ├── payments/                              # Financial ledger & proof tracking
│   ├── rooms/                                 # Room inventory, types & amenities
│   └── users/                                 # Custom User model & 4-role RBAC
└── tests/                                     # 3-Tier Enterprise Test Suite
    ├── conftest.py                            # Pytest fixtures & authenticated clients
    ├── unit/                                  # Unit tests (Last-Room rule, pricing, validators, throttle)
    ├── integration/                           # Offline sync, 409 conflict, payment rejection room release
    └── e2e/                                   # Real-world user flows (online booking, walkin, lockout)
```

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/DrLeroK/room_management_backend.git
cd room_management_backend
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env and adjust DATABASE_URL, SECRET_KEY, and ports as needed
```

### 3. Run with Docker Compose (Recommended)
Launch both the **PostgreSQL database** and the **Django web application** with a single command:
```bash
docker compose up --build
```
The application will be accessible at `http://localhost:8000/`.

---

## 💻 Local Development Setup (Without Docker)

### 1. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/development.txt
```

### 2. Apply Database Migrations & Create Cache Table
```bash
python manage.py migrate
python manage.py createcachetable
```

### 3. Seed Database with Demo Accounts & Rooms
```bash
python manage.py seed_db
```

### 4. Start Development Server
```bash
python manage.py runserver 8000
```

---

## 🧪 Testing Suite (3-Tier Testing Architecture)

Run the full automated test suite (67 tests, 87% test coverage):
```bash
# Run all tests across apps and 3-tier suite
pytest apps/ tests/

# Run unit tests only
pytest tests/unit/ -m unit

# Run integration & RBAC security tests
pytest tests/integration/ -m integration

# Run end-to-end user journey tests
pytest tests/e2e/ -m e2e

# Run with test coverage report
pytest apps/ tests/ --cov=apps --cov-report=term-missing
```

---

## 🔒 Code Quality & Security Audits

Run the Ruff linter and static analyzer:
```bash
ruff check apps/ config/ tests/
```

Run Django's production deployment security audit:
```bash
DJANGO_ENV=production python manage.py check --deploy
```

---

## 🔑 Pre-Seeded System Accounts & Luxury Demo Data

Execute `python manage.py seed_db --force` to populate complete test accounts, luxury room types with curated Unsplash photography, multi-bank accounts (CBE, Telebirr, Awash, BOA), testimonials, FAQs, in-app notifications, and guest inquiries:

```bash
# Seed or refresh the complete production demo dataset
python manage.py seed_db --force
```

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `admin` | `admin12345` | `ADMIN` | System Administrator / Superuser |
| `owner` | `owner12345` | `OWNER` | Hotel Owner |
| `manager` | `manager12345` | `MANAGER` | Hotel Manager |
| `receptionist1` | `receptionist12345` | `RECEPTIONIST` | Senior Receptionist (Helen Tesfaye) |
| `receptionist2` | `receptionist12345` | `RECEPTIONIST` | Front Desk Receptionist (Yared Alemu) |

---

## 🇪🇹 Currency Localization & Public Relaxation
- **Ethiopian Birr (ETB)**: All models, notifications, and templates standardly format amounts in `ETB` (e.g. `1,500.00 ETB`).
- **Resilient Public Content Browsing**: Public endpoints implement `PublicReadAuthMixin`, returning content anonymously without triggering 401s when cookies or stale tokens are present.
- **Inquiry Notifications**: Client contact inquiries dispatch real-time in-app notifications to all `RECEPTIONIST` and `MANAGER` users and record audit logs.

---

## 🌐 API Documentation

Access interactive API documentation at:
- **API Base URL**: `http://localhost:8000/api/v1/`
- **Health Check Probe**: `http://localhost:8000/health/`
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **ReDoc**: `http://localhost:8000/api/redoc/`

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.