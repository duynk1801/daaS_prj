"""
Booking status enumeration.

Represents all valid lifecycle states for a drone booking.
State transitions are governed by booking_rules.py.
"""
from enum import Enum


class BookingStatus(str, Enum):
    """
    Booking lifecycle states.

    State machine:
        DRAFT → PENDING_PAYMENT → PAID → CONFIRMED → IN_PROGRESS → COMPLETED
                             ↓              ↓
                     PAYMENT_FAILED      CANCELLED
        Any state (except COMPLETED/CANCELLED) → EXPIRED (via scheduler)
    """

    DRAFT = "DRAFT"
    """Initial state when booking is first created."""

    PENDING_PAYMENT = "PENDING_PAYMENT"
    """Booking created, awaiting payment confirmation."""

    PAID = "PAID"
    """Payment confirmed, awaiting operator confirmation."""

    CONFIRMED = "CONFIRMED"
    """Booking confirmed by operator, drone allocated."""

    IN_PROGRESS = "IN_PROGRESS"
    """Drone mission currently underway."""

    COMPLETED = "COMPLETED"
    """Mission successfully completed."""

    EXPIRED = "EXPIRED"
    """Booking expired due to payment timeout or inactivity."""

    CANCELLED = "CANCELLED"
    """Booking cancelled by user or operator."""

    PAYMENT_FAILED = "PAYMENT_FAILED"
    """Payment processing failed."""

    @property
    def is_terminal(self) -> bool:
        """Return True if this is a final, non-changeable state."""
        return self in (
            BookingStatus.COMPLETED,
            BookingStatus.EXPIRED,
            BookingStatus.CANCELLED,
            BookingStatus.PAYMENT_FAILED,
        )

    @property
    def is_active(self) -> bool:
        """Return True if the booking is still active (occupying a slot)."""
        return self in (
            BookingStatus.DRAFT,
            BookingStatus.PENDING_PAYMENT,
            BookingStatus.PAID,
            BookingStatus.CONFIRMED,
            BookingStatus.IN_PROGRESS,
        )

    def can_transition_to(self, new_status: "BookingStatus") -> bool:
        """
        Validate if transition from current state to new_status is allowed.

        Args:
            new_status: Target status to transition to.

        Returns:
            True if the transition is valid.
        """
        allowed: dict[BookingStatus, set[BookingStatus]] = {
            BookingStatus.DRAFT: {BookingStatus.PENDING_PAYMENT, BookingStatus.CANCELLED},
            BookingStatus.PENDING_PAYMENT: {
                BookingStatus.PAID,
                BookingStatus.PAYMENT_FAILED,
                BookingStatus.EXPIRED,
                BookingStatus.CANCELLED,
            },
            BookingStatus.PAID: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
            BookingStatus.CONFIRMED: {BookingStatus.IN_PROGRESS, BookingStatus.CANCELLED},
            BookingStatus.IN_PROGRESS: {BookingStatus.COMPLETED},
            BookingStatus.COMPLETED: set(),
            BookingStatus.EXPIRED: set(),
            BookingStatus.CANCELLED: set(),
            BookingStatus.PAYMENT_FAILED: {BookingStatus.PENDING_PAYMENT},
        }
        return new_status in allowed.get(self, set())
