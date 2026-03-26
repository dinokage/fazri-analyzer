import requests
from jose import jwt, JWTError, ExpiredSignatureError
from typing import Dict, Any

from config import settings
from auth.exceptions import TokenExpiredError, InvalidTokenError, AuthServiceUnavailableError

_jwks_cache: dict | None = None


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    url = f"{settings.AUTH_SERVICE_URL.rstrip('/')}/api/auth/jwks"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache
    except (requests.exceptions.RequestException, OSError) as e:
        _jwks_cache = None
        raise AuthServiceUnavailableError(
            detail=f"Could not fetch JWKS from auth service: {str(e)}"
        )


def _decode(token: str, jwks: dict) -> Dict[str, Any]:
    return jwt.decode(
        token,
        jwks,
        algorithms=["EdDSA", "RS256", "ES256"],
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": False,
        },
    )


def decode_jwt_token(token: str) -> Dict[str, Any]:
    global _jwks_cache
    try:
        jwks = _get_jwks()
        return _decode(token, jwks)

    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        # Stale JWKS (key rotation) — clear cache and retry once
        _jwks_cache = None
        try:
            jwks = _get_jwks()
            return _decode(token, jwks)
        except ExpiredSignatureError:
            raise TokenExpiredError()
        except JWTError as e:
            raise InvalidTokenError(detail=f"Invalid token: {str(e)}")
