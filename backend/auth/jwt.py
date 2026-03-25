import requests
from jose import jwt, JWTError, ExpiredSignatureError
from typing import Dict, Any

from config import settings
from auth.exceptions import TokenExpiredError, InvalidTokenError

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    url = f"{settings.AUTH_SERVICE_URL.rstrip('/')}/api/auth/jwks"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    _jwks_cache = response.json()
    return _jwks_cache


def decode_jwt_token(token: str) -> Dict[str, Any]:
    global _jwks_cache
    try:
        jwks = _get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["EdDSA", "RS256", "ES256"],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,
            },
        )
        return payload

    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError as e:
        raise InvalidTokenError(detail=f"Invalid token: {str(e)}")
    except Exception as e:
        # Clear cache on failure so next request retries the JWKS fetch
        _jwks_cache = None
        raise InvalidTokenError(detail=f"Token validation failed: {str(e)}")
