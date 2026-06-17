"""
CreateBooking use case.

Orchestrates the full booking creation flow:
  1. Validate domain rules
  2. Check slot availability (DB query)
  3. Acquire distributed Redis lock
  4. Create and persist booking entity
  5. Publish BookingCreated event

SOLID: Single responsibility — this class only handles booking creation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.features.booking.domain.booking_entity import BookingEntity
from app.features.booking.domain.booking_rules import BookingRules
from app.features.booking.domain.booking_status import BookingStatus
from app.features.booking.events.booking_created import BookingCreatedEvent
from app.features.booking.infrastructure.booking_repository import BookingRepository
from app.features.booking.infrastructure.rabbitmq_publisher import RabbitMQBookingPublisher
from app.features.booking.infrastructure.redis_slot_lock import RedisSlotLock
from app.shared.exceptions.custom_exceptions import SlotConflictError, SlotLockError
from redis import Redis

logger = logging.getLogger(__name__)

_settings = get_settings()


@dataclass
class CreateBookingCommand:
    """Input data for the CreateBooking use case."""

    user_id: str
    drone_id: str
    area_id: str
    package_id: str
    start_time: datetime
    end_time: datetime
    total_price: float
    notes: Optional[str] = None

    # Injected package/area info for domain rule validation
    package_is_active: bool = True
    package_name: str = ""
    area_is_supported: bool = True
    area_name: str = ""


class CreateBookingUseCase:
    """
    Use case: Create a new drone booking.

    Dependencies are injected via constructor (Dependency Inversion Principle).
    """

    def __init__(
        self,
        db: Session,
        redis_client: Redis,
        publisher: RabbitMQBookingPublisher,
        rules: Optional[BookingRules] = None,
    ) -> None:
        self._repository = BookingRepository(db)
        self._slot_lock = RedisSlotLock(redis_client)
        self._publisher = publisher
        self._rules = rules or BookingRules()
        self._db = db

    def execute(self, command: CreateBookingCommand) -> BookingEntity:
        """
        Execute the booking creation workflow.

        Args:
            command: CreateBookingCommand with all required booking details.

        Returns:
            The created BookingEntity in PENDING_PAYMENT status.

        Raises:
            DomainRuleViolationError: If business rules are violated.
            SlotConflictError: If the slot is already booked.
            SlotLockError: If the Redis lock cannot be acquired.
            DatabaseError: On unexpected database failure.
        """
        # ── Step 1: Validate domain rules ──────────────────────────────────
        self._rules.validate_new_booking(
            start_time=command.start_time,
            end_time=command.end_time,
            package=_PackageInfoAdapter(command.package_is_active, command.package_name),
            area=_AreaInfoAdapter(command.area_is_supported, command.area_name),
        )
        logger.debug("Domain rules validated for booking request user=%s", command.user_id)

        # ── Step 2: Check slot availability in DB ──────────────────────────
        overlapping = self._repository.find_overlapping(
            drone_id=command.drone_id,
            start_time=command.start_time,
            end_time=command.end_time,
        )
        if overlapping:
            raise SlotConflictError(
                drone_id=command.drone_id,
                start_time=command.start_time.isoformat(),
                end_time=command.end_time.isoformat(),
            )

        # ── Step 3: Acquire Redis slot lock ────────────────────────────────
        # Create entity first to get its ID for lock ownership
        booking = BookingEntity(
            user_id=command.user_id,
            drone_id=command.drone_id,
            area_id=command.area_id,
            package_id=command.package_id,
            start_time=command.start_time,
            end_time=command.end_time,
            total_price=command.total_price,
            notes=command.notes,
        )

        slot_date = command.start_time.date().isoformat()
        start_hour = command.start_time.hour
        end_hour = command.end_time.hour or 24  # Handle midnight

        lock_acquired = self._slot_lock.acquire_locks_for_booking(
            drone_id=command.drone_id,
            slot_date=slot_date,
            start_hour=start_hour,
            end_hour=end_hour,
            booking_id=booking.id,
        )
        if not lock_acquired:
            raise SlotLockError(
                slot_key=f"{command.drone_id}:{slot_date}:{start_hour}-{end_hour}"
            )

        try:
            # ── Step 4: Persist booking ────────────────────────────────────
            expired_at = datetime.now(timezone.utc) + timedelta(
                minutes=_settings.BOOKING_EXPIRY_MINUTES
            )
            booking.mark_as_pending_payment(expired_at=expired_at)
            saved_booking = self._repository.save(booking)
            self._db.commit()

            # ── Step 5: Publish event ──────────────────────────────────────
            event = BookingCreatedEvent(
                booking_id=saved_booking.id,
                user_id=saved_booking.user_id,
                drone_id=saved_booking.drone_id,
                area_id=saved_booking.area_id,
                package_id=saved_booking.package_id,
                start_time=saved_booking.start_time.isoformat(),
                end_time=saved_booking.end_time.isoformat(),
                total_price=saved_booking.total_price,
                status=saved_booking.status.value,
            )
            self._publisher.publish_booking_created(event)

            logger.info(
                "Booking created: id=%s user=%s drone=%s",
                saved_booking.id,
                saved_booking.user_id,
                saved_booking.drone_id,
            )
            return saved_booking

        except Exception:
            # Rollback: release all acquired slot locks on failure
            self._slot_lock.release_locks_for_booking(
                drone_id=command.drone_id,
                slot_date=slot_date,
                start_hour=start_hour,
                end_hour=end_hour,
                booking_id=booking.id,
            )
            self._db.rollback()
            raise


# ─── Adapters for domain rule protocols ──────────────────────────────────────

class _PackageInfoAdapter:
    """Adapts command data to the PackageInfo protocol."""

    def __init__(self, is_active: bool, name: str) -> None:
        self.is_active = is_active
        self.name = name


class _AreaInfoAdapter:
    """Adapts command data to the AreaInfo protocol."""

    def __init__(self, is_supported: bool, name: str) -> None:
        self.is_supported = is_supported
        self.name = name
