"""
Booking domain rules.

Contains pure business rule validators — no I/O, no DB, no HTTP.
Each rule raises DomainRuleViolationError on failure.
"""
from __future__ import annotations

from datetime import datetime, timezone, time as time_type
from typing import Protocol

from app.config.settings import get_settings
from app.shared.exceptions.custom_exceptions import DomainRuleViolationError

_settings = get_settings()


# ─── Protocols (for dependency inversion) ────────────────────────────────────

class PackageInfo(Protocol):
    """Minimal interface for package data needed by domain rules."""
    is_active: bool
    name: str


class AreaInfo(Protocol):
    """Minimal interface for area data needed by domain rules."""
    is_supported: bool
    name: str


# ─── Individual Rule Functions ────────────────────────────────────────────────

def validate_not_in_past(start_time: datetime) -> None:
    """
    Rule: Bookings cannot be created for a past time.

    Args:
        start_time: The requested booking start time (timezone-aware).

    Raises:
        DomainRuleViolationError: If start_time is in the past.
    """
    now = datetime.now(timezone.utc)
    # Ensure start_time is timezone-aware for comparison
    if start_time.tzinfo is None:
        raise DomainRuleViolationError("start_time must be timezone-aware")
    if start_time <= now:
        raise DomainRuleViolationError(
            "Booking start time must be in the future"
        )


def validate_operating_hours(start_time: datetime, end_time: datetime) -> None:
    """
    Rule: Bookings must be within operating hours (06:00–18:00 local UTC).

    Args:
        start_time: Booking start (timezone-aware).
        end_time:   Booking end (timezone-aware).

    Raises:
        DomainRuleViolationError: If either time falls outside operating hours.
    """
    min_hour = _settings.BOOKING_MIN_HOUR  # default 6
    max_hour = _settings.BOOKING_MAX_HOUR  # default 18

    operating_start = time_type(min_hour, 0)
    operating_end = time_type(max_hour, 0)

    start_local = start_time.time().replace(tzinfo=None)
    end_local = end_time.time().replace(tzinfo=None)

    if start_local < operating_start:
        raise DomainRuleViolationError(
            f"Booking cannot start before {min_hour:02d}:00"
        )
    if end_local > operating_end:
        raise DomainRuleViolationError(
            f"Booking cannot end after {max_hour:02d}:00"
        )
    if start_time >= end_time:
        raise DomainRuleViolationError(
            "Booking end time must be after start time"
        )


def validate_minimum_duration(start_time: datetime, end_time: datetime, min_minutes: int = 30) -> None:
    """
    Rule: Booking must be at least min_minutes long.

    Args:
        start_time:   Booking start.
        end_time:     Booking end.
        min_minutes:  Minimum booking duration in minutes.

    Raises:
        DomainRuleViolationError: If duration is too short.
    """
    duration_minutes = (end_time - start_time).total_seconds() / 60
    if duration_minutes < min_minutes:
        raise DomainRuleViolationError(
            f"Booking must be at least {min_minutes} minutes long"
        )


def validate_package_is_active(package: PackageInfo) -> None:
    """
    Rule: Only active packages can be booked.

    Args:
        package: Package data object.

    Raises:
        DomainRuleViolationError: If the package is not active.
    """
    if not package.is_active:
        raise DomainRuleViolationError(
            f"Package '{package.name}' is not currently available for booking"
        )


def validate_area_is_supported(area: AreaInfo) -> None:
    """
    Rule: Bookings can only be made for supported areas.

    Args:
        area: Area data object.

    Raises:
        DomainRuleViolationError: If the area is not supported.
    """
    if not area.is_supported:
        raise DomainRuleViolationError(
            f"Area '{area.name}' is not supported for drone operations"
        )


# ─── Composite Rule Validator ─────────────────────────────────────────────────

class BookingRules:
    """
    Facade that runs all booking domain rules in one call.

    Usage:
        rules = BookingRules()
        rules.validate_new_booking(start_time, end_time, package, area)
    """

    def validate_new_booking(
        self,
        start_time: datetime,
        end_time: datetime,
        package: PackageInfo,
        area: AreaInfo,
    ) -> None:
        """
        Run all validation rules for creating a new booking.

        Args:
            start_time: Requested booking start time (timezone-aware).
            end_time:   Requested booking end time (timezone-aware).
            package:    Package being booked.
            area:       Area being booked.

        Raises:
            DomainRuleViolationError: On any rule violation (first failure wins).
        """
        validate_not_in_past(start_time)
        validate_operating_hours(start_time, end_time)
        validate_minimum_duration(start_time, end_time)
        validate_package_is_active(package)
        validate_area_is_supported(area)
