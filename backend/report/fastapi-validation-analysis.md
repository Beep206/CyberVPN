# CyberVPN Backend - FastAPI Validation Analysis

**Date**: 2026-01-29
**Scope**: All Pydantic schemas, request/response models, Query/Path params, DTOs
**Stack**: FastAPI, Pydantic v2, pydantic-settings

---

## 1. Summary

| Metric | Value |
|--------|-------|
| Pydantic schema files | 8 |
| Total schema classes | 28 |
| Application DTOs (dataclass) | 5 |
| Route modules with typed schemas | 8 of 21 |
| Route modules using raw `dict` | 11 of 21 |
| Route modules with no validation | 2 of 21 |
| Overall validation coverage | **38%** |

**Verdict**: The 8 core modules (auth, users, servers, monitoring, payments, admin, telegram, two-factor) have properly typed Pydantic schemas. The remaining 11 modules accept unvalidated `dict` payloads, and 2 modules use raw `Request` objects. This creates a significant validation gap where invalid data can reach business logic unchecked.

---

## 2. What's Working Well

### 2.1 Auth Schemas - GOOD

`src/presentation/api/v1/auth/schemas.py`

| Schema | Fields | Validation | Verdict |
|--------|--------|-----------|---------|
| `LoginRequest` | login_or_email, password | min_length=1 on both | OK - basic |
| `RegisterRequest` | login, email, password | regex pattern, EmailStr, min/max_length | GOOD |
| `RefreshTokenRequest` | refresh_token | str (no constraints) | WEAK |
| `LogoutRequest` | refresh_token | str (no constraints) | WEAK |
| `TokenResponse` | access_token, refresh_token, token_type, expires_in | defaults present | OK |
| `AdminUserResponse` | id, login, email, role, etc. | from_attributes=True, UUID type | GOOD |

**Issues**:
- `LoginRequest.password` only validates `min_length=1` - no max_length cap, which could allow extremely long strings (potential DoS via bcrypt)
- `RefreshTokenRequest.refresh_token` and `LogoutRequest.refresh_token` have zero validation - no min_length, no max_length, no pattern
- `RegisterRequest` is well-validated: regex `^[a-zA-Z0-9_]+$` for login, `EmailStr` for email, length constraints on password

### 2.2 Users Schemas - GOOD

`src/presentation/api/v1/users/schemas.py`

| Schema | Fields | Validation | Verdict |
|--------|--------|-----------|---------|
| `CreateUserRequest` | username, password, email, etc. | min/max_length, EmailStr | GOOD |
| `UpdateUserRequest` | username, password, email, etc. | Optional + min/max_length | GOOD |
| `UserResponse` | uuid, username, status, traffic, etc. | from_attributes=True | GOOD |
| `UserListResponse` | users, total, page, page_size | typed List[UserResponse] | GOOD |
| `BulkUserActionRequest` | user_ids | List[UUID], min_length=1 | GOOD |

**Issues**:
- `BulkUserActionRequest.user_ids` has `min_length=1` but no `max_length` - could submit thousands of UUIDs
- `CreateUserRequest.data_limit` (bytes) has no upper bound - could submit absurdly large values
- No custom validators to check that `expire_at` is in the future

### 2.3 Servers Schemas - GOOD

`src/presentation/api/v1/servers/schemas.py`

| Schema | Fields | Validation | Verdict |
|--------|--------|-----------|---------|
| `CreateServerRequest` | name, address, port | min/max_length, port 1-65535 | GOOD |
| `UpdateServerRequest` | name, address, port | Optional + same constraints | GOOD |
| `ServerResponse` | uuid, name, status, traffic, etc. | from_attributes=True | GOOD |
| `ServerStatsResponse` | online, offline, warning, etc. | typed ints | OK |

**Issues**:
- `CreateServerRequest.address` only validates `min_length=1` - no pattern for IP/hostname
- `ServerStatsResponse` uses deprecated `class Config` instead of `model_config = ConfigDict(...)`

### 2.4 Monitoring Schemas - GOOD

`src/presentation/api/v1/monitoring/schemas.py`

Well-documented schemas with `Field(description=...)` on every field. Uses `default_factory=datetime.utcnow` for timestamps.

**Issues**:
- Routes return `Dict[str, Any]` instead of using the defined response schemas (`HealthResponse`, `StatsResponse`, etc.) - the schemas exist but aren't wired to `response_model`
- `datetime.utcnow` is deprecated in Python 3.12+ - should use `datetime.now(UTC)`

### 2.5 Payments Schemas - GOOD

`src/presentation/api/v1/payments/schemas.py`

| Schema | Fields | Validation | Verdict |
|--------|--------|-----------|---------|
| `CreateInvoiceRequest` | user_uuid, plan_id, currency | min/max_length on currency | OK |
| `InvoiceResponse` | invoice_id, payment_url, amount, etc. | gt=0 on amount | GOOD |
| `PaymentHistoryResponse` | id, amount, currency, status, etc. | typed fields | OK |

Includes `json_schema_extra` examples for OpenAPI docs.

**Issues**:
- `CreateInvoiceRequest.user_uuid` is `str` instead of `UUID` - no UUID format validation
- `CreateInvoiceRequest.plan_id` is `str` instead of `UUID` - inconsistent with other modules
- `CreateInvoiceRequest.currency` has `min_length=3, max_length=3` (good) but no pattern to enforce uppercase ISO 4217 codes
- `InvoiceResponse.payment_url` is `str` instead of `HttpUrl` - no URL format validation

### 2.6 Telegram Schemas - OK

`src/presentation/api/v1/telegram/schemas.py`

All schemas include `json_schema_extra` examples.

**Issues**:
- Uses deprecated `class Config` instead of `model_config = ConfigDict(...)` (Pydantic v2 deprecation warning)
- `NotifyRequest.message` has `min_length=1` but no `max_length` - potential for very long messages
- `CreateSubscriptionRequest.duration_days` has `gt=0` but no upper bound

### 2.7 Admin Schemas - OK

`src/presentation/api/v1/admin/schemas.py`

**Issues**:
- Uses deprecated `class Config` instead of `model_config = ConfigDict(...)`
- `AuditLogResponse.details: Optional[Dict[str, Any]]` - untyped dict, could contain anything
- No request schemas for admin write operations

---

## 3. Critical Issues

### CRIT-1: 11 Route Modules Accept Unvalidated `dict` Payloads

**Severity**: HIGH
**Impact**: No request validation - any JSON structure is accepted and forwarded to Remnawave API

**Affected modules**:

| Module | Route | Accepts |
|--------|-------|---------|
| billing | POST `/billing/` | `payment_data: dict` |
| plans | POST `/plans/`, PUT `/plans/{id}` | `plan_data: dict` |
| subscriptions | POST `/subscriptions/template` | `template_data: dict` |
| config_profiles | POST `/config-profiles/`, PUT | `profile_data: dict` |
| hosts | POST `/hosts/`, PUT `/hosts/{id}` | `host_data: dict` |
| keygen | POST `/keygen/` | `payload_data: dict` |
| snippets | POST `/snippets/`, PUT | `snippet_data: dict` |
| squads | POST `/squads/`, PUT | `squad_data: dict` |
| xray | POST `/xray/config`, PUT | `config_data: dict` |
| settings | PUT `/settings/{key}` | `setting_data: dict` |

**Example of unvalidated route**:

```python
# src/presentation/api/v1/billing/routes.py
@router.post("/")
async def create_payment(
    payment_data: dict,  # No validation! Any JSON accepted.
    remnawave=Depends(get_remnawave_client),
    ...
):
    result = await remnawave.post("/api/billing", json=payment_data)
    return result
```

**Risks**:
- Injection of unexpected fields
- Type mismatches causing errors at the Remnawave API level (poor error messages)
- No documentation in OpenAPI spec (shows as `object` with no properties)
- Impossible to validate request structure at the API boundary

**Fix**: Create typed Pydantic schemas for each module. Even minimal schemas are better than `dict`:

```python
class CreatePaymentRequest(BaseModel):
    user_uuid: UUID
    plan_id: UUID
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
```

### CRIT-2: No Request Size Limits

**Severity**: MEDIUM
**Impact**: Potential denial-of-service via oversized payloads

No global request body size limit is configured in FastAPI or middleware. Combined with `dict`-typed endpoints, an attacker could send arbitrarily large JSON payloads.

**Fields without upper bounds**:
- `BulkUserActionRequest.user_ids` - no `max_length` (List[UUID])
- `CreateUserRequest.data_limit` - no upper bound (Optional[int])
- `CreateSubscriptionRequest.duration_days` - no upper bound (int, gt=0)
- `NotifyRequest.message` - no `max_length`
- `LoginRequest.password` - no `max_length` (bcrypt truncates at 72 bytes but still processes the full string for hashing)
- `RefreshTokenRequest.refresh_token` - no length constraint at all

### CRIT-3: Monitoring Schemas Defined but Not Used

**Severity**: MEDIUM
**Impact**: Response format is undocumented and unvalidated

`monitoring/schemas.py` defines `HealthResponse`, `StatsResponse`, `BandwidthResponse` etc., but the routes return `Dict[str, Any]`:

```python
# monitoring/routes.py
@router.get("/health")
async def health(...):
    result = await use_case.execute()
    return result  # Returns raw dict, not HealthResponse
```

The schemas serve no purpose - they exist as dead code. Either wire them to `response_model` or remove them.

---

## 4. Architectural Issues

### ARCH-1: Deprecated Pydantic v1 `class Config` Pattern

**Severity**: LOW (generates deprecation warnings, will break in Pydantic v3)
**Files affected**: 8 schema classes across 3 files

```python
# Current (deprecated):
class AuditLogResponse(BaseModel):
    class Config:
        from_attributes = True

# Should be (Pydantic v2):
class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes = True)
```

**Affected files**:
- `admin/schemas.py` — `AuditLogResponse`, `WebhookLogResponse`, `AdminSettingsResponse`
- `telegram/schemas.py` — `TelegramUserResponse`, `CreateSubscriptionRequest`, `ConfigResponse`, `NotifyRequest`
- `servers/schemas.py` — `ServerStatsResponse`

### ARCH-2: Inconsistent Type Usage

| Issue | Location | Current | Should Be |
|-------|----------|---------|-----------|
| UUID as string | `payments/schemas.py` CreateInvoiceRequest | `user_uuid: str` | `user_uuid: UUID` |
| UUID as string | `payments/schemas.py` CreateInvoiceRequest | `plan_id: str` | `plan_id: UUID` |
| URL as string | `payments/schemas.py` InvoiceResponse | `payment_url: str` | `payment_url: HttpUrl` |
| Status as string | `users/schemas.py` UserResponse | `status: str` | `status: UserStatus` (enum) |
| Status as string | `servers/schemas.py` ServerResponse | `status: str` | `status: ServerStatus` (enum) |
| Status as string | `payments/schemas.py` InvoiceResponse | `status: str` | `status: Literal["pending", "paid", "expired"]` |

Using proper types provides:
- Automatic validation (UUID format, URL format, enum membership)
- Better OpenAPI documentation
- Type safety at compile time

### ARCH-3: No Shared Pagination Response Pattern

Pagination is handled inconsistently:

| Module | Pattern |
|--------|---------|
| Users | `UserListResponse(users=[], total=N, page=P, page_size=S)` |
| Admin audit log | `List[AuditLogResponse]` (no total count, no page info) |
| Admin webhook log | `List[WebhookLogResponse]` (no total count, no page info) |
| Payments history | Raw dict with offset/limit |

**Fix**: Create a generic paginated response:

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int  # computed
```

### ARCH-4: No Custom Validators

None of the 28 schema classes use `@field_validator` or `@model_validator`. Missing validations:

| Schema | Missing Validation |
|--------|--------------------|
| `RegisterRequest` | Password strength (uppercase, digit, special char) |
| `CreateUserRequest` | `expire_at` should be in the future |
| `CreateInvoiceRequest` | `currency` should be uppercase ISO 4217 |
| `CreateServerRequest` | `address` should be valid IP or hostname |
| `UpdateServerRequest` | At least one field should be non-None |
| `CreateSubscriptionRequest` | `duration_days` upper bound (e.g., 3650) |

### ARCH-5: No Global Validation Error Handler

No custom `RequestValidationError` handler is registered. FastAPI's default returns verbose error details including internal field names and types. A custom handler would:
- Return consistent error format
- Hide internal field names from API consumers
- Log validation failures for monitoring

---

## 5. Scoring

| Category | Score | Max | Notes |
|----------|-------|-----|-------|
| Schema Coverage | 4 | 10 | 8/21 modules have schemas, 11 use raw dict |
| Field Constraints | 6 | 10 | Good on present schemas, some fields lack bounds |
| Type Safety | 5 | 10 | UUID/URL/enum as strings, inconsistent types |
| Custom Validators | 1 | 10 | Zero validators across all schemas |
| Response Models | 5 | 10 | Core modules good, monitoring schemas unused |
| Query/Path Params | 7 | 10 | Pagination and path params well-typed |
| Error Handling | 3 | 10 | No custom validation error handler |
| OpenAPI Docs | 5 | 10 | Some json_schema_extra, but dict endpoints show nothing |
| Security | 4 | 10 | No size limits, password length uncapped |
| Pydantic v2 Usage | 6 | 10 | Most use v2 patterns, 8 classes use deprecated Config |

**Overall Validation Score: 46/100**

---

## 6. Fix Priority

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 1 | CRIT-1: Add schemas for 11 unvalidated modules | High | Closes major validation gap |
| 2 | CRIT-2: Add `max_length` to unbounded fields | Low | Prevents DoS vectors |
| 3 | ARCH-1: Migrate deprecated `class Config` to `ConfigDict` | Low | Removes deprecation warnings |
| 4 | ARCH-2: Use proper types (UUID, HttpUrl, enums) | Low | Better validation + docs |
| 5 | ARCH-4: Add custom validators (password, dates, IP) | Medium | Business rule enforcement |
| 6 | CRIT-3: Wire monitoring schemas to response_model | Low | Fixes dead code + docs |
| 7 | ARCH-5: Add global validation error handler | Low | Consistent error format |
| 8 | ARCH-3: Create generic paginated response | Medium | Consistent pagination |

---

## 7. Module-by-Module Status

| Module | Schema File | Request Validation | Response Validation | Status |
|--------|-------------|-------------------|--------------------|----|
| auth | schemas.py | GOOD | GOOD | OK |
| users | schemas.py | GOOD | GOOD | OK |
| servers | schemas.py | GOOD | GOOD | OK |
| monitoring | schemas.py | N/A (GET only) | NOT WIRED | WARN |
| payments | schemas.py | OK (weak types) | OK | WARN |
| admin | schemas.py | N/A (GET only) | OK | OK |
| telegram | schemas.py | OK | OK | OK |
| two-factor | inline | MINIMAL | NONE | WARN |
| billing | NONE | NONE (dict) | NONE | FAIL |
| plans | NONE | NONE (dict) | NONE | FAIL |
| subscriptions | NONE | NONE (dict) | NONE | FAIL |
| config_profiles | NONE | NONE (dict) | NONE | FAIL |
| hosts | NONE | NONE (dict) | NONE | FAIL |
| inbounds | NONE | N/A (GET only) | NONE | WARN |
| keygen | NONE | NONE (dict) | NONE | FAIL |
| snippets | NONE | NONE (dict) | NONE | FAIL |
| squads | NONE | NONE (dict) | NONE | FAIL |
| xray | NONE | NONE (dict) | NONE | FAIL |
| settings | NONE | NONE (dict) | NONE | FAIL |
| webhooks | NONE | RAW REQUEST | NONE | OK* |
| oauth | NONE | QUERY PARAMS | NONE | OK* |

\* Webhooks intentionally use raw payloads for signature verification. OAuth uses simple query params.

---

## 8. Conclusion

The backend has a **split validation landscape**:

- **8 core modules** (auth, users, servers, monitoring, payments, admin, telegram, 2FA) have proper Pydantic schemas with reasonable field constraints. These cover the primary admin dashboard operations.

- **11 pass-through modules** (billing, plans, subscriptions, hosts, etc.) accept raw `dict` payloads with zero validation. These are proxy endpoints forwarding to the Remnawave VPN API.

The most impactful improvement is **adding typed schemas to the 11 unvalidated modules**. Even if these endpoints proxy to Remnawave, validating at the API boundary:
1. Provides OpenAPI documentation for frontend developers
2. Catches malformed requests before they hit the external API
3. Prevents injection of unexpected fields
4. Enforces consistent data types (UUID, datetime, enums)

The existing schemas would benefit from: stronger field constraints (max_length on all strings, upper bounds on numeric fields), proper Pydantic types (UUID instead of str, HttpUrl, domain enums), and custom validators for business rules (password strength, future dates, valid IP addresses).
