"""
ExpireBooking use case.

Handles the background process of expiring bookings that have
exceeded their payment window. Designed to be called by a scheduler.

Flow:
  1. Find all PENDING_PAYMENT bookings past their expired_at timestamp
  2. For each: update status to EXPIRED
  3. Release Redis slot locks
  4. Publish BookingExpired event
"""
from __future__ import annotations

import logging
from typing import List

from redis import Redis
from sqlalchemy.orm import Session

from app.features.booking.domain.booking_entity import BookingEntity
from app.features.booking.events.booking_expired import BookingExpiredEvent
from app.features.booking.infrastructure.booking_repository import BookingRepository
from app.features.booking.infrastructure.rabbitmq_publisher import RabbitMQBookingPublisher
from app.features.booking.infrastructure.redis_slot_lock import RedisSlotLock

logger = logging.getLogger(__name__)


class ExpireBookingUseCase:
    """
    Use case: Process and expire overdue bookings.

    Intended to be run by a periodic scheduler (e.g., every minute).
    Each booking is processed independently to ensure partial failures
    don't block other expirations.
    """

    def __init__(
        self,
        db: Session,
        redis_client: Redis,
        publisher: RabbitMQBookingPublisher,
    ) -> None:
        self._repository = BookingRepository(db)
        self._slot_lock = RedisSlotLock(redis_client)
        self._publisher = publisher
        self._db = db

    def execute(self) -> List[str]:
        """
        Find and expire all overdue bookings.

        Returns:
            List of booking IDs that were successfully expired.
        """
        expired_ids: List[str] = []

        try:
            expired_bookings = self._repository.find_expired()
        except Exception as exc:
            logger.error("Failed to fetch expired bookings: %s", type(exc).__name__)
            return expired_ids

        logger.info("Found %d booking(s) to expire", len(expired_bookings))

        for booking in expired_bookings:
            try:
                self._expire_single(booking)
                expired_ids.append(booking.id)
            except Exception as exc:
                # Continue processing remaining bookings even if one fails
                logger.error(
                    "Failed to expire booking %s: %s",
                    booking.id,
                    type(exc).__name__,
                )

        return expired_ids

    def _expire_single(self, booking: BookingEntity) -> None:
        """
        Expire a single booking.

        Args:
            booking: The BookingEntity to expire.
        """
        # Mark as expired in domain model
        booking.mark_as_expired()

        # Persist status change
        self._repository.save(booking)
        self._db.commit()

        # Release Redis slot locks so the slot becomes available again
        if booking.start_time and booking.end_time:
            slot_date = booking.start_time.date().isoformat()
            start_hour = booking.start_time.hour
            end_hour = booking.end_time.hour or 24

            self._slot_lock.release_locks_for_booking(
                drone_id=booking.drone_id,
                slot_date=slot_date,
                start_hour=start_hour,
                end_hour=end_hour,
                booking_id=booking.id,
            )

        # Publish expiry event
        event = BookingExpiredEvent(
            booking_id=booking.id,
            user_id=booking.user_id,
            drone_id=booking.drone_id,
            start_time=booking.start_time.isoformat() if booking.start_time else "",
            end_time=booking.end_time.isoformat() if booking.end_time else "",
            reason="payment_timeout",
        )
        self._publisher.publish_booking_expired(event)

        logger.info("Booking expired: id=%s user=%s", booking.id, booking.user_id)
