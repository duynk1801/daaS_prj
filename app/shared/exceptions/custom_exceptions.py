"""
Custom exception hierarchy for the Drone Booking Service.

Error messages returned to clients are intentionally generic.
Detailed context is logged server-side only.
"""


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail  # Internal detail, never sent to client


# ─── Auth / Security ────────────────────────────────────────────────────────

class UnauthorizedError(AppError):
    """Raised when authentication fails or token is invalid."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


class ForbiddenError(AppError):
    """Raised when authenticated user lacks permission for the operation."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message)


# ─── Domain / Business Rules ─────────────────────────────────────────────────

class DomainRuleViolationError(AppError):
    """Raised when a domain business rule is violated."""
    pass


class BookingNotFoundError(AppError):
    """Raised when a booking cannot be found."""

    def __init__(self, booking_id: str) -> None:
        super().__init__(
            f"Booking not found",
            detail=f"Booking with id={booking_id} does not exist",
        )
        self.booking_id = booking_id


class SlotConflictError(AppError):
    """Raised when a time slot is already booked or locked."""

    def __init__(self, drone_id: str, start_time: str, end_time: str) -> None:
        super().__init__(
            "The selected time slot is not available",
            detail=f"Drone {drone_id} slot [{start_time} - {end_time}] is already taken",
        )


class SlotLockError(AppError):
    """Raised when acquiring a distributed slot lock fails."""

    def __init__(self, slot_key: str) -> None:
        super().__init__(
            "Unable to reserve slot — please try again",
            detail=f"Failed to acquire Redis lock for slot: {slot_key}",
        )


# ─── Infrastructure ───────────────────────────────────────────────────────────

class DatabaseError(AppError):
    """Raised for unexpected database errors (after being caught internally)."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(
            "A database error occurred",
            detail=detail,
        )


class MessagingError(AppError):
    """Raised when event publishing to the message broker fails."""

    def __init__(self, event_name: str) -> None:
        super().__init__(
            "Failed to process request",
            detail=f"Could not publish event: {event_name}",
        )


# ─── Validation ───────────────────────────────────────────────────────────────

class ValidationError(AppError):
    """Raised for input validation failures not covered by Pydantic."""
    pass
