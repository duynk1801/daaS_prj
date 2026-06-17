# 🚁 Drone Booking Service

A production-ready FastAPI backend for drone booking management built with **Feature-Based + Layered Architecture**.

## Architecture Overview

```
app/
├── features/
│   ├── booking/                 # Booking feature module
│   │   ├── api/                 # HTTP layer (FastAPI routes, Pydantic schemas)
│   │   ├── domain/              # Business logic (entities, rules, enums)
│   │   ├── application/         # Use cases (create_booking, expire_booking)
│   │   ├── infrastructure/      # DB, Redis, RabbitMQ implementations
│   │   └── events/              # Domain event dataclasses
│   └── scheduling/              # (Skeleton — future feature)
├── shared/
│   ├── database/                # SQLAlchemy engine, base model
│   ├── cache/                   # Redis connection pool
│   ├── messaging/               # RabbitMQ connection, event bus
│   ├── security/                # JWT utilities
│   └── exceptions/              # Custom exception hierarchy
├── config/
│   ├── settings.py              # Pydantic Settings (env-based)
│   └── logging.py               # Logging configuration
└── main.py                      # FastAPI app + middleware + routes
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.137+ |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 ORM) |
| Cache / Locking | Redis 7 |
| Message Broker | RabbitMQ 3 |
| Auth | JWT (python-jose) |
| Migrations | Alembic |
| Testing | pytest + pytest-mock |

## Quick Start

### 1. Clone & Setup Environment

```bash
cd /Volumes/ssd_roi/prj/my-fastapi-project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
# CRITICAL: Set a strong JWT_SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start Infrastructure

```bash
docker-compose up -d
# Wait for services to be healthy:
docker-compose ps
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start the Application

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Open API Documentation

```
http://localhost:8000/docs
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Only domain rule tests (fast, no I/O)
pytest tests/features/booking/domain/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

## API Endpoints

All endpoints require `Authorization: Bearer <token>` header.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/bookings` | Create a booking |
| `GET` | `/api/v1/bookings` | List my bookings |
| `GET` | `/api/v1/bookings/{id}` | Get booking by ID |
| `PATCH` | `/api/v1/bookings/{id}/cancel` | Cancel a booking |

## Booking Status Flow

```
DRAFT → PENDING_PAYMENT → PAID → CONFIRMED → IN_PROGRESS → COMPLETED
                    ↓              ↓
            PAYMENT_FAILED     CANCELLED
        (any non-terminal) → EXPIRED (via scheduler)
```

## Security Notes

- **JWT secrets** are never hardcoded — loaded from env or fail with ephemeral key + warning
- **SQL injection** prevented via SQLAlchemy ORM (no raw string queries)
- **IDOR protection** — ownership checked at DB level for all resource access
- **Slot locking** — Redis `SET NX EX` (atomic) prevents double-booking race conditions
- **Security headers** — CSP, X-Frame-Options, X-Content-Type-Options on all responses
- **CORS** — strict allow-list, no wildcard origins
- **Ports** — Docker services bound to `127.0.0.1` only (not `0.0.0.0`)

## Database Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1

# Generate new migration (after model changes)
alembic revision --autogenerate -m "description"

# Show current revision
alembic current

# Show migration history
alembic history
```

## RabbitMQ Events

The service publishes events to the `booking.events` topic exchange:

| Routing Key | Trigger |
|-------------|---------|
| `booking.created` | New booking created |
| `booking.expired` | Payment timeout expired |
| `booking.cancelled` | User cancelled booking |
| `booking.confirmed` | Operator confirmed booking |
| `booking.completed` | Mission completed |

## Development

### Project Structure Conventions

- **Domain layer**: No external dependencies (pure Python)
- **Application layer**: Orchestrates domain + infrastructure via DI
- **Infrastructure layer**: SQLAlchemy, Redis, RabbitMQ implementations
- **API layer**: FastAPI routes, Pydantic schemas, HTTP concerns only

### Adding a New Feature

1. Create `app/features/<feature_name>/`
2. Add `domain/`, `application/`, `infrastructure/`, `api/`, `events/` sub-directories
3. Create `__init__.py` in each directory
4. Add your router to `app/main.py`
5. Create tests in `tests/features/<feature_name>/`
