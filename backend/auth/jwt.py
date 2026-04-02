import threading
import requests
from jose import jwt, JWTError, ExpiredSignatureError
from typing import Dict, Any

from config import settings
from auth.exceptions import TokenExpiredError, InvalidTokenError, AuthServiceUnavailableError

_jwks_cache: dict | None = None
_jwks_lock = threading.Lock()


def _get_jwks() -> dict:
    global _jwks_cache
    with _jwks_lock:
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
                detail=f"Could not fetch JWKS from auth service: {e!r}"
            ) from e


def _decode(token: str, jwks: dict) -> Dict[str, Any]:
    return jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": False,
        },
    )

def decode_jwt_token(token: str) -> Dict[str, Any]:
    # Test-only bypass: accept HS256 tokens when TESTING=true.
    # This path is unreachable unless the setting is explicitly set.
    if settings.TESTING and settings.TEST_JWT_SECRET:
        try:
            return jwt.decode(
                token,
                settings.TEST_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_aud": False},
            )
        except ExpiredSignatureError as e:
            raise TokenExpiredError() from e
        except JWTError:
            pass  # fall through to RS256 path

    try:
        jwks = _get_jwks()
        return _decode(token, jwks)

    except ExpiredSignatureError as e:
        raise TokenExpiredError() from e
    except JWTError:
        # Stale JWKS (key rotation) — clear cache and retry once
        with _jwks_lock:
            global _jwks_cache
            _jwks_cache = None
        try:
            jwks = _get_jwks()
            return _decode(token, jwks)
        except ExpiredSignatureError as e:
            raise TokenExpiredError() from e
        except JWTError as e:
            raise InvalidTokenError(detail=f"Invalid token: {e!r}") from e
