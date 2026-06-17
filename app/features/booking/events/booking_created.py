"""
BookingCreated domain event.

Published when a new booking is successfully created.
Consumers: notification service, analytics, slot management.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class BookingCreatedEvent:
    """
    Immutable event emitted when a booking is created.

    Fields are intentionally minimal — downstream consumers
    should query the booking service for full details if needed.
    """

    booking_id: str
    user_id: str
    drone_id: str
    area_id: str
    package_id: str
    start_time: str   # ISO-8601 string for serialization
    end_time: str     # ISO-8601 string for serialization
    total_price: float
    status: str

    event_type: str = field(default="booking.created", init=False)
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        init=False,
    )
