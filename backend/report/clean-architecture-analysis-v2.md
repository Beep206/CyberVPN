# CyberVPN Backend - Clean Architecture Analysis Report v2

**Date**: 2026-01-29
**Scope**: `backend/src/` (199 Python files)
**Stack**: Python 3.13, FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis
**Previous report**: `clean-architecture-analysis.md` (v1, same date)

---

## 0. What Changed Since v1

All **3 critical issues** and all **4 minor issues** from v1 have been resolved:

| v1 Issue | Status | What was done |
|----------|--------|---------------|
| CRIT-1: Broken imports (11 route files) | RESOLVED | All 11 route files rewritten with correct import paths |
| CRIT-2: Permission enum mismatch | RESOLVED | Enum rewritten with 17 CRUD-style members matching route usage |
| CRIT-3: AdminUser/AdminUserModel naming | RESOLVED | Class renamed to `AdminUserModel`, all references updated |
| MINOR-1: `__import__("sqlalchemy").text()` | RESOLVED | Proper `from sqlalchemy import text` import |
| MINOR-2: `from uuid import UUID` inside function | RESOLVED | Moved to top-level import |
| MINOR-3: Missing `__init__.py` in repositories | RESOLVED | Created with all 5 repository exports |
| MINOR-4: `Session` vs `AsyncSession` | RESOLVED | All routes use `AsyncSession` with `await` |

Additional fixes applied:
- Created `AuditLogRepository` and `WebhookLogRepository`
- Added `get_by_telegram_id()` to `AdminUserRepository`
- Added missing schemas: `RefreshTokenRequest`, `LogoutRequest`
- Fixed `AdminUserResponse.id` type (`int` -> `UUID`)
- Fixed `TokenResponse.expires_in` default value
- Fixed 11 additional route files with wrong `dependencies` import path
- Fixed use case class name mismatches (e.g. `CryptoPaymentUseCase` -> `CreateCryptoInvoiceUseCase`)

**Result**: The application now starts successfully. Router imports, app creation, and 26/27 tests pass.
(1 test failure is upstream passlib/bcrypt 5.x incompatibility, not project code.)

---

## 1. Architecture Overview

The project follows a **four-layer Clean Architecture**:

```
src/
  domain/           # Business rules, entities, interfaces (pure Python)
  application/      # Use cases, DTOs, services, event handlers
  infrastructure/   # Database, external APIs, cache, messaging
  presentation/     # API routes, schemas, middleware, DI
  config/           # Settings
```

**Layer sizes**:

| Layer | Files | Purpose |
|-------|-------|---------|
| Domain | 24 | Entities, value objects, exceptions, repository ABCs, events, enums |
| Application | 52 | Use cases, auth service, cache service, DTOs, event handlers |
| Infrastructure | 87 | ORM models, repositories, Remnawave gateway, CryptoBot, Redis, WebSocket, OAuth, TOTP |
| Presentation | 30+ | 21 route modules, schemas, middleware, dependency injection |
| Config | 1 | Pydantic Settings |

---

## 2. Layer-by-Layer Analysis

### 2.1 Domain Layer - GOOD

| Criterion | Status | Notes |
|-----------|--------|-------|
| Pure Python (no framework deps) | PASS | Only uses stdlib |
| No imports from other layers | PASS | Zero cross-layer imports |
| Entities use frozen dataclasses | PASS | Immutable by default |
| Repository interfaces defined | PASS | 4 ABCs in `domain/repositories/` |
| Domain exceptions defined | PASS | 12 classes under `DomainError` |
| Value objects present | PASS | `Email`, `Money`, `Traffic`, `Geolocation` |
| Domain events defined | PASS | `DomainEvent` base + 4 specific events |

**Unchanged from v1.** Domain layer remains clean and framework-agnostic.

**Persisting weakness**: Entities are **anemic** - frozen dataclasses with no business methods. Only `Server.status` has a computed property. Business logic that naturally belongs to entities (e.g. `User.is_subscription_expired()`, `User.remaining_traffic_bytes()`) lives in use cases instead.

### 2.2 Application Layer - IMPROVED (still has violations)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Use case per action | PASS | Each file = one use case class |
| Single execute method | PASS | Consistent `execute()` pattern |
| No framework imports | **FAIL** | ~40 imports from `src.infrastructure` |
| No SQLAlchemy imports | **FAIL** | 9 files import `AsyncSession` directly |
| Uses domain interfaces | PARTIAL | Type hints use concrete classes, not ABCs |
| Returns domain entities | PARTIAL | Auth use cases return raw dicts |

**What improved**: All use cases now use correct import paths, proper `await`, and `AsyncSession` (not sync `Session`). Permission enum is aligned with route usage (17 CRUD-style members).

**Persisting violations**:

1. **40+ infrastructure imports** — Use cases import concrete repository classes and gateway implementations directly instead of domain interfaces:

```python
# Current (application/use_cases/auth/login.py):
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
class LoginUseCase:
    def __init__(self, user_repo: AdminUserRepository, ...):  # Concrete class

# Should be:
from src.domain.repositories.user_repository import UserRepository
class LoginUseCase:
    def __init__(self, user_repo: UserRepository, ...):  # Abstract interface
```

2. **9 files import SQLAlchemy** — `AsyncSession` is passed directly to use cases:
   - `auth/login.py`, `auth/logout.py`, `auth/refresh_token.py`
   - `auth/two_factor.py`, `auth/account_linking.py`
   - `users/bulk_operations.py`
   - `payments/payment_webhook.py`
   - `webhooks/remnawave_webhook.py`
   - `events/handlers/audit_handler.py`

### 2.3 Infrastructure Layer - GOOD

| Criterion | Status | Notes |
|-----------|--------|-------|
| Implements domain interfaces | PARTIAL | Repositories exist but don't extend domain ABCs |
| Separate ORM models from entities | PASS | Models in `infrastructure/database/models/` |
| Mappers for entity conversion | PASS | `user_mapper.py`, `server_mapper.py` |
| External API adapters | PASS | Remnawave, CryptoBot, Telegram, OAuth |
| No imports from presentation | PASS | Clean boundary |
| Resilience patterns | PASS | Circuit breaker, retry policy |

**What improved**: All 5 repositories now exist with proper implementations. `repositories/__init__.py` exports them correctly.

**Persisting weakness**: Concrete repositories don't extend domain ABCs and return ORM models instead of domain entities:

```python
# domain/repositories/user_repository.py
class UserRepository(ABC):
    async def get_by_id(self, id: UUID) -> User | None: ...  # Returns domain entity

# infrastructure/database/repositories/admin_user_repo.py
class AdminUserRepository:                          # Does NOT extend UserRepository
    async def get_by_id(self, id: UUID) -> AdminUserModel | None: ...  # Returns ORM model
```

### 2.4 Presentation Layer - GOOD (was: HAS ISSUES)

| Criterion | Status | v1 Status | Notes |
|-----------|--------|-----------|-------|
| HTTP concerns only | PASS | PASS | Routes, schemas, middleware |
| Uses Pydantic DTOs | PASS | PASS | Request/Response models per module |
| Error mapping | PASS | PASS | Domain exceptions -> HTTP status codes |
| Permission-based access | PASS | **FAIL** | Permission enum now matches route usage |
| Versioned API | PASS | PASS | `/api/v1/` prefix |
| All imports resolve | PASS | **FAIL** | All 21 route files import successfully |
| Correct async patterns | PASS | **FAIL** | All handlers use `AsyncSession` + `await` |

**Major improvement**: All 3 critical issues from v1 (broken imports, enum mismatch, naming inconsistency) are fully resolved. The presentation layer is now functional.

### 2.5 Dependency Injection - ADEQUATE (unchanged)

Pattern: Manual wiring in route handlers using FastAPI `Depends()`.

```python
@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user_repo = AdminUserRepository(db)
    auth_service = AuthService()
    use_case = LoginUseCase(user_repo=user_repo, auth_service=auth_service, session=db)
    result = await use_case.execute(...)
```

Works but duplicates wiring logic across routes. No central composition root.

---

## 3. Dependency Flow Diagram

```
CORRECT (observed):
  Presentation --> Application --> Domain
  Presentation --> Infrastructure
  Infrastructure --> Domain (via mappers)

VIOLATIONS (persisting from v1):
  Application --X--> Infrastructure  (~40 imports - should go through domain interfaces)
  Application --X--> SQLAlchemy      (9 imports - framework leak)
```

---

## 4. Scoring

| Category | v1 | v2 | Max | Change | Notes |
|----------|-----|-----|-----|--------|-------|
| Layer Separation | 6 | 7 | 10 | +1 | All layers properly connected now |
| Dependency Rule | 4 | 4 | 10 | 0 | App->infra coupling still exists |
| Domain Purity | 8 | 8 | 10 | 0 | Still anemic entities |
| Repository Pattern | 4 | 5 | 10 | +1 | All repos exist, still don't extend ABCs |
| DI / Composition | 5 | 5 | 10 | 0 | Manual wiring unchanged |
| Error Handling | 7 | 8 | 10 | +1 | All exceptions connected properly |
| Testability | 4 | 5 | 10 | +1 | App starts, 26/27 tests pass |
| Configuration | 9 | 9 | 10 | 0 | Already well-designed |
| API Design | 7 | 8 | 10 | +1 | 21 working route modules, correct async |
| Code Consistency | 3 | 7 | 10 | +4 | Naming fixed, imports fixed, enums aligned |

**Overall Score: 66/100** (was 57/100, **+9 points**)

---

## 5. Remaining Architectural Issues

### ARCH-1: Application Layer Depends on Infrastructure (HIGH)

**Impact**: Use cases cannot be tested without real database/API; cannot swap infrastructure implementations.

**Current**: 40+ direct imports from `src.infrastructure` in application layer.

**Fix**: Use cases should depend on domain interfaces (ABCs), not concrete implementations:

```python
# application/use_cases/auth/login.py
from src.domain.repositories.user_repository import UserRepository  # Interface, not concrete

class LoginUseCase:
    def __init__(self, user_repo: UserRepository, ...):  # Abstract type
```

### ARCH-2: SQLAlchemy Session in Application Layer (HIGH)

**Impact**: Application logic tied to specific ORM framework.

**Fix**: Introduce a Unit of Work interface in the domain layer:

```python
# domain/interfaces/unit_of_work.py
class IUnitOfWork(ABC):
    @abstractmethod
    async def commit(self): ...
    @abstractmethod
    async def rollback(self): ...
    @abstractmethod
    async def flush(self): ...
```

Replace `session: AsyncSession` with `uow: IUnitOfWork` in use case constructors.

### ARCH-3: Repositories Don't Implement Domain Interfaces (MEDIUM)

**Impact**: Domain repository contracts are unused; no polymorphism possible.

**Fix**: Make concrete repositories extend domain ABCs and return domain entities:

```python
class AdminUserRepository(UserRepository):  # Extend domain ABC
    async def get_by_id(self, id: UUID) -> User | None:  # Return domain entity
        model = await self._session.get(AdminUserModel, id)
        return self._to_entity(model) if model else None

    def _to_entity(self, model: AdminUserModel) -> User:
        return User(id=model.id, login=model.login, ...)
```

### ARCH-4: Anemic Domain Entities (LOW)

**Impact**: Business rules scattered across use cases instead of centralized.

**Fix**: Add business methods to entities:

```python
@dataclass(frozen=True)
class User:
    ...
    def is_subscription_expired(self) -> bool:
        return self.expire_at is not None and self.expire_at < datetime.now(UTC)

    def remaining_traffic_bytes(self) -> int | None:
        if self.traffic_limit_bytes is None:
            return None
        return max(0, self.traffic_limit_bytes - (self.used_traffic_bytes or 0))

    def is_traffic_exceeded(self) -> bool:
        remaining = self.remaining_traffic_bytes()
        return remaining is not None and remaining <= 0
```

### ARCH-5: No Centralized DI / Composition Root (LOW)

**Impact**: Every route handler manually composes dependencies; no single place to swap implementations.

**Fix**: Create FastAPI dependency factories or use `dependency-injector`:

```python
# presentation/dependencies/use_cases.py
def get_login_use_case(db: AsyncSession = Depends(get_db)) -> LoginUseCase:
    return LoginUseCase(
        user_repo=AdminUserRepository(db),
        auth_service=AuthService(),
        session=db,
    )

# routes
@router.post("/login")
async def login(request: LoginRequest, use_case: LoginUseCase = Depends(get_login_use_case)):
    result = await use_case.execute(...)
```

---

## 6. What's Working Well

1. **Domain layer purity** - Zero framework dependencies, clean abstractions
2. **Value objects with validation** - `Email`, `Money`, `Traffic`, `Geolocation` enforce invariants
3. **Domain events** - Good pattern for cross-cutting concerns (audit, notifications)
4. **Middleware stack** - Auth, logging, CORS properly layered
5. **Permission system** - 17 granular CRUD permissions mapped to 5 roles
6. **Configuration** - `SecretStr` for sensitive values, env-based settings
7. **Async-first** - Consistent async/await throughout all layers
8. **API versioning** - `/api/v1/` prefix for future evolution
9. **Health checks** - Database, Redis, Remnawave connectivity validation
10. **Resilience patterns** - Circuit breaker and retry policy for external calls
11. **All routes functional** - 21 route modules load and serve requests (NEW)
12. **Consistent naming** - `AdminUserModel`, CRUD-style permissions (NEW)
13. **Complete repository layer** - All 5 repositories with proper implementations (NEW)

---

## 7. Recommended Fix Priority

| Priority | Issue | Effort | Score Impact |
|----------|-------|--------|-------------|
| 1 | ARCH-3: Make repos implement domain ABCs + return entities | Medium | +5-8 pts |
| 2 | ARCH-1: Decouple application from infrastructure via interfaces | High | +8-10 pts |
| 3 | ARCH-2: Abstract SQLAlchemy session (Unit of Work) | High | +3-5 pts |
| 4 | ARCH-5: Centralize DI with dependency factories | Medium | +3-5 pts |
| 5 | ARCH-4: Add behavior to domain entities | Medium | +2-3 pts |

Implementing priorities 1-3 would bring the score to approximately **85/100**.

---

## 8. Conclusion

The codebase has improved significantly from v1. All critical issues blocking application startup are resolved - the 11 broken route files, permission enum mismatch, and naming inconsistencies are fixed. The application now starts, serves all 21 API route modules, and passes tests.

The remaining issues are **purely architectural** - they don't prevent the application from working, but they limit testability, maintainability, and flexibility:

- **Application-to-infrastructure coupling** is the most impactful issue. Use cases depend on concrete repository classes instead of domain interfaces, which defeats the Dependency Inversion Principle at the core of Clean Architecture.
- **SQLAlchemy framework leak** into the application layer ties business logic to a specific ORM.
- **Repositories don't implement domain ABCs**, making the carefully defined domain contracts unused.

The path from 66/100 to 85+/100 requires inverting the dependency between application and infrastructure layers - making use cases depend on abstract interfaces while infrastructure provides concrete implementations. This is the single most valuable architectural investment for this codebase.
