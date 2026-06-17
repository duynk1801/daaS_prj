"""
BookingService — Application facade.

Provides a unified interface to all booking use cases.
Controllers and external code should interact with this service,
not directly with individual use cases.

Pattern: Facade + Dependency Injection
"""
from __future__ import annotations

import logging
from typing import List, Optional

from redis import Redis
from sqlalchemy.orm import Session

from app.features.booking.application.create_booking import (
    CreateBookingCommand,
    CreateBookingUseCase,
)
from app.features.booking.application.expire_booking import ExpireBookingUseCase
from app.features.booking.domain.booking_entity import BookingEntity
from app.features.booking.infrastructure.booking_repository import BookingRepository
from app.features.booking.infrastructure.rabbitmq_publisher import RabbitMQBookingPublisher
from app.shared.exceptions.custom_exceptions import DomainRuleViolationError, ForbiddenError

logger = logging.getLogger(__name__)


class BookingService:
    """
    Facade service for all booking operations.

    All business operations are delegated to dedicated use cases.
    This class handles dependency wiring and high-level orchestration.
    """

    def __init__(
        self,
        db: Session,
        redis_client: Redis,
        publisher: Optional[RabbitMQBookingPublisher] = None,
    ) -> None:
        self._db = db
        self._redis = redis_client
        self._publisher = publisher or RabbitMQBookingPublisher()
        self._repository = BookingRepository(db)

    def create_booking(self, command: CreateBookingCommand) -> BookingEntity:
        """
        Create a new drone booking.

        Args:
            command: All required booking creation parameters.

        Returns:
            The created BookingEntity.
        """
        use_case = CreateBookingUseCase(
            db=self._db,
            redis_client=self._redis,
            publisher=self._publisher,
        )
        return use_case.execute(command)

    def get_booking(self, booking_id: str, requesting_user_id: str) -> BookingEntity:
        """
        Get a booking by ID, validating ownership.

        Security: Only the booking owner can view their booking.
        Prevents IDOR (Insecure Direct Object Reference) attacks.

        Args:
            booking_id:         The booking UUID.
            requesting_user_id: The authenticated user's ID.

        Returns:
            BookingEntity if found and owned by requesting user.

        Raises:
            BookingNotFoundError: If booking doesn't exist or doesn't belong to user.
        """
        # get_by_id_and_user enforces ownership check at DB level
        return self._repository.get_by_id_and_user(booking_id, requesting_user_id)

    def list_bookings(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[BookingEntity]:
        """
        List bookings for the authenticated user.

        Users can only see their own bookings.

        Args:
            user_id: The authenticated user's ID.
            limit:   Max records per page (capped at 100 in repository).
            offset:  Pagination offset.

        Returns:
            List of BookingEntity objects.
        """
        return self._repository.find_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def cancel_booking(
        self,
        booking_id: str,
        requesting_user_id: str,
        reason: Optional[str] = None,
    ) -> BookingEntity:
        """
        Cancel a booking, validating ownership and cancellability.

        Args:
            booking_id:         The booking UUID.
            requesting_user_id: The authenticated user's ID.
            reason:             Optional cancellation reason.

        Returns:
            Updated BookingEntity in CANCELLED status.

        Raises:
            BookingNotFoundError: If booking not found or not owned by user.
            DomainRuleViolationError: If booking cannot be cancelled.
        """
        booking = self._repository.get_by_id_and_user(booking_id, requesting_user_id)
        booking.cancel(reason=reason)
        saved = self._repository.save(booking)
        self._db.commit()
        logger.info("Booking cancelled: id=%s user=%s", booking_id, requesting_user_id)
        return saved

    def process_expired_bookings(self) -> List[str]:
        """
        Background job: expire all overdue bookings.

        Returns:
            List of expired booking IDs.
        """
        use_case = ExpireBookingUseCase(
            db=self._db,
            redis_client=self._redis,
            publisher=self._publisher,
        )
        return use_case.execute()
