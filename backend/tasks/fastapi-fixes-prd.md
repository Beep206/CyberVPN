# CyberVPN Backend - FastAPI Best Practices Fixes

**Date**: 2026-01-29
**Source**: backend/report/fastapi-best-practices-analysis.md
**Current Grade**: B- (65/100)
**Target Grade**: A (90+/100)

## Overview

This PRD describes high-priority fixes to bring CyberVPN backend to production-ready state based on FastAPI best practices analysis. Focus on P0-P2 issues that block deployment or compromise security/reliability.

---

## Task 1: Configure Alembic Database Migrations

**Priority**: P0 (CRITICAL - blocks schema evolution)

**Description**: Initialize Alembic for database migration management. Currently no migration system exists despite alembic being in dependencies.

**Details**:
- Initialize Alembic in backend/: `alembic init alembic`
- Configure alembic.ini with async SQLAlchemy URL
- Update alembic/env.py to use async engine from src.infrastructure.database.session
- Import all SQLAlchemy models in env.py (AdminUserModel, RefreshToken, PaymentModel, AuditLog, WebhookLog, OAuthAccount, NotificationQueue, ServerGeolocation)
- Create initial migration: `alembic revision --autogenerate -m "initial schema"`
- Verify migration: `alembic upgrade head` on test database
- Add migration commands to README

**Test Strategy**:
1. `alembic upgrade head` creates all tables in empty database
2. `alembic downgrade base` drops all tables
3. Run upgrade again - no errors
4. Make schema change (add column), autogenerate migration, verify SQL is correct

**Acceptance Criteria**:
- [ ] alembic/ directory exists with env.py, script.py.mako, versions/
- [ ] alembic.ini configured with async database URL
- [ ] Initial migration file created
- [ ] Migration runs successfully on test database
- [ ] Documentation added to README

**Files**:
- Create: backend/alembic.ini
- Create: backend/alembic/env.py
- Create: backend/alembic/script.py.mako
- Create: backend/alembic/versions/001_initial_schema.py
- Modify: backend/README.md (add migration section)

---

## Task 2: Implement Comprehensive Test Suite

**Priority**: P0 (CRITICAL - <5% coverage is unacceptable)

**Description**: Build test suite to achieve 70%+ coverage with unit, integration, and e2e tests for critical paths.

**Details**:

**Phase 1: Test Infrastructure**
- Install pytest-cov, pytest-asyncio, httpx
- Create pytest.ini with coverage config (min 70%, exclude tests/)
- Create conftest.py fixtures: test database, async client, mock factories
- Create tests/unit/, tests/integration/, tests/e2e/ directories

**Phase 2: Unit Tests (35+ tests)**
- Domain entities (User, Server, Payment) - 5 tests
- Value objects (Email, Money, Traffic, Geolocation) - 8 tests
- AuthService (hash_password, verify_password, create_token, decode_token) - 6 tests
- Permission system (has_permission, require_permission) - 4 tests
- Use cases (LoginUseCase, CreateUserUseCase) - 12 tests

**Phase 3: Integration Tests (20+ tests)**
- Auth routes (login, register, refresh, logout, verify-token) - 5 tests
- User CRUD (list, get, create, update, delete) - 5 tests
- Middleware (AuthMiddleware passes valid token, rejects invalid) - 3 tests
- Exception handlers (validation errors, domain errors) - 3 tests
- Database repositories (create, read, update, delete) - 4 tests

**Phase 4: E2E Tests (5+ tests)**
- Complete auth flow: register → login → access protected → refresh → logout
- Payment flow: create payment → webhook callback → update status
- User management: admin creates user → user logs in → admin deactivates → login fails

**Test Strategy**:
- Unit tests: mock all dependencies, test business logic
- Integration tests: use test database, test API contracts
- E2E tests: full stack with real database, test critical user journeys
- All tests must be async (pytest-asyncio)
- Use pytest fixtures for test data
- Coverage must be >70%

**Acceptance Criteria**:
- [ ] pytest.ini configured
- [ ] Test fixtures in conftest.py
- [ ] 35+ unit tests passing
- [ ] 20+ integration tests passing
- [ ] 5+ e2e tests passing
- [ ] `pytest --cov` shows >70% coverage
- [ ] CI/CD pipeline runs tests (if applicable)

**Files**:
- Create: backend/pytest.ini
- Modify: backend/tests/conftest.py
- Create: backend/tests/unit/test_auth_service.py
- Create: backend/tests/unit/test_permissions.py
- Create: backend/tests/unit/test_value_objects.py
- Create: backend/tests/integration/test_auth_routes.py
- Create: backend/tests/integration/test_user_routes.py
- Create: backend/tests/integration/test_middleware.py
- Create: backend/tests/e2e/test_auth_flow.py
- Create: backend/tests/e2e/test_payment_flow.py

---

## Task 3: Fix Error Handling Security Issues

**Priority**: P1 (HIGH - security vulnerability)

**Description**: Eliminate information leakage in error responses and implement global domain exception handlers.

**Details**:

**Phase 1: Global Exception Handlers**
- Add handlers in src/presentation/exception_handlers.py:
  - UserNotFoundError → 404 with generic message
  - InvalidCredentialsError → 401 "Invalid credentials"
  - InvalidTokenError → 401 "Invalid or expired token"
  - PermissionDeniedError → 403 "Insufficient permissions"
  - SubscriptionExpiredError → 402 "Subscription expired"
  - DomainError (catch-all) → 400 with safe message
  - Exception (unhandled) → 500 "Internal server error" + log exception
- Register all handlers in main.py via app.add_exception_handler()

**Phase 2: Remove Try/Except from Routes**
- Remove all route-level try/except blocks that catch DomainError subclasses
- Remove all `detail=f"Failed to X: {str(e)}"` patterns
- Let exceptions bubble up to global handlers
- Keep try/except only for non-domain errors (e.g., httpx.RequestError)

**Phase 3: Standardize Error Format**
- All errors return: `{"detail": "message"}` (FastAPI standard)
- Validation errors return: `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`
- Never expose: stack traces, SQL errors, internal service names

**Test Strategy**:
1. Invalid login → 401 `{"detail": "Invalid credentials"}` (no username leak)
2. Missing user → 404 `{"detail": "User not found"}` (no UUID leak)
3. Expired token → 401 `{"detail": "Invalid or expired token"}` (no expiry time leak)
4. Insufficient permissions → 403 `{"detail": "Insufficient permissions"}` (no role leak)
5. Unhandled exception → 500 `{"detail": "Internal server error"}` (no stack trace)
6. Check logs contain full exception details (for debugging)

**Acceptance Criteria**:
- [ ] Global handlers for all domain exceptions
- [ ] Generic error handler for Exception
- [ ] All route try/except blocks removed or refactored
- [ ] No internal error details in responses
- [ ] Error format consistent across all endpoints
- [ ] Logs contain full exception context

**Files**:
- Modify: backend/src/presentation/exception_handlers.py
- Modify: backend/src/main.py
- Modify: All routes in backend/src/presentation/api/v1/*/routes.py (19 files)

---

## Task 4: Refactor Dependency Injection Patterns

**Priority**: P1 (HIGH - testability and SOLID compliance)

**Description**: Replace module-level singletons and in-handler instantiation with proper FastAPI dependency injection.

**Details**:

**Phase 1: Create Dependency Factories**
Create src/presentation/dependencies/services.py:
- `def get_auth_service() -> AuthService: return AuthService()`
- `def get_remnawave_client() -> RemnawaveClient: return RemnawaveClient()`
- `def get_crypto_client() -> CryptoBotClient: return CryptoBotClient(settings.cryptobot_token)`
- Repository factories (if needed): `def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository: return AdminUserRepository(db)`

**Phase 2: Remove Module Singletons**
- src/presentation/dependencies/auth.py:14 - remove `auth_service = AuthService()`
- src/infrastructure/remnawave/client.py:57 - remove `remnawave_client = RemnawaveClient()`
- Replace with Depends(get_auth_service), Depends(get_remnawave_client)

**Phase 3: Refactor Route Handlers**
Update all routes to use DI:
```python
# Before:
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService()  # ❌ bad
    ...

# After:
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),  # ✅ good
):
    ...
```

Apply to:
- Auth routes: AuthService
- Payment routes: CryptoBotClient
- User/Proxy routes: RemnawaveClient
- All routes: Repositories

**Test Strategy**:
1. Mock factories in tests: `app.dependency_overrides[get_auth_service] = lambda: MockAuthService()`
2. Verify no module-level instantiation (grep for `= AuthService()`, `= RemnawaveClient()`)
3. All routes accept dependencies via Depends()
4. Integration tests verify real dependencies work
5. Unit tests verify mock dependencies work

**Acceptance Criteria**:
- [ ] services.py with all factory functions
- [ ] No module-level service instantiation
- [ ] All routes use Depends() for services/repos
- [ ] Tests use dependency_overrides successfully
- [ ] No breaking changes to API contracts

**Files**:
- Create: backend/src/presentation/dependencies/services.py
- Modify: backend/src/presentation/dependencies/auth.py
- Modify: backend/src/infrastructure/remnawave/client.py
- Modify: All routes in backend/src/presentation/api/v1/*/routes.py (19+ files)

---

## Task 5: Fix Async Patterns (Blocking Bcrypt)

**Priority**: P1 (HIGH - event loop blocking under load)

**Description**: Make bcrypt password hashing/verification async-safe using asyncio.to_thread().

**Details**:

**Phase 1: Refactor AuthService**
In src/application/services/auth_service.py:

```python
import asyncio

class AuthService:
    @staticmethod
    async def hash_password(password: str) -> str:
        """Hash password asynchronously (bcrypt is CPU-intensive)."""
        return await asyncio.to_thread(pwd_context.hash, password)

    @staticmethod
    async def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password asynchronously (bcrypt is CPU-intensive)."""
        return await asyncio.to_thread(pwd_context.verify, plain_password, hashed_password)
```

**Phase 2: Update All Callers**
Find all calls to:
- `auth_service.hash_password()` → `await auth_service.hash_password()`
- `auth_service.verify_password()` → `await auth_service.verify_password()`

Files to update:
- Use cases: LoginUseCase, RegisterUseCase, ChangePasswordUseCase
- Routes: Any direct calls (should be via use cases)
- Tests: Update assertions to await

**Test Strategy**:
1. Unit test: verify hash_password returns different hash each time (bcrypt salt)
2. Unit test: verify verify_password(plain, hash) returns True
3. Unit test: verify verify_password(wrong, hash) returns False
4. Load test: 100 concurrent login requests don't block event loop (response time <500ms)
5. Check no "RuntimeWarning: coroutine was never awaited"

**Acceptance Criteria**:
- [ ] hash_password and verify_password are async
- [ ] All callers use await
- [ ] Tests pass with async methods
- [ ] No blocking detected in load testing
- [ ] No coroutine warnings

**Files**:
- Modify: backend/src/application/services/auth_service.py
- Modify: backend/src/application/use_cases/auth/login.py
- Modify: backend/src/application/use_cases/auth/register.py (if exists)
- Modify: backend/tests/unit/test_auth_service.py

---

## Task 6: Enable and Configure Middleware

**Priority**: P2 (MEDIUM - security and observability)

**Description**: Fix middleware ordering (CORS first) and enable RateLimitMiddleware.

**Details**:

**Phase 1: Fix Middleware Order**
In src/main.py, CORS must run first (be added last):

```python
# Current (WRONG):
app.add_middleware(CORSMiddleware, ...)  # Added first, runs last
app.add_middleware(AuthMiddleware)       # Runs second
app.add_middleware(LoggingMiddleware)    # Added last, runs first

# Fixed (CORRECT):
app.add_middleware(LoggingMiddleware)     # Runs last
app.add_middleware(AuthMiddleware)        # Runs second
app.add_middleware(CORSMiddleware, ...)   # Added last, runs FIRST (handles preflight)
```

**Phase 2: Enable RateLimitMiddleware**
- Verify src/presentation/middleware/rate_limit.py exists
- Add to main.py: `app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)`
- Configure: 100 requests/minute per IP (adjust based on needs)
- Critical endpoints (login, register): 5 requests/minute per IP
- Use Redis for distributed rate limiting (optional)

**Phase 3: Restrict CORS**
Replace wildcards:
```python
# Before:
allow_methods=["*"]
allow_headers=["*"]

# After:
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
allow_headers=["Content-Type", "Authorization", "X-Request-ID"]
```

**Test Strategy**:
1. Send OPTIONS preflight request → 200 OK with CORS headers (before auth)
2. Send request without auth → 401 (AuthMiddleware works)
3. Send 101 requests in 60s → last one gets 429 Too Many Requests
4. Login 6 times in 60s → 6th request gets 429
5. Verify LoggingMiddleware logs all requests

**Acceptance Criteria**:
- [ ] CORS middleware added last (runs first)
- [ ] Preflight requests succeed without auth
- [ ] RateLimitMiddleware enabled
- [ ] Rate limits enforced (429 responses)
- [ ] CORS wildcards removed
- [ ] All middleware tested

**Files**:
- Modify: backend/src/main.py
- Verify: backend/src/presentation/middleware/rate_limit.py
- Create: backend/tests/integration/test_rate_limit.py

---

## Task 7: Complete Configuration Settings

**Priority**: P2 (MEDIUM - runtime errors on payment paths)

**Description**: Add missing configuration keys and create .env.example template.

**Details**:

**Phase 1: Add Missing Settings**
In src/config/settings.py:

```python
class Settings(BaseSettings):
    # ... existing ...

    # Payment gateway
    cryptobot_token: SecretStr  # Required for CryptoBotClient

    # Environment
    environment: str = "development"  # development, staging, production

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
```

**Phase 2: Update Code Using Missing Settings**
- src/infrastructure/payments/cryptobot/client.py - use settings.cryptobot_token
- src/main.py - use settings.log_level for logging config
- src/presentation/middleware/rate_limit.py - use settings.rate_limit_*

**Phase 3: Create .env.example**
Create backend/.env.example:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://cybervpn:cybervpn@localhost:6767/cybervpn

# Redis
REDIS_URL=redis://localhost:6379/0

# Remnawave API
REMNAWAVE_URL=http://localhost:3000
REMNAWAVE_TOKEN=your_token_here

# JWT
JWT_SECRET=your_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Payment Gateway
CRYPTOBOT_TOKEN=your_cryptobot_token_here

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

**Test Strategy**:
1. Start app without .env → fails with clear error about missing required settings
2. Copy .env.example to .env → app starts successfully
3. Access payment endpoint → CryptoBotClient uses settings.cryptobot_token
4. Check logs → use configured log_level
5. Verify environment differentiation works (dev vs prod behavior)

**Acceptance Criteria**:
- [ ] All missing settings added to Settings class
- [ ] .env.example created with all variables
- [ ] Code updated to use new settings
- [ ] App fails fast on missing required settings
- [ ] Documentation updated

**Files**:
- Modify: backend/src/config/settings.py
- Create: backend/.env.example
- Modify: backend/src/infrastructure/payments/cryptobot/client.py
- Modify: backend/README.md

---

## Success Metrics

**Before fixes**:
- Overall Grade: B- (65/100)
- Test Coverage: <5%
- Security Issues: 4 (info leakage, CORS, rate limit, hardcoded creds)
- Production Blockers: 2 (no migrations, no tests)

**After fixes**:
- Overall Grade: A (90+/100)
- Test Coverage: >70%
- Security Issues: 0
- Production Blockers: 0
- All P0-P2 issues resolved

**Quality Gates**:
1. ✅ All tests pass
2. ✅ Coverage >70%
3. ✅ No info leakage in error responses
4. ✅ Migrations run successfully
5. ✅ Rate limiting enforced
6. ✅ CORS configured correctly
7. ✅ Async patterns verified
8. ✅ DI pattern consistent

---

## Dependencies Between Tasks

```
Task 1 (Migrations) - independent
Task 2 (Tests) - depends on Tasks 3,4,5,6,7 (test fixed code)
Task 3 (Error Handling) - independent
Task 4 (DI Refactor) - independent
Task 5 (Async Bcrypt) - independent
Task 6 (Middleware) - independent
Task 7 (Config) - independent
```

**Recommended order**: 3 → 4 → 5 → 7 → 6 → 1 → 2
(Fix code issues first, then infrastructure, then comprehensive testing)

---

## Notes

- Use context7 MCP plugin for up-to-date FastAPI, Pydantic, SQLAlchemy, pytest documentation
- Each task should have subtasks for phases/components
- Follow existing code style (ruff, mypy)
- Update documentation as you go
- Create git commits per logical change
