# JWT Authentication Test Suite

Comprehensive test suite for JWT authentication and role-based access control (RBAC).

## Test Structure

```
test_auth/
├── README.md                 # This file
├── conftest.py              # Test fixtures and utilities
├── test_jwt.py              # JWT validation tests
├── test_dependencies.py     # Auth dependency tests
└── test_integration.py      # API endpoint integration tests
```

## Test Coverage

### 1. JWT Validation (`test_jwt.py`)
- ✅ Valid token decoding for all roles (STUDENT, STAFF, FACULTY, SUPER_ADMIN)
- ✅ Token expiry detection
- ✅ Invalid signature rejection
- ✅ Malformed token handling
- ✅ Required claims verification
- ✅ Role enum validation

**Total**: 12 test cases

### 2. Auth Dependencies (`test_dependencies.py`)
- ✅ `get_current_user()` with valid/invalid tokens
- ✅ Authorization header parsing (Bearer token)
- ✅ `require_role()` factory function
- ✅ Role shortcuts: `require_staff()`, `require_faculty()`, `require_admin()`
- ✅ Permission denied scenarios (403)
- ✅ Missing/malformed header handling (401)

**Total**: 22 test cases

### 3. Integration Tests (`test_integration.py`)
- ✅ Health check endpoints with auth
- ✅ Entity endpoints with self-access checks
- ✅ Graph/timeline endpoints (STAFF+)
- ✅ Alert endpoints (STAFF+ and admin-only)
- ✅ Demo endpoints (admin-only)
- ✅ GitLab endpoints (admin-only)
- ✅ Chat endpoints (all authenticated)
- ✅ Invalid token scenarios

**Total**: 28+ test cases

## Quick Start

### Run All Tests
```bash
cd backend
python -m pytest tests/test_auth/ -v
```

### Run with Coverage
```bash
cd backend
python -m pytest tests/test_auth/ --cov=auth --cov-report=html
```

### Run Specific Test File
```bash
cd backend
python -m pytest tests/test_auth/test_jwt.py -v
```

### Run Specific Test
```bash
cd backend
python -m pytest tests/test_auth/test_jwt.py::TestJWTValidation::test_decode_valid_student_token -v
```

**Note**: Always use `python -m pytest` to ensure correct Python path.

## Test Fixtures

All fixtures are defined in `conftest.py`:

### User Claims Fixtures
- `student_claims` - JWT claims for a student user
- `staff_claims` - JWT claims for a staff user
- `faculty_claims` - JWT claims for a faculty user
- `admin_claims` - JWT claims for a super admin user
- `expired_claims` - Expired JWT claims

### Token Fixtures
- `student_token` - Valid student JWT token
- `staff_token` - Valid staff JWT token
- `faculty_token` - Valid faculty JWT token
- `admin_token` - Valid admin JWT token
- `expired_token` - Expired JWT token
- `invalid_signature_token` - Token with wrong signature
- `malformed_token` - Malformed JWT string

### Configuration Fixtures
- `jwt_secret` - NEXTAUTH_SECRET from settings
- `jwt_algorithm` - JWT algorithm (HS256)

## Example Usage

```python
import pytest
from auth.dependencies import get_current_user
from auth.models import UserRole

@pytest.mark.asyncio
async def test_my_feature(student_token):
    """Test my feature with student auth"""
    # Arrange
    auth_header = f"Bearer {student_token}"

    # Act
    user = await get_current_user(authorization=auth_header)

    # Assert
    assert user.role == UserRole.STUDENT
    assert user.entity_id == "220101001"
```

## Environment Requirements

Required environment variables:
- `NEXTAUTH_SECRET` - Must match frontend secret
- `JWT_ALGORITHM` - Default: HS256

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

### GitHub Actions
```yaml
- name: Run auth tests
  env:
    NEXTAUTH_SECRET: ${{ secrets.NEXTAUTH_SECRET }}
  run: |
    cd backend
    pytest tests/test_auth/ -v --cov=auth
```

### Jenkins
See [JENKINS_SETUP.md](../../../JENKINS_SETUP.md) for detailed setup.

## Coverage Goals

- **JWT validation**: 100%
- **Auth dependencies**: 95%+
- **Overall auth module**: 95%+

Current coverage:
```bash
pytest tests/test_auth/ --cov=auth --cov-report=term
```

## Troubleshooting

### "No module named 'auth'" or "No module named 'config'"
Always run from backend directory using `python -m pytest`:
```bash
cd backend
python -m pytest tests/test_auth/
```

The `pytest.ini` file configures the Python path automatically.

### "NEXTAUTH_SECRET not set"
```bash
cd backend
export NEXTAUTH_SECRET="<your-nextauth-secret>"
python -m pytest tests/test_auth/
```

### Wrong jose library
```bash
pip uninstall jose
pip install python-jose[cryptography]
```

## Documentation

- [TESTING.md](../../../TESTING.md) - Complete testing guide
- [JENKINS_SETUP.md](../../../JENKINS_SETUP.md) - Jenkins CI/CD setup

## Contributing

When adding new auth tests:
1. Add fixtures to `conftest.py` if needed
2. Follow naming convention: `test_<scenario>_<expected_result>`
3. Use `@pytest.mark.asyncio` for async tests
4. Add docstrings to explain what is being tested
5. Ensure tests are isolated and don't depend on order
