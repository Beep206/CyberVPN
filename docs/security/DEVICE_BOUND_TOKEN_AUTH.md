# Device-Bound Token Authentication Flow

## Overview

Replace plaintext credential storage with a device-bound token exchange system. After initial login, the device receives a long-lived device token that is cryptographically bound to the device's hardware identity. Biometric enrollment gates token usage.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  Mobile App  │────▶│  Backend API │────▶│  Database   │
│             │     │              │     │            │
│  SecureStorage    │  /mobile/auth │     │ device_tokens│
│  (device_token)   │  /biometric/* │     │ table       │
└─────────────┘     └──────────────┘     └────────────┘
```

## Token Types

| Token | Lifetime | Storage | Purpose |
|-------|----------|---------|---------|
| Access Token | 15 min | Memory | API authentication |
| Refresh Token | 7 days | SecureStorage | Token renewal |
| Device Token | 90 days | SecureStorage | Biometric re-auth |

## API Endpoints

### POST /mobile/auth/biometric/enroll

Enrolls the current device for biometric authentication. Called after successful login when user enables biometric login.

**Request:**
```json
{
  "device_id": "uuid-device-id",
  "device_fingerprint": "sha256-of-device-properties",
  "biometric_type": "fingerprint|face",
  "public_key": "base64-encoded-public-key"
}
```

**Response:**
```json
{
  "device_token": "opaque-device-bound-token",
  "expires_at": "2026-05-07T00:00:00Z"
}
```

**Notes:**
- The `device_fingerprint` is a SHA-256 hash of stable device properties (device ID, OS, model)
- The `public_key` is generated on-device using Android Keystore / iOS Secure Enclave
- The device token is bound to the device fingerprint and cannot be used on other devices

### POST /mobile/auth/biometric/authenticate

Exchanges a device token for access + refresh tokens after biometric verification.

**Request:**
```json
{
  "device_token": "opaque-device-bound-token",
  "device_id": "uuid-device-id",
  "challenge_response": "signed-challenge-with-private-key"
}
```

**Response:**
```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com"
  }
}
```

### DELETE /mobile/auth/biometric/revoke

Revokes the device token (called on logout or biometric enrollment change).

**Request:**
```json
{
  "device_id": "uuid-device-id"
}
```

## Flow Diagrams

### Initial Enrollment (after login)

```
1. User logs in with email/password → receives access + refresh tokens
2. User enables biometric login in settings
3. App generates keypair in Android Keystore / iOS Secure Enclave
4. App calls POST /biometric/enroll with public key + device info
5. Backend stores enrollment, returns device_token
6. App stores device_token in SecureStorage (biometric-gated)
7. App deletes plaintext credentials from storage
```

### Biometric Re-authentication (app unlock)

```
1. App detects lock state (background timeout)
2. App prompts for biometric verification via local_auth
3. On success, app reads device_token from SecureStorage
4. App signs a challenge with private key (Keystore/Secure Enclave)
5. App calls POST /biometric/authenticate with device_token + signature
6. Backend validates device_token + challenge signature
7. Backend returns fresh access + refresh tokens
8. App proceeds normally with new tokens
```

### Enrollment Change Detection

```
1. App checks BiometricService.hasEnrollmentChanged() on startup
2. If changed (fingerprints added/removed):
   a. Revoke device token via DELETE /biometric/revoke
   b. Clear SecureStorage credentials
   c. Require full re-login with email/password
   d. Prompt to re-enroll biometrics after login
```

## Database Schema

```sql
CREATE TABLE device_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES mobile_users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    device_fingerprint VARCHAR(64) NOT NULL,
    public_key TEXT NOT NULL,
    token_hash VARCHAR(64) NOT NULL,  -- SHA-256 of device_token
    biometric_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,

    UNIQUE(user_id, device_id),
    INDEX idx_device_tokens_token_hash (token_hash),
    INDEX idx_device_tokens_expires (expires_at) WHERE revoked_at IS NULL
);
```

## Security Considerations

1. **No plaintext credentials**: Device token replaces stored email/password
2. **Hardware binding**: Private key never leaves Keystore/Secure Enclave
3. **Challenge-response**: Prevents token replay attacks
4. **Enrollment change detection**: Re-auth required when biometrics change
5. **Token expiry**: 90-day max lifetime, auto-revoke on enrollment change
6. **Rate limiting**: Max 5 biometric auth attempts per 15 minutes
7. **Audit logging**: All enrollment/authentication/revocation events logged

## Migration Path

1. **Phase 1** (current): Biometric gates access to locally stored credentials
2. **Phase 2** (this design): Device-bound token exchange, no local credentials
3. **Phase 3** (future): FIDO2/WebAuthn passkey support
