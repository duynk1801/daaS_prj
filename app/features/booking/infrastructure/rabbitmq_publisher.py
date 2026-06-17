"""
RabbitMQ publisher for booking domain events.

Publishes serialized event payloads to the booking events exchange.
Failures are logged but do not propagate — use dead-letter queues in production.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel

from app.config.settings import get_settings
from app.shared.messaging.rabbitmq import get_rabbitmq_channel

logger = logging.getLogger(__name__)

_settings = get_settings()


class RabbitMQBookingPublisher:
    """
    Publishes booking events to RabbitMQ topic exchange.

    Routing key pattern: booking.<event_type>
    Exchange: configured via RABBITMQ_BOOKING_EXCHANGE env var
    """

    ROUTING_KEY_CREATED = "booking.created"
    ROUTING_KEY_EXPIRED = "booking.expired"
    ROUTING_KEY_CANCELLED = "booking.cancelled"
    ROUTING_KEY_CONFIRMED = "booking.confirmed"
    ROUTING_KEY_COMPLETED = "booking.completed"

    def _publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        """
        Internal method to publish a message to the exchange.

        Args:
            routing_key: AMQP routing key.
            payload:     Event payload dict (will be JSON-serialized).
        """
        try:
            channel: BlockingChannel = get_rabbitmq_channel()
            body = json.dumps(payload, default=str).encode("utf-8")

            channel.basic_publish(
                exchange=_settings.RABBITMQ_BOOKING_EXCHANGE,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,        # Persistent message (survives broker restart)
                    content_type="application/json",
                    content_encoding="utf-8",
                ),
            )
            logger.info(
                "Published event: exchange=%s routing_key=%s",
                _settings.RABBITMQ_BOOKING_EXCHANGE,
                routing_key,
            )
        except Exception as exc:
            # TODO(security): Route to dead-letter queue for guaranteed delivery
            logger.error(
                "Failed to publish event (routing_key=%s): %s",
                routing_key,
                type(exc).__name__,
            )

    def publish_booking_created(self, event: Any) -> None:
        """Publish a booking.created event."""
        self._publish(self.ROUTING_KEY_CREATED, asdict(event))

    def publish_booking_expired(self, event: Any) -> None:
        """Publish a booking.expired event."""
        self._publish(self.ROUTING_KEY_EXPIRED, asdict(event))

    def publish_booking_cancelled(self, event: Any) -> None:
        """Publish a booking.cancelled event."""
        self._publish(self.ROUTING_KEY_CANCELLED, asdict(event))

    def publish_booking_confirmed(self, event: Any) -> None:
        """Publish a booking.confirmed event."""
        self._publish(self.ROUTING_KEY_CONFIRMED, asdict(event))

    def publish_booking_completed(self, event: Any) -> None:
        """Publish a booking.completed event."""
        self._publish(self.ROUTING_KEY_COMPLETED, asdict(event))
