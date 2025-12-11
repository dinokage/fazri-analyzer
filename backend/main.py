# backend/app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import entity_routes, graph_routes, spatial_routes, anomaly_routes, chat_routes
from routes import alert_router, staff_router, notification_router, demo_router
from config import settings

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
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Include alert system routers
if settings.ALERT_SYSTEM_ENABLED:
    app.include_router(alert_router)
    app.include_router(staff_router)
    app.include_router(notification_router)
    app.include_router(demo_router)
    logger.info("Alert system routes registered")

@app.get("/")
async def root():
    return {
        "message": "Campus Entity Resolution API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)