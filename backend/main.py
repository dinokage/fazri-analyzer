# backend/app/main.py
import logging
from contextlib import asynccontextmanager
import re

from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import entity_routes, graph_routes, spatial_routes, anomaly_routes, chat_routes
from routes import alert_router, staff_router, notification_router, demo_router
from routes.gitlab_routes import router as gitlab_router
from config import settings
from auth.dependencies import get_current_user
from auth.models import AuthenticatedUser
from middleware import SentryContextMiddleware

# Sentry imports
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


# =========================================================================
# Sentry Error Tracking & Performance Monitoring
# =========================================================================

def filter_sensitive_data(event, hint):
    """
    Filter sensitive data from Sentry events before sending
    Removes Authorization headers, JWT tokens, passwords, etc.
    """
    # Remove sensitive headers
    if event.get('request', {}).get('headers'):
        headers = event['request']['headers']
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'

    # Remove query parameters that might contain tokens
    if event.get('request', {}).get('query_string'):
        # Don't send query strings that might contain tokens
        event['request']['query_string'] = '[Filtered]'

    # Filter JWT tokens from exception messages
    if event.get('exception', {}).get('values'):
        for exc in event['exception']['values']:
            if exc.get('value'):
                # Replace Bearer tokens with [Filtered]
                exc['value'] = re.sub(
                    r'Bearer [A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
                    'Bearer [Filtered]',
                    exc['value']
                )
                # Replace password patterns
                exc['value'] = re.sub(
                    r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+',
                    'password=[Filtered]',
                    exc['value'],
                    flags=re.IGNORECASE
                )

    # Filter sensitive data from extra context
    if event.get('extra'):
        sensitive_keys = ['password', 'token', 'secret', 'api_key', 'authorization']
        for key in list(event['extra'].keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                event['extra'][key] = '[Filtered]'

    return event


# Initialize Sentry if enabled
if settings.SENTRY_ENABLED and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,

        # Performance and error tracking integrations
        integrations=[
            FastApiIntegration(transaction_style="url"),
            StarletteIntegration(transaction_style="url"),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors and above as events
            ),
        ],

        # Enable performance monitoring
        enable_tracing=True,

        # Filter sensitive data before sending
        before_send=filter_sensitive_data,

        # Release tracking (will be set by CI/CD)
        release=f"fazri-analyzer-backend@{settings.PROJECT_NAME}",

        # Send default PII (we'll filter manually)
        send_default_pii=False,
    )
    logger_init = logging.getLogger(__name__)
    logger_init.info(f"Sentry initialized for environment: {settings.SENTRY_ENVIRONMENT}")
else:
    logger_init = logging.getLogger(__name__)
    logger_init.info("Sentry disabled - error tracking not active")


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events"""
    # Startup
    logger.info("Starting Fazri Analyzer API...")

    # Initialize alert system database if enabled
    if settings.ALERT_SYSTEM_ENABLED:
        try:
            from database.init_alerts import init_alert_system
            init_alert_system()
            logger.info("Alert system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize alert system: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Fazri Analyzer API...")


app = FastAPI(
    title="Fazri Analyzer API",
    description="API for campus security monitoring, entity tracking, and alert management",
    version="1.0.1",
    lifespan=lifespan,
)

# CORS configuration for allowed domains and their subdomains
ALLOWED_DOMAIN_PATTERNS = [
    r"^https?://([a-zA-Z0-9-]+\.)*rayzrsole\.com$",
    r"^https?://([a-zA-Z0-9-]+\.)*rdpdc\.in$",
    r"^http://localhost(:[0-9]+)?$",  # Allow localhost for development
]

def is_origin_allowed(origin: str) -> bool:
    """Check if origin matches allowed domain patterns"""
    for pattern in ALLOWED_DOMAIN_PATTERNS:
        if re.match(pattern, origin):
            return True
    return False

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://([a-zA-Z0-9-]+\.)*rayzrsole\.com$|^https?://([a-zA-Z0-9-]+\.)*rdpdc\.in$|^http://localhost(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Sentry context middleware if Sentry is enabled
if settings.SENTRY_ENABLED:
    app.add_middleware(SentryContextMiddleware)
    logger.info("Sentry context middleware enabled")


# =========================================================================
# Global Exception Handlers (Sentry Integration)
# =========================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that captures unhandled exceptions in Sentry
    and returns a user-friendly error response
    """
    # Capture exception in Sentry if enabled
    if settings.SENTRY_ENABLED:
        sentry_sdk.capture_exception(exc)

    # Log the error
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
    )

    # Return user-friendly error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. The error has been logged and will be investigated.",
            "type": type(exc).__name__
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    if settings.SENTRY_ENABLED:
        sentry_sdk.capture_exception(exc)

    logger.warning(f"Validation error: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

# Include existing routers
app.include_router(entity_routes.router)
app.include_router(graph_routes.router)
app.include_router(spatial_routes.router)
app.include_router(anomaly_routes.router)
app.include_router(chat_routes.router)
app.include_router(gitlab_router)

# Include alert system routers
if settings.ALERT_SYSTEM_ENABLED:
    app.include_router(alert_router)
    app.include_router(staff_router)
    app.include_router(notification_router)
    app.include_router(demo_router)
    logger.info("Alert system routes registered")

@app.get("/")
async def root():
    """Public root endpoint - no authentication required"""
    return {
        "message": "Campus Entity Resolution API",
        "status": "running",
        "version": "1.0.1"
    }

@app.get("/health")
async def health_check():
    """Public health check endpoint - no authentication required"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)