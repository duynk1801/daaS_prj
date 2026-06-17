# Agent Rules — VNPT Drone DaaS Backend Service

> **VERSION:** 1.0.0 | **UPDATED:** 2026-06-17
> 
> These rules are **binding** for every AI agent on this project. Violations will result in rejected PRs.

---

## 🧠 1. GENERAL & AI PROTOCOL

### 1.1 Read Rules First
- **ALWAYS** read `.agent/README.md`, `.agent/rules.md`, and `.agent/project_structure.md` before coding.
- No exceptions for "simple" requests.
- If files are updated mid-session, re-read the updated version.

### 1.2 Task Checklist Required
- Create or update a **task checklist** for EVERY change, no matter how small.
- Format: markdown checkbox list with file-level granularity.
- **No checklist = No code.** Checklist must be approved before implementation starts.

```markdown
## Task Checklist: [Feature Name]

### Pre-Implementation
- [ ] Read all .agent/ rules
- [ ] Understand the scope
- [ ] Present plan for approval

### Implementation
- [ ] feat: `features/booking/domain/entity.py` — add `expire()` method
- [ ] feat: `features/booking/application/expire_booking.py` — use case
- [ ] feat: `features/booking/infrastructure/repository.py` — `find_expired()` query
- [ ] test: `tests/unit/domain/test_booking_entity.py` — test expire()
- [ ] test: `tests/unit/application/test_expire_booking.py`

### Post-Implementation
- [ ] Run: `pytest --cov=src`
- [ ] Update: `.agent/doc/booking-doc.md`
- [ ] Verify imports
```

### 1.3 Ask First Protocol
- **BEFORE** writing any code, summarize what you plan to do.
- If ambiguity exists, list **at least 3 solutions** with pros/cons.
- Wait for user confirmation before proceeding.
- **DO NOT assume approval.**

```
✅ CORRECT: "I plan to do X. Here are 3 approaches: ..."
❌ WRONG:   Start coding immediately without confirming scope.
```

### 1.4 Documentation Sync (MANDATORY)
| Change Type | Required Doc Update |
|-------------|---------------------|
| Architecture/file structure changes | `.agent/plan/` ADR |
| Feature code changes | `.agent/doc/<feature>-doc.md` |
| Import/ownership changes | Migration checklist |
| New endpoints | `.agent/doc/<feature>-doc.md` API section |

**No silent architecture drift.** Every change is traceable.

### 1.5 No Single Option Rule
- Always present **at least 3 distinct solution approaches** with pros/cons.
- Never present only one option for non-trivial decisions.

### 1.6 Communication Protocol
- **Explain During:** Step-by-step explanation of what you're doing and why.
- **Confirm Ambiguity:** List solutions and let user decide.
- **No Assumptions:** Never assume requirements, technologies, or patterns.

---

## 🏗️ 2. ARCHITECTURE & FILE STRUCTURE

### 2.1 Core Architecture

```
Feature-based + Layered Architecture (DDD-inspired)

┌─────────────────────────────────────────┐
│  API Layer (FastAPI Controller)          │  ← HTTP, Pydantic validation only
├─────────────────────────────────────────┤
│  Application Layer (Use Cases)           │  ← Orchestration, business flow
├─────────────────────────────────────────┤
│  Domain Layer (Entities + Rules)         │  ← Pure business logic, NO I/O
├─────────────────────────────────────────┤
│  Infrastructure Layer (Repository)       │  ← DB, Redis, RabbitMQ, APIs
├─────────────────────────────────────────┤
│  Shared Layer (Database, Cache, Events)  │  ← Cross-cutting concerns
└─────────────────────────────────────────┘
```

### 2.2 Target File Structure

```
src/
├── app/                                    # Application composition
│   ├── main.py                             # FastAPI app instance
│   ├── config/
│   │   ├── settings.py                     # Pydantic Settings (env vars)
│   │   └── logging.py                      # Logging configuration
│   └── middleware/
│       ├── auth.py                         # JWT authentication middleware
│       ├── cors.py                         # CORS configuration
│       ├── rate_limit.py                   # Rate limiting (Redis-backed)
│       └── error_handler.py               # Global exception handler
│
├── features/                               # Feature modules
│   ├── booking/                            # Booking domain
│   │   ├── api/
│   │   │   ├── controller.py               # FastAPI routes
│   │   │   └── schemas.py                  # Pydantic request/response
│   │   ├── domain/                         # PURE BUSINESS LOGIC
│   │   │   ├── entity.py                   # Booking entity
│   │   │   ├── status.py                   # BookingStatus enum
│   │   │   ├── rules.py                    # Business rules (pure functions)
│   │   │   └── exceptions.py               # Domain-specific exceptions
│   │   ├── application/                    # Use cases
│   │   │   ├── create_booking.py
│   │   │   ├── expire_booking.py
│   │   │   ├── cancel_booking.py
│   │   │   └── booking_service.py          # Facade
│   │   ├── infrastructure/                 # External dependencies
│   │   │   ├── repository.py               # SQLAlchemy queries
│   │   │   ├── redis_lock.py               # Slot locking
│   │   │   └── rabbitmq_publisher.py       # Event publishing
│   │   ├── events/                         # Domain events
│   │   │   ├── booking_created.py
│   │   │   └── booking_expired.py
│   │   ├── constants.py                    # Feature constants
│   │   ├── types.py                        # Feature types
│   │   └── index.py                        # Public exports
│   │
│   ├── payment/
│   ├── scheduling/
│   ├── tracking/
│   ├── reports/
│   ├── wallet/
│   ├── profile/
│   ├── notifications/
│   └── analytics/
│
├── shared/                                 # Cross-feature shared code
│   ├── database/
│   │   ├── postgres.py                     # Connection pool (asyncpg)
│   │   ├── base.py                         # SQLAlchemy DeclarativeBase
│   │   └── unit_of_work.py                 # Unit of Work pattern
│   ├── cache/
│   │   └── redis_client.py                 # Redis connection pool
│   ├── messaging/
│   │   ├── rabbitmq.py                     # RabbitMQ connection
│   │   ├── event_bus.py                    # Publish/subscribe
│   │   └── outbox.py                       # Outbox pattern (guaranteed delivery)
│   ├── exceptions/
│   │   └── custom_exceptions.py            # App exception hierarchy
│   └── utils/
│       ├── datetime_utils.py
│       ├── id_generator.py
│       └── validators.py
│
├── alembic/                                # Database migrations
│   └── versions/
│
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   └── application/
│   ├── integration/
│   └── e2e/
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

### 2.3 Feature Module Canonical Shape

```
src/features/<feature>/
  api/
    controller.py       # ONLY: receive request, validate, call use case, return response
    schemas.py          # ONLY: Pydantic input/output models

  domain/               # PURE BUSINESS LOGIC (zero external dependencies)
    entity.py           # Domain entity with business methods
    status.py           # Enum/Status definitions
    rules.py            # Pure validation functions (no I/O)
    exceptions.py       # Domain-specific exceptions

  application/          # USE CASES (orchestration only)
    create_<entity>.py  # Single use case per file
    update_<entity>.py
    service.py          # Facade — delegates to use cases

  infrastructure/       # EXTERNAL DEPENDENCIES
    repository.py       # SQLAlchemy CRUD
    redis_lock.py       # Redis distributed lock
    rabbitmq.py         # Event publisher

  events/               # DOMAIN EVENTS (immutable dataclasses)
    <event>_created.py
    <event>_updated.py

  constants.py          # MAX_RETRIES, SLOT_LOCK_TTL, PAYMENT_DEADLINE, etc.
  types.py              # TypedDict, Protocol, NewType definitions
  index.py              # Public API surface — what other features can import
```

### 2.4 Dependency Flow (IMMUTABLE RULE)

```
API Controller
    ↓ (calls)
Use Case
    ↓ (calls)              ↓ (creates)
Repository           Domain Entity
    ↓ (writes)             ↓ (validates with)
Database            Domain Rules
                           ↓ (raises)
                    Domain Exceptions
                           
Use Case ──→ Event Bus ──→ RabbitMQ
```

**Allowed imports:**
| Layer | Can import from |
|-------|----------------|
| API Controller | application layer, schemas |
| Use Case | domain, infrastructure, events |
| Domain Entity/Rules | nothing (pure Python only) |
| Repository | shared/database |
| Shared | nothing from features |

**Forbidden imports:**
- ❌ Domain importing from infrastructure
- ❌ Domain importing from application
- ❌ Shared importing from features
- ❌ Cross-feature direct imports (use `index.py` public API)

---

## 💎 3. CODE QUALITY & BEST PRACTICES

### 3.1 File Size Limits
| Component | Max Lines |
|-----------|-----------|
| Domain entity | 300 |
| Use case | 100 |
| Service/Facade | 200 |
| Repository | 200 |
| Controller | 150 |
| Any other file | 200 |
| Any function | 30 |

### 3.2 Single Responsibility (SRP)
- One file = One responsibility
- One class = One reason to change
- One function = One task
- One use case = One business operation

### 3.3 Type Safety — MANDATORY
```python
# ✅ CORRECT
def create_booking(
    user_id: int,
    area: str,
    start_time: datetime,
) -> BookingEntity:
    ...

# ❌ WRONG — no type hints
def create_booking(user_id, area, start_time):
    ...
```

- Type hints for ALL functions (Python 3.12+)
- Pydantic v2 for ALL data validation
- No `Any` unless absolutely necessary (add `# noqa: ANN401` comment explaining why)
- Use `Optional[T]` for nullable fields
- Use `TypedDict` for dict shapes, not bare `dict`

### 3.4 Docstring Standard
```python
async def create_booking(command: CreateBookingCommand) -> BookingEntity:
    """
    Create a new drone booking with slot lock and event publishing.

    Args:
        command: CreateBookingCommand with user_id, area, start_time, package_id.

    Returns:
        BookingEntity in PENDING_PAYMENT status with payment deadline set.

    Raises:
        DomainRuleViolationError: If booking date is in the past or outside hours.
        SlotConflictError: If the time slot is already booked.
        SlotLockError: If Redis lock cannot be acquired.
        DatabaseError: If the booking cannot be persisted.

    Example:
        >>> cmd = CreateBookingCommand(user_id=1, area="A3", ...)
        >>> booking = await usecase.execute(cmd)
        >>> print(booking.status)
        BookingStatus.PENDING_PAYMENT
    """
```

### 3.5 Async/Await — MANDATORY

**ALL I/O operations must be async:**
- Database queries → `asyncpg` / SQLAlchemy async
- HTTP calls → `httpx.AsyncClient`
- Redis → `redis.asyncio`
- RabbitMQ → `aio-pika`

```python
# ✅ CORRECT
async def get_booking(booking_id: int) -> Optional[BookingEntity]:
    result = await self.session.execute(
        select(BookingModel).where(BookingModel.id == booking_id)
    )
    ...

# ❌ WRONG — blocking I/O in async context
def get_booking(booking_id: int) -> Optional[BookingEntity]:
    result = self.session.query(BookingModel).filter(...).first()
    ...
```

### 3.6 Error Handling Pattern
```python
async def execute(self, command: CreateBookingCommand) -> BookingEntity:
    try:
        result = await self.repository.save(booking)
    except DatabaseError as exc:
        logger.error(
            "Database error creating booking",
            extra={"user_id": command.user_id, "error": type(exc).__name__},
            exc_info=True,
        )
        raise  # Re-raise, let global handler convert to HTTP response
    except Exception as exc:
        logger.error(
            "Unexpected error creating booking",
            extra={"user_id": command.user_id},
            exc_info=True,
        )
        raise InfrastructureError("Booking creation failed") from exc
```

### 3.7 Logging Rules
- Use structured logging (JSON in production)
- Log levels: `DEBUG` (dev), `INFO` (staging), `WARNING` (prod errors), `ERROR` (exceptions)
- Always include `exc_info=True` on errors
- **NEVER log:** passwords, tokens, full PII (mask if needed)
- Include correlation context: `user_id`, `booking_id`, `request_id`

```python
# ✅ CORRECT
logger.info("Booking created", extra={"booking_id": booking.id, "user_id": user_id})
logger.error("Lock failed", extra={"slot": slot_key}, exc_info=True)

# ❌ WRONG
logger.info(f"User {user.email} created booking with token {token}")
```

---

## 🌐 4. API DESIGN STANDARDS

### 4.1 RESTful Conventions
```
GET    /api/v1/bookings              # List (paginated)
GET    /api/v1/bookings/{id}         # Get one
POST   /api/v1/bookings              # Create
PUT    /api/v1/bookings/{id}         # Full update
PATCH  /api/v1/bookings/{id}         # Partial update
DELETE /api/v1/bookings/{id}         # Delete

# Sub-resources
PATCH  /api/v1/bookings/{id}/cancel  # State transition
POST   /api/v1/bookings/{id}/payment # Trigger payment
```

### 4.2 HTTP Status Codes
```
201 Created          → POST (new resource)
200 OK               → GET, PUT, PATCH
204 No Content       → DELETE
400 Bad Request      → Malformed request
401 Unauthorized     → Missing/invalid JWT
403 Forbidden        → Valid JWT, no permission
404 Not Found        → Resource doesn't exist
409 Conflict         → Slot conflict, duplicate
422 Unprocessable    → Validation failed (Pydantic)
429 Too Many Requests → Rate limit exceeded
500 Internal Server  → Unexpected errors
503 Service Unavail  → DB/Redis/RabbitMQ down
```

### 4.3 Standard Response Envelope

**Success:**
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-06-17T10:30:00Z",
    "path": "/api/v1/bookings",
    "version": "v1",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "error": null
}
```

**Paginated List:**
```json
{
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "meta": { ... },
  "error": null
}
```

**Error:**
```json
{
  "data": null,
  "meta": {
    "timestamp": "2026-06-17T10:30:00Z",
    "path": "/api/v1/bookings",
    "version": "v1",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "error": {
    "code": "SLOT_CONFLICT",
    "message": "The selected time slot is not available",
    "details": [
      { "field": "start_time", "message": "Slot already booked" }
    ]
  }
}
```

### 4.4 Rate Limiting
- Authenticated: **100 req/min** per user
- Unauthenticated: **20 req/min** per IP
- Return `429` with `Retry-After: <seconds>` header

### 4.5 API Versioning
- Version in URL: `/api/v1/...`
- Increment major version (`v2`) only for **breaking changes**
- Deprecated endpoints: add `Deprecation: <date>` header and doc warning

---

## 🗄️ 5. DATABASE & MIGRATIONS

### 5.1 ORM Settings
- **Framework:** SQLAlchemy 2.0 (async mode)
- **Driver:** `asyncpg`
- **Pool:** `min=5, max=20, timeout=30s`

### 5.2 Model Convention
```python
# Location: features/<feature>/infrastructure/repository.py
from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.sql import func
from shared.database.base import Base

class BookingModel(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    drone_id = Column(String(36), nullable=False)
    area_id = Column(String(36), nullable=False)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.DRAFT)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_bookings_drone_time", "drone_id", "start_time", "end_time"),
        Index("ix_bookings_status_expired", "status", "expired_at"),
    )
```

### 5.3 Migration Rules
- **Every schema change** MUST have a migration file.
- Migration MUST have both `upgrade()` and `downgrade()`.
- **NEVER edit** a migration that's already merged to main.
- Naming: `YYYYMMDD_NNN_description.py` (e.g., `20260617_001_create_bookings.py`)

```bash
# Generate
alembic revision --autogenerate -m "create bookings table"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

### 5.4 Repository Pattern
```python
class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, booking: BookingEntity) -> BookingEntity:
        model = BookingModel.from_entity(booking)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def get_by_id(self, booking_id: str) -> Optional[BookingEntity]:
        result = await self._session.execute(
            select(BookingModel).where(BookingModel.id == booking_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def find_expired(self) -> List[BookingEntity]:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(BookingModel)
            .where(BookingModel.status == BookingStatus.PENDING_PAYMENT)
            .where(BookingModel.expired_at <= now)
        )
        return [m.to_entity() for m in result.scalars().all()]
```

### 5.5 Transactions
```python
async with self._session.begin():
    booking = await booking_repo.save(booking_entity)
    outbox_msg = await outbox_repo.save(event_message)
    # Both committed atomically, or both rolled back
```

### 5.6 N+1 Prevention
```python
# ✅ CORRECT — eager load relations
query = (
    select(BookingModel)
    .options(
        joinedload(BookingModel.user),
        selectinload(BookingModel.payment),
    )
    .where(BookingModel.user_id == user_id)
)

# ❌ WRONG — triggers N+1
bookings = await session.execute(select(BookingModel))
for b in bookings.scalars():
    user = b.user  # Lazy load = N extra queries
```

---

## 🚨 6. ERROR HANDLING

### 6.1 Exception Hierarchy
```python
class AppException(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

# Domain errors (4xx)
class DomainError(AppException): status_code = 400
class ValidationError(DomainError): code = "VALIDATION_ERROR"
class NotFoundError(DomainError): status_code = 404; code = "NOT_FOUND"
class ConflictError(DomainError): status_code = 409; code = "CONFLICT"
class DomainRuleViolationError(DomainError): code = "RULE_VIOLATION"

# Auth errors
class UnauthorizedError(AppException): status_code = 401; code = "UNAUTHORIZED"
class ForbiddenError(AppException): status_code = 403; code = "FORBIDDEN"
class RateLimitError(AppException): status_code = 429; code = "RATE_LIMIT_EXCEEDED"

# Infrastructure errors (5xx)
class InfrastructureError(AppException): status_code = 500
class DatabaseError(InfrastructureError): code = "DATABASE_ERROR"
class CacheError(InfrastructureError): code = "CACHE_ERROR"
class MessagingError(InfrastructureError): code = "MESSAGING_ERROR"
```

### 6.2 Global Exception Handler
```python
@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    logger.error(
        "Application error",
        extra={"code": exc.code, "path": str(request.url.path)},
        exc_info=isinstance(exc, InfrastructureError),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(request, exc),
    )
```

---

## 🧪 7. TESTING

### 7.1 Framework & Targets
- **Framework:** `pytest` + `pytest-asyncio`
- **Coverage target:** ≥ 80% overall, 100% for domain rules
- **Command:** `pytest --cov=src --cov-report=html -v`

### 7.2 Test Naming Convention
```
test_<what>_<when>_<expected>

test_cannot_book_in_past_raises_domain_error
test_create_booking_when_slot_available_returns_entity
test_acquire_lock_when_slot_taken_returns_false
```

### 7.3 Unit Test Requirements (Domain)
- **Zero real I/O** — mock everything
- Test each domain rule individually
- Test all state transitions
- Test edge cases: empty, null, boundary values

```python
class TestBookingRules:
    def test_future_booking_passes(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        validate_not_in_past(future)  # Should not raise

    def test_past_booking_raises(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(DomainRuleViolationError, match="future"):
            validate_not_in_past(past)
```

### 7.4 Use Case Test Requirements
```python
@pytest.mark.asyncio
async def test_create_booking_success(mock_repo, mock_lock, mock_publisher):
    mock_repo.find_overlapping.return_value = []
    mock_lock.acquire.return_value = True
    mock_repo.save.return_value = sample_entity

    result = await CreateBookingUseCase(mock_repo, mock_lock, mock_publisher).execute(cmd)

    assert result.status == BookingStatus.PENDING_PAYMENT
    mock_publisher.publish_booking_created.assert_called_once()
```

### 7.5 Integration Tests
- Use real PostgreSQL (test database, rolled back after each test)
- Use real Redis (test DB index, flushed after each test)
- Use RabbitMQ in-memory mock or real test instance
- Test repository methods end-to-end

### 7.6 E2E Tests
```python
@pytest.mark.asyncio
async def test_create_booking_api(async_client: AsyncClient, auth_headers: dict):
    response = await async_client.post(
        "/api/v1/bookings",
        json={"drone_id": "...", "start_time": "...", ...},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["status"] == "PENDING_PAYMENT"
    assert data["error"] is None
```

---

## 📡 8. EVENT-DRIVEN ARCHITECTURE

### 8.1 Event Definition Standard
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

@dataclass(frozen=True)
class BookingCreated:
    booking_id: str
    user_id: str
    drone_id: str
    start_time: str          # ISO-8601
    end_time: str
    total_price: float
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = field(default="booking.created", init=False)
    version: int = 1
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        init=False,
    )
```

### 8.2 Outbox Pattern (MANDATORY for reliability)

Every event MUST be saved to the `outbox_messages` table in the **same transaction** as the business data.

```
Transaction:
  1. INSERT INTO bookings ...
  2. INSERT INTO outbox_messages ...
  ← COMMIT

Background Worker:
  3. SELECT * FROM outbox_messages WHERE status = 'PENDING'
  4. Publish to RabbitMQ
  5. UPDATE outbox_messages SET status = 'SENT'
  6. On failure: retry up to 3 times, then → DLQ
```

### 8.3 Consumer Idempotency (MANDATORY)
```python
async def handle(self, event: BookingCreated) -> None:
    if await self.idempotency_store.is_processed(event.event_id):
        return  # Already processed — safe to ignore

    async with self.session.begin():
        await self.process_event(event)
        await self.idempotency_store.mark_processed(event.event_id)
```

### 8.4 Dead Letter Queue (DLQ)
- Max retries: **3**
- After 3 failures → route to `<exchange>.dlq`
- Alert when DLQ message count > 10
- DLQ messages require manual review

---

## 🔒 9. SECURITY

### 9.1 JWT Authentication
- Access token expiry: **15 minutes**
- Refresh token expiry: **7 days** (stored in DB for revocation)
- Algorithm: **HS256** (hardcoded, never read from token)
- Reject `none` algorithm
- Validate `exp` claim on every request

### 9.2 Authorization (RBAC)
```python
@router.delete("/api/v1/bookings/{id}")
@requires_role("admin")
async def delete_booking(booking_id: str, user: User = Depends(get_current_user)):
    ...
```

### 9.3 Input Validation
```python
class CreateBookingRequest(BaseModel):
    drone_id: str = Field(..., min_length=36, max_length=36, pattern=r'^[a-f0-9-]{36}$')
    start_time: datetime = Field(...)
    total_price: float = Field(..., gt=0, le=10_000_000)
    notes: Optional[str] = Field(None, max_length=500)
```

### 9.4 Secrets Management
- **ALL** secrets via environment variables
- **NEVER** hardcode secrets in source code
- Dev: `.env` file (gitignored)
- Staging/Prod: AWS Secrets Manager or HashiCorp Vault

### 9.5 SQL Injection Prevention
- Use SQLAlchemy ORM **always** (parameterized queries)
- Never: `f"SELECT * FROM bookings WHERE id = {user_input}"`

### 9.6 Sensitive Data Handling
- Never log passwords, tokens, or full card numbers
- Mask PII in logs: `email[:3]***@domain.com`
- Encrypt PII fields at rest

---

## ⚡ 10. PERFORMANCE STANDARDS

### 10.1 Response Time Targets
| Endpoint Type | P95 Target |
|---------------|-----------|
| List (paginated) | < 200ms |
| Get single | < 100ms |
| Create/Update | < 500ms |
| Complex with locks | < 1000ms |

### 10.2 Connection Pool Settings
```
PostgreSQL: min=5, max=20, pool_timeout=30s
Redis:      min=5, max=10
RabbitMQ:   Reuse channels (not connections)
```

### 10.3 Caching Strategy
| Data | TTL | Invalidation |
|------|-----|-------------|
| User profile | 5 min | On update |
| Booking status | 1 min | On status change |
| Static config | 60 min | On deploy |
| Auth token | 15 min | On logout |

### 10.4 Pagination (MANDATORY for list endpoints)
```python
# Always paginate — never return unbounded lists
async def list_bookings(page: int = 1, page_size: int = 20) -> PaginatedResponse:
    # Cap page_size
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    ...
```

---

## 🎯 11. PERFORMANCE AUDITOR PROTOCOL

When reviewing code, act as a **Senior Backend Engineer & Performance Auditor** and check:

### Audit Categories
```
🔍 PERFORMANCE
   ├── N+1 queries (use joinedload/selectinload)
   ├── Missing database indexes
   ├── Sync I/O in async context (blocking event loop)
   ├── Unbounded list queries (missing pagination)
   └── Cache hit ratio & cache invalidation correctness

🏗️ ARCHITECTURE
   ├── DDD layer violation (domain importing from infrastructure)
   ├── Business logic in controllers or repositories
   ├── Cross-feature imports bypassing index.py
   └── God classes/functions violating SRP

🔒 SECURITY
   ├── Hardcoded secrets
   ├── SQL injection vectors
   ├── Missing input validation
   ├── Overly permissive CORS
   └── JWT algorithm confusion

🛡️ RELIABILITY
   ├── Missing retry logic for external calls
   ├── No circuit breaker for downstream services
   ├── Events published outside transactions (no Outbox)
   └── Non-idempotent consumers
```

### Report Format
```markdown
## 🔍 PERFORMANCE AUDIT — `features/booking/`

### [HIGH] N+1 Query — `repository.py:45`
**File:** `features/booking/infrastructure/repository.py`
**Line:** 45
**Issue:** `booking.user` lazy-loads inside a loop
**Fix:** Add `joinedload(BookingModel.user)` to base query

### [MEDIUM] Missing Index — `bookings.status`
**File:** Migration `20260617_001_create_bookings.py`
**Issue:** `WHERE status = 'PENDING_PAYMENT'` lacks index
**Fix:** Add `Index("ix_bookings_status", "status")`
```

---

## 📋 12. MIGRATION CHECKLIST

### Before Merging Any Change
```markdown
- [ ] Task checklist was created and approved
- [ ] All new code has type hints
- [ ] All new functions have docstrings
- [ ] No secrets hardcoded in code
- [ ] Domain layer has zero external imports
- [ ] Tests written (unit + integration if applicable)
- [ ] `pytest --cov=src` passes with ≥80% coverage
- [ ] Alembic migration created for schema changes
- [ ] `.agent/doc/<feature>-doc.md` updated
- [ ] No N+1 queries introduced
- [ ] No blocking I/O in async context
- [ ] Rate limiting applies to new endpoints
- [ ] Security headers present on all responses
```
