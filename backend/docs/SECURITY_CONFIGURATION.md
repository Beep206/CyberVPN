# Security Configuration Guide

This document describes all security-related configuration options for the CyberVPN backend.

## Environment Variables

### Registration Security (CRIT-1)

| Variable | Default | Description |
|----------|---------|-------------|
| `REGISTRATION_ENABLED` | `false` | Enable/disable public registration |
| `REGISTRATION_INVITE_REQUIRED` | `true` | Require invite token for registration |
| `INVITE_TOKEN_EXPIRY_HOURS` | `24` | Invite token expiration time |

### JWT Configuration (MED-5)

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | **Required** | Secret key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ALLOWED_ALGORITHMS` | `["HS256", "HS384", "HS512"]` | Allowed algorithms (validated on startup) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `JWT_ISSUER` | `null` | Optional issuer claim |
| `JWT_AUDIENCE` | `null` | Optional audience claim |

### Rate Limiting (MED-1)

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Window size in seconds |
| `RATE_LIMIT_FAIL_OPEN` | `false` | Allow requests when Redis unavailable (development only) |

### Proxy Configuration (MED-8)

| Variable | Default | Description |
|----------|---------|-------------|
| `TRUST_PROXY_HEADERS` | `false` | Trust X-Forwarded-For headers |
| `TRUSTED_PROXY_IPS` | `[]` | List of trusted proxy IP addresses |

### TOTP Encryption (MED-6)

| Variable | Default | Description |
|----------|---------|-------------|
| `TOTP_ENCRYPTION_KEY` | `""` | AES encryption key for TOTP secrets |

**Note**: If not set, TOTP secrets are stored in plaintext. Always set in production!

### Swagger UI (MED-7)

| Variable | Default | Description |
|----------|---------|-------------|
| `SWAGGER_ENABLED` | `true` | Enable Swagger UI documentation |
| `DEBUG` | `false` | Debug mode (affects HSTS headers) |

### Telegram OAuth (CRIT-2)

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | `""` | Bot token for HMAC validation |
| `TELEGRAM_BOT_USERNAME` | `""` | Bot username for link generation |
| `TELEGRAM_AUTH_MAX_AGE_SECONDS` | `86400` | Max age for auth data (24h) |

### GitHub OAuth (CRIT-2)

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_CLIENT_ID` | `""` | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | `""` | GitHub OAuth app client secret |

### OTP Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OTP_EXPIRATION_HOURS` | `3` | OTP code expiration time |
| `OTP_MAX_ATTEMPTS` | `5` | Max verification attempts |
| `OTP_MAX_RESENDS` | `3` | Max resend attempts per window |
| `OTP_RESEND_WINDOW_HOURS` | `1` | Resend attempt tracking window |
| `OTP_RESEND_COOLDOWN_SECONDS` | `30` | Cooldown between resends |

## Security Features

### 1. Registration Protection (CRIT-1)

Registration is disabled by default. To enable:

```bash
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=true  # Recommended
```

Generate invite tokens via admin API:
```bash
POST /api/v1/admin/invites
Authorization: Bearer <admin_token>
{
  "email_hint": "user@example.com",
  "role": "VIEWER"
}
```

### 2. OAuth Security (CRIT-2)

- **Telegram**: HMAC-SHA256 signature validation on all callbacks
- **GitHub**: State tokens with 10-minute expiration for CSRF protection
- **Provider validation**: Only "github" and "telegram" accepted

### 3. 2FA Security (CRIT-3)

- Requires password re-authentication before enabling 2FA
- TOTP secrets stored encrypted (when TOTP_ENCRYPTION_KEY set)
- Backup codes stored hashed

### 4. Login Protection (HIGH-1)

Progressive lockout after failed attempts:
- 3 failures: 5 second delay
- 5 failures: 15 second delay
- 10 failures: 30 minute lockout

### 5. WebSocket Security (HIGH-2, HIGH-3)

- Topic authorization based on user role
- Ticket-based authentication (30-second single-use tokens)

### 6. Rate Limiting (MED-1)

- Fail-closed by default (503 when Redis unavailable)
- Circuit breaker after 3 consecutive failures

### 7. Security Headers (MED-2)

Automatically added to all responses:
- Content-Security-Policy
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy (restricts dangerous APIs)
- HSTS (production only)
- Cache-Control: no-store

## Production Checklist

- [ ] Set `REGISTRATION_ENABLED=false` or require invites
- [ ] Set strong `JWT_SECRET` (32+ characters)
- [ ] Set `TOTP_ENCRYPTION_KEY` for TOTP encryption
- [ ] Set `SWAGGER_ENABLED=false` in production
- [ ] Set `DEBUG=false`
- [ ] Set `RATE_LIMIT_FAIL_OPEN=false`
- [ ] Configure `TRUSTED_PROXY_IPS` if behind load balancer
- [ ] Ensure Redis is available for rate limiting
