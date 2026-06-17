"""
Unit tests for Booking domain rules.

All tests are pure — no database, no Redis, no HTTP.
Domain rules are deterministic functions, easily testable in isolation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.features.booking.domain.booking_rules import (
    BookingRules,
    validate_not_in_past,
    validate_operating_hours,
    validate_minimum_duration,
    validate_package_is_active,
    validate_area_is_supported,
)
from app.shared.exceptions.custom_exceptions import DomainRuleViolationError


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_time(hour: int, days_from_now: int = 2) -> datetime:
    """Create a future datetime at the given hour."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=days_from_now)
    return future.replace(hour=hour, minute=0, second=0, microsecond=0)


def _active_package() -> MagicMock:
    p = MagicMock()
    p.is_active = True
    p.name = "Standard Package"
    return p


def _inactive_package() -> MagicMock:
    p = MagicMock()
    p.is_active = False
    p.name = "Discontinued Package"
    return p


def _supported_area() -> MagicMock:
    a = MagicMock()
    a.is_supported = True
    a.name = "Zone A"
    return a


def _unsupported_area() -> MagicMock:
    a = MagicMock()
    a.is_supported = False
    a.name = "Restricted Zone"
    return a


# ─── validate_not_in_past ─────────────────────────────────────────────────────

class TestValidateNotInPast:
    def test_future_time_passes(self) -> None:
        """Booking in the future should pass validation."""
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        validate_not_in_past(future)  # Should not raise

    def test_past_time_raises(self) -> None:
        """Booking in the past should be rejected."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(DomainRuleViolationError, match="future"):
            validate_not_in_past(past)

    def test_current_time_raises(self) -> None:
        """Booking at exactly now (or slightly past) should be rejected."""
        now = datetime.now(timezone.utc) - timedelta(seconds=1)
        with pytest.raises(DomainRuleViolationError):
            validate_not_in_past(now)

    def test_naive_datetime_raises(self) -> None:
        """Timezone-naive datetimes should be rejected."""
        naive = datetime.now()  # No tzinfo
        with pytest.raises(DomainRuleViolationError, match="timezone"):
            validate_not_in_past(naive)


# ─── validate_operating_hours ─────────────────────────────────────────────────

class TestValidateOperatingHours:
    def test_within_hours_passes(self) -> None:
        """Booking between 06:00-18:00 should pass."""
        start = _make_time(8)
        end = _make_time(10)
        validate_operating_hours(start, end)  # Should not raise

    def test_start_before_opening_raises(self) -> None:
        """Booking starting before 06:00 should fail."""
        start = _make_time(5)
        end = _make_time(8)
        with pytest.raises(DomainRuleViolationError, match="06:00"):
            validate_operating_hours(start, end)

    def test_end_after_closing_raises(self) -> None:
        """Booking ending after 18:00 should fail."""
        start = _make_time(17)
        end = _make_time(19)
        with pytest.raises(DomainRuleViolationError, match="18:00"):
            validate_operating_hours(start, end)

    def test_start_equals_end_raises(self) -> None:
        """Zero-duration booking should fail."""
        t = _make_time(10)
        with pytest.raises(DomainRuleViolationError, match="after start"):
            validate_operating_hours(t, t)

    def test_end_before_start_raises(self) -> None:
        """Reversed time range should fail."""
        start = _make_time(12)
        end = _make_time(10)
        with pytest.raises(DomainRuleViolationError, match="after start"):
            validate_operating_hours(start, end)

    def test_at_boundary_passes(self) -> None:
        """Booking exactly at 06:00 - 18:00 should pass."""
        start = _make_time(6)
        end = _make_time(18)
        validate_operating_hours(start, end)  # Should not raise


# ─── validate_minimum_duration ───────────────────────────────────────────────

class TestValidateMinimumDuration:
    def test_sufficient_duration_passes(self) -> None:
        """2-hour booking should pass (>= 30 min min)."""
        start = _make_time(9)
        end = _make_time(11)
        validate_minimum_duration(start, end)

    def test_exactly_minimum_passes(self) -> None:
        """Exactly 30 minutes should pass."""
        start = _make_time(9)
        end = start + timedelta(minutes=30)
        validate_minimum_duration(start, end)

    def test_below_minimum_raises(self) -> None:
        """15-minute booking should fail."""
        start = _make_time(9)
        end = start + timedelta(minutes=15)
        with pytest.raises(DomainRuleViolationError, match="30 minutes"):
            validate_minimum_duration(start, end)


# ─── validate_package_is_active ──────────────────────────────────────────────

class TestValidatePackageIsActive:
    def test_active_package_passes(self) -> None:
        validate_package_is_active(_active_package())

    def test_inactive_package_raises(self) -> None:
        with pytest.raises(DomainRuleViolationError, match="not currently available"):
            validate_package_is_active(_inactive_package())


# ─── validate_area_is_supported ──────────────────────────────────────────────

class TestValidateAreaIsSupported:
    def test_supported_area_passes(self) -> None:
        validate_area_is_supported(_supported_area())

    def test_unsupported_area_raises(self) -> None:
        with pytest.raises(DomainRuleViolationError, match="not supported"):
            validate_area_is_supported(_unsupported_area())


# ─── BookingRules (composite) ─────────────────────────────────────────────────

class TestBookingRules:
    def setup_method(self) -> None:
        self.rules = BookingRules()

    def test_valid_booking_passes_all_rules(self) -> None:
        """A fully valid booking should pass all rules without raising."""
        start = _make_time(9)
        end = _make_time(11)
        self.rules.validate_new_booking(
            start_time=start,
            end_time=end,
            package=_active_package(),
            area=_supported_area(),
        )

    def test_past_booking_fails(self) -> None:
        """Past booking should fail even if other rules pass."""
        past_start = datetime.now(timezone.utc) - timedelta(hours=2)
        past_end = past_start + timedelta(hours=1)
        with pytest.raises(DomainRuleViolationError):
            self.rules.validate_new_booking(
                start_time=past_start,
                end_time=past_end,
                package=_active_package(),
                area=_supported_area(),
            )

    def test_inactive_package_fails(self) -> None:
        """Booking with inactive package should fail."""
        start = _make_time(9)
        end = _make_time(11)
        with pytest.raises(DomainRuleViolationError):
            self.rules.validate_new_booking(
                start_time=start,
                end_time=end,
                package=_inactive_package(),
                area=_supported_area(),
            )

    def test_unsupported_area_fails(self) -> None:
        """Booking in unsupported area should fail."""
        start = _make_time(9)
        end = _make_time(11)
        with pytest.raises(DomainRuleViolationError):
            self.rules.validate_new_booking(
                start_time=start,
                end_time=end,
                package=_active_package(),
                area=_unsupported_area(),
            )
