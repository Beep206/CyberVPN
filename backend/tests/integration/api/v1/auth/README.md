# Backend Auth Flow Integration Tests (TE-1)

## Overview

Comprehensive integration tests for the CyberVPN backend authentication system, covering:

- **Complete auth cycle:** register → OTP verify → login → refresh → logout
- **Magic link authentication:** request → verify (with auto-registration)
- **Password reset flow:** forgot-password → reset-password → login with new password
- **Brute force protection:** lockout after failed attempts, constant-time responses
- **OTP resend rate limiting:** 3 resends per hour
- **Multi-device logout:** logout-all functionality

## Test Files

### `test_auth_flows.py`
Main integration test suite with 100+ test cases organized into classes:

1. **TestCompleteAuthFlow** - Full registration and login cycle
2. **TestMagicLinkFlow** - Passwordless authentication via email
3. **TestPasswordResetFlow** - Password recovery with OTP
4. **TestBruteForceProtection** - Security protections and rate limiting
5. **TestOTPResendFlow** - OTP resend rate limiting
6. **TestLogoutAllDevices** - Multi-session management

## Prerequisites

### 1. Test Database

```bash
# Start PostgreSQL test database (Docker)
docker run -d \
  --name cybervpn_test_db \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=cybervpn_test \
  -p 5433:5432 \
  postgres:17.7-alpine

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://test:test@localhost:5433/cybervpn_test"
```

### 2. Redis Cache

```bash
# Start Redis test instance (Docker)
docker run -d \
  --name cybervpn_test_redis \
  -p 6380:6379 \
  redis:alpine

# Set environment variable
export REDIS_URL="redis://localhost:6380/1"
```

### 3. Run Migrations

```bash
# Apply database migrations to test database
cd /home/beep/projects/VPNBussiness/backend
DATABASE_URL="postgresql+asyncpg://test:test@localhost:5433/cybervpn_test" \
  alembic upgrade head
```

## Running Tests

### Run All Auth Flow Tests

```bash
cd /home/beep/projects/VPNBussiness/backend
python -m pytest tests/integration/api/v1/auth/test_auth_flows.py -v
```

### Run Specific Test Class

```bash
# Complete auth flow tests only
python -m pytest tests/integration/api/v1/auth/test_auth_flows.py::TestCompleteAuthFlow -v

# Magic link tests only
python -m pytest tests/integration/api/v1/auth/test_auth_flows.py::TestMagicLinkFlow -v

# Brute force protection tests
python -m pytest tests/integration/api/v1/auth/test_auth_flows.py::TestBruteForceProtection -v
```

### Run Single Test

```bash
python -m pytest tests/integration/api/v1/auth/test_auth_flows.py::TestCompleteAuthFlow::test_complete_registration_and_login_flow -v
```

### Run with Coverage

```bash
python -m pytest tests/integration/api/v1/auth/test_auth_flows.py \
  --cov=src/presentation/api/v1/auth \
  --cov=src/application/use_cases/auth \
  --cov-report=html
```

## Test Strategy

### Mocking Strategy

Tests mock external dependencies to remain fast and deterministic:

- **Email dispatcher:** Mocked to prevent actual email sends
- **Remnawave VPN adapter:** Mocked for user creation calls
- **Database:** Real test database with automatic cleanup
- **Redis:** Real Redis instance for token/cache operations

### Database Cleanup

Each test uses an isolated database session with automatic rollback after completion, ensuring no test pollution.

### Rate Limiting Tests

Rate limiting tests use real Redis to verify:
- Login attempt lockouts (3 fails → 5 min lock)
- OTP resend limits (3 per hour)
- Constant-time responses (prevent timing attacks)

## Key Test Scenarios

### Registration Flow
```
1. POST /auth/register → 201 (inactive user)
2. Extract OTP from database
3. POST /auth/verify-otp → 200 (auto-login with tokens)
4. GET /auth/me → 200 (verify user activated)
```

### Login Flow
```
1. POST /auth/login → 200 (tokens)
2. GET /auth/me → 200 (current user)
3. POST /auth/refresh → 200 (new tokens)
4. POST /auth/logout → 204 (invalidate refresh token)
```

### Magic Link Flow
```
1. POST /auth/magic-link → 200 (always same response)
2. Extract token from Redis
3. POST /auth/magic-link/verify → 200 (tokens + auto-register if new)
4. Verify token is single-use (2nd verify fails)
```

### Password Reset Flow
```
1. POST /auth/forgot-password → 200
2. Extract OTP from database
3. POST /auth/reset-password → 200
4. POST /auth/login (old password) → 401
5. POST /auth/login (new password) → 200
```

### Brute Force Protection
```
1. Make 3 failed login attempts
2. 4th attempt → 423 Locked (even with correct password)
3. Wait or admin unlock required
```

## Configuration

Tests read from environment variables set by `conftest.py`:

```python
{
    "ENVIRONMENT": "test",
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/cybervpn_test",
    "REDIS_URL": "redis://localhost:6379/1",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "CORS_ORIGINS": "http://localhost:3000",
    "DEBUG": "true",
}
```

## Fixtures

### `async_client` (from conftest.py)
HTTP client using ASGI transport for testing FastAPI app without network I/O.

### `db` (from conftest.py)
Async database session with automatic table creation/cleanup.

## Current Status

**✅ Test Suite Complete:** All test cases written and follow backend patterns
**⚠️  Infrastructure Needed:** Test database + Redis need to be running
**📋 Coverage Target:** ~70% coverage of auth endpoints and use cases

## Next Steps

1. **Set up test infrastructure** (database + Redis containers)
2. **Run migrations** on test database
3. **Execute tests** and verify all pass
4. **Check coverage** and add edge case tests if needed
5. **Add to CI/CD** pipeline for automated testing

## Notes

- Tests use `@pytest.mark.integration` for categorization
- Tests follow existing backend patterns (async/await, dependency injection)
- Tests verify both success and failure scenarios
- Security tests verify timing attack protections
- All tests are idempotent and can run in any order
