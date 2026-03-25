from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime
from typing import Dict, Any

from config import settings
from auth.exceptions import TokenExpiredError, InvalidTokenError


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token using BETTER_AUTH_SECRET

    Args:
        token: JWT token string

    Returns:
        Dictionary of JWT claims

    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or signature doesn't match
    """
    try:
        # Decode and validate JWT
        payload = jwt.decode(
            token,
            settings.BETTER_AUTH_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            }
        )

        return payload

    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError as e:
        raise InvalidTokenError(detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise InvalidTokenError(detail=f"Token validation failed: {str(e)}")
