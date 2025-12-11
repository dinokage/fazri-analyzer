# Routes package
from .alert_routes import router as alert_router
from .staff_routes import router as staff_router
from .notification_routes import router as notification_router
from .demo_routes import router as demo_router

__all__ = [
    "alert_router",
    "staff_router",
    "notification_router",
    "demo_router",
]
