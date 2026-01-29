# CyberVPN Backend - Clean Architecture Analysis Report

**Date**: 2026-01-29
**Scope**: `backend/src/` (197 Python files)
**Stack**: Python 3.13, FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis

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

**Verdict**: The layer structure is well-defined and mostly follows Clean Architecture conventions. However, there are **significant dependency rule violations** at the application layer that undermine the architecture's core benefit.

---

## 2. Layer-by-Layer Analysis

### 2.1 Domain Layer - GOOD

| Criterion | Status | Notes |
|-----------|--------|-------|
| Pure Python (no framework deps) | PASS | Only uses stdlib `dataclasses`, `enum`, `abc`, `uuid`, `datetime` |
| No imports from other layers | PASS | Zero imports from `application`, `infrastructure`, or `presentation` |
| No SQLAlchemy imports | PASS | Clean separation from ORM |
| Entities use frozen dataclasses | PASS | Immutable by default |
| Repository interfaces defined | PASS | ABCs in `domain/repositories/` |
| Domain exceptions defined | PASS | Hierarchy under `DomainError` |
| Value objects present | PASS | `Email`, `Money`, `Traffic`, `Geolocation` with validation |
| Domain events defined | PASS | `DomainEvent` base + specific events |

**Strengths**:
- Domain is completely framework-agnostic
- Entities are frozen dataclasses with `__slots__` on value objects
- Clear exception hierarchy with structured `details` dict
- Repository ABCs define clean contracts

**Weaknesses**:
- Entities are **anemic** - no business behavior methods, only data holders
- No domain services to encapsulate complex business rules
- `User` entity (VPN user from Remnawave) has no business methods despite having rich status logic
- The `Server.status` computed property in the entity is a good start, but is the only example

### 2.2 Application Layer - HAS VIOLATIONS

| Criterion | Status | Notes |
|-----------|--------|-------|
| Use case per action | PASS | Each file = one use case class |
| Single execute method | PASS | Consistent `execute()` / `execute_*()` pattern |
| No framework imports | **FAIL** | **37 imports from `src.infrastructure`** |
| No SQLAlchemy imports | **FAIL** | **11 files import `sqlalchemy`** directly |
| Uses domain interfaces | PARTIAL | Some use cases use domain repos, many use infra directly |
| Returns domain entities | PARTIAL | Auth use cases return raw dicts instead of typed DTOs |

**Critical Violation - Application imports Infrastructure**:

The application layer has **37 direct imports** from `src.infrastructure`:

```
application/use_cases/auth/login.py      -> infrastructure/database/models/admin_user_model
application/use_cases/auth/login.py      -> infrastructure/database/models/refresh_token_model
application/use_cases/auth/login.py      -> infrastructure/database/repositories/admin_user_repo
application/use_cases/auth/register.py   -> infrastructure/database/models/admin_user_model
application/use_cases/auth/register.py   -> infrastructure/database/repositories/admin_user_repo
application/use_cases/users/create_user.py -> infrastructure/remnawave/user_gateway
application/events/handlers/audit_handler.py -> infrastructure/database/models/audit_log_model
application/use_cases/webhooks/*         -> infrastructure/messaging/websocket_manager
... (29 more)
```

This means **use cases are tightly coupled to specific infrastructure implementations**. If you swap PostgreSQL for MongoDB, or Remnawave for another VPN panel, you must rewrite the use cases.

**Critical Violation - SQLAlchemy in Application Layer**:

11 application files import `sqlalchemy.ext.asyncio.AsyncSession` directly:

```python
# application/use_cases/auth/login.py
from sqlalchemy.ext.asyncio import AsyncSession  # Framework leak!

class LoginUseCase:
    def __init__(self, ..., session: AsyncSession):  # ORM coupling!
        self._session = session
```

The application layer should not know about SQLAlchemy sessions. This is a Unit of Work concern that should be abstracted.

### 2.3 Infrastructure Layer - GOOD

| Criterion | Status | Notes |
|-----------|--------|-------|
| Implements domain interfaces | PARTIAL | `AdminUserRepository` exists but doesn't extend domain ABC |
| Separate ORM models from entities | PASS | Models in `infrastructure/database/models/` |
| Mappers for entity conversion | PASS | `user_mapper.py`, `server_mapper.py` |
| External API adapters | PASS | Remnawave, CryptoBot, Telegram, OAuth |
| No imports from presentation | PASS | Clean boundary |
| Resilience patterns | PASS | Circuit breaker, retry policy |

**Weakness - Repository doesn't implement domain interface**:

```python
# domain/repositories/user_repository.py
class UserRepository(ABC):  # Interface exists
    async def get_by_id(self, id: UUID) -> User | None: ...

# infrastructure/database/repositories/admin_user_repo.py
class AdminUserRepository:  # Does NOT extend UserRepository ABC!
    async def get_by_id(self, id: UUID) -> AdminUserModel | None: ...
    #                                      ^^^^^^^^^^^^^^ Returns ORM model, not domain entity!
```

The concrete repository:
1. Does **not** inherit from the domain ABC
2. Returns **ORM models** instead of **domain entities**
3. Has a **different interface** (different method names, different return types)

This defeats the purpose of defining repository interfaces in the domain layer.

### 2.4 Presentation Layer - HAS ISSUES

| Criterion | Status | Notes |
|-----------|--------|-------|
| HTTP concerns only | PASS | Routes, schemas, middleware |
| Uses Pydantic DTOs | PASS | Request/Response models per module |
| Error mapping | PASS | Domain exceptions -> HTTP status codes |
| Permission-based access | PASS | `require_permission()` / `require_role()` |
| Versioned API | PASS | `/api/v1/` prefix |

**Issue - Broken Imports (non-existent modules)**:

13 route files import from paths that **do not exist**:

```
src/infrastructure/repositories/admin_user_repository  # Does not exist
src/infrastructure/repositories/server_repository      # Does not exist
src/infrastructure/repositories/payment_repository     # Does not exist
src/infrastructure/repositories/audit_log_repository   # Does not exist
src/infrastructure/repositories/webhook_log_repository # Does not exist
src/infrastructure/repositories/telegram_user_repository # Does not exist
src/infrastructure/security/password_hasher            # Does not exist
src/infrastructure/security/token_manager              # Does not exist
```

The actual repositories are at `src/infrastructure/database/repositories/`, not `src/infrastructure/repositories/`.

**Affected routes**: `auth/routes.py`, `auth/registration.py`, `users/routes.py`, `users/bulk.py`, `users/actions.py`, `servers/routes.py`, `monitoring/routes.py`, `payments/routes.py`, `webhooks/routes.py`, `admin/routes.py`, `telegram/routes.py`

These files will **crash at import time** with `ModuleNotFoundError`.

**Issue - Permission Enum Mismatch**:

Routes use permission names that don't exist in the `Permission` enum:

| Used in routes | Defined in `Permission` enum |
|---|---|
| `Permission.USER_CREATE` | Not defined |
| `Permission.USER_READ` | Not defined |
| `Permission.USER_UPDATE` | Not defined |
| `Permission.USER_DELETE` | Not defined |
| `Permission.SERVER_READ` | Not defined |
| `Permission.SERVER_CREATE` | Not defined |
| `Permission.SERVER_UPDATE` | Not defined |
| `Permission.SERVER_DELETE` | Not defined |
| `Permission.PAYMENT_CREATE` | Not defined |
| `Permission.PAYMENT_READ` | Not defined |
| `Permission.MONITORING_READ` | Not defined |
| `Permission.AUDIT_READ` | Not defined |
| `Permission.WEBHOOK_READ` | Not defined |
| `Permission.SUBSCRIPTION_CREATE` | Not defined |

Defined names: `READ_USERS`, `WRITE_USERS`, `DELETE_USERS`, `READ_SERVERS`, `WRITE_SERVERS`, `DELETE_SERVERS`, `MANAGE_PAYMENTS`, `VIEW_ANALYTICS`, `MANAGE_ADMINS`, `VIEW_AUDIT_LOG`, `VIEW_WEBHOOK_LOG`, `MANAGE_PLANS`

Routes will crash with `AttributeError` because these enum members don't exist.

**Issue - ORM Model Naming Inconsistency**:

The `AdminUser` ORM model class is called `AdminUser` in the model file, but some imports reference it as `AdminUserModel`:

```python
# admin_user_model.py
class AdminUser(Base):  # Named "AdminUser"

# Some files import it as:
from ...admin_user_model import AdminUserModel  # Will fail - class is "AdminUser"
```

Files importing `AdminUserModel` (non-existent name):
- `presentation/dependencies/auth.py`
- `presentation/dependencies/roles.py`
- `presentation/api/v1/two_factor/routes.py`
- `presentation/api/v1/oauth/routes.py`
- `application/use_cases/auth/two_factor.py`

### 2.5 Dependency Injection - ADEQUATE

| Criterion | Status | Notes |
|-----------|--------|-------|
| DI container | NO | No IoC container (no `dependency-injector`) |
| FastAPI Depends() | YES | Used for DB sessions, auth, roles |
| Constructor injection | PARTIAL | Use cases take deps in constructor, but wired manually in routes |

**Pattern used**: Manual wiring in route handlers:

```python
@router.post("/")
async def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    user_repo = AdminUserRepository(db)       # Manual instantiation
    use_case = CreateUserUseCase(user_repo)    # Manual wiring
    user = use_case.execute(...)
```

This works but:
- Every route handler manually creates repository + use case instances
- No central composition root for swapping implementations
- Makes testing routes harder (can't easily inject mocks)

---

## 3. Dependency Flow Diagram

```
CORRECT (observed):
  Presentation --> Application --> Domain
  Presentation --> Infrastructure
  Infrastructure --> Domain

VIOLATIONS (observed):
  Application --X--> Infrastructure  (37 imports - SHOULD go through domain interfaces)
  Application --X--> SQLAlchemy      (11 imports - framework leak)
```

---

## 4. Scoring

| Category | Score | Max | Details |
|----------|-------|-----|---------|
| Layer Separation | 6 | 10 | Good structure, but app->infra coupling |
| Dependency Rule | 4 | 10 | Domain is clean, but application violates heavily |
| Domain Purity | 8 | 10 | No framework deps, but anemic entities |
| Repository Pattern | 4 | 10 | Interfaces exist but aren't implemented |
| DI / Composition | 5 | 10 | FastAPI Depends works, no IoC container |
| Error Handling | 7 | 10 | Good hierarchy, proper HTTP mapping |
| Testability | 4 | 10 | Hard to test use cases without real infra |
| Configuration | 9 | 10 | Proper Pydantic settings with SecretStr |
| API Design | 7 | 10 | Good versioning, permissions, pagination |
| Code Consistency | 3 | 10 | Naming mismatches, broken imports |

**Overall Score: 57/100**

---

## 5. Critical Issues (Must Fix)

### CRIT-1: Broken Imports - Files Will Not Load

**Severity**: CRITICAL (application won't start)
**Files affected**: 11 route files
**Problem**: Imports reference `src.infrastructure.repositories.*` and `src.infrastructure.security.*` which don't exist
**Fix**: Update imports to use actual paths:
- `src.infrastructure.repositories.admin_user_repository` -> `src.infrastructure.database.repositories.admin_user_repo`
- `src.infrastructure.security.password_hasher` -> use `src.application.services.auth_service.AuthService`
- `src.infrastructure.security.token_manager` -> use `src.application.services.auth_service.AuthService`

### CRIT-2: Permission Enum Mismatch

**Severity**: CRITICAL (routes will crash on access)
**Files affected**: All routes using `require_permission()`
**Problem**: Routes use `Permission.USER_CREATE`, `Permission.SERVER_READ`, etc. but enum defines `Permission.READ_USERS`, `Permission.WRITE_USERS`, etc.
**Fix**: Either rename the enum members to match the routes, or update routes to use existing enum names.

### CRIT-3: ORM Model Class Name Inconsistency

**Severity**: HIGH (some imports will fail)
**Problem**: Class is `AdminUser` but 5+ files import `AdminUserModel`
**Fix**: Rename the class to `AdminUserModel` for consistency with other models (`PaymentModel`, `WebhookLog`, etc.), or fix all import references.

---

## 6. Architectural Issues (Should Fix)

### ARCH-1: Application Layer Depends on Infrastructure

**Severity**: HIGH
**Impact**: Use cases cannot be tested without real database/API; cannot swap infrastructure
**Fix**: Use cases should depend on domain interfaces (ABCs), not concrete implementations:

```python
# CURRENT (bad):
class LoginUseCase:
    def __init__(self, user_repo: AdminUserRepository, ...):  # Concrete class

# TARGET (good):
class LoginUseCase:
    def __init__(self, user_repo: IAdminUserRepository, ...):  # Abstract interface
```

### ARCH-2: SQLAlchemy Session in Application Layer

**Severity**: HIGH
**Impact**: Application logic tied to specific ORM
**Fix**: Introduce a Unit of Work interface in the domain layer:

```python
# domain/interfaces/unit_of_work.py
class IUnitOfWork(ABC):
    @abstractmethod
    async def commit(self): ...
    @abstractmethod
    async def rollback(self): ...
```

### ARCH-3: Repositories Don't Implement Domain Interfaces

**Severity**: MEDIUM
**Impact**: Domain repository contracts are unused; interface/implementation mismatch
**Fix**: Make `AdminUserRepository` extend `UserRepository` ABC and return domain entities:

```python
class AdminUserRepository(UserRepository):  # Extend domain ABC
    async def get_by_id(self, id: UUID) -> User | None:  # Return domain entity
        model = await self._session.get(AdminUserModel, id)
        return self._to_entity(model) if model else None
```

### ARCH-4: Anemic Domain Entities

**Severity**: LOW
**Impact**: Business rules scattered across use cases instead of centralized in entities
**Current**: Entities are pure data holders with no behavior
**Fix**: Add business methods to entities:

```python
@dataclass
class User:
    ...
    def is_subscription_expired(self) -> bool:
        return self.expire_at is not None and self.expire_at < datetime.now(UTC)

    def remaining_traffic_bytes(self) -> int | None:
        if self.traffic_limit_bytes is None:
            return None
        return max(0, self.traffic_limit_bytes - (self.used_traffic_bytes or 0))
```

---

## 7. Minor Issues

### MINOR-1: `sqlalchemy.text` imported via `__import__`

```python
# session.py:41
await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
```

Should be a normal import at the top of the file.

### MINOR-2: `from uuid import UUID` inside function body

```python
# presentation/dependencies/auth.py:30
from uuid import UUID  # Should be at top of file
user = await repo.get_by_id(UUID(user_id))
```

### MINOR-3: Missing `__init__.py` in some modules

Some API modules have `__init__.py`, others don't. Should be consistent.

### MINOR-4: `Session` vs `AsyncSession` in type hints

`users/routes.py` uses `from sqlalchemy.orm import Session` (sync) but the actual dependency provides `AsyncSession`. This will cause type checking errors.

---

## 8. What's Working Well

1. **Domain layer purity** - Zero framework dependencies, clean abstractions
2. **Value objects with validation** - `Email`, `Money`, `Traffic`, `Geolocation` enforce invariants
3. **Domain events** - Good pattern for cross-cutting concerns (audit, notifications)
4. **Middleware stack** - Auth, rate limiting, logging, CORS properly layered
5. **Permission system** - Role hierarchy with granular permissions
6. **Configuration** - `SecretStr` for sensitive values, env-based settings
7. **Async-first** - Consistent async/await throughout
8. **API versioning** - `/api/v1/` prefix for future evolution
9. **Health checks** - Database, Redis, Remnawave connectivity validation
10. **Resilience patterns** - Circuit breaker and retry policy for external calls

---

## 9. Recommended Fix Priority

| Priority | Issue | Effort |
|----------|-------|--------|
| 1 | CRIT-1: Fix broken imports in route files | Low |
| 2 | CRIT-2: Align Permission enum with route usage | Low |
| 3 | CRIT-3: Fix AdminUser/AdminUserModel naming | Low |
| 4 | MINOR-4: Fix Session vs AsyncSession type | Low |
| 5 | ARCH-3: Make repos implement domain ABCs | Medium |
| 6 | ARCH-1: Decouple application from infrastructure | High |
| 7 | ARCH-2: Abstract SQLAlchemy session from app layer | High |
| 8 | ARCH-4: Add behavior to domain entities | Medium |

---

## 10. Conclusion

The codebase has a **good architectural skeleton** - the four-layer structure, domain purity, and naming conventions demonstrate understanding of Clean Architecture principles. However, the **implementation has significant gaps**: the application layer bypasses domain interfaces to import infrastructure directly, repositories don't implement their domain contracts, and multiple route files have broken imports that prevent the application from starting.

The most impactful improvements would be:
1. **Fix the 3 critical issues** to get the application running
2. **Make repositories implement domain ABCs** and return domain entities
3. **Invert the application-to-infrastructure dependency** using domain interfaces

These changes would bring the architecture score from 57/100 to approximately 80/100.
