# Coding Conventions — VNPT Drone DaaS Backend

> **VERSION:** 1.0.0 | **UPDATED:** 2026-06-17
>
> These conventions apply to **all Python code** in this project.
> Enforced via `ruff`, `mypy`, and CI checks.

---

## 1. NAMING CONVENTIONS

### 1.1 Files & Directories
```
snake_case.py                # All Python files
booking_service.py           # ✅
bookingService.py            # ❌
BookingService.py            # ❌
```

### 1.2 Classes
```python
# PascalCase
class BookingEntity:          # ✅ Domain entity
class BookingRepository:      # ✅ Repository
class CreateBookingUseCase:   # ✅ Use case
class BookingResponse:        # ✅ Pydantic schema
class BookingStatus:          # ✅ Enum
```

### 1.3 Functions & Methods
```python
# snake_case + verb-first naming
async def create_booking(...)     # ✅ Use case
async def find_expired(...)       # ✅ Repository query
async def acquire_lock(...)       # ✅ Infrastructure
def validate_not_in_past(...)     # ✅ Domain rule
def mark_as_paid(...)             # ✅ Entity method
```

### 1.4 Variables & Parameters
```python
# snake_case, descriptive
booking_id: str               # ✅
user_id: str                  # ✅
start_time: datetime          # ✅
b: BookingEntity              # ❌ single letter (except loop vars: i, k, v)
bookingID: str                # ❌ camelCase
```

### 1.5 Constants
```python
# UPPER_SNAKE_CASE in constants.py
SLOT_LOCK_TTL_SECONDS: int = 300
PAYMENT_DEADLINE_MINUTES: int = 30
MAX_BOOKING_DURATION_HOURS: int = 8
OPERATING_HOURS_START: int = 6    # 06:00 UTC
OPERATING_HOURS_END: int = 18     # 18:00 UTC
```

### 1.6 Type Aliases & TypeVars
```python
# PascalCase for type aliases
from typing import TypeAlias, TypeVar

SlotKey: TypeAlias = str                    # "drone_id:2026-06-17:09"
BookingDict: TypeAlias = dict[str, Any]
T = TypeVar("T")
EntityT = TypeVar("EntityT", bound="BaseEntity")
```

---

## 2. TYPE HINTS — MANDATORY

### 2.1 All Function Signatures
```python
# ✅ CORRECT — full type hints
async def get_booking_by_id(
    booking_id: str,
    user_id: str,
) -> Optional[BookingEntity]:
    ...

# ❌ WRONG — missing type hints
async def get_booking_by_id(booking_id, user_id):
    ...
```

### 2.2 Return Types Always Explicit
```python
# ✅ CORRECT
def can_be_cancelled(self) -> bool:
    return not self.status.is_terminal

# ✅ CORRECT — None return
async def release_lock(self, slot_key: str) -> None:
    await self._redis.delete(slot_key)

# ❌ WRONG — missing return type
def can_be_cancelled(self):
    return not self.status.is_terminal
```

### 2.3 Collections
```python
# ✅ Use generics (Python 3.9+)
def find_expired(self) -> list[BookingEntity]:
    ...

def get_slots(self) -> dict[str, list[int]]:
    ...

# ❌ WRONG — untyped
def find_expired(self) -> List:
    ...
```

### 2.4 Optional vs Union
```python
from typing import Optional, Union

# ✅ Optional for nullable
notes: Optional[str] = None

# ✅ Union for multiple types
def process(value: Union[str, int]) -> str:
    ...

# ✅ Python 3.10+ syntax (preferred in new code)
def process(value: str | int) -> str:
    ...
```

### 2.5 No `Any` Without Comment
```python
# ✅ With justification
extra_data: Any  # noqa: ANN401 — raw JSON from VNPay webhook, schema varies

# ❌ WRONG — unexplained Any
def process(data: Any) -> Any:
    ...
```

---

## 3. PYDANTIC V2 PATTERNS

### 3.1 Request/Response Schemas
```python
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional

class CreateBookingRequest(BaseModel):
    """Request body for creating a new drone booking."""

    model_config = {"str_strip_whitespace": True}

    drone_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the drone to book",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    start_time: datetime = Field(
        ...,
        description="Booking start time (ISO-8601, timezone required)",
        examples=["2026-06-20T09:00:00+07:00"],
    )
    end_time: datetime = Field(
        ...,
        description="Booking end time (must be after start_time)",
    )
    total_price: float = Field(..., gt=0, le=10_000_000)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Datetime must include timezone (e.g., +07:00 or Z)")
        return v

    @model_validator(mode="after")
    def end_after_start(self) -> "CreateBookingRequest":
        if self.start_time >= self.end_time:
            raise ValueError("end_time must be strictly after start_time")
        return self
```

### 3.2 Response Schemas
```python
class BookingResponse(BaseModel):
    """Single booking response."""

    id: str
    user_id: str
    drone_id: str
    status: str
    total_price: float
    start_time: datetime
    end_time: datetime
    created_at: datetime
    expired_at: Optional[datetime] = None

    model_config = {"from_attributes": True}  # Allow ORM model mapping


class PaginatedBookingResponse(BaseModel):
    """Paginated list of bookings."""

    items: list[BookingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### 3.3 Standard API Envelope
```python
from typing import Generic, TypeVar
from pydantic import BaseModel
from datetime import datetime, timezone

DataT = TypeVar("DataT")

class ApiMeta(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    path: str
    version: str = "v1"
    request_id: Optional[str] = None

class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[list[dict]] = None

class ApiResponse(BaseModel, Generic[DataT]):
    data: Optional[DataT] = None
    meta: ApiMeta
    error: Optional[ApiError] = None

    @classmethod
    def ok(cls, data: DataT, path: str, request_id: Optional[str] = None) -> "ApiResponse[DataT]":
        return cls(data=data, meta=ApiMeta(path=path, request_id=request_id))

    @classmethod
    def fail(cls, error: ApiError, path: str) -> "ApiResponse[None]":
        return cls(data=None, meta=ApiMeta(path=path), error=error)
```

---

## 4. SQLALCHEMY 2.0 PATTERNS

### 4.1 Model Definition
```python
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from shared.database.base import Base

class BookingModel(Base):
    """SQLAlchemy ORM model for the bookings table."""

    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    drone_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_bookings_drone_time", "drone_id", "start_time", "end_time"),
    )

    @classmethod
    def from_entity(cls, entity: BookingEntity) -> "BookingModel":
        """Map domain entity → ORM model."""
        return cls(
            id=entity.id,
            user_id=entity.user_id,
            drone_id=entity.drone_id,
            status=entity.status.value,
            start_time=entity.start_time,
            end_time=entity.end_time,
            total_price=entity.total_price,
            notes=entity.notes,
        )

    def to_entity(self) -> BookingEntity:
        """Map ORM model → domain entity."""
        return BookingEntity(
            id=self.id,
            user_id=self.user_id,
            drone_id=self.drone_id,
            status=BookingStatus(self.status),
            start_time=self.start_time,
            end_time=self.end_time,
            total_price=self.total_price,
            notes=self.notes,
        )
```

### 4.2 Async Repository Pattern
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

class BookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entity: BookingEntity) -> BookingEntity:
        model = BookingModel.from_entity(entity)
        merged = await self._session.merge(model)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged.to_entity()

    async def get_by_id(self, booking_id: str) -> BookingEntity | None:
        result = await self._session.execute(
            select(BookingModel).where(BookingModel.id == booking_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def find_overlapping(
        self,
        drone_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[BookingEntity]:
        result = await self._session.execute(
            select(BookingModel).where(
                and_(
                    BookingModel.drone_id == drone_id,
                    BookingModel.status.in_(ACTIVE_STATUSES),
                    BookingModel.start_time < end_time,
                    BookingModel.end_time > start_time,
                )
            )
        )
        return [m.to_entity() for m in result.scalars().all()]
```

### 4.3 Transaction Scoping
```python
# Preferred: Use Unit of Work in use case
class CreateBookingUseCase:
    async def execute(self, command: CreateBookingCommand) -> BookingEntity:
        async with self._uow:
            booking = BookingEntity(...)
            saved = await self._uow.bookings.save(booking)
            await self._uow.outbox.save(BookingCreatedEvent(...))
            await self._uow.commit()
            return saved

# Alternative: explicit session.begin() in repository
async with self._session.begin():
    booking = await self._booking_repo.save(entity)
    await self._outbox_repo.save(event)
    # Auto-commits on exit, rollback on exception
```

---

## 5. FASTAPI CONTROLLER PATTERNS

### 5.1 Controller Structure
```python
from fastapi import APIRouter, Depends, status, Query, Path
from typing import Annotated

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=ApiResponse[BookingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new drone booking",
    response_description="Booking created successfully in PENDING_PAYMENT status",
)
async def create_booking(
    request: CreateBookingRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    service: Annotated[BookingService, Depends(get_booking_service)],
    req: Request,
) -> ApiResponse[BookingResponse]:
    """
    Create a new drone booking.

    Validates business rules, checks slot availability,
    acquires a distributed Redis lock, and publishes a BookingCreated event.
    """
    try:
        entity = await service.create_booking(
            CreateBookingCommand(
                user_id=user_id,
                drone_id=request.drone_id,
                start_time=request.start_time,
                end_time=request.end_time,
                total_price=request.total_price,
                notes=request.notes,
            )
        )
        return ApiResponse.ok(
            data=BookingResponse.model_validate(entity),
            path=str(req.url.path),
        )
    except DomainRuleViolationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except SlotConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
```

### 5.2 Dependency Injection
```python
# deps.py — centralize all dependencies
from functools import cache

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(connection_pool=_pool)
    try:
        yield client
    finally:
        await client.aclose()

def get_booking_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> BookingService:
    return BookingService(db=db, redis_client=redis)

async def get_current_user_id(
    authorization: str | None = Header(None),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = authorization[7:]
    return get_subject(token)  # Raises UnauthorizedError if invalid
```

### 5.3 Router Registration
```python
# app/main.py
from features.booking.api.controller import router as booking_router
from features.payment.api.controller import router as payment_router
from features.auth.api.controller import router as auth_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(booking_router, prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
```

---

## 6. DOMAIN ENTITY PATTERNS

### 6.1 Pure Domain Entity
```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from app.features.booking.domain.status import BookingStatus
from app.shared.exceptions.custom_exceptions import DomainRuleViolationError

@dataclass
class BookingEntity:
    """
    Domain entity for drone booking.

    INVARIANT: No I/O in this class — pure Python only.
    All state mutations go through explicit methods that enforce invariants.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    drone_id: str = ""
    status: BookingStatus = BookingStatus.DRAFT
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_price: float = 0.0
    notes: Optional[str] = None
    expired_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Business Methods ──────────────────────────────────────────────────

    def can_be_cancelled(self) -> bool:
        """Return True if booking can be cancelled by user."""
        return not self.status.is_terminal and self.status != BookingStatus.IN_PROGRESS

    def is_overdue(self) -> bool:
        """Return True if payment window has expired."""
        if self.expired_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expired_at

    def mark_as_paid(self) -> None:
        """Transition to PAID status."""
        self._transition_to(BookingStatus.PAID)

    def expire(self) -> None:
        """Transition to EXPIRED status."""
        self._transition_to(BookingStatus.EXPIRED)

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel booking with optional reason."""
        if not self.can_be_cancelled():
            raise DomainRuleViolationError(
                f"Booking in status '{self.status.value}' cannot be cancelled"
            )
        self._transition_to(BookingStatus.CANCELLED)

    def _transition_to(self, new_status: BookingStatus) -> None:
        """Internal state machine transition with validation."""
        if not self.status.can_transition_to(new_status):
            raise DomainRuleViolationError(
                f"Invalid transition: {self.status.value} → {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
```

### 6.2 Domain Rules (Pure Functions)
```python
"""
Booking domain rules.

ALL functions are pure — no I/O, no side effects, no external imports.
Each function raises DomainRuleViolationError on failure.
"""
from datetime import datetime, timezone, time as time_type
from app.shared.exceptions.custom_exceptions import DomainRuleViolationError


def validate_not_in_past(start_time: datetime) -> None:
    """Booking must not start in the past."""
    if start_time.tzinfo is None:
        raise DomainRuleViolationError("start_time must be timezone-aware")
    if start_time <= datetime.now(timezone.utc):
        raise DomainRuleViolationError("Booking start time must be in the future")


def validate_operating_hours(
    start_time: datetime,
    end_time: datetime,
    open_hour: int = 6,
    close_hour: int = 18,
) -> None:
    """Booking must fall within operating hours."""
    if start_time.time() < time_type(open_hour, 0):
        raise DomainRuleViolationError(f"Cannot start before {open_hour:02d}:00")
    if end_time.time() > time_type(close_hour, 0):
        raise DomainRuleViolationError(f"Cannot end after {close_hour:02d}:00")
    if start_time >= end_time:
        raise DomainRuleViolationError("end_time must be after start_time")
```

---

## 7. EVENTS & OUTBOX PATTERN

### 7.1 Event Dataclass
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

@dataclass(frozen=True)
class BookingCreated:
    """
    Emitted when a drone booking is successfully created.

    Immutable (frozen=True) — events are facts, never mutated.
    """
    booking_id: str
    user_id: str
    drone_id: str
    start_time: str        # ISO-8601 string for JSON serialization
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

### 7.2 Outbox Usage in Use Case
```python
async def execute(self, command: CreateBookingCommand) -> BookingEntity:
    # ... validation and slot lock ...

    async with self._session.begin():
        # 1. Save entity
        saved = await self._repo.save(booking)

        # 2. Save event to Outbox (SAME transaction — guaranteed delivery)
        event = BookingCreated(
            booking_id=saved.id,
            user_id=saved.user_id,
            drone_id=saved.drone_id,
            start_time=saved.start_time.isoformat(),
            end_time=saved.end_time.isoformat(),
            total_price=saved.total_price,
        )
        await self._outbox.save(event)

        # Both committed atomically
    # Background worker will pick up the outbox message and publish to RabbitMQ
    return saved
```

---

## 8. TESTING CONVENTIONS

### 8.1 File Naming
```
tests/unit/domain/test_booking_rules.py    # Test domain rules
tests/unit/domain/test_booking_entity.py   # Test entity methods
tests/unit/application/test_create_booking.py  # Test use case
tests/integration/test_booking_repository.py   # Real DB
tests/e2e/test_booking_api.py              # Full HTTP
```

### 8.2 Test Class Organization
```python
class TestValidateNotInPast:
    """Tests for validate_not_in_past domain rule."""

    def test_future_time_passes(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        validate_not_in_past(future)  # No exception

    def test_past_time_raises_domain_error(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(DomainRuleViolationError, match="future"):
            validate_not_in_past(past)

    def test_naive_datetime_raises_domain_error(self) -> None:
        with pytest.raises(DomainRuleViolationError, match="timezone"):
            validate_not_in_past(datetime.now())  # no tzinfo
```

### 8.3 Async Test Fixtures
```python
# tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest_asyncio.fixture
async def db_session():
    """Provide a test DB session that rolls back after each test."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test_db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def redis_client():
    """Provide a test Redis client (DB 15, flushed after test)."""
    import redis.asyncio as redis
    client = redis.Redis(host="localhost", port=6379, db=15)
    yield client
    await client.flushdb()
    await client.aclose()
```

### 8.4 Mock Strategy
```python
# Use pytest-mock or unittest.mock
# Mock at the boundary of the layer under test

@pytest.mark.asyncio
async def test_create_booking_publishes_event(
    mocker: MockerFixture,
) -> None:
    mock_repo = AsyncMock(spec=BookingRepository)
    mock_lock = AsyncMock(spec=RedisSlotLock)
    mock_outbox = AsyncMock(spec=OutboxRepository)

    mock_repo.find_overlapping.return_value = []   # No conflicts
    mock_lock.acquire_locks_for_booking.return_value = True
    mock_repo.save.return_value = sample_entity

    use_case = CreateBookingUseCase(mock_repo, mock_lock, mock_outbox)
    result = await use_case.execute(make_command())

    assert result.status == BookingStatus.PENDING_PAYMENT
    mock_outbox.save.assert_called_once()  # Event was queued
```

---

## 9. IMPORT ORGANIZATION

### 9.1 Import Order (enforced by ruff)
```python
# 1. Standard library
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

# 2. Third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local — shared
from shared.database.postgres import get_db
from shared.exceptions.custom_exceptions import DomainRuleViolationError

# 4. Local — same feature
from features.booking.domain.entity import BookingEntity
from features.booking.domain.status import BookingStatus
from features.booking.application.booking_service import BookingService
```

### 9.2 Relative vs Absolute Imports
```python
# ✅ PREFERRED — absolute imports everywhere
from features.booking.domain.entity import BookingEntity

# ❌ AVOID — relative imports (harder to refactor)
from ..domain.entity import BookingEntity
```

---

## 10. TOOLING CONFIGURATION

### pyproject.toml
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "ANN", "B", "S", "UP"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/migrations/*"]
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
```

---

## 11. ANTI-PATTERNS (NEVER DO)

```python
# ❌ Business logic in controllers
@router.post("/bookings")
async def create_booking(request: CreateBookingRequest, db = Depends(get_db)):
    if request.start_time < datetime.now():  # WRONG — domain logic here
        raise HTTPException(400, "Past date")
    booking = BookingModel(...)           # WRONG — ORM in controller
    db.add(booking)
    db.commit()

# ❌ Infrastructure in domain
class BookingEntity:
    async def save(self) -> None:         # WRONG — entity doing I/O
        await db.execute(...)

# ❌ Raw SQL with string interpolation
query = f"SELECT * FROM bookings WHERE id = {booking_id}"  # SQL INJECTION

# ❌ Hardcoded secrets
JWT_SECRET = "my-secret-key-123"         # CRITICAL SECURITY VIOLATION

# ❌ Blocking I/O in async context
async def get_booking(id: str):
    import requests
    response = requests.get(f"http://api/bookings/{id}")  # BLOCKS EVENT LOOP

# ❌ Unbounded queries
async def list_all_bookings():
    return await session.execute(select(BookingModel)).scalars().all()  # NO LIMIT

# ❌ Catching and swallowing exceptions
try:
    await do_something()
except Exception:
    pass  # NEVER silently swallow exceptions

# ❌ Cross-feature internal imports
from features.payment.infrastructure.repository import PaymentModel  # BYPASS INDEX
```

---

## 12. CHECKLIST: Before Every Commit

```markdown
### Code Quality
- [ ] All functions have type hints and docstrings
- [ ] No `Any` without justification comment
- [ ] No hardcoded secrets, URLs, or magic numbers
- [ ] No business logic in API layer or repository layer
- [ ] Domain layer has zero external imports
- [ ] No blocking I/O in async functions

### Performance
- [ ] All list queries are paginated (limit/offset)
- [ ] No N+1 queries (use eager loading)
- [ ] New columns used in WHERE have indexes in migration

### Security
- [ ] All user inputs validated via Pydantic
- [ ] No raw SQL string interpolation
- [ ] No PII in logs
- [ ] New endpoints have JWT auth dependency

### Testing
- [ ] New domain rules have unit tests
- [ ] New use cases have use case tests (mocked deps)
- [ ] `pytest` passes without warnings
- [ ] Coverage ≥ 80% for changed files

### Documentation
- [ ] `.agent/doc/<feature>-doc.md` updated if API changed
- [ ] Migration file has both upgrade() and downgrade()
- [ ] New migrations named YYYYMMDD_NNN_description.py
```
