"""
Booking repository — SQLAlchemy implementation.

Security: All queries use ORM/parameterized statements.
NEVER use raw string concatenation to build SQL.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.features.booking.domain.booking_entity import BookingEntity
from app.features.booking.domain.booking_status import BookingStatus
from app.features.booking.infrastructure.booking_model import BookingModel
from app.shared.exceptions.custom_exceptions import BookingNotFoundError, DatabaseError

logger = logging.getLogger(__name__)


class BookingRepository:
    """
    Repository for Booking persistence operations.

    Translates between BookingEntity (domain) and BookingModel (ORM).
    SQL errors are caught and converted to DatabaseError — never exposed raw.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ─── Mapping Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(model: BookingModel) -> BookingEntity:
        """Map ORM model → domain entity."""
        return BookingEntity(
            id=model.id,
            user_id=model.user_id,
            drone_id=model.drone_id,
            area_id=model.area_id,
            package_id=model.package_id,
            start_time=model.start_time,
            end_time=model.end_time,
            status=BookingStatus(model.status),
            total_price=model.total_price,
            notes=model.notes,
            cancellation_reason=model.cancellation_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            expired_at=model.expired_at,
        )

    @staticmethod
    def _to_model(entity: BookingEntity) -> BookingModel:
        """Map domain entity → ORM model."""
        return BookingModel(
            id=entity.id,
            user_id=entity.user_id,
            drone_id=entity.drone_id,
            area_id=entity.area_id,
            package_id=entity.package_id,
            start_time=entity.start_time,
            end_time=entity.end_time,
            status=entity.status.value,
            total_price=entity.total_price,
            notes=entity.notes,
            cancellation_reason=entity.cancellation_reason,
            expired_at=entity.expired_at,
        )

    # ─── Public API ───────────────────────────────────────────────────────────

    def get_by_id(self, booking_id: str) -> BookingEntity:
        """
        Retrieve a booking by its ID.

        Args:
            booking_id: The booking UUID string.

        Returns:
            BookingEntity if found.

        Raises:
            BookingNotFoundError: If no booking with that ID exists.
            DatabaseError: On unexpected database failure.
        """
        try:
            stmt = select(BookingModel).where(BookingModel.id == booking_id)
            model = self._db.execute(stmt).scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.error("DB error in get_by_id: %s", type(exc).__name__)
            raise DatabaseError(detail=str(exc)) from exc

        if model is None:
            raise BookingNotFoundError(booking_id)

        return self._to_entity(model)

    def get_by_id_and_user(self, booking_id: str, user_id: str) -> BookingEntity:
        """
        Retrieve a booking by ID, validated to belong to the given user.

        Enforces resource ownership — prevents IDOR attacks.

        Args:
            booking_id: The booking UUID string.
            user_id:    The authenticated user's ID.

        Returns:
            BookingEntity if found and owned by user.

        Raises:
            BookingNotFoundError: If booking not found or not owned by user.
        """
        try:
            stmt = select(BookingModel).where(
                and_(
                    BookingModel.id == booking_id,
                    BookingModel.user_id == user_id,  # Ownership check
                )
            )
            model = self._db.execute(stmt).scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.error("DB error in get_by_id_and_user: %s", type(exc).__name__)
            raise DatabaseError(detail=str(exc)) from exc

        if model is None:
            # Return generic "not found" — don't reveal if it exists for another user
            raise BookingNotFoundError(booking_id)

        return self._to_entity(model)

    def save(self, entity: BookingEntity) -> BookingEntity:
        """
        Persist a booking entity (INSERT or UPDATE via merge).

        Args:
            entity: The BookingEntity to save.

        Returns:
            The saved entity.

        Raises:
            DatabaseError: On unexpected database failure.
        """
        try:
            model = self._to_model(entity)
            merged = self._db.merge(model)
            self._db.flush()
            self._db.refresh(merged)
            return self._to_entity(merged)
        except SQLAlchemyError as exc:
            logger.error("DB error in save: %s", type(exc).__name__)
            raise DatabaseError(detail=str(exc)) from exc

    def find_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[BookingEntity]:
        """
        List bookings for a specific user with pagination.

        Args:
            user_id: The user's ID.
            limit:   Maximum records to return.
            offset:  Records to skip (for pagination).

        Returns:
            List of BookingEntity ordered by created_at descending.
        """
        try:
            stmt = (
                select(BookingModel)
                .where(BookingModel.user_id == user_id)
                .order_by(BookingModel.created_at.desc())
                .limit(min(limit, 100))   # Cap at 100 to prevent abuse
                .offset(offset)
            )
            models = self._db.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]
        except SQLAlchemyError as exc:
            logger.error("DB error in find_by_user: %s", type(exc).__name__)
            raise DatabaseError(detail=str(exc)) from exc

    def find_expired(self) -> List[BookingEntity]:
        """
        Find all bookings that have passed their expiry time and are still active.

        Returns:
            List of expired BookingEntity objects awaiting status update.
        """
        now = datetime.now(timezone.utc)
        try:
            stmt = select(BookingModel).where(
                and_(
                    BookingModel.expired_at <= now,
                    BookingModel.status == BookingStatus.PENDING_PAYMENT.value,
                )
            )
            models = self._db.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]
        except SQLAlchemyError as exc:
            logger.error("DB error in find_expired: %s", type(exc).__name__)
            raise DatabaseError(detail=str(exc)) from exc

    def find_overlapping(
        self,
        drone_id: str,
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[str] = None,
    ) -> List[BookingEntity]:
        """
        Find active bookings for a drone that overlap with the given time range.

        Uses parameterized ORM queries — no raw SQL.

        Args:
            drone_id:           The drone to check.
            start_time:         Requested start.
            end_time:           Requested end.
            exclude_booking_id: Exclude this booking ID (useful when updating).

        Returns:
            List of overlapping active bookings.
        """
        # Active statuses that count as "occupying" a slot
        active_statuses = [
            s.value for s in BookingStatus if s.is_active
        ]

        try:
            stmt = select(BookingModel).where(
                and_(
                    BookingModel.drone_id == drone_id,
                    BookingModel.status.in_(active_statuses),
                    # Overlap condition: new[start, end) overlaps existing[start, end)
                    and_(
                        BookingModel.start_time < end_time,
                        BookingModel.end_time > start_time,
                    ),
                )
            )
            if exclude_booking_id:
                stmt = stmt.where(BookingModel.id != exclude_booking_id)

            models = self._db.execute(stmt).scalars().all()
            return [self._to_entity(m) for m in models]
        except SQLAlchemyError as exc:
            logger.error("DB error in find_overlapping: %s", type(exc).__name__)
            raise DatabaseError(detail=str(exc)) from exc
