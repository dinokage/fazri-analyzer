from typing import List, Optional, Callable
from fastapi import Header, Depends
import logging

from auth.jwt import decode_jwt_token
from auth.models import AuthenticatedUser, UserRole
from auth.exceptions import AuthenticationError, PermissionDeniedError

logger = logging.getLogger(__name__)


async def get_current_user(
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

    # Debug logging (remove in production)
    logger.debug(f"[Auth] Received token length: {len(token)}")
    logger.debug(f"[Auth] Token preview: {token[:50]}...")

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
        )
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
