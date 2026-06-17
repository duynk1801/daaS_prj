"""
Redis-based distributed slot lock for drone booking.

Prevents double-booking race conditions using Redis SET NX EX pattern.
This is an atomic operation — no TOCTOU vulnerability.
"""
from __future__ import annotations

import logging
from typing import Optional

from redis import Redis

from app.config.settings import get_settings
from app.shared.exceptions.custom_exceptions import SlotLockError

logger = logging.getLogger(__name__)

_settings = get_settings()

_LOCK_PREFIX = "booking:slot_lock:"


class RedisSlotLock:
    """
    Manages distributed slot locks for drone bookings.

    Uses Redis SET NX EX (atomic set-if-not-exists with expiry) to prevent
    race conditions when multiple users book the same drone time slot.

    Thread-safe: Redis SET NX is atomic at the server level.
    """

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client
        self._ttl = _settings.REDIS_SLOT_LOCK_TTL_SECONDS

    @staticmethod
    def _build_key(drone_id: str, slot_date: str, slot_hour: int) -> str:
        """
        Build a deterministic lock key for a drone time slot.

        Args:
            drone_id:  The drone's UUID string.
            slot_date: ISO date string (e.g., "2025-06-15").
            slot_hour: Integer hour (0–23).

        Returns:
            Redis key string.
        """
        return f"{_LOCK_PREFIX}{drone_id}:{slot_date}:{slot_hour:02d}"

    def acquire_lock(
        self,
        drone_id: str,
        slot_date: str,
        slot_hour: int,
        booking_id: str,
    ) -> bool:
        """
        Attempt to acquire a slot lock.

        Uses atomic SET NX EX — only one caller can win the race.

        Args:
            drone_id:   The drone's ID.
            slot_date:  The booking date (ISO format).
            slot_hour:  The booking hour.
            booking_id: The booking ID to store as lock value (for ownership).

        Returns:
            True if lock was acquired, False if slot is already taken.
        """
        key = self._build_key(drone_id, slot_date, slot_hour)
        acquired = self._redis.set(
            key,
            booking_id,
            nx=True,     # Only set if key does NOT exist (atomic)
            ex=self._ttl,  # Auto-expire the lock
        )
        if acquired:
            logger.info("Slot lock acquired: key=%s booking=%s", key, booking_id)
        else:
            logger.info("Slot lock failed (taken): key=%s", key)
        return bool(acquired)

    def release_lock(self, drone_id: str, slot_date: str, slot_hour: int, booking_id: str) -> bool:
        """
        Release a slot lock, but ONLY if it belongs to the given booking.

        Uses Lua script for atomic check-and-delete to prevent releasing
        a lock that was re-acquired by another booking.

        Args:
            drone_id:   The drone's ID.
            slot_date:  The booking date.
            slot_hour:  The booking hour.
            booking_id: Must match the lock's stored value.

        Returns:
            True if lock was released, False if not owned or already gone.
        """
        key = self._build_key(drone_id, slot_date, slot_hour)

        # Atomic Lua script: check owner then delete
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        result = self._redis.eval(lua_script, 1, key, booking_id)  # type: ignore[no-untyped-call]
        released = bool(result)

        if released:
            logger.info("Slot lock released: key=%s booking=%s", key, booking_id)
        else:
            logger.warning("Slot lock release skipped (not owner or missing): key=%s", key)
        return released

    def acquire_locks_for_booking(
        self,
        drone_id: str,
        slot_date: str,
        start_hour: int,
        end_hour: int,
        booking_id: str,
    ) -> bool:
        """
        Acquire locks for all hours in a booking's time range.

        If any lock acquisition fails, all previously acquired locks are released
        (transactional rollback).

        Args:
            drone_id:   The drone's ID.
            slot_date:  The booking date.
            start_hour: First hour to lock (inclusive).
            end_hour:   Last hour to lock (exclusive).
            booking_id: The booking ID.

        Returns:
            True if all locks acquired successfully.
        """
        acquired_hours: list[int] = []
        for hour in range(start_hour, end_hour):
            if self.acquire_lock(drone_id, slot_date, hour, booking_id):
                acquired_hours.append(hour)
            else:
                # Rollback: release all previously acquired locks
                logger.warning(
                    "Failed to acquire lock for hour %d — rolling back %d locks",
                    hour,
                    len(acquired_hours),
                )
                for rollback_hour in acquired_hours:
                    self.release_lock(drone_id, slot_date, rollback_hour, booking_id)
                return False
        return True

    def release_locks_for_booking(
        self,
        drone_id: str,
        slot_date: str,
        start_hour: int,
        end_hour: int,
        booking_id: str,
    ) -> None:
        """Release all slot locks for a booking's time range."""
        for hour in range(start_hour, end_hour):
            self.release_lock(drone_id, slot_date, hour, booking_id)

    def is_slot_locked(self, drone_id: str, slot_date: str, slot_hour: int) -> bool:
        """Check if a specific slot hour is currently locked."""
        key = self._build_key(drone_id, slot_date, slot_hour)
        return self._redis.exists(key) > 0
