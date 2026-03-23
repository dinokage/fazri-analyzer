"""
Sentry Context Middleware

Extracts user information from authenticated requests and adds it to Sentry context.
This ensures all Sentry events include user information for better debugging.
"""

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SentryContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enriches Sentry events with user and request context

    This middleware:
    1. Extracts authenticated user from request.state (set by auth dependencies)
    2. Sets user context in Sentry for all subsequent events
    3. Adds request metadata (method, URL, client host) to Sentry context
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Add user context if available
        if hasattr(request.state, "user"):
            user = request.state.user

            # Set user identification
            sentry_sdk.set_user({
                "id": user.id,
                "email": user.email,
                "username": user.entity_id,
            })

            # Add additional user context
            sentry_sdk.set_context("user_details", {
                "entity_id": user.entity_id,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "department": user.department,
                "student_id": user.student_id,
                "staff_id": user.staff_id,
            })

            # Add user role as a tag for filtering
            sentry_sdk.set_tag("user_role", user.role.value if hasattr(user.role, 'value') else str(user.role))
        else:
            # Clear user context for unauthenticated requests
            sentry_sdk.set_user(None)
            sentry_sdk.set_tag("user_role", "anonymous")

        # Add request context
        sentry_sdk.set_context("request_info", {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        })

        # Add request path as a tag for filtering
        sentry_sdk.set_tag("endpoint", request.url.path)

        # Process the request
        response = await call_next(request)

        return response
