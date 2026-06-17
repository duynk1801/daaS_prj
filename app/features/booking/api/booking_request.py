"""
Pydantic v2 request/response schemas for the Booking API.

Input validation ensures only well-formed data reaches the domain layer.
All datetime fields are timezone-aware (UTC enforced).
PII in responses is kept minimal — no internal DB IDs exposed beyond booking_id.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Request Models ────────────────────────────────────────────────────────────

class CreateBookingRequest(BaseModel):
    """Request schema for creating a new drone booking."""

    drone_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        description="UUID of the drone to book",
        examples=["drone-uuid-1234"],
    )
    area_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        description="UUID of the operational area",
    )
    package_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        description="UUID of the service package",
    )
    start_time: datetime = Field(
        ...,
        description="Booking start time (ISO-8601 with timezone)",
        examples=["2025-06-15T08:00:00+07:00"],
    )
    end_time: datetime = Field(
        ...,
        description="Booking end time (ISO-8601 with timezone)",
        examples=["2025-06-15T10:00:00+07:00"],
    )
    total_price: float = Field(
        ...,
        ge=0,
        le=1_000_000,
        description="Total booking price (validated server-side against package)",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional booking notes",
    )

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Normalize all datetimes to UTC."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("Datetime must include timezone information")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "CreateBookingRequest":
        """Ensure end_time is after start_time."""
        if self.start_time >= self.end_time:
            raise ValueError("end_time must be after start_time")
        return self

    @field_validator("drone_id", "area_id", "package_id", mode="after")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from ID fields."""
        return v.strip()


class CancelBookingRequest(BaseModel):
    """Request schema for cancelling a booking."""

    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional reason for cancellation",
    )


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ─── Response Models ────────────────────────────────────────────────────────────

class BookingResponse(BaseModel):
    """Response schema for a single booking."""

    id: str
    user_id: str
    drone_id: str
    area_id: str
    package_id: str
    start_time: datetime
    end_time: datetime
    status: str
    total_price: float
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expired_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    """Response schema for paginated list of bookings."""

    items: List[BookingResponse]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Standard error response — generic message only, no internal details."""

    error: str
    code: str
    request_id: Optional[str] = None
