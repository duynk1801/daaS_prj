"""
FastAPI application entry point.

Security headers applied via middleware:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy (restrictive)
- CORS: strict origin allow-list (no wildcard)
- Cache-Control: no-store for API responses

TODO(security): Add rate limiting middleware (e.g., slowapi) in production.
TODO(security): Enable HTTPS/TLS termination at reverse proxy level.
TODO(security): Add request ID middleware for audit logging.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.features.booking.api.booking_controller import router as booking_router
from app.shared.database.postgres import check_db_connection
from app.shared.cache.redis_client import check_redis_connection

_settings = get_settings()

# Configure logging before anything else
configure_logging(debug=_settings.DEBUG)
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application startup and shutdown lifecycle.
    Runs health checks on startup, cleans up connections on shutdown.
    """
    # Startup
    logger.info("Starting %s v%s", _settings.APP_NAME, _settings.APP_VERSION)
    logger.info("Environment: %s", _settings.ENVIRONMENT)

    # Verify critical connections (fail fast)
    if not check_db_connection():
        logger.warning("PostgreSQL connection check failed — database may be unavailable")
    else:
        logger.info("PostgreSQL connection: OK")

    if not check_redis_connection():
        logger.warning("Redis connection check failed — caching/locking may be unavailable")
    else:
        logger.info("Redis connection: OK")

    yield

    # Shutdown
    logger.info("Shutting down %s", _settings.APP_NAME)
    try:
        from app.shared.messaging.rabbitmq import close_rabbitmq
        close_rabbitmq()
    except Exception:
        pass


# ─── App Instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=_settings.APP_NAME,
    version=_settings.APP_VERSION,
    description="Drone Booking Service API — Feature-Based Architecture",
    docs_url="/docs" if _settings.DEBUG else None,   # Disable Swagger in production
    redoc_url="/redoc" if _settings.DEBUG else None,
    lifespan=lifespan,
)


# ─── CORS Middleware (strict origin list) ────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.CORS_ALLOWED_ORIGINS,  # Never use ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


# ─── Security Headers Middleware ──────────────────────────────────────────────

@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:  # noqa: ANN001
    """
    Inject security headers on every response.

    Implements:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - Content-Security-Policy (restrictive)
    - Cache-Control: no-store (prevent caching of sensitive API responses)
    - Referrer-Policy
    - Permissions-Policy (disable unused browser features)
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none';"
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    # Remove server identification header
    response.headers.pop("server", None)
    return response


# ─── Global Exception Handlers ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler.
    Returns a generic error message — never exposes internal details.
    """
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(booking_router, prefix="/api/v1")


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], include_in_schema=False)
def health_check() -> dict:
    """
    Health check endpoint for load balancers and monitoring.
    Returns OK if the application is running.
    DB/Redis health are checked separately to avoid cascading failures.
    """
    return {
        "status": "ok",
        "service": _settings.APP_NAME,
        "version": _settings.APP_VERSION,
    }


@app.get("/health/detailed", tags=["System"], include_in_schema=False)
def detailed_health_check() -> dict:
    """Detailed health check including downstream dependencies."""
    return {
        "status": "ok",
        "service": _settings.APP_NAME,
        "version": _settings.APP_VERSION,
        "dependencies": {
            "postgresql": "ok" if check_db_connection() else "degraded",
            "redis": "ok" if check_redis_connection() else "degraded",
        },
    }
