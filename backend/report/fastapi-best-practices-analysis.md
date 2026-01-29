# CyberVPN Backend — FastAPI Best Practices Analysis

**Date**: 2026-01-29
**Scope**: Full backend codebase — architecture, async patterns, DI, security, testing, database, middleware, configuration
**Stack**: FastAPI 0.128+, Pydantic v2, SQLAlchemy 2.0 (async), Python 3.13

---

## 1. Executive Summary

| Category | Grade | Notes |
|----------|-------|-------|
| Project Structure | **A** | Excellent Clean Architecture with DDD layers |
| Async Patterns | **B+** | All handlers async; blocking bcrypt issue |
| Dependency Injection | **C+** | FastAPI DI used but inconsistent; module singletons |
| Repository Pattern | **A** | Clean separation, gateways for external APIs |
| Service Layer | **A-** | Thin routes, business logic in use cases |
| Pydantic Schemas | **A** | v2 patterns, ConfigDict, validators, 65+ schemas |
| Error Handling | **C** | Domain exceptions exist but info leakage in routes |
| Security | **B+** | JWT, bcrypt, HMAC webhooks; CORS wildcards |
| Testing | **F** | <5% coverage, minimal tests |
| Database | **B** | Good async session management; no migrations |
| Middleware | **B-** | Auth/Logging present; ordering issue, no rate limit |
| Configuration | **B** | pydantic-settings, SecretStr; missing keys |

**Overall Grade: B-** — Excellent architecture, production-readiness gaps.

---

## 2. Project Structure

### Current Layout

```
backend/src/
├── config/                    # Settings (pydantic-settings)
├── domain/                    # DDD Domain Layer
│   ├── entities/              # User, Server, Payment (frozen dataclasses)
│   ├── enums/                 # StrEnum: UserStatus, ServerStatus, AdminRole, etc.
│   ├── exceptions/            # DomainError hierarchy
│   ├── repositories/          # Abstract base repository (ABC)
│   └── value_objects/         # Email, Money, Traffic, Geolocation
├── application/               # Application Layer
│   ├── dto/                   # Data transfer objects
│   ├── interfaces/            # Gateway interfaces
│   ├── services/              # AuthService (JWT, bcrypt)
│   └── use_cases/             # Login, CreateUser, Payments, etc.
├── infrastructure/            # Infrastructure Layer
│   ├── database/              # SQLAlchemy models, repositories, session
│   ├── cache/                 # Redis client + pool
│   ├── remnawave/             # HTTP client, gateways, mappers
│   ├── payments/              # CryptoBot client + webhook handler
│   ├── messaging/             # WebSocket + SSE managers
│   └── external/              # External service adapters
└── presentation/              # Presentation Layer
    ├── api/v1/                # 23 route modules, schemas
    ├── dependencies/          # DI: auth, database, roles, pagination
    ├── middleware/             # Auth, Logging, RateLimit
    └── exception_handlers.py  # Global validation handler
```

### vs. FastAPI Best Practices

| Aspect | Best Practice | CyberVPN | Status |
|--------|--------------|----------|--------|
| Layer separation | Domain → App → Infra → Presentation | Fully implemented | **Excellent** |
| API versioning | `/api/v1/` prefix | Yes | **Good** |
| Schemas separate from routes | Dedicated `schemas.py` per module | Yes, 21 schema files | **Excellent** |
| Repository pattern | Abstract + concrete | ABC in domain, impl in infra | **Excellent** |
| Gateway pattern for external APIs | Dedicated gateway classes | Remnawave gateways with mappers | **Excellent** |
| Database migrations | Alembic directory | **Missing** | **Critical gap** |
| Test structure | unit/integration/e2e | Present but minimal content | **Poor** |

---

## 3. Async Patterns

### Route Handlers — All Async

Verified all 78 route handlers use `async def` with proper `await` on all I/O:

```python
# src/presentation/api/v1/auth/routes.py:37
@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    use_case = LoginUseCase(...)
    result = await use_case.execute(...)  # Properly awaited
```

### Database — Fully Async

```python
# src/infrastructure/database/session.py:9-15
engine = create_async_engine(
    settings.database_url,
    pool_size=10, max_overflow=20,
    pool_pre_ping=True,  # Connection health checks
)
```

```python
# src/presentation/dependencies/database.py:8-16
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()   # Auto-commit
        except Exception:
            await session.rollback() # Auto-rollback
            raise
```

### External HTTP — Fully Async (httpx)

```python
# src/infrastructure/remnawave/client.py:21-25
async def get(self, path: str, **kwargs) -> dict:
    client = await self._get_client()  # httpx.AsyncClient
    response = await client.get(path, **kwargs)
    response.raise_for_status()
    return response.json()
```

### Issues Found

| # | Issue | Severity | File:Line | Description |
|---|-------|----------|-----------|-------------|
| 1 | Blocking bcrypt in async context | **HIGH** | `application/services/auth_service.py:43-47` | `pwd_context.hash()` and `pwd_context.verify()` are CPU-intensive synchronous calls that block the event loop |
| 2 | No retry logic | MEDIUM | `infrastructure/remnawave/client.py:21-43` | HTTP requests fail permanently on transient errors |
| 3 | Silent exception swallowing | LOW | `infrastructure/messaging/websocket_manager.py:35` | Broadcast catches `Exception` silently |

**Fix for #1:**
```python
import asyncio
async def hash_password(password: str) -> str:
    return await asyncio.to_thread(pwd_context.hash, password)
```

---

## 4. Dependency Injection

### Good DI Patterns

```python
# Database session — src/presentation/dependencies/database.py
async def get_db() -> AsyncGenerator[AsyncSession, None]: ...

# Auth guard — src/presentation/dependencies/roles.py:23
def require_permission(permission: Permission):
    async def checker(user = Depends(get_current_active_user)):
        if not has_permission(AdminRole(user.role), permission):
            raise HTTPException(403, ...)
        return user
    return checker

# Usage in routes
_: None = Depends(require_permission(Permission.USER_CREATE))
```

### Anti-Patterns Found

| # | Issue | Severity | File:Line | Description |
|---|-------|----------|-----------|-------------|
| 1 | Global singleton | **HIGH** | `presentation/dependencies/auth.py:14` | `auth_service = AuthService()` — hardcoded at module level |
| 2 | In-handler instantiation | **HIGH** | `presentation/api/v1/auth/routes.py:44` | `auth_service = AuthService()` created inside route |
| 3 | In-handler instantiation | **HIGH** | `presentation/api/v1/payments/routes.py:42` | `CryptoBotClient()` created inside route |
| 4 | Module singleton | **HIGH** | `infrastructure/remnawave/client.py:57` | `remnawave_client = RemnawaveClient()` |
| 5 | Repositories not injected | MEDIUM | All route files | Repos created manually: `AdminUserRepository(db)` |

**Fix pattern:**
```python
def get_auth_service() -> AuthService:
    return AuthService()

def get_crypto_client() -> CryptoBotClient:
    return CryptoBotClient()

# In routes:
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
): ...
```

---

## 5. Repository & Service Layer

### Repository Pattern — Excellent

No direct DB queries in route handlers. All data access goes through:

```
Route Handler → Use Case → Gateway/Repository → External API/Database
```

**Abstract base:**
```python
# src/domain/repositories/base.py
class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None: ...
    @abstractmethod
    async def create(self, entity: T) -> T: ...
```

**Gateway pattern for Remnawave:**
```python
# src/infrastructure/remnawave/user_gateway.py
class RemnawaveUserGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        data = await self._client.get(f"/api/users/{uuid}")
        return map_remnawave_user(data)  # Maps to domain entity
```

### Service Layer — Good

**Thin routes** — business logic in use cases:

```python
# src/presentation/api/v1/users/routes.py:88-137
async def create_user(request: CreateUserRequest, ...):
    gateway = RemnawaveUserGateway(client=client)
    use_case = CreateUserUseCase(gateway=gateway)
    dto = CreateUserDTO(...)
    user = await use_case.execute(dto=dto)
    return UserResponse(...)
```

**Use cases encapsulate business rules:**

```python
# src/application/use_cases/auth/login.py
class LoginUseCase:
    async def execute(self, login_or_email: str, password: str) -> dict:
        user = await self._user_repo.get_by_login_or_email(login_or_email)
        if not user or not user.is_active:
            raise InvalidCredentialsError()
        if not self._auth_service.verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        # Token generation, refresh token storage...
```

---

## 6. Pydantic Schemas

### v2 Adoption — Complete

All 65+ schema classes use Pydantic v2 patterns:

```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # v2 syntax
    uuid: UUID
    username: str
    status: UserStatus  # StrEnum
```

### Validation Depth

| Feature | Count | Examples |
|---------|-------|---------|
| `min_length` / `max_length` | 42+ fields | All string fields constrained |
| `ge` / `le` / `gt` | 14+ fields | Ports, amounts, limits |
| `pattern` (regex) | 2 fields | Login, 2FA code |
| `EmailStr` | 3 fields | Registration, user schemas |
| `UUID` type | 8+ fields | Entity IDs |
| `@field_validator` | 6 validators | Password, address, currency, CORS |
| `Literal` types | 6 fields | Health status, 2FA, OAuth |
| `StrEnum` types | 5 fields | UserStatus, ServerStatus, etc. |
| `json_schema_extra` | 16 schemas | OpenAPI examples |

### Response Schema Coverage

| Category | Routes | With response_model | With responses={} | Untyped |
|----------|--------|--------------------|--------------------|---------|
| Auth | 5 | 4 | 0 | 1 |
| Users | 5 | 4 | 0 | 1 (204) |
| Servers | 6 | 5 | 0 | 1 (204) |
| Payments | 3 | 3 | 0 | 0 |
| Monitoring | 3 | 1 | 2 | 0 |
| 2FA | 4 | 4 | 0 | 0 |
| OAuth | 5 | 5 | 0 | 0 |
| Admin | 2 | 2 | 0 | 0 |
| Telegram | 3 | 2 | 0 | 1 |
| Proxy (11 modules) | 35 | 0 | 35 | 0 |
| Webhooks | 2 | 0 | 0 | 2 |
| **Total** | **73** | **30** | **37** | **6** |

**Coverage: 92% documented** (67/73 routes have typed response schemas or responses={}).

---

## 7. Error Handling

### Domain Exception Hierarchy

```python
# src/domain/exceptions/domain_errors.py
class DomainError(Exception):
    def __init__(self, message: str, details: dict | None = None): ...

class UserNotFoundError(DomainError): ...
class InvalidCredentialsError(DomainError): ...
class InvalidTokenError(DomainError): ...
class TrafficLimitExceededError(DomainError): ...
class SubscriptionExpiredError(DomainError): ...
```

### Global Handlers

```python
# src/presentation/exception_handlers.py — RequestValidationError handler
# src/main.py — registered via app.add_exception_handler()
```

### Issues Found

| # | Issue | Severity | File Pattern | Description |
|---|-------|----------|-------------|-------------|
| 1 | Information leakage | **CRITICAL** | All route files | `detail=f"Failed to list users: {str(e)}"` exposes internal errors to clients |
| 2 | No global domain handler | **HIGH** | `main.py` | `DomainError` subclasses not caught globally — each route has try/except |
| 3 | Catch-all exceptions | **HIGH** | 19 route files | `except Exception as e` catches too broadly |
| 4 | Error format inconsistency | MEDIUM | Routes vs exception_handlers | Routes return `{"detail": "string"}`, validation handler returns `{"detail": [objects]}` |

**Fix for #1 and #2:**
```python
# Add to exception_handlers.py
from src.domain.exceptions import DomainError, UserNotFoundError, InvalidCredentialsError

@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": exc.message})

@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request, exc):
    return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

@app.exception_handler(DomainError)
async def domain_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": exc.message})

@app.exception_handler(Exception)
async def generic_error_handler(request, exc):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

---

## 8. Security

### Authentication

| Aspect | Implementation | Grade |
|--------|---------------|-------|
| JWT tokens | `python-jose` with HS256 | **Good** |
| Token types | `access` + `refresh` discriminated | **Good** |
| Token expiry | 15 min access / 7 day refresh | **Good** |
| Refresh token storage | SHA256 hash in DB | **Excellent** |
| Password hashing | bcrypt 12 rounds via `passlib` | **Good** |
| Permission system | Role-based + fine-grained permissions | **Excellent** |
| WebSocket auth | JWT via query param (added) | **Good** |

### Input Validation

| Aspect | Status | Notes |
|--------|--------|-------|
| Pydantic schemas on all POST/PUT | **88%** | 21/24 routes |
| String length limits | **Complete** | All string fields constrained |
| Numeric bounds | **Good** | Ports, amounts, limits validated |
| SQL injection prevention | **Excellent** | SQLAlchemy ORM exclusively |
| XSS prevention | **Good** | JSON API, no HTML rendering |

### Webhook Security

```python
# src/infrastructure/payments/cryptobot/webhook_handler.py:12-16
def validate_signature(self, body: bytes, signature: str) -> bool:
    computed = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)  # Timing-attack resistant
```

### Issues Found

| # | Issue | Severity | File:Line | Description |
|---|-------|----------|-----------|-------------|
| 1 | CORS wildcard methods/headers | MEDIUM | `main.py:100-101` | `allow_methods=["*"]`, `allow_headers=["*"]` |
| 2 | HS256 algorithm | LOW | `config/settings.py:21` | HS512 or RS256 preferred for production |
| 3 | Hardcoded DB credentials in default | MEDIUM | `config/settings.py:8` | Default URL contains `cybervpn:cybervpn` |
| 4 | No rate limiting on login | MEDIUM | `auth/routes.py` | Brute-force protection absent at route level |

---

## 9. Testing

### Current State

| Metric | Value |
|--------|-------|
| Test files | 5 |
| Test functions | 35 |
| Estimated coverage | **<5%** |
| Unit tests | 31 (domain entities + auth service + permissions) |
| Integration tests | 2 (health check + unauthenticated access) |
| E2E tests | 2 (critical flows) |

### Test Infrastructure

```python
# tests/conftest.py — Good async test setup
@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
```

### Missing Tests

| Category | Missing | Priority |
|----------|---------|----------|
| Auth flow (login/register/refresh/logout) | 4+ tests | **CRITICAL** |
| User CRUD operations | 5+ tests | **CRITICAL** |
| Payment processing | 3+ tests | **HIGH** |
| Middleware (auth, logging) | 3+ tests | **HIGH** |
| WebSocket connections | 2+ tests | MEDIUM |
| Proxy routes (Remnawave) | 35+ tests | MEDIUM |
| Error handling paths | 10+ tests | HIGH |
| Permission system integration | 5+ tests | HIGH |
| Database repository operations | 5+ tests | **CRITICAL** |

### Missing Test Infrastructure

- No `pytest-cov` for coverage reporting
- No mock factories for `RemnawaveClient`, `CryptoBotClient`
- No database test fixtures (test DB setup/teardown)
- No CI/CD test pipeline

---

## 10. Database

### Session Management — Good

- Async engine with connection pooling (`pool_size=10`, `max_overflow=20`)
- `pool_pre_ping=True` for health checks
- SQLAlchemy 2.0 syntax (`Mapped`, `mapped_column`)
- Timezone-aware datetimes with `server_default=func.now()`

### Models

| Model | Table | Purpose |
|-------|-------|---------|
| `AdminUserModel` | `admin_users` | Dashboard authentication |
| `RefreshToken` | `refresh_tokens` | JWT refresh token storage |
| `PaymentModel` | `payments` | Payment tracking |
| `AuditLog` | `audit_logs` | Activity logging |
| `WebhookLog` | `webhook_logs` | Webhook event tracking |
| `OAuthAccount` | `oauth_accounts` | Social auth linking |
| `NotificationQueue` | `notification_queue` | Async notifications |
| `ServerGeolocation` | `server_geolocations` | Server location data |

### Issues

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | No Alembic migrations | **CRITICAL** | `alembic` is a dependency but not configured. No `alembic/` directory, no `alembic.ini` |
| 2 | No core entity models | MEDIUM | User, Server, Subscription only exist in Remnawave (single point of failure) |
| 3 | `flush()` vs `commit()` ambiguity | LOW | Repositories use `flush()`, session dependency uses `commit()` — correct but non-obvious |

---

## 11. Middleware

### Current Stack

```python
# src/main.py — Order: last added = first executed
app.add_middleware(CORSMiddleware, ...)   # Executes 3rd
app.add_middleware(AuthMiddleware)        # Executes 2nd
app.add_middleware(LoggingMiddleware)     # Executes 1st
```

**Execution order**: Logging → Auth → CORS → Route

### Issues

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | CORS should execute first | MEDIUM | Preflight requests may fail because Auth middleware runs before CORS |
| 2 | Rate limiting not enabled | **HIGH** | `RateLimitMiddleware` exists but is NOT added to `main.py` |
| 3 | No request ID tracking | MEDIUM | No correlation ID for distributed tracing |
| 4 | Basic logging | LOW | No structured JSON logging, no user ID in logs |

**Fix for #1** (swap add order so CORS runs first):
```python
app.add_middleware(LoggingMiddleware)     # Executes 1st
app.add_middleware(AuthMiddleware)        # Executes 2nd
app.add_middleware(CORSMiddleware, ...)   # Executes 3rd (last added = first exec)
```

Wait — actually FastAPI's CORS middleware is added last but needs to run first. The current order IS correct for ASGI: last added = first executed. So `LoggingMiddleware` (added last) runs first, then `AuthMiddleware`, then `CORSMiddleware`. But CORS should run BEFORE auth to handle preflight OPTIONS requests.

**Correct fix:**
```python
# CORS must be last added so it executes FIRST
app.add_middleware(AuthMiddleware)        # Executes 2nd
app.add_middleware(LoggingMiddleware)     # Executes 3rd
app.add_middleware(CORSMiddleware, ...)   # Executes 1st (last added)
```

---

## 12. Configuration

### Settings — Good

```python
# src/config/settings.py
class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    database_url: str = "postgresql+asyncpg://..."
    redis_url: str = "redis://localhost:6379/0"
    remnawave_url: str = "http://localhost:3000"
    remnawave_token: SecretStr       # Required
    jwt_secret: SecretStr            # Required
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = [...]
```

### Issues

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | Missing `cryptobot_token` | MEDIUM | Referenced in code but not in Settings |
| 2 | Missing `environment` flag | MEDIUM | No dev/staging/prod differentiation |
| 3 | Missing `log_level` | LOW | Logging not configurable |
| 4 | Hardcoded DB credentials in default | MEDIUM | `cybervpn:cybervpn` in default URL |
| 5 | No `.env.example` | LOW | New developers have no template |

---

## 13. Domain Layer

### Value Objects — Excellent

| Value Object | File | Validation |
|-------------|------|------------|
| `Email` | `domain/value_objects/email.py` | Regex pattern, immutable, slots |
| `Money` | `domain/value_objects/money.py` | Currency whitelist, non-negative |
| `Traffic` | `domain/value_objects/traffic.py` | Non-negative, unit conversion (KB/MB/GB) |
| `Geolocation` | `domain/value_objects/geolocation.py` | Lat -90..90, Lng -180..180 |

### Domain Entities

```python
# src/domain/entities/server.py — Rich domain model
@dataclass(frozen=True)
class Server:
    @property
    def status(self) -> ServerStatus:
        if self.is_disabled: return ServerStatus.MAINTENANCE
        if self.is_connecting: return ServerStatus.WARNING
        if self.is_connected: return ServerStatus.ONLINE
        return ServerStatus.OFFLINE
```

### Issue: Anemic Domain Models

Most entities (User, Payment) are pure data holders. Business logic lives in use cases, not entities. This is a design choice (transaction script vs. rich domain model) — acceptable for a proxy-heavy application but limits domain expressiveness.

---

## 14. Scoring

| Category | Score | Max | Notes |
|----------|-------|-----|-------|
| Project Structure | 9 | 10 | Clean Architecture + DDD, missing migrations dir |
| Async Patterns | 8 | 10 | All async, blocking bcrypt issue |
| Dependency Injection | 5 | 10 | Module singletons, in-handler instantiation |
| Repository/Gateway | 9 | 10 | Excellent separation, gateway + mapper pattern |
| Service/Use Case Layer | 9 | 10 | Thin routes, business logic in use cases |
| Pydantic Schemas | 9 | 10 | v2, validators, Literal types, 65+ schemas |
| Error Handling | 4 | 10 | Info leakage, no global domain handler |
| Security | 7 | 10 | JWT + bcrypt solid; CORS, rate limit gaps |
| Testing | 1 | 10 | <5% coverage, minimal tests |
| Database | 6 | 10 | Good session mgmt, no migrations |
| Middleware | 5 | 10 | Ordering issue, rate limit disabled |
| Configuration | 6 | 10 | Good base, missing keys and env differentiation |

**Overall Score: 65/100**

---

## 15. Fix Priority

| # | Issue | Effort | Impact | Priority |
|---|-------|--------|--------|----------|
| 1 | Implement Alembic database migrations | Medium | Cannot evolve schema safely | **P0** |
| 2 | Build test suite to 70%+ coverage | High | No confidence in correctness | **P0** |
| 3 | Fix error handling info leakage | Medium | Security vulnerability | **P1** |
| 4 | Add global domain exception handlers | Low | Remove try/except boilerplate from routes | **P1** |
| 5 | Make bcrypt hashing async-safe | Low | Event loop blocking under load | **P1** |
| 6 | Refactor DI anti-patterns | Medium | Testability, SOLID compliance | **P1** |
| 7 | Enable rate limiting middleware | Low | Brute-force protection | **P2** |
| 8 | Fix middleware ordering (CORS first) | Low | Preflight failures | **P2** |
| 9 | Add missing config keys | Low | Runtime errors on payment paths | **P2** |
| 10 | Add retry logic to HTTP clients | Medium | Resilience against transient failures | **P2** |
| 11 | Add structured JSON logging | Medium | Observability | **P3** |
| 12 | Add request ID correlation | Medium | Distributed tracing | **P3** |
| 13 | Add `.env.example` template | Low | Developer onboarding | **P3** |
| 14 | Enrich domain entities with behavior | Medium | Domain expressiveness | **P4** |

---

## 16. Production Readiness Checklist

### Must Have (blocking deployment)

- [ ] Configure Alembic migrations
- [ ] Achieve 70%+ test coverage
- [ ] Fix all error message information leakage
- [ ] Add global domain exception handlers
- [ ] Fix bcrypt blocking in async context
- [ ] Enable rate limiting
- [ ] Add missing settings (`cryptobot_token`, `environment`)

### Should Have (deploy with caveats)

- [ ] Refactor DI to proper factory pattern
- [ ] Fix middleware ordering
- [ ] Add structured logging
- [ ] Add request ID tracking
- [ ] Add HTTP retry logic
- [ ] Add `.env.example`
- [ ] Increase connection pool sizes for production

### Nice to Have

- [ ] OpenTelemetry tracing
- [ ] Circuit breakers for Remnawave
- [ ] Database query monitoring
- [ ] Local caching of Remnawave responses
- [ ] Enrich domain models
- [ ] GraphQL API layer

---

## 17. Comparison with Previous Analyses

| Metric | Validation Analysis (prev) | Contract Analysis (prev) | This Report |
|--------|---------------------------|-------------------------|-------------|
| Focus | Request validation | API contracts + OpenAPI | Full best practices |
| Schema classes | 42 → 65 | 42 | 65+ |
| Request coverage | 88% | 88% | 88% |
| Response coverage | 26% | 26% → 92% | 92% |
| Error handling | Global handler added | Per-route errors added | Info leakage found |
| Testing | Not analyzed | Not analyzed | **<5% coverage** |
| Database | Not analyzed | Not analyzed | **No migrations** |
| DI quality | Not analyzed | Not analyzed | **Inconsistent** |
| Security | Not analyzed | Not analyzed | **Mostly solid** |

**Key new findings not covered in previous reports:**
1. Blocking bcrypt in async context
2. DI anti-patterns (module singletons)
3. Test coverage crisis (<5%)
4. Missing Alembic migrations
5. Middleware ordering issue
6. Rate limiting not enabled
7. Error information leakage in all routes
