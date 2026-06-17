# Booking Feature — Documentation

> **Feature:** Drone Booking  
> **Owner:** Backend Team  
> **Status:** ✅ Implemented (Phase 1 — sync)  
> **Last Updated:** 2026-06-17

---

## 📌 Overview

The Booking feature manages the complete lifecycle of drone booking requests, from creation through payment, confirmation, mission execution, and completion (or expiry/cancellation).

---

## 🗺️ Booking State Machine

```
                    ┌─────────────────────────┐
                    ▼                         │
DRAFT ──────→ PENDING_PAYMENT ──→ PAID ──→ CONFIRMED ──→ IN_PROGRESS ──→ COMPLETED
                    │                 │
                    ▼                 ▼
              PAYMENT_FAILED     CANCELLED
                    │
                    ▼
                 EXPIRED (scheduler)
```

### State Transitions

| From | To | Trigger |
|------|----|---------|
| `DRAFT` | `PENDING_PAYMENT` | User submits booking |
| `PENDING_PAYMENT` | `PAID` | VNPay webhook payment success |
| `PENDING_PAYMENT` | `PAYMENT_FAILED` | VNPay webhook payment failed |
| `PENDING_PAYMENT` | `EXPIRED` | Scheduler (30-min timeout) |
| `PAID` | `CONFIRMED` | Operator confirms |
| `PAID` | `CANCELLED` | User or admin cancels |
| `CONFIRMED` | `IN_PROGRESS` | Mission starts |
| `IN_PROGRESS` | `COMPLETED` | Mission completed |
| `DRAFT/PENDING_PAYMENT/PAID/CONFIRMED` | `CANCELLED` | User cancels |

---

## 📡 API Endpoints

### Create Booking
```
POST /api/v1/bookings
Authorization: Bearer <token>

Request:
{
  "drone_id": "uuid",
  "area_id": "uuid",
  "package_id": "uuid",
  "start_time": "2026-06-20T09:00:00+07:00",
  "end_time": "2026-06-20T11:00:00+07:00",
  "total_price": 500000.0,
  "notes": "Optional note"
}

Response 201:
{
  "data": {
    "id": "uuid",
    "status": "PENDING_PAYMENT",
    "expired_at": "2026-06-20T09:30:00Z",
    ...
  },
  "meta": { ... },
  "error": null
}
```

### Get Booking
```
GET /api/v1/bookings/{id}
Authorization: Bearer <token>

Response 200: { "data": BookingResponse }
Response 404: { "error": { "code": "NOT_FOUND" } }
```

### List Bookings
```
GET /api/v1/bookings?page=1&page_size=20
Authorization: Bearer <token>

Response 200: { "data": PaginatedBookingResponse }
```

### Cancel Booking
```
PATCH /api/v1/bookings/{id}/cancel
Authorization: Bearer <token>

Request: { "reason": "Optional reason" }
Response 200: { "data": BookingResponse (CANCELLED) }
Response 422: { "error": { "code": "RULE_VIOLATION" } }  # IN_PROGRESS can't cancel
```

---

## 🏗️ Architecture

```
booking/
  api/
    controller.py     # Routes: create, get, list, cancel
    schemas.py        # CreateBookingRequest, BookingResponse, CancelBookingRequest

  domain/
    entity.py         # BookingEntity with business methods
    status.py         # BookingStatus enum (9 states)
    rules.py          # validate_not_in_past, validate_operating_hours, etc.

  application/
    create_booking.py   # CreateBookingUseCase: validate → lock → save → event
    expire_booking.py   # ExpireBookingUseCase: find expired → update → unlock → event
    cancel_booking.py   # Via BookingService.cancel_booking()
    booking_service.py  # Facade

  infrastructure/
    repository.py       # save, get_by_id, get_by_id_and_user, find_expired, find_overlapping
    redis_lock.py       # RedisSlotLock: acquire/release with Lua script
    rabbitmq_publisher.py # publish_booking_created, publish_booking_expired

  events/
    booking_created.py  # BookingCreated event dataclass
    booking_expired.py  # BookingExpired event dataclass
```

---

## 🔑 Business Rules

| Rule | Implementation | File |
|------|---------------|------|
| No past bookings | `validate_not_in_past()` | `domain/rules.py` |
| Operating hours 06:00-18:00 | `validate_operating_hours()` | `domain/rules.py` |
| Min 30 min duration | `validate_minimum_duration()` | `domain/rules.py` |
| Package must be active | `validate_package_is_active()` | `domain/rules.py` |
| Area must be supported | `validate_area_is_supported()` | `domain/rules.py` |
| No double booking | `find_overlapping()` + Redis lock | `infrastructure/` |
| Payment expires in 30 min | `BOOKING_EXPIRY_MINUTES=30` | `config/settings.py` |

---

## 📊 Database

### Table: `bookings`
| Column | Type | Notes |
|--------|------|-------|
| `id` | `VARCHAR(36)` | UUID primary key |
| `user_id` | `VARCHAR(36)` | Indexed |
| `drone_id` | `VARCHAR(36)` | Indexed |
| `area_id` | `VARCHAR(36)` | |
| `package_id` | `VARCHAR(36)` | |
| `status` | `VARCHAR(30)` | Indexed |
| `start_time` | `TIMESTAMPTZ` | |
| `end_time` | `TIMESTAMPTZ` | |
| `expired_at` | `TIMESTAMPTZ` | Nullable |
| `total_price` | `FLOAT` | |
| `notes` | `TEXT` | Nullable |
| `cancellation_reason` | `TEXT` | Nullable |
| `created_at` | `TIMESTAMPTZ` | Auto |
| `updated_at` | `TIMESTAMPTZ` | Auto-update trigger |

### Indexes
- `ix_bookings_user_id` — `(user_id)`
- `ix_bookings_drone_id` — `(drone_id)`
- `ix_bookings_status` — `(status)`
- `ix_bookings_drone_time` — `(drone_id, start_time, end_time)` ← overlap detection
- `ix_bookings_status_expired` — `(status, expired_at)` ← scheduler

---

## 🔴 Redis Slot Lock

**Pattern:** `booking:slot_lock:{drone_id}:{date}:{hour:02d}`  
**Example:** `booking:slot_lock:drone-123:2026-06-20:09`  
**TTL:** 300 seconds (configurable via `REDIS_SLOT_LOCK_TTL_SECONDS`)  
**Acquire:** `SET key booking_id NX EX 300` (atomic)  
**Release:** Lua script (check owner before delete)

---

## 📨 Events Published

| Event | Routing Key | Trigger |
|-------|-------------|---------|
| `BookingCreated` | `booking.created` | Booking created successfully |
| `BookingExpired` | `booking.expired` | Payment timeout reached |
| `BookingCancelled` | `booking.cancelled` | User cancels |

Exchange: `booking.events` (topic, durable)

---

## 🧪 Test Coverage

| Test File | Coverage |
|-----------|---------|
| `tests/unit/domain/test_booking_rules.py` | Domain rules (all cases) |
| `tests/unit/application/test_create_booking.py` | Use case + rollback |

**Known gaps (TODO):**
- Integration tests for repository
- E2E tests for full booking flow
- Tests for expire_booking scheduler use case
