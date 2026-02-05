# API Security Requirements

## Authentication

### Bearer Token Authentication

All authenticated endpoints require a valid JWT access token:

```
Authorization: Bearer <access_token>
```

**Token Lifetime:**
- Access tokens: 15 minutes
- Refresh tokens: 7 days

### Refresh Token Flow

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<refresh_token>"
}
```

### Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <access_token>

# Revokes the current token
```

```
POST /api/v1/auth/logout-all
Authorization: Bearer <access_token>

# Revokes ALL user tokens (logout everywhere)
```

## Rate Limiting

All endpoints are rate-limited:

| Endpoint Type | Limit |
|--------------|-------|
| Authentication | 10/minute |
| API (authenticated) | 100/minute |
| WebSocket | Connection-based |

**Response Headers:**
- `Retry-After`: Seconds until rate limit resets

**Error Response:**
```json
{
  "detail": "Too many requests"
}
```

## Security Headers

All responses include:
- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (HTTPS only)
- `Cache-Control: no-store`

## Registration

### Invite-Only Mode (Default)

Registration requires an invite token:

```
POST /api/v1/auth/register?invite_token=<token>
Content-Type: application/json

{
  "login": "username",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "locale": "en-EN"
}
```

**Password Requirements:**
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Not in common passwords list

## Two-Factor Authentication

### Enable 2FA

Requires password re-authentication:

```
POST /api/v1/2fa/request-setup
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "current_password"
}
```

Response:
```json
{
  "secret": "<base32_secret>",
  "qr_uri": "otpauth://totp/CyberVPN:user?secret=..."
}
```

### Confirm 2FA

```
POST /api/v1/2fa/confirm-setup
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "code": "123456"
}
```

### Login with 2FA

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "login": "username",
  "password": "password",
  "totp_code": "123456"
}
```

## OAuth

### GitHub

```
GET /api/v1/oauth/github/authorize
```

Redirects to GitHub. After authorization:
```
GET /api/v1/oauth/github/callback?code=<code>&state=<state>
```

### Telegram

```
GET /api/v1/oauth/telegram/authorize
```

Redirects to Telegram widget. After authorization:
```
POST /api/v1/oauth/telegram/callback
Content-Type: application/json

{
  "id": 123456789,
  "first_name": "User",
  "auth_date": 1234567890,
  "hash": "<signature>"
}
```

**Security:** Telegram callback validates HMAC-SHA256 signature.

## WebSocket Authentication

### Get Ticket

```
POST /api/v1/ws/tickets
Authorization: Bearer <access_token>
```

Response:
```json
{
  "ticket": "<single_use_ticket>",
  "expires_at": "2026-02-05T12:00:00Z"
}
```

### Connect

```
ws://api.example.com/ws?ticket=<ticket>
```

**Ticket Properties:**
- Single-use (consumed on first connection)
- 30-second expiration
- IP-bound (must connect from same IP)

## Error Responses

### Authentication Errors

| Status | Meaning |
|--------|---------|
| 401 | Invalid or expired token |
| 403 | Insufficient permissions |
| 429 | Rate limit exceeded |

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 12 characters",
      "type": "value_error"
    }
  ]
}
```

## Audit Logging

All security-relevant actions are logged:
- Login attempts (success/failure)
- Registration attempts
- 2FA enable/disable
- Token revocation
- Admin actions

Access audit logs via admin API:
```
GET /api/v1/admin/audit-logs
Authorization: Bearer <admin_token>
```
