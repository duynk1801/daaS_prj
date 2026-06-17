"""
Unit tests for CreateBooking use case.

Uses mocked dependencies — no real DB, Redis, or RabbitMQ.
Tests orchestration logic, rollback behavior, and event publishing.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

from app.features.booking.application.create_booking import (
    CreateBookingCommand,
    CreateBookingUseCase,
)
from app.features.booking.domain.booking_entity import BookingEntity
from app.features.booking.domain.booking_status import BookingStatus
from app.shared.exceptions.custom_exceptions import (
    DomainRuleViolationError,
    SlotConflictError,
    SlotLockError,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_command(**overrides) -> CreateBookingCommand:
    """Create a valid CreateBookingCommand with sensible defaults."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        user_id="user-123",
        drone_id="drone-456",
        area_id="area-789",
        package_id="pkg-001",
        start_time=(now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0),
        end_time=(now + timedelta(days=2)).replace(hour=11, minute=0, second=0, microsecond=0),
        total_price=500.0,
        notes=None,
        package_is_active=True,
        package_name="Standard",
        area_is_supported=True,
        area_name="Zone A",
    )
    defaults.update(overrides)
    return CreateBookingCommand(**defaults)


def _make_saved_entity(command: CreateBookingCommand) -> BookingEntity:
    """Create a mock saved entity matching the command."""
    entity = BookingEntity(
        user_id=command.user_id,
        drone_id=command.drone_id,
        area_id=command.area_id,
        package_id=command.package_id,
        start_time=command.start_time,
        end_time=command.end_time,
        total_price=command.total_price,
        status=BookingStatus.PENDING_PAYMENT,
    )
    entity.expired_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    return entity


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestCreateBookingUseCase:

    def _make_use_case(
        self,
        mock_db=None,
        mock_redis=None,
        mock_publisher=None,
        repository_returns=None,
        overlapping_returns=None,
        lock_returns=True,
    ):
        """Factory to create use case with all dependencies mocked."""
        db = mock_db or MagicMock()
        redis = mock_redis or MagicMock()
        publisher = mock_publisher or MagicMock()

        use_case = CreateBookingUseCase(db=db, redis_client=redis, publisher=publisher)

        # Mock the repository
        mock_repo = MagicMock()
        if overlapping_returns is not None:
            mock_repo.find_overlapping.return_value = overlapping_returns
        else:
            mock_repo.find_overlapping.return_value = []

        if repository_returns is not None:
            mock_repo.save.return_value = repository_returns

        use_case._repository = mock_repo

        # Mock the slot lock
        mock_lock = MagicMock()
        mock_lock.acquire_locks_for_booking.return_value = lock_returns
        use_case._slot_lock = mock_lock

        return use_case, mock_repo, mock_lock, publisher, db

    def test_successful_booking_creation(self) -> None:
        """Happy path: valid command → booking created, event published."""
        command = _make_command()
        saved_entity = _make_saved_entity(command)

        use_case, mock_repo, mock_lock, mock_publisher, mock_db = self._make_use_case(
            repository_returns=saved_entity,
        )

        result = use_case.execute(command)

        # Entity was saved
        mock_repo.save.assert_called_once()

        # DB committed
        mock_db.commit.assert_called_once()

        # Slot locks acquired
        mock_lock.acquire_locks_for_booking.assert_called_once()

        # Event published
        mock_publisher.publish_booking_created.assert_called_once()

        # Result is the saved entity
        assert result == saved_entity

    def test_domain_rule_violation_stops_execution(self) -> None:
        """If domain rules fail, nothing should be saved or locked."""
        now = datetime.now(timezone.utc)
        # Create booking in the past — should fail domain rules
        command = _make_command(
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
        )

        use_case, mock_repo, mock_lock, mock_publisher, _ = self._make_use_case()

        with pytest.raises(DomainRuleViolationError):
            use_case.execute(command)

        # Nothing should be persisted or locked
        mock_repo.save.assert_not_called()
        mock_lock.acquire_locks_for_booking.assert_not_called()
        mock_publisher.publish_booking_created.assert_not_called()

    def test_slot_conflict_stops_execution(self) -> None:
        """If overlapping bookings exist, should raise SlotConflictError."""
        command = _make_command()
        existing_booking = MagicMock(spec=BookingEntity)

        use_case, mock_repo, mock_lock, mock_publisher, _ = self._make_use_case(
            overlapping_returns=[existing_booking],  # Conflict!
        )

        with pytest.raises(SlotConflictError):
            use_case.execute(command)

        # No lock acquired, no save, no event
        mock_lock.acquire_locks_for_booking.assert_not_called()
        mock_repo.save.assert_not_called()
        mock_publisher.publish_booking_created.assert_not_called()

    def test_redis_lock_failure_stops_execution(self) -> None:
        """If Redis lock cannot be acquired, should raise SlotLockError."""
        command = _make_command()

        use_case, mock_repo, mock_lock, mock_publisher, _ = self._make_use_case(
            lock_returns=False,  # Lock acquisition fails
        )

        with pytest.raises(SlotLockError):
            use_case.execute(command)

        # Repository should not be called
        mock_repo.save.assert_not_called()
        mock_publisher.publish_booking_created.assert_not_called()

    def test_db_failure_releases_locks(self) -> None:
        """If DB save fails, Redis locks should be released (rollback)."""
        from app.shared.exceptions.custom_exceptions import DatabaseError
        command = _make_command()

        use_case, mock_repo, mock_lock, mock_publisher, mock_db = self._make_use_case()

        # Make save raise an error
        mock_repo.save.side_effect = DatabaseError("DB down")

        with pytest.raises(DatabaseError):
            use_case.execute(command)

        # Lock was acquired then released during rollback
        mock_lock.acquire_locks_for_booking.assert_called_once()
        mock_lock.release_locks_for_booking.assert_called_once()

        # DB rolled back
        mock_db.rollback.assert_called_once()

        # No event published
        mock_publisher.publish_booking_created.assert_not_called()

    def test_booking_status_is_pending_payment(self) -> None:
        """Created booking should be in PENDING_PAYMENT status."""
        command = _make_command()

        # Use real entity from save (test what's passed to repo.save)
        saved_entities = []

        def capture_save(entity):
            saved_entities.append(entity)
            return entity

        use_case, mock_repo, mock_lock, mock_publisher, mock_db = self._make_use_case()
        mock_repo.save.side_effect = capture_save

        use_case.execute(command)

        assert len(saved_entities) == 1
        assert saved_entities[0].status == BookingStatus.PENDING_PAYMENT

    def test_booking_has_expiry_set(self) -> None:
        """Created booking should have expired_at set."""
        command = _make_command()

        saved_entities = []

        def capture_save(entity):
            saved_entities.append(entity)
            return entity

        use_case, mock_repo, mock_lock, mock_publisher, mock_db = self._make_use_case()
        mock_repo.save.side_effect = capture_save

        use_case.execute(command)

        assert saved_entities[0].expired_at is not None
        # Expiry should be in the future
        assert saved_entities[0].expired_at > datetime.now(timezone.utc)
