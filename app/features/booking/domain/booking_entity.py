"""
Booking domain entity.

Pure domain object — no database or framework dependencies.
Encapsulates business logic and invariants for drone bookings.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.features.booking.domain.booking_status import BookingStatus
from app.shared.exceptions.custom_exceptions import DomainRuleViolationError


@dataclass
class BookingEntity:
    """
    Domain entity representing a drone booking.

    All state-changing operations go through methods that enforce
    business rules and valid state transitions.
    """

    # ─── Identity ────────────────────────────────────────────────────────────
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""

    # ─── Booking Details ──────────────────────────────────────────────────────
    drone_id: str = ""
    area_id: str = ""
    package_id: str = ""

    # ─── Schedule ─────────────────────────────────────────────────────────────
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # ─── Status & Lifecycle ───────────────────────────────────────────────────
    status: BookingStatus = BookingStatus.DRAFT
    total_price: float = 0.0
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None

    # ─── Timestamps ───────────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expired_at: Optional[datetime] = None  # Absolute expiry deadline

    # ─── Business Methods ─────────────────────────────────────────────────────

    def is_expired(self) -> bool:
        """Return True if the booking has passed its expiry deadline."""
        if self.expired_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expired_at

    def can_be_cancelled(self) -> bool:
        """Return True if the booking can be cancelled by the user."""
        return not self.status.is_terminal and self.status != BookingStatus.IN_PROGRESS

    def get_duration_minutes(self) -> float:
        """
        Return booking duration in minutes.

        Returns:
            Duration in minutes, or 0 if times are not set.
        """
        if self.start_time is None or self.end_time is None:
            return 0.0
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 60

    def transition_to(self, new_status: BookingStatus, reason: Optional[str] = None) -> None:
        """
        Transition the booking to a new status, enforcing the state machine.

        Args:
            new_status: The target status.
            reason: Optional reason (used for cancellation/expiry).

        Raises:
            DomainRuleViolationError: If the transition is not allowed.
        """
        if not self.status.can_transition_to(new_status):
            raise DomainRuleViolationError(
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

        if new_status == BookingStatus.CANCELLED and reason:
            self.cancellation_reason = reason

    def mark_as_pending_payment(self, expired_at: datetime) -> None:
        """
        Move booking to PENDING_PAYMENT state with payment expiry deadline.

        Args:
            expired_at: Absolute datetime after which booking auto-expires.
        """
        self.transition_to(BookingStatus.PENDING_PAYMENT)
        self.expired_at = expired_at

    def mark_as_paid(self) -> None:
        """Mark the booking as paid."""
        self.transition_to(BookingStatus.PAID)

    def mark_as_confirmed(self) -> None:
        """Mark the booking as confirmed by operator."""
        self.transition_to(BookingStatus.CONFIRMED)

    def mark_as_in_progress(self) -> None:
        """Mark the booking as currently in-progress."""
        self.transition_to(BookingStatus.IN_PROGRESS)

    def mark_as_completed(self) -> None:
        """Mark the booking as successfully completed."""
        self.transition_to(BookingStatus.COMPLETED)

    def mark_as_expired(self) -> None:
        """Mark the booking as expired (payment timeout)."""
        self.transition_to(BookingStatus.EXPIRED)

    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Cancel the booking.

        Args:
            reason: Optional reason for cancellation.

        Raises:
            DomainRuleViolationError: If booking cannot be cancelled.
        """
        if not self.can_be_cancelled():
            raise DomainRuleViolationError(
                f"Booking in status '{self.status.value}' cannot be cancelled"
            )
        self.transition_to(BookingStatus.CANCELLED, reason=reason)

    def __repr__(self) -> str:
        return (
            f"BookingEntity(id={self.id!r}, drone_id={self.drone_id!r}, "
            f"status={self.status.value!r}, "
            f"start_time={self.start_time!r})"
        )
