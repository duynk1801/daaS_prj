"""
Booking API controller — FastAPI routes.

Security:
- All endpoints require JWT authentication.
- Resource ownership validated in service layer (prevents IDOR).
- Generic error responses — internal details never exposed to clients.
- Rate limiting applied at middleware level.
"""
from __future__ import annotations

import logging
import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.features.booking.api.booking_request import (
    BookingListResponse,
    BookingResponse,
    CancelBookingRequest,
    CreateBookingRequest,
    ErrorResponse,
)
from app.features.booking.application.booking_service import BookingService
from app.features.booking.application.create_booking import CreateBookingCommand
from app.shared.cache.redis_client import get_redis
from app.shared.database.postgres import get_db
from app.shared.exceptions.custom_exceptions import (
    BookingNotFoundError,
    DomainRuleViolationError,
    ForbiddenError,
    SlotConflictError,
    SlotLockError,
    UnauthorizedError,
)
from app.shared.security.jwt import get_subject
from redis import Redis

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        422: {"description": "Validation Error"},
    },
)


# ─── Auth Dependency ──────────────────────────────────────────────────────────

def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """
    Extract and validate the JWT bearer token from the Authorization header.

    Returns:
        The authenticated user's ID (subject claim).

    Raises:
        HTTPException 401: If token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("Bearer "):]
    try:
        return get_subject(token)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_booking_service(
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> BookingService:
    """Dependency injection: create BookingService with db and redis."""
    return BookingService(db=db, redis_client=redis_client)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new drone booking",
)
def create_booking(
    request: CreateBookingRequest,
    user_id: str = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    """
    Create a new drone booking.

    Validates business rules, checks slot availability,
    acquires a distributed lock, and publishes a creation event.
    """
    request_id = str(uuid.uuid4())

    try:
        command = CreateBookingCommand(
            user_id=user_id,
            drone_id=request.drone_id,
            area_id=request.area_id,
            package_id=request.package_id,
            start_time=request.start_time,
            end_time=request.end_time,
            total_price=request.total_price,
            notes=request.notes,
            # TODO: Fetch and validate package/area from their respective services
            package_is_active=True,
            package_name="",
            area_is_supported=True,
            area_name="",
        )
        entity = service.create_booking(command)
        return BookingResponse(
            id=entity.id,
            user_id=entity.user_id,
            drone_id=entity.drone_id,
            area_id=entity.area_id,
            package_id=entity.package_id,
            start_time=entity.start_time,
            end_time=entity.end_time,
            status=entity.status.value,
            total_price=entity.total_price,
            notes=entity.notes,
            cancellation_reason=entity.cancellation_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            expired_at=entity.expired_at,
        )

    except DomainRuleViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SlotConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SlotLockError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        # Generic handler — never expose internal error to client
        logger.error("Unexpected error in create_booking (request_id=%s): %s", request_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request",
        ) from exc


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get a booking by ID",
)
def get_booking(
    booking_id: str,
    user_id: str = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    """
    Retrieve a specific booking by ID.

    Users can only access their own bookings (ownership enforced).
    """
    try:
        entity = service.get_booking(booking_id=booking_id, requesting_user_id=user_id)
        return BookingResponse(
            id=entity.id,
            user_id=entity.user_id,
            drone_id=entity.drone_id,
            area_id=entity.area_id,
            package_id=entity.package_id,
            start_time=entity.start_time,
            end_time=entity.end_time,
            status=entity.status.value,
            total_price=entity.total_price,
            notes=entity.notes,
            cancellation_reason=entity.cancellation_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            expired_at=entity.expired_at,
        )
    except BookingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",  # Generic — don't reveal ownership info
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error in get_booking: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request",
        ) from exc


@router.get(
    "",
    response_model=BookingListResponse,
    summary="List my bookings",
)
def list_bookings(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
) -> BookingListResponse:
    """
    List all bookings for the authenticated user with pagination.
    """
    try:
        entities = service.list_bookings(user_id=user_id, limit=limit, offset=offset)
        items = [
            BookingResponse(
                id=e.id,
                user_id=e.user_id,
                drone_id=e.drone_id,
                area_id=e.area_id,
                package_id=e.package_id,
                start_time=e.start_time,
                end_time=e.end_time,
                status=e.status.value,
                total_price=e.total_price,
                notes=e.notes,
                cancellation_reason=e.cancellation_reason,
                created_at=e.created_at,
                updated_at=e.updated_at,
                expired_at=e.expired_at,
            )
            for e in entities
        ]
        return BookingListResponse(
            items=items,
            total=len(items),
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("Unexpected error in list_bookings: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request",
        ) from exc


@router.patch(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking",
)
def cancel_booking(
    booking_id: str,
    request: CancelBookingRequest,
    user_id: str = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    """
    Cancel a booking.

    Only the booking owner can cancel. In-progress bookings cannot be cancelled.
    """
    try:
        entity = service.cancel_booking(
            booking_id=booking_id,
            requesting_user_id=user_id,
            reason=request.reason,
        )
        return BookingResponse(
            id=entity.id,
            user_id=entity.user_id,
            drone_id=entity.drone_id,
            area_id=entity.area_id,
            package_id=entity.package_id,
            start_time=entity.start_time,
            end_time=entity.end_time,
            status=entity.status.value,
            total_price=entity.total_price,
            notes=entity.notes,
            cancellation_reason=entity.cancellation_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            expired_at=entity.expired_at,
        )
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found") from exc
    except DomainRuleViolationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected error in cancel_booking: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request",
        ) from exc
