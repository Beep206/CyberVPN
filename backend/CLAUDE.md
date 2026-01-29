# Backend Coding Rules

Rules and best practices for the CyberVPN FastAPI backend.

## Stack & Versions

| Library | Version | Purpose |
|---------|---------|---------|
| Python | ≥3.13 | Runtime |
| FastAPI | ≥0.128.0 | Web framework |
| Uvicorn | standard | ASGI server |
| Pydantic | ≥2.0 | Validation & schemas |
| pydantic-settings | latest | Env-based config |
| SQLAlchemy | ≥2.0 | ORM (async) |
| Alembic | latest | DB migrations |
| asyncpg | latest | PostgreSQL async driver |
| httpx | latest | Async HTTP client |
| redis | latest | Cache client |
| python-jose | latest | JWT (consider PyJWT) |
| argon2-cffi | latest | Password hashing (Argon2id) |
| pyotp | latest | TOTP 2FA |
| pytest | dev | Testing |
| pytest-asyncio | dev | Async test support |
| ruff | dev | Linter + formatter |

**Infrastructure:** PostgreSQL 17.7, Redis/Valkey 8.1, Docker

---

## Architecture: Clean Architecture + DDD

```
presentation/  → application/  → domain/  ← infrastructure/
(FastAPI routes)  (use cases)    (entities)  (DB, cache, APIs)
```

### Layer Rules

**Domain** (`src/domain/`):
- **Zero framework imports** — no FastAPI, SQLAlchemy, httpx, redis
- Pure Python: entities, value objects, enums, exceptions, repository interfaces
- Business logic lives here — validate invariants in entity methods

**Application** (`src/application/`):
- Use cases orchestrate domain entities + repository interfaces
- DTOs for input/output — never expose domain entities to presentation
- May import domain, MUST NOT import infrastructure directly
- Use dependency injection for repository implementations

**Infrastructure** (`src/infrastructure/`):
- Concrete implementations: SQLAlchemy repos, Redis cache, httpx clients
- Implements domain repository interfaces
- Framework-specific code (ORM models, HTTP clients, external APIs)

**Presentation** (`src/presentation/`):
- Thin FastAPI routes — delegate logic to use cases
- Request/response Pydantic schemas
- Middleware, dependencies, exception handlers
- MUST NOT contain business logic

---

## Python 3.13

### Type Hints
- **`TypeIs`** for type narrowing (replaces `TypeGuard` where applicable):
  ```python
  from typing import TypeIs
  def is_admin(user: User) -> TypeIs[AdminUser]:
      return user.role == "admin"
  ```
- **`ReadOnly`** for immutable TypedDict fields:
  ```python
  from typing import ReadOnly, TypedDict
  class Config(TypedDict):
      db_url: ReadOnly[str]
      debug: bool
  ```
- **`TypeVar` defaults** — no more required type params:
  ```python
  from typing import TypeVar
  T = TypeVar("T", default=str)
  ```
- **`Required` / `NotRequired`** for TypedDict field optionality

### Performance
- Experimental JIT compiler available (opt-in via build flag)
- Free-threaded CPython (no GIL) experimental — useful for CPU-bound parallel tasks
- `mimalloc` allocator enabled by default

### Other
- Colorized tracebacks by default
- Stripped docstring indentation (memory savings)
- Removed legacy modules: `cgi`, `smtpd`, etc.

---

## FastAPI ≥0.128

### Async Rules
- **All routes MUST be `async def`** when using async I/O (asyncpg, httpx, redis):
  ```python
  # GOOD — async route with async DB call
  @router.get("/users/{user_id}")
  async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
      user = await db.execute(select(User).where(User.id == user_id))
      return user.scalar_one_or_none()

  # BAD — blocking call in async route freezes the event loop
  @router.get("/users/{user_id}")
  async def get_user(user_id: UUID):
      user = sync_db.query(User).get(user_id)  # BLOCKS EVENT LOOP
  ```
- **Never use blocking calls in `async def` routes** — no `time.sleep()`, no sync DB, no sync file I/O
- **Sync routes (`def`)** run in a threadpool — use for CPU-bound or legacy sync code
- **Prefer async dependencies** for non-I/O helpers — sync deps run in threadpool with overhead

### Structure
- **Router-based modular structure** — one router per API domain:
  ```python
  from fastapi import APIRouter
  router = APIRouter(prefix="/api/v1/users", tags=["users"])
  ```
- **Lifespan context manager** for startup/shutdown:
  ```python
  from contextlib import asynccontextmanager
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Startup: init DB pool, Redis, httpx client
      yield
      # Shutdown: close connections
  app = FastAPI(lifespan=lifespan)
  ```
- **Dependency injection** for DB sessions, auth, rate limiting — no global state
- **`BackgroundTasks`** for minor async work (emails, logs); message queues for heavy processing

### Response Models
- Always specify `response_model` or return type for API docs:
  ```python
  @router.get("/users/{user_id}", response_model=UserResponse)
  ```
- Use `status_code` parameter for non-200 responses
- Use `HTTPException` with appropriate status codes

---

## Pydantic v2

### Model Configuration
- **`model_config` dict** (not deprecated `class Config`):
  ```python
  from pydantic import BaseModel, ConfigDict

  class UserSchema(BaseModel):
      model_config = ConfigDict(
          from_attributes=True,  # ORM mode (replaces orm_mode=True)
          frozen=True,           # Immutable (replaces allow_mutation=False)
          strict=True,           # No type coercion
      )
      id: UUID
      email: str
  ```

### Validators
- **`@field_validator`** with modes (`before`, `after`, `plain`, `wrap`):
  ```python
  from pydantic import field_validator

  class CreateUser(BaseModel):
      email: str

      @field_validator("email", mode="before")
      @classmethod
      def normalize_email(cls, v: str) -> str:
          return v.strip().lower()
  ```
- **`@model_validator`** for cross-field validation:
  ```python
  from pydantic import model_validator

  class DateRange(BaseModel):
      start: datetime
      end: datetime

      @model_validator(mode="after")
      def check_dates(self) -> "DateRange":
          if self.start >= self.end:
              raise ValueError("start must be before end")
          return self
  ```
- **Always return the value** from validators
- **Raise `ValueError` or `AssertionError`** — never `ValidationError`

### Reusable Validated Types
- Use `Annotated` + `AfterValidator` for reusable patterns:
  ```python
  from typing import Annotated
  from pydantic import AfterValidator

  def validate_positive(v: int) -> int:
      if v <= 0:
          raise ValueError("must be positive")
      return v

  PositiveInt = Annotated[int, AfterValidator(validate_positive)]
  ```

### Settings
- **`pydantic-settings`** with `BaseSettings` for env-based configuration:
  ```python
  from pydantic_settings import BaseSettings

  class Settings(BaseSettings):
      database_url: str
      redis_url: str
      jwt_secret: str
      model_config = ConfigDict(env_file=".env")
  ```

---

## SQLAlchemy 2.0 (Async)

### Modern Declarative Style
- **`DeclarativeBase` + `AsyncAttrs`** mixin:
  ```python
  from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
  from sqlalchemy.ext.asyncio import AsyncAttrs

  class Base(AsyncAttrs, DeclarativeBase):
      pass
  ```
- **`Mapped[]` + `mapped_column()`** — not legacy `Column()`:
  ```python
  class User(Base):
      __tablename__ = "users"
      id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
      email: Mapped[str] = mapped_column(String(255), unique=True)
      is_active: Mapped[bool] = mapped_column(default=True)
  ```

### Async Session
- **`create_async_engine` + `async_sessionmaker`**:
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

  engine = create_async_engine(
      "postgresql+asyncpg://...",
      pool_size=10,
      max_overflow=20,
      pool_pre_ping=True,
      pool_recycle=3600,
  )
  async_session = async_sessionmaker(engine, expire_on_commit=False)
  ```
- **`expire_on_commit=False`** — required for async to avoid lazy loads after commit

### Relationships
- **`selectinload`** for eager loading (lazy load raises in async):
  ```python
  from sqlalchemy.orm import selectinload
  stmt = select(User).options(selectinload(User.orders))
  result = await session.execute(stmt)
  ```
- **`lazy="raise"`** on relationships to prevent implicit SQL:
  ```python
  orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy="raise")
  ```
- **`WriteOnlyMapped`** for large collections — never load all into memory

### Naming Conventions
- Define constraint naming in `MetaData` for predictable migration names:
  ```python
  convention = {
      "ix": "ix_%(column_0_label)s",
      "uq": "uq_%(table_name)s_%(column_0_name)s",
      "ck": "ck_%(table_name)s_%(constraint_name)s",
      "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
      "pk": "pk_%(table_name)s",
  }
  metadata = MetaData(naming_convention=convention)
  ```

---

## Alembic (Migrations)

- **Async template**: `alembic init -t async alembic`
- **Set `target_metadata`** = `Base.metadata` in `env.py` for autogeneration
- **Always review autogenerated migrations** — autogenerate doesn't catch everything
- **Load DB URL from env vars** — never hardcode in `alembic.ini`
- **Mixins** for common fields:
  ```python
  class TimestampMixin:
      created_at: Mapped[datetime] = mapped_column(default=func.now())
      updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
  ```
- **Run migrations before app startup** in Docker (`alembic upgrade head`)
- **Define tables directly** in data migrations — don't import models (schema may change)

---

## httpx (Async HTTP Client)

### Singleton Pattern
- **Single long-lived `AsyncClient`** — never create per-request:
  ```python
  # In lifespan
  client = httpx.AsyncClient(
      base_url="http://remnawave:3000",
      timeout=httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=3.0),
      limits=httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0),
      transport=httpx.AsyncHTTPTransport(retries=2),
  )
  ```
- **Explicit timeouts** — never use defaults blindly
- **Transport-level retries** for connection failures: `AsyncHTTPTransport(retries=2)`
- **Response-level retries** (429, 503): use `tenacity` library
- **Always `await client.aclose()`** in shutdown
- **Watch for `PoolTimeout`** on long-running clients — monitor and recreate if needed

---

## JWT Authentication

### Current: python-jose
- **Note:** python-jose is barely maintained — FastAPI docs now recommend **PyJWT**
- Consider migrating to **`joserfc`** (Authlib) for full JOSE suite (JWS + JWE + JWK)

### Best Practices
- **Short-lived access tokens** (15 min), **refresh tokens** (7 days)
- **Store secrets in env vars** — never in code or config files
- **HS256 minimum** for HMAC signing; prefer RS256 for microservices
- **Validate `exp`, `iss`, `aud` claims** on every request
- **Rotate secrets** without downtime by supporting multiple valid keys

---

## Testing (pytest + pytest-asyncio)

### Configuration
```ini
# pytest.ini
[pytest]
asyncio_mode = auto
markers =
    unit: Unit tests (no external deps)
    integration: Integration tests (DB, Redis)
    e2e: End-to-end tests
```

### Patterns
- **Async fixtures** with `async def`:
  ```python
  @pytest.fixture
  async def async_client():
      async with AsyncClient(app=app, base_url="http://test") as client:
          yield client
  ```
- **`loop_scope="session"`** for shared event loops across tests
- **`event_loop` fixture removed** in pytest-asyncio 1.0+ — use `loop_scope` instead
- **Isolated test DB** — create/drop per test session, rollback per test
- **Factory fixtures** for domain entities — don't use production data

### Structure
```
tests/
├── conftest.py         # Shared fixtures
├── unit/               # Fast, no external deps
├── integration/        # DB, Redis, external APIs
└── e2e/                # Full API flow
```

---

## Ruff (Linter + Formatter)

### Commands
```bash
ruff check .           # Lint
ruff check --fix .     # Auto-fix
ruff format .          # Format (replaces Black)
```

### Recommended Configuration (`pyproject.toml`)
```toml
[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # Pyflakes
    "I",   # isort (import sorting)
    "B",   # flake8-bugbear
    "UP",  # pyupgrade (modernize syntax)
    "S",   # flake8-bandit (security)
    "ASYNC", # flake8-async
]

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

### Rules
- **Always run both `ruff check` and `ruff format`** — they complement each other
- **`I` rules** handle import sorting (replaces isort)
- **`B` rules** catch common bugs (bugbear)
- **`UP` rules** modernize syntax to Python 3.13+
- **`S` rules** catch security issues (bandit)
- **`ASYNC` rules** catch async anti-patterns

---

## Security

- **Never commit secrets/tokens** — use `.env` + `pydantic-settings`
- **CORS:** explicit origins list, no wildcards in production
- **Rate limiting** on all public endpoints via middleware
- **Input validation** at API boundary via Pydantic schemas
- **Password hashing:** Argon2id via `argon2-cffi` (OWASP 2025) — never store plaintext
- **2FA:** TOTP via `pyotp` — backup codes stored hashed
- **SQL injection:** prevented by SQLAlchemy parameterized queries — never raw SQL with f-strings
- **Auth in routes/dependencies** — not in middleware/proxy (lessons from CVE-2025-29927)

---

## Docker

### Dockerfile
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Deployment
- **Gunicorn + Uvicorn workers** for multi-core:
  ```bash
  gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
  ```
- **Run migrations first:** `alembic upgrade head` before app start
- **Health check:** `GET /health` endpoint
- **Graceful shutdown:** handle `SIGTERM` in lifespan

---

## Infrastructure

| Service | Port | Purpose |
|---------|------|---------|
| Backend API | 8000 | FastAPI app |
| Remnawave | 3000 | VPN backend API |
| PostgreSQL | 6767 | Database |
| Redis/Valkey | 6379 | Cache |
| Prometheus | 9090 | Metrics (optional) |
| Grafana | 3002 | Dashboards (optional) |
