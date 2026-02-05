# CyberVPN Backend Security Audit Report

**Date:** 2026-02-05  
**Auditor:** Application Security Engineer  
**Scope:** FastAPI Backend (`/home/beep/projects/VPNBussiness/backend/`)  
**Version:** 0.1.0

---

## Executive Summary

This security audit evaluates the CyberVPN FastAPI backend against OWASP Top 10 2025, API security best practices, and the security controls outlined in the project requirements. The codebase demonstrates **strong security posture** with evidence of proactive security remediation (referenced as HIGH-X, MED-X, CRIT-X, LOW-X throughout the code).

### Overall Risk Assessment: **LOW-MEDIUM**

The backend implements robust security controls including:
- Argon2id password hashing (OWASP 2025 recommended)
- JWT with proper algorithm allowlist and token rotation
- Redis-backed rate limiting with fail-closed behavior
- Comprehensive input validation via Pydantic
- CSRF protection for OAuth flows
- Brute force protection with progressive lockout

However, several issues require attention before production deployment.

### Summary Statistics

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 2 |
| Medium | 5 |
| Low | 6 |
| Info | 4 |

---

## Findings Summary

| ID | Severity | Category | Finding | Affected File |
|----|----------|----------|---------|---------------|
| SEC-001 | HIGH | A07: Auth Failures | TOTP secret stored in plaintext | `admin_user_model.py:41` |
| SEC-002 | HIGH | A05: Misconfiguration | Docker runs as root user | `Dockerfile:1-16` |
| SEC-003 | MEDIUM | A07: Auth Failures | JWT revocation not checked in auth dependency | `auth.py:22-30` |
| SEC-004 | MEDIUM | A05: Misconfiguration | Default credentials in .env | `.env:4-5` |
| SEC-005 | MEDIUM | A02: Crypto Failures | Client fingerprint uses IP (unstable for mobile) | `fingerprint.py:38-39` |
| SEC-006 | MEDIUM | A01: Access Control | Missing IDOR protection on mobile `/me` endpoint | `mobile_auth/routes.py:360-384` |
| SEC-007 | MEDIUM | A09: Logging Failures | Sensitive data in audit log details | `registration.py:40-51` |
| SEC-008 | LOW | A05: Misconfiguration | Swagger enabled by default | `settings.py:74` |
| SEC-009 | LOW | A05: Misconfiguration | Debug mode check insufficient | `security_headers.py:48` |
| SEC-010 | LOW | A07: Auth Failures | No session limit enforcement | `jwt_revocation_service.py:27` |
| SEC-011 | LOW | A03: Injection | Exception re-raising loses context | `users/routes.py:67-68` |
| SEC-012 | LOW | A09: Logging Failures | Request body not sanitized in logs | `logging.py:21-45` |
| SEC-013 | LOW | A05: Misconfiguration | CORS origins include localhost in example | `settings.py:31` |
| SEC-014 | INFO | A02: Crypto Failures | JWT secret minimum length not enforced | `settings.py:23` |
| SEC-015 | INFO | A06: Vulnerable Components | Dependencies need regular updates | `pyproject.toml:10-26` |
| SEC-016 | INFO | A05: Misconfiguration | Redis connection without TLS | `redis_client.py:18-22` |
| SEC-017 | INFO | Best Practice | Consider adding security.txt | N/A |

---

## Detailed Findings

### SEC-001: TOTP Secret Stored in Plaintext (HIGH)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/infrastructure/database/models/admin_user_model.py:41`

**Description:**  
TOTP secrets are stored in plaintext in the database. While the `.env.example` documents `TOTP_ENCRYPTION_KEY` for encryption, the actual model and TOTP service do not implement encryption.

```python
totp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

**Risk Assessment:**  
If the database is compromised, attackers can extract TOTP secrets and bypass 2FA for all users.

**Remediation:**
1. Encrypt TOTP secrets using AES-256-GCM with the `TOTP_ENCRYPTION_KEY`
2. Implement decrypt-on-read, encrypt-on-write in the TOTP service
3. Add migration to encrypt existing plaintext secrets

**Reference:** CWE-311 (Missing Encryption of Sensitive Data), OWASP A02:2025

---

### SEC-002: Docker Container Runs as Root (HIGH)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/Dockerfile:1-16`

**Description:**  
The Dockerfile does not specify a non-root user, meaning the application runs as root inside the container.

```dockerfile
FROM python:3.13-slim
WORKDIR /app
# ... no USER directive
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Risk Assessment:**  
Container escape vulnerabilities or application compromises can lead to host system access with root privileges.

**Remediation:**
```dockerfile
FROM python:3.13-slim

# Create non-root user
RUN groupadd -r cybervpn && useradd -r -g cybervpn cybervpn

WORKDIR /app
COPY --chown=cybervpn:cybervpn pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY --chown=cybervpn:cybervpn . .

USER cybervpn
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Reference:** CWE-250 (Execution with Unnecessary Privileges), OWASP A05:2025

---

### SEC-003: JWT Revocation Not Checked in Auth Dependency (MEDIUM)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/presentation/dependencies/auth.py:22-30`

**Description:**  
The `get_current_user` dependency decodes JWT tokens but does not check the revocation list implemented in `JWTRevocationService`.

```python
async def get_current_user(...):
    try:
        payload = auth_service.decode_token(credentials.credentials)
        # No revocation check: await revocation_service.is_revoked(payload.get("jti"))
        ...
```

**Risk Assessment:**  
Revoked tokens (from logout or logout-all) remain valid until expiration, defeating the purpose of token revocation.

**Remediation:**
1. Inject Redis client into the auth dependency
2. Check `JWTRevocationService.is_revoked(jti)` before returning the user
3. Return 401 if token is revoked

**Reference:** CWE-613 (Insufficient Session Expiration), OWASP A07:2025

---

### SEC-004: Default Credentials in .env File (MEDIUM)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/.env:4-5`

**Description:**  
The `.env` file contains weak test credentials:
```
REMNAWAVE_TOKEN=test_token
JWT_SECRET=test_secret_key_minimum_32_characters_long
```

While `.env` is gitignored, these values are problematic if accidentally deployed.

**Risk Assessment:**  
Predictable JWT secret allows token forgery. Test tokens may be accepted by production services.

**Remediation:**
1. Generate cryptographically random secrets:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
2. Add startup validation in production to reject known weak secrets
3. Consider using a secrets manager (HashiCorp Vault, AWS Secrets Manager)

**Reference:** CWE-798 (Use of Hard-coded Credentials), OWASP A02:2025

---

### SEC-005: Client Fingerprint Includes Unstable IP Address (MEDIUM)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/shared/security/fingerprint.py:38-39`

**Description:**  
The client fingerprint includes IP address, which changes frequently for mobile users.

```python
if request.client:
    client_ip = request.client.host
components.append(f"ip:{client_ip}")
```

**Risk Assessment:**  
When `ENFORCE_TOKEN_BINDING=true`, mobile users may be logged out when IP changes (carrier transitions, WiFi/cellular switches).

**Remediation:**
1. Remove IP from fingerprint for mobile auth
2. Use device-specific identifiers (device_id from mobile request) instead
3. Create separate fingerprint strategies for web and mobile

**Reference:** OWASP MASVS-AUTH-2

---

### SEC-006: Mobile `/me` Endpoint Missing IDOR Protection (MEDIUM)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/mobile_auth/routes.py:360-384`

**Description:**  
The endpoint extracts `user_id` from JWT but does not verify the user exists and is active before returning data.

```python
async def get_me(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    ...
    result = await use_case.execute(user_id)  # No active check
```

**Risk Assessment:**  
A valid JWT for a deactivated user could still access their profile data.

**Remediation:**
1. Verify user is active in `get_current_mobile_user_id`
2. Or check `user.status == "active"` in the use case before returning data

**Reference:** CWE-639 (Authorization Bypass Through User-Controlled Key), OWASP A01:2025

---

### SEC-007: Sensitive Data in Audit Log Details (MEDIUM)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/auth/registration.py:40-51`

**Description:**  
Registration audit logs store email and login in plaintext:

```python
await audit_repo.create(
    event_type="registration_attempt",
    details={
        "success": success,
        "email": email,  # PII stored
        "login": login,  # PII stored
        ...
    },
)
```

**Risk Assessment:**  
Audit logs may be retained longer than user data, violating data minimization principles (GDPR).

**Remediation:**
1. Hash or truncate email in audit logs: `email[:3] + "***" + email.split("@")[1]`
2. Store user_id reference instead of raw PII
3. Implement audit log retention policy

**Reference:** CWE-532 (Insertion of Sensitive Information into Log File), OWASP A09:2025

---

### SEC-008: Swagger UI Enabled by Default (LOW)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/config/settings.py:74`

**Description:**  
```python
swagger_enabled: bool = True  # MED-7: Disable in production via env
```

Swagger UI exposes API documentation which may reveal sensitive endpoints.

**Risk Assessment:**  
Information disclosure risk if deployed without setting `SWAGGER_ENABLED=false`.

**Remediation:**
1. Default to `False` in settings
2. Add startup warning if enabled in production environment
3. Protect Swagger with authentication if needed

**Reference:** CWE-200 (Exposure of Sensitive Information), OWASP A05:2025

---

### SEC-009: Debug Mode Check Insufficient (LOW)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/presentation/middleware/security_headers.py:48`

**Description:**  
HSTS header only added when `settings.debug` is False, but this doesn't account for staging environments:

```python
if not settings.debug:
    response.headers["Strict-Transport-Security"] = ...
```

**Risk Assessment:**  
HSTS may not be applied in staging if debug is disabled there.

**Remediation:**
Check `settings.environment == "production"` instead of `not settings.debug`.

**Reference:** OWASP A05:2025

---

### SEC-010: No Session Limit Enforcement (LOW)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/application/services/jwt_revocation_service.py:27`

**Description:**  
`MAX_TOKENS_PER_USER = 10` is defined but not enforced:

```python
MAX_TOKENS_PER_USER = 10  # Limit concurrent sessions
# ... but _prune_user_tokens only removes expired, doesn't enforce limit
```

**Risk Assessment:**  
Users can accumulate unlimited active sessions, increasing attack surface.

**Remediation:**
Implement FIFO eviction when `MAX_TOKENS_PER_USER` is exceeded.

**Reference:** CWE-770 (Allocation of Resources Without Limits), OWASP A07:2025

---

### SEC-011: Exception Re-raising Loses Context (LOW)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/users/routes.py:67-68`

**Description:**  
```python
except Exception:
    raise  # No logging, context lost
```

**Risk Assessment:**  
Makes debugging and incident response difficult.

**Remediation:**
Log exception with context before re-raising, or use structured exception handlers.

**Reference:** CWE-755 (Improper Handling of Exceptional Conditions), OWASP A09:2025

---

### SEC-012: Request Body Not Sanitized in Logs (LOW)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/presentation/middleware/logging.py:21-45`

**Description:**  
Logging middleware sanitizes URLs but not request bodies. If body logging is added, passwords could be leaked.

**Risk Assessment:**  
Low - body is not currently logged, but future changes could introduce leaks.

**Remediation:**
Document that body logging should use sanitization if added.

**Reference:** CWE-532, OWASP A09:2025

---

### SEC-013: CORS Origins Include Localhost (LOW)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/config/settings.py:31`

**Description:**  
```python
cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
```

Default includes localhost which is development-only.

**Risk Assessment:**  
If deployed without overriding, localhost may be accepted as valid origin.

**Remediation:**
Default to empty list `[]` in settings, require explicit configuration.

**Reference:** CWE-942 (Overly Permissive Cross-domain Whitelist), OWASP A05:2025

---

### SEC-014: JWT Secret Minimum Length Not Enforced (INFO)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/config/settings.py:23`

**Description:**  
No validation that JWT secret meets minimum length for security (256 bits recommended for HS256).

**Risk Assessment:**  
Weak secrets could be brute-forced.

**Remediation:**
Add Pydantic validator to require minimum 32-character secret for HS256.

**Reference:** RFC 7518 Section 3.2

---

### SEC-015: Dependencies Need Regular Updates (INFO)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/pyproject.toml:10-26`

**Description:**  
Dependencies should be regularly scanned for vulnerabilities.

**Remediation:**
1. Add `pip-audit` or `safety` to CI pipeline
2. Enable Dependabot/Renovate for automatic PR creation
3. Pin minor versions for stability

**Reference:** OWASP A06:2025

---

### SEC-016: Redis Connection Without TLS (INFO)

**Affected File:** `/home/beep/projects/VPNBussiness/backend/src/infrastructure/cache/redis_client.py:18-22`

**Description:**  
```python
_redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,  # redis:// not rediss://
    ...
)
```

No TLS for Redis connection.

**Risk Assessment:**  
Data in transit is unencrypted. Low risk if Redis is on localhost/private network.

**Remediation:**
Use `rediss://` URL scheme for TLS in production with external Redis.

**Reference:** CWE-319 (Cleartext Transmission of Sensitive Information)

---

### SEC-017: Consider Adding security.txt (INFO)

**Description:**  
No `/.well-known/security.txt` endpoint for security researchers.

**Remediation:**
Add security contact information per RFC 9116.

**Reference:** RFC 9116

---

## Positive Security Controls

The following security controls are **properly implemented**:

### Authentication & Authorization

| Control | Implementation | Location |
|---------|---------------|----------|
| Password Hashing | Argon2id with OWASP 2025 params | `auth_service.py:19-24` |
| JWT Algorithm Allowlist | HS256/384/512, RS256/384/512, ES256 | `auth_service.py:29` |
| JWT Token Types | Separate access/refresh with `type` claim | `auth_service.py:74,129` |
| Token Rotation | Refresh tokens rotated on use | `refresh_token.py:123-148` |
| Brute Force Protection | Progressive lockout (30s/5min/30min/permanent) | `login_protection.py:30-35` |
| Password Policy | 12+ chars, uppercase, lowercase, digit, special | `password.py:39-95` |
| 2FA Implementation | TOTP with rate limiting and re-auth | `two_factor/routes.py` |
| RBAC | Permission-based access control | `permissions.py:6-89` |

### Input Validation

| Control | Implementation | Location |
|---------|---------------|----------|
| Pydantic Schemas | All API inputs validated | Throughout `schemas.py` files |
| Email Validation | `EmailStr` type | `schemas.py` |
| UUID Validation | `UUID` type with proper parsing | Repository layer |
| SQL Injection Prevention | SQLAlchemy ORM with parameterized queries | All repositories |

### Rate Limiting

| Control | Implementation | Location |
|---------|---------------|----------|
| Global Rate Limit | 100 req/min per IP with circuit breaker | `rate_limit.py:88-255` |
| Fail-Closed Behavior | 503 on Redis failure (configurable) | `rate_limit.py:141-148` |
| Auth Endpoint Limits | 5 login/min, 3 register/min | `mobile_rate_limit.py:32-34` |
| 2FA Rate Limit | 5 attempts/15 min | `two_factor/routes.py:46-47` |

### Security Headers

| Header | Value | Location |
|--------|-------|----------|
| X-Content-Type-Options | nosniff | `security_headers.py:42` |
| X-Frame-Options | DENY | `security_headers.py:43` |
| X-XSS-Protection | 1; mode=block | `security_headers.py:44` |
| Content-Security-Policy | Restrictive directives | `security_headers.py:25-36` |
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | `security_headers.py:49-51` |
| Referrer-Policy | strict-origin-when-cross-origin | `security_headers.py:45` |
| Permissions-Policy | Restrictive | `security_headers.py:58-60` |
| Cache-Control | no-store, max-age=0 | `security_headers.py:64-65` |

### CORS Configuration

| Control | Implementation | Location |
|---------|---------------|----------|
| Explicit Origins | List-based, no wildcards in production | `main.py:193-204` |
| Credentials Warning | Logs warning if `*` with credentials | `main.py:194-196` |

### OAuth Security

| Control | Implementation | Location |
|---------|---------------|----------|
| CSRF State Token | Redis-backed with IP validation | `oauth/routes.py:55-59` |
| Telegram Signature | HMAC-SHA256 validation | `telegram.py` (provider) |
| GitHub Code Exchange | Server-side token exchange | `github.py` (provider) |

### Secrets Management

| Control | Implementation | Location |
|---------|---------------|----------|
| SecretStr Types | For all sensitive config values | `settings.py:20-21,23,43` |
| .gitignore | `.env` files excluded | `.gitignore:29-30,46,100` |
| No Hardcoded Secrets | All secrets from environment | Throughout codebase |

### Error Handling

| Control | Implementation | Location |
|---------|---------------|----------|
| Generic Error Messages | No internal details leaked | `exception_handlers.py` |
| Request ID Tracking | X-Request-ID for correlation | `request_id.py`, handlers |
| Structured Logging | With sanitization enabled | `logging.py`, `sanitization.py` |

### Webhook Security

| Control | Implementation | Location |
|---------|---------------|----------|
| Signature Validation | HMAC-SHA256 with timing-safe comparison | `webhook_validator.py:10-11` |
| Constant-Time Compare | `hmac.compare_digest()` | `webhook_validator.py:11` |

---

## Recommendations Summary

### Immediate Actions (Before Production)

1. **Encrypt TOTP secrets** in database (SEC-001)
2. **Add non-root user** to Dockerfile (SEC-002)
3. **Implement JWT revocation check** in auth dependency (SEC-003)
4. **Generate strong production secrets** (SEC-004)
5. **Set `SWAGGER_ENABLED=false`** for production (SEC-008)

### Short-Term Improvements

6. Refactor fingerprint generation for mobile stability (SEC-005)
7. Add active user check to mobile auth (SEC-006)
8. Sanitize PII in audit logs (SEC-007)
9. Enforce MAX_TOKENS_PER_USER limit (SEC-010)

### Long-Term Enhancements

10. Implement TLS for Redis in production (SEC-016)
11. Add security.txt endpoint (SEC-017)
12. Set up automated dependency scanning (SEC-015)
13. Conduct penetration testing before launch

---

## Compliance Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| OWASP Top 10 2025 | Partial | SEC-001, SEC-003 need remediation |
| OWASP API Security Top 10 | Good | CSRF, rate limiting, input validation |
| GDPR (if applicable) | Partial | SEC-007 (audit log PII) needs attention |

---

## Appendix: Files Reviewed

- `/backend/src/main.py`
- `/backend/src/config/settings.py`
- `/backend/src/presentation/api/v1/auth/*`
- `/backend/src/presentation/api/v1/mobile_auth/*`
- `/backend/src/presentation/api/v1/oauth/*`
- `/backend/src/presentation/api/v1/two_factor/*`
- `/backend/src/presentation/api/v1/admin/*`
- `/backend/src/presentation/api/v1/users/*`
- `/backend/src/presentation/api/v1/webhooks/*`
- `/backend/src/presentation/dependencies/*`
- `/backend/src/presentation/middleware/*`
- `/backend/src/presentation/exception_handlers.py`
- `/backend/src/application/services/auth_service.py`
- `/backend/src/application/services/login_protection.py`
- `/backend/src/application/services/jwt_revocation_service.py`
- `/backend/src/application/use_cases/auth/*`
- `/backend/src/application/use_cases/mobile_auth/*`
- `/backend/src/infrastructure/database/repositories/*`
- `/backend/src/infrastructure/database/models/*`
- `/backend/src/infrastructure/cache/redis_client.py`
- `/backend/src/infrastructure/totp/totp_service.py`
- `/backend/src/infrastructure/remnawave/webhook_validator.py`
- `/backend/src/shared/validators/password.py`
- `/backend/src/shared/security/fingerprint.py`
- `/backend/src/shared/logging/sanitization.py`
- `/backend/Dockerfile`
- `/backend/pyproject.toml`
- `/backend/.env`
- `/backend/.env.example`
- `/.gitignore`

---

**Report Generated:** 2026-02-05  
**Next Audit Recommended:** 2026-05-05 (quarterly)
