"""
BookingExpired domain event.

Published when a booking's payment window expires.
Consumers: slot release service, notification service, analytics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class BookingExpiredEvent:
    """
    Immutable event emitted when a booking expires due to payment timeout.
    """

    booking_id: str
    user_id: str
    drone_id: str
    start_time: str   # ISO-8601 string for serialization
    end_time: str     # ISO-8601 string for serialization
    reason: str = "payment_timeout"

    event_type: str = field(default="booking.expired", init=False)
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        init=False,
    )
