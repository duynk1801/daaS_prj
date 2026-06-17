"""
RabbitMQ connection and channel management using pika.

Provides a thread-safe connection wrapper with automatic reconnection.
"""
import logging
import threading
import time
from typing import Optional

import pika
import pika.exceptions
from pika import BlockingConnection, ConnectionParameters, PlainCredentials
from pika.adapters.blocking_connection import BlockingChannel

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()


class RabbitMQConnection:
    """
    Thread-safe RabbitMQ connection wrapper with reconnection logic.

    Usage:
        rmq = RabbitMQConnection()
        channel = rmq.get_channel()
        channel.basic_publish(...)
    """

    def __init__(self) -> None:
        self._connection: Optional[BlockingConnection] = None
        self._channel: Optional[BlockingChannel] = None
        self._lock = threading.Lock()

    def _connect(self) -> None:
        """Establish connection to RabbitMQ broker."""
        credentials = PlainCredentials(
            username=_settings.RABBITMQ_USER,
            password=_settings.RABBITMQ_PASSWORD,
        )
        params = ConnectionParameters(
            host=_settings.RABBITMQ_HOST,
            port=_settings.RABBITMQ_PORT,
            virtual_host=_settings.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=2,
        )
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()

        # Declare the booking exchange (idempotent)
        self._channel.exchange_declare(
            exchange=_settings.RABBITMQ_BOOKING_EXCHANGE,
            exchange_type="topic",
            durable=True,
        )
        logger.info("RabbitMQ connection established")

    def _is_connected(self) -> bool:
        """Check if connection is alive."""
        return (
            self._connection is not None
            and self._connection.is_open
            and self._channel is not None
            and self._channel.is_open
        )

    def get_channel(self, max_retries: int = 3) -> BlockingChannel:
        """
        Get an active RabbitMQ channel, reconnecting if necessary.

        Args:
            max_retries: Number of reconnection attempts before raising.

        Returns:
            An active BlockingChannel.

        Raises:
            RuntimeError: If unable to establish connection after retries.
        """
        with self._lock:
            for attempt in range(max_retries):
                if self._is_connected():
                    return self._channel  # type: ignore[return-value]
                try:
                    logger.info("Connecting to RabbitMQ (attempt %d/%d)", attempt + 1, max_retries)
                    self._connect()
                    return self._channel  # type: ignore[return-value]
                except pika.exceptions.AMQPConnectionError as exc:
                    logger.warning("RabbitMQ connection attempt %d failed: %s", attempt + 1, exc)
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff

            raise RuntimeError(
                f"Failed to connect to RabbitMQ after {max_retries} attempts"
            )

    def close(self) -> None:
        """Gracefully close the connection."""
        with self._lock:
            if self._connection and self._connection.is_open:
                self._connection.close()
                logger.info("RabbitMQ connection closed")


# Singleton instance for application lifecycle
_rabbitmq_connection = RabbitMQConnection()


def get_rabbitmq_channel() -> BlockingChannel:
    """Get a RabbitMQ channel from the singleton connection."""
    return _rabbitmq_connection.get_channel()


def close_rabbitmq() -> None:
    """Close the global RabbitMQ connection (call on app shutdown)."""
    _rabbitmq_connection.close()


def check_rabbitmq_connection() -> bool:
    """Health check: verify RabbitMQ connectivity."""
    try:
        channel = _rabbitmq_connection.get_channel()
        return channel.is_open
    except Exception as exc:
        logger.error("RabbitMQ health check failed: %s", type(exc).__name__)
        return False
