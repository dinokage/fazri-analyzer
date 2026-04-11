import pytest
from jose import jwt

from auth.jwt import decode_jwt_token
from auth.exceptions import TokenExpiredError, InvalidTokenError
from auth.models import UserRole


class TestJWTValidation:
    """Test JWT token validation"""

    def test_decode_valid_student_token(self, student_token, student_claims):
        """Test decoding a valid student token"""
        payload = decode_jwt_token(student_token)

        assert payload["id"] == student_claims["id"]
        assert payload["entity_id"] == student_claims["entity_id"]
        assert payload["name"] == student_claims["name"]
        assert payload["email"] == student_claims["email"]
        assert payload["role"] == UserRole.STUDENT.value
        assert payload["student_id"] == student_claims["student_id"]

    def test_decode_valid_staff_token(self, staff_token, staff_claims):
        """Test decoding a valid staff token"""
        payload = decode_jwt_token(staff_token)

        assert payload["id"] == staff_claims["id"]
        assert payload["entity_id"] == staff_claims["entity_id"]
        assert payload["role"] == UserRole.STAFF.value
        assert payload["staff_id"] == staff_claims["staff_id"]

    def test_decode_valid_faculty_token(self, faculty_token, faculty_claims):
        """Test decoding a valid faculty token"""
        payload = decode_jwt_token(faculty_token)

        assert payload["id"] == faculty_claims["id"]
        assert payload["role"] == UserRole.FACULTY.value

    def test_decode_valid_admin_token(self, admin_token, admin_claims):
        """Test decoding a valid admin token"""
        payload = decode_jwt_token(admin_token)

        assert payload["id"] == admin_claims["id"]
        assert payload["role"] == UserRole.SUPER_ADMIN.value

    def test_decode_expired_token(self, expired_token):
        """Test that expired tokens raise TokenExpiredError"""
        with pytest.raises(TokenExpiredError) as exc_info:
            decode_jwt_token(expired_token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_decode_invalid_signature(self, invalid_signature_token):
        """Test that tokens with invalid signature raise InvalidTokenError"""
        with pytest.raises(InvalidTokenError) as exc_info:
            decode_jwt_token(invalid_signature_token)

        assert exc_info.value.status_code == 401

    def test_decode_malformed_token(self, malformed_token):
        """Test that malformed tokens raise InvalidTokenError"""
        with pytest.raises(InvalidTokenError) as exc_info:
            decode_jwt_token(malformed_token)

        assert exc_info.value.status_code == 401

    def test_decode_empty_token(self):
        """Test that empty token raises InvalidTokenError"""
        with pytest.raises(InvalidTokenError):
            decode_jwt_token("")

    def test_token_contains_all_required_claims(self, student_token):
        """Test that decoded token contains all required claims"""
        payload = decode_jwt_token(student_token)

        required_claims = ["id", "entity_id", "name", "email", "role", "iat", "exp"]
        for claim in required_claims:
            assert claim in payload

    def test_token_role_is_valid_enum(self, student_token, staff_token, faculty_token, admin_token):
        """Test that role claim is a valid UserRole enum value"""
        for token in [student_token, staff_token, faculty_token, admin_token]:
            payload = decode_jwt_token(token)
            role_value = payload["role"]

            # Should be able to create UserRole from the value
            role = UserRole(role_value)
            assert role in [UserRole.STUDENT, UserRole.STAFF, UserRole.FACULTY, UserRole.SUPER_ADMIN]
