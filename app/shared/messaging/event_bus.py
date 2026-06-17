"""
Event bus abstraction for publish/subscribe messaging.

Decouples event producers from consumers, routing events
to the appropriate message broker (RabbitMQ).
"""
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Optional, Type

from app.config.settings import get_settings
from app.shared.messaging.rabbitmq import get_rabbitmq_channel

logger = logging.getLogger(__name__)

_settings = get_settings()

# Registry of event type → routing key mappings
_EVENT_ROUTING_KEYS: Dict[str, str] = {}
# Registry of routing key → handler functions
_SUBSCRIBERS: Dict[str, list[Callable]] = {}


def register_event(event_class: type, routing_key: str) -> None:
    """
    Register an event class with its RabbitMQ routing key.

    Args:
        event_class: The event dataclass type.
        routing_key: The AMQP routing key (e.g., "booking.created").
    """
    _EVENT_ROUTING_KEYS[event_class.__name__] = routing_key


def publish(event: Any) -> None:
    """
    Publish an event to the message broker.

    Args:
        event: A dataclass instance representing the event.

    Raises:
        ValueError: If the event type is not registered.
    """
    event_name = type(event).__name__
    routing_key = _EVENT_ROUTING_KEYS.get(event_name)

    if not routing_key:
        raise ValueError(
            f"Event '{event_name}' is not registered. "
            "Call register_event() first."
        )

    try:
        import pika
        channel = get_rabbitmq_channel()
        payload = json.dumps(asdict(event), default=str).encode("utf-8")

        channel.basic_publish(
            exchange=_settings.RABBITMQ_BOOKING_EXCHANGE,
            routing_key=routing_key,
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type="application/json",
            ),
        )
        logger.info("Event published: %s (routing_key=%s)", event_name, routing_key)
    except Exception as exc:
        # Log error but don't crash the main flow
        # TODO(security): Consider dead-letter queue for failed events
        logger.error(
            "Failed to publish event %s: %s",
            event_name,
            type(exc).__name__,
        )


def subscribe(routing_key: str) -> Callable:
    """
    Decorator to register a function as a subscriber for a routing key.

    Usage:
        @subscribe("booking.created")
        def handle_booking_created(payload: dict) -> None:
            ...
    """
    def decorator(func: Callable) -> Callable:
        if routing_key not in _SUBSCRIBERS:
            _SUBSCRIBERS[routing_key] = []
        _SUBSCRIBERS[routing_key].append(func)
        logger.debug("Subscriber registered: %s → %s", routing_key, func.__name__)
        return func
    return decorator
