from typing import List, Optional, Callable
from fastapi import Header, Depends, Request

from auth.jwt import decode_jwt_token
from auth.models import AuthenticatedUser, UserRole
from auth.exceptions import AuthenticationError, PermissionDeniedError
from config import settings


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> AuthenticatedUser:
    """
    FastAPI dependency to extract and validate current user from JWT token

    Args:
        authorization: Authorization header value (Bearer token)

    Returns:
        AuthenticatedUser instance with user claims

    Raises:
        AuthenticationError: If token is missing, invalid, or expired
    """
    if not authorization:
        raise AuthenticationError(detail="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise AuthenticationError(detail="Invalid authorization header format. Expected: Bearer <token>")

    # Extract token from "Bearer <token>"
    token = authorization.replace("Bearer ", "").strip()

    if not token:
        raise AuthenticationError(detail="Token is empty")

    # Decode and validate JWT (will raise TokenExpiredError or InvalidTokenError)
    payload = decode_jwt_token(token)

    # Map JWT claims to AuthenticatedUser model
    try:
        user = AuthenticatedUser(
            id=payload.get("id"),
            entity_id=payload.get("entity_id"),
            name=payload.get("name"),
            email=payload.get("email"),
            role=UserRole(payload.get("role")),
            face_id=payload.get("face_id"),
            student_id=payload.get("student_id"),
            staff_id=payload.get("staff_id"),
            department=payload.get("department"),
            sessionId=payload.get("sessionId"),
            organizationId=payload.get("organizationId"),
        )

        # Store user in request state for Sentry middleware
        request.state.user = user

        return user
    except (KeyError, ValueError, TypeError) as e:
        raise AuthenticationError(detail=f"Invalid token claims: {str(e)}")


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """
    Factory function to create a dependency that requires specific roles

    Args:
        allowed_roles: List of roles that are allowed to access the endpoint

    Returns:
        Dependency function that validates user role

    Example:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: AuthenticatedUser = Depends(require_role([UserRole.SUPER_ADMIN]))
        ):
            pass
    """
    async def role_checker(
        current_user: AuthenticatedUser = Depends(get_current_user)
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            allowed_role_names = ", ".join([role.value for role in allowed_roles])
            raise PermissionDeniedError(
                detail=f"Insufficient permissions. Required role: {allowed_role_names}"
            )
        return current_user

    return role_checker


def require_staff() -> Callable:
    """Require STAFF, FACULTY, or SUPER_ADMIN role"""
    return require_role([UserRole.STAFF, UserRole.FACULTY, UserRole.SUPER_ADMIN])


def require_faculty() -> Callable:
    """Require FACULTY or SUPER_ADMIN role"""
    return require_role([UserRole.FACULTY, UserRole.SUPER_ADMIN])


def require_admin() -> Callable:
    """Require SUPER_ADMIN role"""
    return require_role([UserRole.SUPER_ADMIN])


async def require_org_member(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require user to have an active organization set in their JWT.
    SUPER_ADMIN bypasses this check — they operate across all orgs."""
    if current_user.role == UserRole.SUPER_ADMIN:
        return current_user
    if not current_user.organizationId:
        raise PermissionDeniedError(
            detail="No active organization. Please select a college first."
        )
    return current_user


async def require_org_admin(
    request: Request,
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> AuthenticatedUser:
    """
    Require admin or owner role within the active org.

    Checks membership via the auth service so role changes take
    effect immediately without re-login.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        return current_user

    import httpx as _httpx
    import logging

    logger = logging.getLogger(__name__)
    auth_header = request.headers.get("Authorization")
    forward_headers = {"Authorization": auth_header} if auth_header else {}

    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/auth/organization/get-full-organization",
                params={"organizationId": current_user.organizationId},
                headers=forward_headers,
            )
            if resp.status_code != 200:
                logger.error(
                    "require_org_admin: auth service returned %s — %s",
                    resp.status_code,
                    resp.text,
                )
            else:
                data = resp.json()
                members = data.get("members", [])
                user_member = next(
                    (m for m in members if m.get("userId") == current_user.id),
                    None,
                )
                if user_member and user_member.get("role") in ("owner", "admin"):
                    return current_user
    except Exception:
        logger.exception("require_org_admin: unexpected error calling auth service")

    raise PermissionDeniedError(detail="Admin access required for this organization.")
