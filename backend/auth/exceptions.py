from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Base authentication error (401 Unauthorized)"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(HTTPException):
    """Permission denied error (403 Forbidden)"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    def __init__(self):
        super().__init__(detail="Token has expired")


class InvalidTokenError(AuthenticationError):
    """Invalid token format or signature"""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)
