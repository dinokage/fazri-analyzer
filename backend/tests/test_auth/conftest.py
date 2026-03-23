import pytest
from jose import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from config import settings
from auth.models import UserRole


@pytest.fixture
def jwt_secret() -> str:
    """Get JWT secret for testing"""
    return settings.NEXTAUTH_SECRET


@pytest.fixture
def jwt_algorithm() -> str:
    """Get JWT algorithm for testing"""
    return settings.JWT_ALGORITHM


@pytest.fixture
def student_claims() -> Dict[str, Any]:
    """Create JWT claims for a student user"""
    now = datetime.now(timezone.utc)
    return {
        "id": "test-student-id-123",
        "entity_id": "220101001",
        "name": "Test Student",
        "email": "student@test.com",
        "role": UserRole.STUDENT.value,
        "face_id": "face-123",
        "student_id": "220101001",
        "staff_id": None,
        "department": "Computer Science",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
    }


@pytest.fixture
def staff_claims() -> Dict[str, Any]:
    """Create JWT claims for a staff user"""
    now = datetime.now(timezone.utc)
    return {
        "id": "test-staff-id-456",
        "entity_id": "staff-001",
        "name": "Test Staff",
        "email": "staff@test.com",
        "role": UserRole.STAFF.value,
        "face_id": "face-456",
        "student_id": None,
        "staff_id": "staff-001",
        "department": "Security",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
    }


@pytest.fixture
def faculty_claims() -> Dict[str, Any]:
    """Create JWT claims for a faculty user"""
    now = datetime.now(timezone.utc)
    return {
        "id": "test-faculty-id-789",
        "entity_id": "faculty-001",
        "name": "Test Faculty",
        "email": "faculty@test.com",
        "role": UserRole.FACULTY.value,
        "face_id": "face-789",
        "student_id": None,
        "staff_id": None,
        "department": "Computer Science",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
    }


@pytest.fixture
def admin_claims() -> Dict[str, Any]:
    """Create JWT claims for a super admin user"""
    now = datetime.now(timezone.utc)
    return {
        "id": "test-admin-id-999",
        "entity_id": "admin-001",
        "name": "Test Admin",
        "email": "admin@test.com",
        "role": UserRole.SUPER_ADMIN.value,
        "face_id": "face-999",
        "student_id": None,
        "staff_id": "admin-001",
        "department": "Administration",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
    }


@pytest.fixture
def expired_claims(student_claims) -> Dict[str, Any]:
    """Create expired JWT claims"""
    now = datetime.now(timezone.utc)
    claims = student_claims.copy()
    claims["iat"] = int((now - timedelta(days=31)).timestamp())
    claims["exp"] = int((now - timedelta(days=1)).timestamp())
    return claims


def create_test_token(claims: Dict[str, Any], secret: str = None, algorithm: str = None) -> str:
    """
    Helper function to create a test JWT token

    Args:
        claims: JWT claims dictionary
        secret: JWT secret (defaults to settings.NEXTAUTH_SECRET)
        algorithm: JWT algorithm (defaults to settings.JWT_ALGORITHM)

    Returns:
        Encoded JWT token string
    """
    return jwt.encode(
        claims,
        secret or settings.NEXTAUTH_SECRET,
        algorithm=algorithm or settings.JWT_ALGORITHM,
    )


@pytest.fixture
def student_token(student_claims, jwt_secret, jwt_algorithm) -> str:
    """Create a valid student JWT token"""
    return create_test_token(student_claims, jwt_secret, jwt_algorithm)


@pytest.fixture
def staff_token(staff_claims, jwt_secret, jwt_algorithm) -> str:
    """Create a valid staff JWT token"""
    return create_test_token(staff_claims, jwt_secret, jwt_algorithm)


@pytest.fixture
def faculty_token(faculty_claims, jwt_secret, jwt_algorithm) -> str:
    """Create a valid faculty JWT token"""
    return create_test_token(faculty_claims, jwt_secret, jwt_algorithm)


@pytest.fixture
def admin_token(admin_claims, jwt_secret, jwt_algorithm) -> str:
    """Create a valid admin JWT token"""
    return create_test_token(admin_claims, jwt_secret, jwt_algorithm)


@pytest.fixture
def expired_token(expired_claims, jwt_secret, jwt_algorithm) -> str:
    """Create an expired JWT token"""
    return create_test_token(expired_claims, jwt_secret, jwt_algorithm)


@pytest.fixture
def invalid_signature_token(student_claims) -> str:
    """Create a token with invalid signature"""
    return create_test_token(student_claims, secret="wrong-secret-key")


@pytest.fixture
def malformed_token() -> str:
    """Create a malformed JWT token"""
    return "this.is.not.a.valid.jwt.token"
