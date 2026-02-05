# CyberVPN Backend Security Remediation - Product Requirements Document

## Metadata

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Date** | 2026-02-05 |
| **Author** | Claude Code (PRD Writer) |
| **Status** | Ready for Implementation |
| **Clarity Score** | 93/100 |
| **Source Document** | Security Audit Report 2026-02-05 |
| **Overall Risk Rating** | LOW (with recommendations) |

---

## 1. Executive Summary

### 1.1 Problem Statement

A security audit conducted on February 5, 2026 identified **16 findings** in the CyberVPN FastAPI backend (`backend/src/`):

| Severity | Count | Description |
|----------|-------|-------------|
| HIGH | 1 | TOTP secrets stored unencrypted when key missing |
| MEDIUM | 4 | Password policy inconsistency, token binding, type errors, rate limit behavior |
| LOW | 5 | Cryptographic improvements, async patterns, logging enhancements |
| Informational | 6 | Development configuration and best practices |

The audit reveals that while the backend has a **mature security posture** with comprehensive controls (Argon2id password hashing, JWT with JTI claims, rate limiting with circuit breaker, brute force protection), several defense-in-depth improvements are needed to achieve full OWASP ASVS Level 2 compliance.

### 1.2 Why Now

1. **Production Readiness**: TOTP encryption key enforcement is critical before production launch
2. **Consistency Gap**: Mobile auth has weaker password policy than admin auth, creating an inconsistent security posture
3. **Code Quality**: Type errors in token handling could cause runtime failures
4. **Compliance**: Addressing these findings achieves full OWASP ASVS Level 2 compliance
5. **Audit Cadence**: Remediation should complete before next scheduled security review

### 1.3 Proposed Solution

Implement a phased security remediation plan:

- **Phase 1 (Immediate)**: Fix HIGH-001 and MED-003 - critical cryptographic and type safety issues
- **Phase 2 (Short-term)**: Fix MED-001, MED-004, LOW-002 - authentication and rate limiting consistency
- **Phase 3 (Medium-term)**: Fix MED-002, LOW-004, LOW-005 - session security and observability
- **Phase 4 (Backlog)**: Fix LOW-001, LOW-003, INFO items - defense-in-depth improvements

### 1.4 Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| HIGH vulnerabilities resolved | 1/1 (100%) | Security re-audit |
| MEDIUM vulnerabilities resolved | 4/4 (100%) | Security re-audit |
| LOW vulnerabilities resolved | 5/5 (100%) | Security re-audit |
| Application startup with missing TOTP key | Fails in production | Integration test |
| Mobile password policy alignment | Matches admin policy | Unit test |
| Rate limit fail-closed verification | 100% in production | Redis outage simulation |
| Request ID in all log entries | 100% | Log analysis |
| OWASP ASVS Level 2 compliance | 100% | Compliance checklist |

---

## 2. User Experience & Functionality

### 2.1 User Personas

#### Security Auditor
- **Goal**: Verify all identified vulnerabilities are properly remediated
- **Needs**: Clear acceptance criteria, reproducible test cases, audit trails
- **Pain Points**: Vague fixes that do not address root cause

#### DevOps Engineer
- **Goal**: Deploy secure, observable systems
- **Needs**: Clear configuration requirements, proper error handling, log correlation
- **Pain Points**: Missing documentation, unclear failure modes

#### Mobile App User
- **Goal**: Secure access to VPN service via mobile app
- **Needs**: Strong authentication without friction
- **Pain Points**: Inconsistent security requirements across platforms

#### Incident Responder
- **Goal**: Investigate security incidents efficiently
- **Needs**: Correlated logs, request tracing, audit trails
- **Pain Points**: Missing request IDs, sensitive data in logs

### 2.2 User Stories

#### US-1: TOTP Encryption Enforcement
**As a** security auditor
**I want** the application to refuse starting without TOTP encryption key in production
**So that** 2FA secrets are never stored in plaintext

**Acceptance Criteria:**
- [ ] Application fails to start when `TOTP_ENCRYPTION_KEY` is not set and `ENVIRONMENT=production`
- [ ] Clear error message indicates the missing configuration
- [ ] Development environment logs warning but continues (for local testing)
- [ ] Documentation updated with key generation procedure

#### US-2: Consistent Password Policy
**As a** mobile app user
**I want** my password to meet the same security standards as admin users
**So that** my account is equally protected against attacks

**Acceptance Criteria:**
- [ ] Mobile auth requires minimum 12-character passwords
- [ ] Mobile auth enforces uppercase, lowercase, digit, special character
- [ ] Mobile auth checks against common password blocklist
- [ ] Validation errors are specific and actionable

#### US-3: Request Tracing
**As an** incident responder
**I want** every log entry to include a unique request ID
**So that** I can correlate events during investigation

**Acceptance Criteria:**
- [ ] Middleware generates UUID request ID if not provided
- [ ] Request ID included in all log entries
- [ ] Request ID returned in `X-Request-ID` response header
- [ ] Request ID propagated to downstream services

### 2.3 Non-Goals (Out of Scope v1.0)

| Feature | Reason | Future Version |
|---------|--------|----------------|
| Hardware Security Module (HSM) integration | Cost/complexity for current scale | v2.0 |
| mTLS for internal services | Single service architecture currently | v2.0 |
| SIEM integration | Requires dedicated infrastructure | v1.1 |
| Automated key rotation | Manual rotation sufficient initially | v1.1 |

---

## 3. Functional Requirements

### Phase 1: Immediate (Week 1) - HIGH-001, MED-003

#### 3.1.1 HIGH-001: TOTP Encryption Key Enforcement

**Current State:**
```python
# backend/src/infrastructure/totp/totp_encryption.py:35-40
if not master_key:
    logger.warning(
        "TOTP_ENCRYPTION_KEY not set - secrets will not be encrypted. "
        "Set TOTP_ENCRYPTION_KEY in production!"
    )
    self._fernet = None  # Falls back to plaintext storage
```

**Target State:**
- Application MUST fail to start in production without `TOTP_ENCRYPTION_KEY`
- Development environment may continue with warning (configurable)

**Implementation:**

**File**: `backend/src/main.py` (lifespan modification)

```python
from contextlib import asynccontextmanager
from src.config.settings import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Enforce TOTP encryption key in production
    if settings.environment == "production" and not settings.totp_encryption_key:
        raise RuntimeError(
            "TOTP_ENCRYPTION_KEY is required in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # ... rest of lifespan
    yield
```

**File**: `backend/src/config/settings.py` (settings modification)

```python
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    totp_encryption_key: str | None = None
    environment: str = "development"

    @field_validator("totp_encryption_key", mode="after")
    @classmethod
    def warn_missing_totp_key(cls, v: str | None, info) -> str | None:
        if v is None:
            import logging
            logging.getLogger(__name__).warning(
                "TOTP_ENCRYPTION_KEY not set - TOTP secrets will be unencrypted. "
                "This is acceptable for development only."
            )
        return v
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| HIGH-001-T1 | Start app in production without TOTP key | RuntimeError raised |
| HIGH-001-T2 | Start app in development without TOTP key | Warning logged, app starts |
| HIGH-001-T3 | Start app with valid TOTP key | App starts normally |
| HIGH-001-T4 | TOTP encryption/decryption roundtrip | Secret matches after decrypt |

**Rollback Plan:**
- Revert lifespan changes if blocking legitimate deployments
- Add `TOTP_ENCRYPTION_REQUIRED=false` override for emergency bypass

---

#### 3.1.2 MED-003: Token Return Type Handling

**Current State:**
```python
# backend/src/application/use_cases/auth/login.py:68-72
access_token = self._auth_service.create_access_token(  # Returns tuple!
    subject=str(user.id),
    role=user.role,
)
refresh_token = self._auth_service.create_refresh_token(subject=str(user.id))  # Returns tuple!
```

**Target State:**
- Proper tuple unpacking for token creation
- JTI values stored for revocation support

**Implementation:**

**File**: `backend/src/application/use_cases/auth/login.py`

```python
async def execute(self, request: LoginRequest) -> LoginResponse:
    # ... validation logic ...

    # Unpack token tuple: (token, jti, expire)
    access_token, access_jti, access_expire = self._auth_service.create_access_token(
        subject=str(user.id),
        role=user.role,
    )

    refresh_token, refresh_jti, refresh_expire = self._auth_service.create_refresh_token(
        subject=str(user.id)
    )

    # Register tokens for revocation tracking
    await self._revocation_service.register_token(
        user_id=str(user.id),
        jti=access_jti,
        token_type="access",
        expires_at=access_expire,
    )
    await self._revocation_service.register_token(
        user_id=str(user.id),
        jti=refresh_jti,
        token_type="refresh",
        expires_at=refresh_expire,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_entity(user),
    )
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| MED-003-T1 | Login returns valid access token | Token is string, not tuple |
| MED-003-T2 | Login registers JTI for revocation | JTI exists in Redis |
| MED-003-T3 | Refresh token follows same pattern | Token is string, JTI registered |
| MED-003-T4 | Logout revokes tokens by JTI | Tokens rejected after logout |

**Rollback Plan:**
- If `create_access_token` signature differs, check method implementation
- Verify method returns consistent type across all callers

---

### Phase 2: Short-term (Weeks 2-3) - MED-001, MED-004, LOW-002

#### 3.2.1 MED-001: Mobile Password Policy Alignment

**Current State:**
```python
# Mobile: 8 chars, one letter + one digit
password: str = Field(..., min_length=8, max_length=128)

# Admin: 12 chars, uppercase, lowercase, digit, special, common password check
password: str = Field(..., min_length=12, max_length=128)
```

**Target State:**
- Mobile password requirements match admin requirements
- Shared password validation logic

**Implementation:**

**File**: `backend/src/presentation/api/v1/mobile_auth/schemas.py`

```python
from pydantic import Field, field_validator
from src.shared.validators.password import validate_password_strength

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)

    @field_validator("password", mode="after")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)
```

**File**: `backend/src/shared/validators/password.py` (new shared validator)

```python
import re
from typing import Set

# Top 10,000 common passwords (loaded from file or constant)
COMMON_PASSWORDS: Set[str] = _load_common_passwords()

def validate_password_strength(password: str) -> str:
    """
    Validate password meets security requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not in common password list
    """
    errors = []

    if len(password) < 12:
        errors.append("Password must be at least 12 characters")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")

    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common, please choose a stronger password")

    if errors:
        raise ValueError("; ".join(errors))

    return password
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| MED-001-T1 | Mobile registration with 8-char password | Validation error |
| MED-001-T2 | Mobile registration with 12-char weak password | Validation error (complexity) |
| MED-001-T3 | Mobile registration with "Password123!" | Validation error (common) |
| MED-001-T4 | Mobile registration with strong password | Registration succeeds |

**Rollback Plan:**
- If breaking existing mobile users, implement password upgrade flow on next login
- Add migration period with warning instead of rejection

---

#### 3.2.2 MED-004: Mobile Rate Limit Fail-Closed

**Current State:**
```python
# backend/src/presentation/dependencies/mobile_rate_limit.py:69-71
except Exception as exc:
    logger.warning("Mobile auth rate limit check failed: %s", exc)
    return True  # Allow on error to avoid blocking users
```

**Target State:**
- Configurable fail-closed behavior
- Circuit breaker pattern consistent with main rate limiter

**Implementation:**

**File**: `backend/src/presentation/dependencies/mobile_rate_limit.py`

```python
from src.config.settings import get_settings

class MobileRateLimiter:
    def __init__(self):
        self._settings = get_settings()
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
        )

    async def check_rate_limit(self, identifier: str) -> bool:
        try:
            if self._circuit_breaker.is_open:
                return self._handle_circuit_open()

            # ... rate limit check logic ...

        except Exception as exc:
            logger.warning("Mobile auth rate limit check failed: %s", exc)
            self._circuit_breaker.record_failure()
            return self._handle_rate_limit_failure()

    def _handle_rate_limit_failure(self) -> bool:
        """Handle rate limit check failure based on configuration."""
        if self._settings.environment == "production":
            # Fail-closed in production
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable. Please try again later."
            )
        else:
            # Fail-open in development for convenience
            logger.warning("Rate limit bypassed due to Redis failure (dev mode)")
            return True

    def _handle_circuit_open(self) -> bool:
        """Handle circuit breaker open state."""
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again later."
        )
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| MED-004-T1 | Redis unavailable in production | 503 Service Unavailable |
| MED-004-T2 | Redis unavailable in development | Warning logged, request proceeds |
| MED-004-T3 | Circuit breaker trips after 3 failures | All requests return 503 for 30s |
| MED-004-T4 | Circuit breaker recovers | Requests resume after recovery timeout |

**Rollback Plan:**
- Add `MOBILE_RATE_LIMIT_FAIL_OPEN=true` environment variable for emergency bypass
- Monitor 503 error rate after deployment

---

#### 3.2.3 LOW-002: Async Sleep in Auth Route

**Current State:**
```python
# backend/src/presentation/api/v1/auth/routes.py:113
if elapsed < min_response_time:
    time.sleep(min_response_time - elapsed + secrets.randbelow(50) / 1000)
```

**Target State:**
- Use `asyncio.sleep()` for non-blocking timing normalization

**Implementation:**

**File**: `backend/src/presentation/api/v1/auth/routes.py`

```python
import asyncio
import secrets

async def normalize_response_time(start_time: float, min_response_time: float = 0.3):
    """
    Normalize response time to prevent timing attacks.
    Uses async sleep to avoid blocking the event loop.
    """
    elapsed = time.monotonic() - start_time
    if elapsed < min_response_time:
        jitter = secrets.randbelow(50) / 1000  # 0-50ms random jitter
        await asyncio.sleep(min_response_time - elapsed + jitter)

@router.post("/login")
async def login(request: LoginRequest, ...):
    start_time = time.monotonic()
    try:
        # ... login logic ...
        return response
    finally:
        await normalize_response_time(start_time)
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| LOW-002-T1 | Fast login completes in < 300ms | Response delayed to ~300ms |
| LOW-002-T2 | Slow login takes > 300ms | No additional delay |
| LOW-002-T3 | Concurrent login requests | No event loop blocking |
| LOW-002-T4 | Response time variance | Random jitter applied |

**Rollback Plan:**
- Revert to `time.sleep()` if async issues arise
- Consider moving to middleware for consistency

---

### Phase 3: Medium-term (Weeks 4-6) - MED-002, LOW-004, LOW-005

#### 3.3.1 MED-002: Admin Token Device Binding

**Current State:**
- Admin refresh tokens not bound to device
- Mobile auth correctly binds tokens to `device_id`

**Target State:**
- Admin refresh tokens bound to client fingerprint
- Token refresh validates fingerprint match

**Implementation:**

**File**: `backend/src/application/use_cases/auth/refresh_token.py`

```python
from hashlib import sha256

def _generate_fingerprint(request: Request) -> str:
    """Generate client fingerprint from request metadata."""
    components = [
        request.headers.get("User-Agent", ""),
        request.client.host if request.client else "",
        request.headers.get("Accept-Language", ""),
    ]
    return sha256("|".join(components).encode()).hexdigest()[:16]

async def execute(self, request: Request, refresh_token: str) -> TokenResponse:
    # Decode and validate refresh token
    payload = self._auth_service.decode_token(refresh_token)

    # Validate fingerprint if present
    stored_fingerprint = payload.get("fingerprint")
    if stored_fingerprint:
        current_fingerprint = _generate_fingerprint(request)
        if stored_fingerprint != current_fingerprint:
            logger.warning(
                "Refresh token fingerprint mismatch",
                extra={
                    "user_id": payload["sub"],
                    "stored": stored_fingerprint,
                    "current": current_fingerprint,
                }
            )
            raise HTTPException(
                status_code=401,
                detail="Session invalid. Please login again."
            )

    # ... rest of refresh logic ...
```

**File**: `backend/src/application/services/auth_service.py`

```python
def create_refresh_token(
    self,
    subject: str,
    fingerprint: str | None = None
) -> tuple[str, str, datetime]:
    """Create refresh token with optional device binding."""
    jti = str(uuid4())
    expire = datetime.now(UTC) + timedelta(days=self._refresh_expire_days)

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
        "jti": jti,
    }

    if fingerprint:
        payload["fingerprint"] = fingerprint

    token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
    return token, jti, expire
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| MED-002-T1 | Refresh from same device | Token refreshed successfully |
| MED-002-T2 | Refresh from different device | 401 Unauthorized |
| MED-002-T3 | Refresh with no fingerprint (legacy) | Token refreshed (backwards compat) |
| MED-002-T4 | Fingerprint includes User-Agent change | 401 Unauthorized |

**Rollback Plan:**
- Make fingerprint validation optional via `ENFORCE_TOKEN_BINDING=false`
- Implement gradual rollout with monitoring

---

#### 3.3.2 LOW-004: Log Sanitization

**Current State:**
```python
# backend/src/presentation/middleware/logging.py:14
logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.0f}ms")
```

**Target State:**
- Sensitive query parameters redacted from logs
- Path segments with tokens redacted

**Implementation:**

**File**: `backend/src/presentation/middleware/logging.py`

```python
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

SENSITIVE_PARAMS = {"token", "invite_token", "reset_token", "api_key", "password"}
SENSITIVE_PATH_PATTERNS = [
    (r"/reset-password/([^/]+)", "/reset-password/[REDACTED]"),
    (r"/verify-email/([^/]+)", "/verify-email/[REDACTED]"),
    (r"/invite/([^/]+)", "/invite/[REDACTED]"),
]

def sanitize_url(url: str) -> str:
    """Sanitize URL by redacting sensitive query parameters and path segments."""
    parsed = urlparse(url)

    # Sanitize query parameters
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        sanitized_params = {
            k: ["[REDACTED]"] if k.lower() in SENSITIVE_PARAMS else v
            for k, v in params.items()
        }
        sanitized_query = urlencode(sanitized_params, doseq=True)
    else:
        sanitized_query = ""

    # Sanitize path segments
    sanitized_path = parsed.path
    for pattern, replacement in SENSITIVE_PATH_PATTERNS:
        sanitized_path = re.sub(pattern, replacement, sanitized_path)

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        sanitized_path,
        parsed.params,
        sanitized_query,
        "",  # No fragment in logs
    ))

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000

        sanitized_url = sanitize_url(str(request.url))
        logger.info(
            f"{request.method} {sanitized_url} {response.status_code} {duration_ms:.0f}ms"
        )
        return response
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| LOW-004-T1 | Request with `?token=secret` | Log shows `?token=[REDACTED]` |
| LOW-004-T2 | Request to `/invite/abc123` | Log shows `/invite/[REDACTED]` |
| LOW-004-T3 | Request with no sensitive data | Log unchanged |
| LOW-004-T4 | Multiple sensitive params | All redacted |

**Rollback Plan:**
- Revert to original logging if sanitization causes issues
- Add `LOG_SANITIZATION_ENABLED=false` bypass

---

#### 3.3.3 LOW-005: Request ID Propagation

**Current State:**
- No request ID generation or propagation
- Log correlation difficult

**Target State:**
- Every request has unique ID
- ID included in all logs and response headers

**Implementation:**

**File**: `backend/src/presentation/middleware/request_id.py` (new file)

```python
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate request IDs."""

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        # Use provided request ID or generate new one
        request_id = request.headers.get(self.HEADER_NAME) or str(uuid.uuid4())

        # Store in context for use in logging
        token = request_id_var.set(request_id)

        try:
            response = await call_next(request)
            response.headers[self.HEADER_NAME] = request_id
            return response
        finally:
            request_id_var.reset(token)
```

**File**: `backend/src/infrastructure/logging/config.py` (logging filter)

```python
import logging
from src.presentation.middleware.request_id import get_request_id

class RequestIDFilter(logging.Filter):
    """Add request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True

# Update logging format
LOGGING_FORMAT = (
    "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
)
```

**File**: `backend/src/main.py` (middleware registration)

```python
from src.presentation.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
```

**Test Cases:**

| Test ID | Scenario | Expected Result |
|---------|----------|-----------------|
| LOW-005-T1 | Request without X-Request-ID | UUID generated and returned |
| LOW-005-T2 | Request with X-Request-ID | Provided ID used and returned |
| LOW-005-T3 | Log entry during request | Contains request ID |
| LOW-005-T4 | Nested async calls | Same request ID throughout |

**Rollback Plan:**
- Remove middleware if causing performance issues
- Make request ID optional in log format

---

### Phase 4: Backlog - LOW-001, LOW-003, INFO Items

#### 3.4.1 LOW-001: HKDF Salt for TOTP Key Derivation

**Current State:**
```python
hkdf = HKDF(
    algorithm=hashes.SHA256(),
    length=32,
    salt=None,  # No salt for deterministic derivation
    info=self.INFO_CONTEXT,
)
```

**Target State:**
- Random salt stored alongside encrypted data
- Or documented justification for deterministic derivation

**Implementation Options:**

**Option A: Add Random Salt**
```python
class TOTPEncryption:
    SALT_LENGTH = 16

    def encrypt(self, secret: str) -> str:
        salt = os.urandom(self.SALT_LENGTH)
        derived_key = self._derive_key(salt)
        fernet = Fernet(base64.urlsafe_b64encode(derived_key))
        encrypted = fernet.encrypt(secret.encode())
        # Prepend salt to encrypted data
        return base64.urlsafe_b64encode(salt + encrypted).decode()

    def decrypt(self, encrypted: str) -> str:
        data = base64.urlsafe_b64decode(encrypted)
        salt = data[:self.SALT_LENGTH]
        encrypted_secret = data[self.SALT_LENGTH:]
        derived_key = self._derive_key(salt)
        fernet = Fernet(base64.urlsafe_b64encode(derived_key))
        return fernet.decrypt(encrypted_secret).decode()
```

**Option B: Document Current Approach**
```python
# Note: salt=None is intentional for deterministic key derivation.
# This allows the same derived key from the master key without storing salt.
# Trade-off: Slightly reduced protection against precomputation attacks.
# Acceptable because:
# 1. Master key is high-entropy (256-bit random)
# 2. HKDF info context provides domain separation
# 3. Adding salt would require database migration for existing secrets
```

**Recommendation:** Option B (document) for v1.0, Option A for v1.1 with migration.

---

#### 3.4.2 LOW-003: Remove OAuth Token from Dict

**Current State:**
```python
return {
    "id": str(user_data.get("id")),
    "username": user_data.get("login"),
    "email": user_data.get("email"),
    "name": user_data.get("name"),
    "avatar_url": user_data.get("avatar_url"),
    "access_token": access_token,  # Sensitive token passed through
}
```

**Target State:**
- Access token not included in user info dict
- Token stored separately if needed for refresh

**Implementation:**

**File**: `backend/src/infrastructure/oauth/github.py`

```python
async def exchange_code(self, code: str) -> tuple[dict, str]:
    """
    Exchange authorization code for user info and access token.

    Returns:
        Tuple of (user_info_dict, access_token)
        Access token returned separately to avoid logging exposure.
    """
    token_response = await self._client.post(
        "https://github.com/login/oauth/access_token",
        data={...},
        headers={"Accept": "application/json"},
    )
    access_token = token_response.json()["access_token"]

    user_response = await self._client.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_data = user_response.json()

    user_info = {
        "id": str(user_data.get("id")),
        "username": user_data.get("login"),
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "avatar_url": user_data.get("avatar_url"),
        # access_token intentionally excluded
    }

    return user_info, access_token
```

---

#### 3.4.3 INFO Items Summary

| ID | Finding | Remediation |
|----|---------|-------------|
| INFO-001 | Default DB credentials in .env | Document in deployment guide: use secrets manager in production |
| INFO-002 | JWT secret appears to be test value | Document key generation: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| INFO-003 | TOTP_ENCRYPTION_KEY not set | Add to `.env.example` with generation instructions |
| INFO-004 | Swagger UI enabled by default | Document `SWAGGER_ENABLED=false` for production |
| INFO-005 | Circuit breaker uses threading.Lock | Replace with `asyncio.Lock()` for async context |
| INFO-006 | Inconsistent exception logging | Add request ID to all exception handlers |

---

## 4. Non-Functional Requirements

### 4.1 Performance Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Token refresh latency | < 50ms p95 | APM monitoring |
| Rate limit check latency | < 5ms p95 | Redis latency |
| Request ID overhead | < 1ms | Middleware timing |
| Password validation | < 100ms | Include common password check |

### 4.2 Compatibility Requirements

| Requirement | Details |
|-------------|---------|
| Python version | >= 3.13 |
| FastAPI version | >= 0.128.0 |
| Redis version | >= 7.0 (for client-side caching) |
| Existing tokens | Must remain valid during rollout |
| Mobile app | Must handle new password requirements gracefully |

### 4.3 Testing Requirements

| Test Type | Coverage Target | Tools |
|-----------|----------------|-------|
| Unit tests | >= 90% for new code | pytest, pytest-asyncio |
| Integration tests | All security endpoints | pytest, httpx |
| Security tests | All vulnerability fixes | pytest, custom security suite |
| Load tests | 1000 concurrent auth requests | locust |

---

## 5. Technical Constraints

### 5.1 Existing Architecture

```
+------------------+     +------------------+     +------------------+
|  FastAPI         |---->|  Auth Service    |---->|  PostgreSQL      |
|  Routes          |     |  (JWT, TOTP)     |     |  (Users, Tokens) |
+------------------+     +------------------+     +------------------+
        |                        |
        v                        v
+------------------+     +------------------+
|  Middleware      |     |  Redis           |
|  (Rate Limit,    |     |  (Sessions,      |
|   Logging)       |     |   Rate Limits)   |
+------------------+     +------------------+
```

### 5.2 Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| python-jose | latest | JWT handling |
| argon2-cffi | latest | Password hashing |
| pyotp | latest | TOTP generation |
| cryptography | >= 42.0.0 | TOTP encryption |
| redis | latest | Caching, rate limiting |

### 5.3 Environment Variables (New)

```env
# Required in production
TOTP_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
ENVIRONMENT=production

# Optional configuration
MOBILE_RATE_LIMIT_FAIL_OPEN=false
ENFORCE_TOKEN_BINDING=true
LOG_SANITIZATION_ENABLED=true
REQUEST_ID_HEADER=X-Request-ID
```

---

## 6. Acceptance Criteria

### 6.1 HIGH-001: TOTP Encryption Key Enforcement

- [ ] Application fails to start with clear error when `TOTP_ENCRYPTION_KEY` missing in production
- [ ] Application logs warning but starts in development without key
- [ ] Documentation includes key generation command
- [ ] Existing encrypted secrets continue to work

### 6.2 MED-001: Mobile Password Policy

- [ ] Mobile registration requires 12+ character passwords
- [ ] Passwords must contain uppercase, lowercase, digit, special character
- [ ] Common passwords rejected with specific error message
- [ ] Validation errors are localized (27 locales)

### 6.3 MED-002: Token Device Binding

- [ ] Admin refresh tokens include client fingerprint
- [ ] Refresh from different device returns 401
- [ ] Legacy tokens without fingerprint still work
- [ ] Fingerprint mismatch logged for security monitoring

### 6.4 MED-003: Token Return Types

- [ ] `create_access_token` returns tuple properly unpacked
- [ ] JTI registered in Redis for each token
- [ ] Logout revokes tokens by JTI
- [ ] No runtime type errors in auth flows

### 6.5 MED-004: Rate Limit Fail-Closed

- [ ] Mobile rate limiter returns 503 on Redis failure in production
- [ ] Circuit breaker trips after 3 consecutive failures
- [ ] Recovery after 30-second timeout
- [ ] Metrics emitted for rate limit bypass events

### 6.6 LOW-002: Async Sleep

- [ ] `asyncio.sleep()` used instead of `time.sleep()`
- [ ] No event loop blocking under concurrent load
- [ ] Response time normalization still works correctly

### 6.7 LOW-004: Log Sanitization

- [ ] Query parameters with sensitive names redacted
- [ ] Path segments with tokens redacted
- [ ] Regular URLs logged unchanged
- [ ] Sanitization configurable via environment variable

### 6.8 LOW-005: Request ID Propagation

- [ ] UUID generated for requests without X-Request-ID
- [ ] Provided X-Request-ID preserved
- [ ] Request ID in all log entries
- [ ] Request ID in response header

---

## 7. Risks & Mitigations

### 7.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Password policy breaks mobile app | High | Medium | Version mobile app with new requirements, grace period |
| Rate limit fail-closed causes outages | High | Low | Monitor Redis health, have failover |
| Token binding locks out legitimate users | Medium | Medium | Make fingerprint matching lenient initially |
| Request ID overhead | Low | Low | Benchmark before deployment |
| TOTP key enforcement blocks deployment | High | Low | Document clearly, provide generation script |

### 7.2 Dependency Risks

| Dependency | Risk | Mitigation |
|------------|------|------------|
| Redis availability | Rate limiting and session management | Redis Sentinel/Cluster for HA |
| cryptography library | Security vulnerabilities | Monitor CVEs, update promptly |
| Password blocklist | False positives | Use well-curated list, allow override |

### 7.3 Rollback Procedures

| Phase | Rollback Steps |
|-------|---------------|
| Phase 1 | Remove lifespan check, revert login.py |
| Phase 2 | Revert password validator, rate limit dependency |
| Phase 3 | Disable fingerprint validation, remove middleware |
| Phase 4 | Documentation-only, no code rollback needed |

---

## 8. Timeline

### Phase 1: Immediate (Days 1-3)

| Day | Tasks | Owner | Deliverable |
|-----|-------|-------|-------------|
| 1 | HIGH-001: TOTP key enforcement | Backend Dev | PR with tests |
| 2 | MED-003: Token return type fix | Backend Dev | PR with tests |
| 3 | Code review, testing, merge | Team | Deployed to staging |

### Phase 2: Short-term (Days 4-10)

| Day | Tasks | Owner | Deliverable |
|-----|-------|-------|-------------|
| 4-5 | MED-001: Password policy alignment | Backend Dev | PR with tests |
| 6-7 | MED-004: Rate limit fail-closed | Backend Dev | PR with tests |
| 8 | LOW-002: Async sleep fix | Backend Dev | PR with tests |
| 9-10 | Integration testing, staging deploy | QA | Staging verified |

### Phase 3: Medium-term (Days 11-20)

| Day | Tasks | Owner | Deliverable |
|-----|-------|-------|-------------|
| 11-13 | MED-002: Token device binding | Backend Dev | PR with tests |
| 14-16 | LOW-004: Log sanitization | Backend Dev | PR with tests |
| 17-19 | LOW-005: Request ID propagation | Backend Dev | PR with tests |
| 20 | Final integration testing | QA | Production-ready |

### Phase 4: Backlog (Post-release)

| Priority | Tasks | Owner | Timeline |
|----------|-------|-------|----------|
| Low | LOW-001: HKDF salt | Backend Dev | v1.1 |
| Low | LOW-003: OAuth token removal | Backend Dev | v1.1 |
| Low | INFO items | Backend Dev | Ongoing |

---

## 9. References

### Security Standards

- [OWASP ASVS v4.0.3](https://owasp.org/www-project-application-security-verification-standard/)
- [NIST SP 800-63B Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)

### Vulnerability References

| Finding | CWE | OWASP |
|---------|-----|-------|
| HIGH-001 | CWE-312 | A02:2021 - Cryptographic Failures |
| MED-001 | CWE-521 | A07:2021 - Auth Failures |
| MED-002 | CWE-384 | A07:2021 - Auth Failures |
| MED-003 | CWE-704 | A04:2021 - Insecure Design |
| MED-004 | CWE-770 | A05:2021 - Security Misconfiguration |
| LOW-001 | CWE-327 | A02:2021 - Cryptographic Failures |
| LOW-002 | CWE-400 | A04:2021 - Insecure Design |
| LOW-003 | CWE-200 | A01:2021 - Broken Access Control |
| LOW-004 | CWE-532 | A09:2021 - Logging Failures |
| LOW-005 | CWE-778 | A09:2021 - Logging Failures |

### Related Documents

- [Security Audit Report 2026-02-05](/home/beep/projects/VPNBussiness/backend/docs/SECURITY_AUDIT_REPORT.md)
- [Backend Security Hardening PRD v1.0](/.taskmaster/docs/prds/backend-security-hardening-v1.0-prd.md)
- [Backend CLAUDE.md](/home/beep/projects/VPNBussiness/backend/CLAUDE.md)

---

**Document Version**: 1.0.0
**Created**: 2026-02-05
**Last Updated**: 2026-02-05
**Author**: Claude Code (PRD Writer)
**Status**: Ready for Implementation
**Clarity Score**: 93/100
