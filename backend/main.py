# backend/app/main.py
import logging
from contextlib import asynccontextmanager
import re

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

import entity_routes, graph_routes, spatial_routes, anomaly_routes, chat_routes
from routes import alert_router, staff_router, notification_router, demo_router
from routes.gitlab_routes import router as gitlab_router
from config import settings
from auth.dependencies import get_current_user
from auth.models import AuthenticatedUser

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