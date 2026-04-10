import pytest
from unittest.mock import AsyncMock

from auth.dependencies import get_current_user, require_role, require_staff, require_faculty, require_admin
from auth.models import AuthenticatedUser, UserRole
from auth.exceptions import AuthenticationError, PermissionDeniedError


class TestGetCurrentUser:
    """Test get_current_user dependency"""

    @pytest.mark.asyncio
    async def test_valid_authorization_header_student(self, student_token, student_claims):
        """Test valid authorization header for student"""
        auth_header = f"Bearer {student_token}"
        user = await get_current_user(authorization=auth_header)

        assert isinstance(user, AuthenticatedUser)
        assert user.id == student_claims["id"]
        assert user.entity_id == student_claims["entity_id"]
        assert user.role == UserRole.STUDENT
        assert user.name == student_claims["name"]
        assert user.email == student_claims["email"]

    @pytest.mark.asyncio
    async def test_valid_authorization_header_staff(self, staff_token, staff_claims):
        """Test valid authorization header for staff"""
        auth_header = f"Bearer {staff_token}"
        user = await get_current_user(authorization=auth_header)

        assert isinstance(user, AuthenticatedUser)
        assert user.role == UserRole.STAFF
        assert user.staff_id == staff_claims["staff_id"]

    @pytest.mark.asyncio
    async def test_valid_authorization_header_admin(self, admin_token, admin_claims):
        """Test valid authorization header for admin"""
        auth_header = f"Bearer {admin_token}"
        user = await get_current_user(authorization=auth_header)

        assert isinstance(user, AuthenticatedUser)
        assert user.role == UserRole.SUPER_ADMIN

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test missing authorization header raises AuthenticationError"""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization=None)

        assert exc_info.value.status_code == 401
        assert "missing" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_authorization_format_no_bearer(self, student_token):
        """Test authorization header without 'Bearer' prefix"""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization=student_token)

        assert exc_info.value.status_code == 401
        assert "invalid authorization header format" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_empty_token_after_bearer(self):
        """Test authorization header with empty token"""
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization="Bearer ")

        assert exc_info.value.status_code == 401
        assert "empty" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_expired_token(self, expired_token):
        """Test expired token raises AuthenticationError"""
        auth_header = f"Bearer {expired_token}"

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization=auth_header)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_signature_token(self, invalid_signature_token):
        """Test token with invalid signature raises AuthenticationError"""
        auth_header = f"Bearer {invalid_signature_token}"

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization=auth_header)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token(self, malformed_token):
        """Test malformed token raises AuthenticationError"""
        auth_header = f"Bearer {malformed_token}"

        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(authorization=auth_header)

        assert exc_info.value.status_code == 401


class TestRequireRole:
    """Test require_role dependency factory"""

    @pytest.mark.asyncio
    async def test_require_role_allows_matching_role(self, student_token):
        """Test require_role allows user with matching role"""
        auth_header = f"Bearer {student_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_role([UserRole.STUDENT])
        result = await role_checker(current_user=user)

        assert result == user
        assert result.role == UserRole.STUDENT

    @pytest.mark.asyncio
    async def test_require_role_allows_one_of_multiple_roles(self, staff_token):
        """Test require_role allows user with one of multiple allowed roles"""
        auth_header = f"Bearer {staff_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_role([UserRole.STAFF, UserRole.FACULTY, UserRole.SUPER_ADMIN])
        result = await role_checker(current_user=user)

        assert result == user
        assert result.role == UserRole.STAFF

    @pytest.mark.asyncio
    async def test_require_role_denies_non_matching_role(self, student_token):
        """Test require_role denies user without matching role"""
        auth_header = f"Bearer {student_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_role([UserRole.STAFF, UserRole.SUPER_ADMIN])

        with pytest.raises(PermissionDeniedError) as exc_info:
            await role_checker(current_user=user)

        assert exc_info.value.status_code == 403
        assert "insufficient permissions" in exc_info.value.detail.lower()


class TestRoleShortcuts:
    """Test role shortcut dependencies"""

    @pytest.mark.asyncio
    async def test_require_staff_allows_staff(self, staff_token):
        """Test require_staff allows STAFF role"""
        auth_header = f"Bearer {staff_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_staff()
        result = await role_checker(current_user=user)

        assert result.role == UserRole.STAFF

    @pytest.mark.asyncio
    async def test_require_staff_allows_faculty(self, faculty_token):
        """Test require_staff allows FACULTY role"""
        auth_header = f"Bearer {faculty_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_staff()
        result = await role_checker(current_user=user)

        assert result.role == UserRole.FACULTY

    @pytest.mark.asyncio
    async def test_require_staff_allows_admin(self, admin_token):
        """Test require_staff allows SUPER_ADMIN role"""
        auth_header = f"Bearer {admin_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_staff()
        result = await role_checker(current_user=user)

        assert result.role == UserRole.SUPER_ADMIN

    @pytest.mark.asyncio
    async def test_require_staff_denies_student(self, student_token):
        """Test require_staff denies STUDENT role"""
        auth_header = f"Bearer {student_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_staff()

        with pytest.raises(PermissionDeniedError):
            await role_checker(current_user=user)

    @pytest.mark.asyncio
    async def test_require_faculty_allows_faculty(self, faculty_token):
        """Test require_faculty allows FACULTY role"""
        auth_header = f"Bearer {faculty_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_faculty()
        result = await role_checker(current_user=user)

        assert result.role == UserRole.FACULTY

    @pytest.mark.asyncio
    async def test_require_faculty_allows_admin(self, admin_token):
        """Test require_faculty allows SUPER_ADMIN role"""
        auth_header = f"Bearer {admin_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_faculty()
        result = await role_checker(current_user=user)

        assert result.role == UserRole.SUPER_ADMIN

    @pytest.mark.asyncio
    async def test_require_faculty_denies_staff(self, staff_token):
        """Test require_faculty denies STAFF role"""
        auth_header = f"Bearer {staff_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_faculty()

        with pytest.raises(PermissionDeniedError):
            await role_checker(current_user=user)

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin(self, admin_token):
        """Test require_admin allows SUPER_ADMIN role"""
        auth_header = f"Bearer {admin_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_admin()
        result = await role_checker(current_user=user)

        assert result.role == UserRole.SUPER_ADMIN

    @pytest.mark.asyncio
    async def test_require_admin_denies_staff(self, staff_token):
        """Test require_admin denies STAFF role"""
        auth_header = f"Bearer {staff_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_admin()

        with pytest.raises(PermissionDeniedError):
            await role_checker(current_user=user)

    @pytest.mark.asyncio
    async def test_require_admin_denies_faculty(self, faculty_token):
        """Test require_admin denies FACULTY role"""
        auth_header = f"Bearer {faculty_token}"
        user = await get_current_user(authorization=auth_header)

        role_checker = require_admin()

        with pytest.raises(PermissionDeniedError):
            await role_checker(current_user=user)
