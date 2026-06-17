"""
Shared pytest fixtures and configuration.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


@pytest.fixture
def future_start_time() -> datetime:
    """A booking start time 2 days from now at 09:00 UTC."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=2)
    return future.replace(hour=9, minute=0, second=0, microsecond=0)


@pytest.fixture
def future_end_time(future_start_time) -> datetime:
    """A booking end time 2 hours after start."""
    return future_start_time + timedelta(hours=2)


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return MagicMock()


@pytest.fixture
def mock_publisher():
    """Mock RabbitMQ publisher."""
    return MagicMock()
