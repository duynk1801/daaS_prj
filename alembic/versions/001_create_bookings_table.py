"""Create bookings table

Revision ID: 001
Revises: 
Create Date: 2025-06-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the bookings table with all columns and indexes."""
    op.create_table(
        "bookings",
        # ─── Primary Key ────────────────────────────────────────────────────
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),

        # ─── Relations ──────────────────────────────────────────────────────
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("drone_id", sa.String(36), nullable=False),
        sa.Column("area_id", sa.String(36), nullable=False),
        sa.Column("package_id", sa.String(36), nullable=False),

        # ─── Schedule ───────────────────────────────────────────────────────
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),

        # ─── Booking Details ─────────────────────────────────────────────────
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("total_price", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),

        # ─── Audit Timestamps ────────────────────────────────────────────────
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ─── Indexes ─────────────────────────────────────────────────────────────
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_drone_id", "bookings", ["drone_id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])

    # Composite: slot overlap detection
    op.create_index(
        "ix_bookings_drone_time",
        "bookings",
        ["drone_id", "start_time", "end_time"],
    )

    # Composite: expiry scheduler queries
    op.create_index(
        "ix_bookings_status_expired",
        "bookings",
        ["status", "expired_at"],
    )

    # Trigger to auto-update updated_at on row changes (PostgreSQL)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER bookings_updated_at
        BEFORE UPDATE ON bookings
        FOR EACH ROW
        EXECUTE PROCEDURE update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop the bookings table and associated objects."""
    op.execute("DROP TRIGGER IF EXISTS bookings_updated_at ON bookings;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column;")
    op.drop_index("ix_bookings_status_expired", table_name="bookings")
    op.drop_index("ix_bookings_drone_time", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_drone_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_table("bookings")
