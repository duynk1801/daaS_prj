"""
SQLAlchemy ORM model for the bookings table.

Mapped to the 'bookings' database table.
All queries MUST go through repository methods — never raw SQL string concat.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class BookingModel(Base):
    """ORM model for the bookings table."""

    __tablename__ = "bookings"

    # ─── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ─── Relations ────────────────────────────────────────────────────────────
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    drone_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    area_id: Mapped[str] = mapped_column(String(36), nullable=False)
    package_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # ─── Schedule ─────────────────────────────────────────────────────────────
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ─── Booking Details ──────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DRAFT", index=True
    )
    total_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ─── Composite Indexes ────────────────────────────────────────────────────
    __table_args__ = (
        # Optimizes overlap detection queries
        Index("ix_bookings_drone_time", "drone_id", "start_time", "end_time"),
        # Optimizes expiry scheduler queries
        Index("ix_bookings_status_expired", "status", "expired_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<BookingModel id={self.id!r} drone_id={self.drone_id!r} "
            f"status={self.status!r}>"
        )
