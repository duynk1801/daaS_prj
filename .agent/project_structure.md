# Project Structure — VNPT Drone DaaS Backend

> **VERSION:** 1.0.0 | **UPDATED:** 2026-06-17
>
> This document is the **source of truth** for the target file structure.
> All deviations MUST be documented as an ADR in `.agent/plan/`.

---

## 🎯 Target Architecture

**Feature-based + Layered Architecture (DDD-inspired)**

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT / FRONTEND                     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────┐
│          API LAYER — FastAPI Controllers                 │
│   (HTTP routing, Pydantic validation, auth middleware)   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│        APPLICATION LAYER — Use Cases                     │
│     (Orchestration, flow control, transaction mgmt)      │
└────────┬───────────────────────────────────┬────────────┘
         │                                   │
┌────────▼────────┐               ┌──────────▼────────────┐
│  DOMAIN LAYER   │               │  INFRASTRUCTURE LAYER  │
│  Entities       │               │  Repository (SQL)      │
│  Domain Rules   │               │  Redis Lock            │
│  Status Enums   │               │  RabbitMQ Publisher    │
│  (PURE PYTHON)  │               │  External APIs         │
└─────────────────┘               └──────────┬────────────┘
                                             │
                               ┌─────────────▼────────────┐
                               │     SHARED LAYER          │
                               │  PostgreSQL pool          │
                               │  Redis pool               │
                               │  RabbitMQ connection      │
                               │  Event Bus / Outbox       │
                               └───────────────────────────┘
```

---

## 🌐 Product Domains

| Domain | Feature Module | Key Responsibilities |
|--------|---------------|----------------------|
| **Auth** | `features/auth/` | Login, register, JWT, refresh, RBAC, OAuth |
| **Booking** | `features/booking/` | 4-step flow, slot lock, status lifecycle |
| **Payment** | `features/payment/` | VNPay integration, webhook, refunds |
| **Scheduling** | `features/scheduling/` | Drone & pilot assignment, mission planning |
| **Tracking** | `features/tracking/` | Telemetry, live GPS, FPV stream |
| **Reports** | `features/reports/` | AI summary, PDF generation, download |
| **Wallet** | `features/wallet/` | VNPT Pay balance, top-up, transactions |
| **Profile** | `features/profile/` | User info, organization, settings |
| **Notifications** | `features/notifications/` | Push, email, SMS dispatch |
| **Analytics** | `features/analytics/` | Usage stats, trends, dashboards |

---

## 📂 Complete Source Layout

```
src/
│
├── app/                                     # Application composition layer
│   ├── main.py                              # FastAPI app factory
│   ├── config/
│   │   ├── settings.py                      # Pydantic BaseSettings (all env vars)
│   │   └── logging.py                       # Structured logging config
│   └── middleware/
│       ├── auth.py                          # JWT bearer token validation
│       ├── cors.py                          # CORS (strict origin list)
│       ├── rate_limit.py                    # Redis-backed rate limiting
│       └── error_handler.py                # Global exception → JSON response
│
├── features/                                # Product feature modules
│   │
│   ├── auth/                                # ── Auth Domain ──
│   │   ├── api/
│   │   │   ├── controller.py                # POST /auth/login, /auth/refresh, /auth/logout
│   │   │   └── schemas.py                   # LoginRequest, TokenResponse
│   │   ├── domain/
│   │   │   ├── entity.py                    # User entity
│   │   │   ├── rules.py                     # Password strength, token rules
│   │   │   └── exceptions.py               # AuthDomainError
│   │   ├── application/
│   │   │   ├── login.py                     # LoginUseCase
│   │   │   ├── refresh_token.py             # RefreshTokenUseCase
│   │   │   └── auth_service.py              # Facade
│   │   ├── infrastructure/
│   │   │   ├── repository.py                # UserRepository, RefreshTokenRepository
│   │   │   └── password_hasher.py           # bcrypt/argon2 wrapper
│   │   ├── constants.py
│   │   ├── types.py
│   │   └── index.py                         # Exports: AuthService, LoginUseCase
│   │
│   ├── booking/                             # ── Booking Domain ──
│   │   ├── api/
│   │   │   ├── controller.py                # CRUD + state transitions
│   │   │   └── schemas.py                   # CreateBookingRequest, BookingResponse
│   │   ├── domain/
│   │   │   ├── entity.py                    # BookingEntity (confirm, cancel, expire)
│   │   │   ├── status.py                    # BookingStatus enum (9 states)
│   │   │   ├── rules.py                     # Booking validation rules
│   │   │   └── exceptions.py               # SlotConflictError, etc.
│   │   ├── application/
│   │   │   ├── create_booking.py            # CreateBookingUseCase
│   │   │   ├── expire_booking.py            # ExpireBookingUseCase (scheduler)
│   │   │   ├── cancel_booking.py            # CancelBookingUseCase
│   │   │   ├── confirm_booking.py           # ConfirmBookingUseCase (operator)
│   │   │   └── booking_service.py           # Facade
│   │   ├── infrastructure/
│   │   │   ├── repository.py                # save, get_by_id, find_expired, find_overlapping
│   │   │   ├── redis_lock.py                # RedisSlotLock (SET NX EX)
│   │   │   └── rabbitmq_publisher.py        # Booking event publisher
│   │   ├── events/
│   │   │   ├── booking_created.py           # BookingCreated event
│   │   │   ├── booking_expired.py           # BookingExpired event
│   │   │   ├── booking_cancelled.py         # BookingCancelled event
│   │   │   └── booking_confirmed.py         # BookingConfirmed event
│   │   ├── constants.py                     # SLOT_LOCK_TTL, PAYMENT_DEADLINE_MINUTES
│   │   ├── types.py                         # SlotKey, BookingDict
│   │   └── index.py
│   │
│   ├── payment/                             # ── Payment Domain ──
│   │   ├── api/
│   │   │   ├── controller.py                # POST /payments, webhook handlers
│   │   │   └── schemas.py                   # PaymentRequest, VNPayWebhook
│   │   ├── domain/
│   │   │   ├── entity.py                    # PaymentEntity
│   │   │   ├── status.py                    # PaymentStatus enum
│   │   │   ├── rules.py                     # Payment validation
│   │   │   └── exceptions.py
│   │   ├── application/
│   │   │   ├── initiate_payment.py          # InitiatePaymentUseCase
│   │   │   ├── process_webhook.py           # ProcessWebhookUseCase
│   │   │   ├── refund_payment.py            # RefundPaymentUseCase
│   │   │   └── payment_service.py           # Facade
│   │   ├── infrastructure/
│   │   │   ├── repository.py
│   │   │   ├── vnpay_client.py              # VNPay API integration
│   │   │   └── rabbitmq_publisher.py
│   │   ├── events/
│   │   │   ├── payment_success.py
│   │   │   └── payment_failed.py
│   │   ├── constants.py
│   │   ├── types.py
│   │   └── index.py
│   │
│   ├── scheduling/                          # ── Scheduling Domain ──
│   │   ├── api/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   ├── events/
│   │   └── index.py
│   │
│   ├── tracking/                            # ── Mission Tracking ──
│   │   ├── api/
│   │   │   ├── controller.py                # WebSocket endpoint for live telemetry
│   │   │   └── schemas.py
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── index.py
│   │
│   ├── reports/                             # ── Mission Reports ──
│   │   ├── api/
│   │   ├── domain/
│   │   ├── application/
│   │   │   └── generate_report.py           # AI summary + PDF generation
│   │   ├── infrastructure/
│   │   └── index.py
│   │
│   ├── wallet/                              # ── VNPT Pay Wallet ──
│   │   ├── api/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   │   └── vnpt_pay_client.py           # VNPT Pay integration
│   │   └── index.py
│   │
│   ├── profile/                             # ── User Profile ──
│   │   ├── api/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── index.py
│   │
│   ├── notifications/                       # ── Notifications ──
│   │   ├── api/
│   │   ├── domain/
│   │   ├── application/
│   │   │   ├── send_push.py
│   │   │   ├── send_email.py
│   │   │   └── send_sms.py
│   │   ├── infrastructure/
│   │   │   ├── firebase_client.py           # FCM push notifications
│   │   │   ├── sendgrid_client.py           # Email
│   │   │   └── twilio_client.py             # SMS
│   │   └── index.py
│   │
│   └── analytics/                           # ── Analytics ──
│       ├── api/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       └── index.py
│
├── shared/                                  # Cross-feature shared infrastructure
│   ├── database/
│   │   ├── postgres.py                      # AsyncEngine, AsyncSession factory
│   │   ├── base.py                          # SQLAlchemy DeclarativeBase + audit cols
│   │   └── unit_of_work.py                  # UoW pattern (transaction scoping)
│   ├── cache/
│   │   └── redis_client.py                  # Async Redis pool + helpers
│   ├── messaging/
│   │   ├── rabbitmq.py                      # aio-pika connection manager
│   │   ├── event_bus.py                     # Publish/subscribe abstraction
│   │   └── outbox.py                        # Outbox pattern (guaranteed delivery)
│   ├── security/
│   │   └── jwt.py                           # JWT encode/decode (HS256, no none alg)
│   ├── exceptions/
│   │   └── custom_exceptions.py             # Full exception hierarchy
│   └── utils/
│       ├── datetime_utils.py                # UTC helpers, ISO formatting
│       ├── id_generator.py                  # UUID v4, snowflake ID
│       ├── pagination.py                    # PaginatedResponse builder
│       └── validators.py                    # Shared validators (phone, VN address)
│
├── alembic/                                 # Database migrations
│   ├── versions/
│   │   ├── 20260617_001_create_bookings.py
│   │   ├── 20260617_002_create_payments.py
│   │   ├── 20260617_003_create_outbox.py
│   │   └── ...
│   ├── env.py                               # Loads settings + imports all models
│   └── script.py.mako                       # Migration template
│
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_booking_rules.py
│   │   │   ├── test_booking_entity.py
│   │   │   ├── test_booking_status.py
│   │   │   └── test_payment_rules.py
│   │   └── application/
│   │       ├── test_create_booking.py
│   │       ├── test_expire_booking.py
│   │       └── test_cancel_booking.py
│   ├── integration/
│   │   ├── test_booking_repository.py       # Real DB (test schema, rollback)
│   │   ├── test_redis_lock.py               # Real Redis (test DB, flush)
│   │   └── test_rabbitmq.py                 # RabbitMQ test instance
│   ├── e2e/
│   │   ├── test_booking_api.py              # Full HTTP with TestClient
│   │   └── test_payment_api.py
│   └── conftest.py                          # Shared fixtures
│
├── docker/
│   ├── Dockerfile                           # Multi-stage production image
│   └── docker-compose.yml                   # Dev: app + postgres + redis + rabbit
│
├── .agent/                                  # AI agent configuration
│   ├── README.md
│   ├── rules.md
│   ├── project_structure.md                 # THIS FILE
│   ├── CODING_CONVENTIONS.md
│   ├── doc/
│   │   ├── auth-doc.md
│   │   ├── booking-doc.md
│   │   └── payment-doc.md
│   └── plan/
│       └── (ADRs)
│
├── .env                                     # Local dev secrets (gitignored)
├── .env.example                             # Template with all required vars
├── alembic.ini                              # Alembic configuration
├── requirements.txt                         # Pinned production dependencies
├── requirements-dev.txt                     # Dev + test dependencies
├── pyproject.toml                           # Tool configuration (ruff, mypy, pytest)
└── README.md
```

---

## 🔗 Cross-Feature Communication Rules

### Allowed
```python
# Feature A imports from Feature B's index.py
from features.payment.index import PaymentService
```

### Forbidden
```python
# ❌ Bypass index.py — imports internals
from features.payment.infrastructure.repository import PaymentRepository

# ❌ Domain importing from infrastructure
# Inside features/booking/domain/entity.py:
from features.booking.infrastructure.repository import BookingRepository  # WRONG
```

### Event-Based Communication (preferred for async flows)
```
Booking Service   →  publishes BookingCreated  →  RabbitMQ
                                                       ↓
                    Payment Service subscribes  ←  Consumer
```

---

## 📊 Database Schema Overview

### Core Tables

| Table | Feature | Key Columns |
|-------|---------|-------------|
| `users` | auth/profile | id, email, role, is_active |
| `refresh_tokens` | auth | token_hash, user_id, expires_at |
| `bookings` | booking | id, user_id, drone_id, status, start_time, end_time |
| `payments` | payment | id, booking_id, amount, status, vnpay_ref |
| `schedules` | scheduling | id, booking_id, drone_id, pilot_id, mission_date |
| `wallets` | wallet | id, user_id, balance, currency |
| `transactions` | wallet | id, wallet_id, type, amount, ref |
| `outbox_messages` | shared | id, event_type, payload, status, retry_count |
| `idempotency_keys` | shared | key, processed_at |

---

## 🗺️ API URL Map

```
/api/v1/
├── auth/
│   ├── POST   login
│   ├── POST   refresh
│   └── POST   logout
│
├── bookings/
│   ├── GET    /                   # List (paginated)
│   ├── POST   /                   # Create
│   ├── GET    /{id}               # Get one
│   ├── PUT    /{id}               # Full update
│   ├── PATCH  /{id}/cancel        # Cancel
│   ├── PATCH  /{id}/confirm       # Confirm (operator)
│   └── POST   /{id}/payment       # Initiate payment
│
├── payments/
│   ├── POST   /                   # Initiate
│   ├── GET    /{id}               # Get status
│   └── POST   /webhook/vnpay      # VNPay webhook
│
├── scheduling/
│   ├── GET    /                   # List missions
│   └── PUT    /{booking_id}       # Assign drone + pilot
│
├── tracking/
│   ├── GET    /{booking_id}/live  # WebSocket telemetry
│   └── GET    /{booking_id}/path  # Historical GPS path
│
├── wallet/
│   ├── GET    /balance
│   ├── GET    /transactions
│   └── POST   /topup
│
├── profile/
│   ├── GET    /me
│   └── PUT    /me
│
└── analytics/
    ├── GET    /usage
    └── GET    /trends
```

---

## ⚙️ Technology Versions

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.137+ | Web framework |
| `sqlalchemy` | 2.0+ | ORM (async) |
| `asyncpg` | 0.29+ | PostgreSQL async driver |
| `redis` | 5.0+ | Redis async client |
| `aio-pika` | 9.0+ | RabbitMQ async client |
| `pydantic` | 2.13+ | Data validation |
| `pydantic-settings` | 2.14+ | Settings management |
| `alembic` | 1.18+ | Database migrations |
| `python-jose` | 3.5+ | JWT (HS256) |
| `passlib[bcrypt]` | 1.7+ | Password hashing |
| `pytest-asyncio` | 0.23+ | Async tests |
| `httpx` | 0.28+ | Async HTTP client |

---

## 🚦 Migration Path: Current → Target

The current project (`/Volumes/ssd_roi/prj/my-fastapi-project`) uses a flat structure.
Migration is **incremental** — never a big bang rewrite.

### Phase 1 (Done ✅)
- [x] `app/config/settings.py`
- [x] `app/config/logging.py`
- [x] `app/shared/*`
- [x] `app/features/booking/*`
- [x] `app/main.py`

### Phase 2 (Next)
- [ ] Migrate to async (asyncpg + aio-pika)
- [ ] Add `app/middleware/` (auth, rate_limit, error_handler)
- [ ] Add `features/auth/` module
- [ ] Add `features/payment/` module
- [ ] Add outbox pattern to `shared/messaging/outbox.py`

### Phase 3
- [ ] `features/scheduling/`
- [ ] `features/tracking/` (WebSocket)
- [ ] `features/wallet/`
- [ ] `features/notifications/`

### Phase 4
- [ ] `features/reports/` (AI + PDF)
- [ ] `features/analytics/`
- [ ] Full e2e test suite
