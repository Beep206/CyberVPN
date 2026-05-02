# Backend OIDC Contract

## Goal

Определить минимальный backend contract для нового mobile Telegram Native Login без ломки legacy endpoint.

## New Endpoint

`POST /api/v1/mobile/auth/telegram/oidc`

## Public vs Internal Path Naming

Public API path:

- `POST /api/v1/mobile/auth/telegram/oidc`

Internal FastAPI router path after the `/api/v1` prefix:

- `POST /mobile/auth/telegram/oidc`

## Why A New Endpoint

Не следует сразу менять legacy endpoint:

- current: `POST /api/v1/mobile/auth/telegram/callback`
- target: `POST /api/v1/mobile/auth/telegram/oidc`

Такой dual-stack упрощает rollout и fallback.

Phase 1 contract assumption:

- mobile submits an SDK-issued Telegram `id_token`
- backend validates that `id_token`
- backend-side authorization code exchange is not required for this endpoint in Phase 1
- official public SDK examples currently show `clientId`, `redirectUri`, `scopes` and success `idToken`, but do not document `nonce` or `state`

## Request

```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "device": {
    "device_id": "string",
    "platform": "ios",
    "platform_id": "string",
    "os_version": "17.4",
    "app_version": "1.2.3",
    "device_model": "iPhone 15 Pro",
    "push_token": "optional"
  }
}
```

## Success Response

To align with the existing mobile auth namespace, reuse the current `AuthResponse` envelope:

```json
{
  "tokens": {
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "Bearer",
    "expires_in": 900
  },
  "user": {
    "id": "uuid",
    "email": "optional-or-synthetic",
    "username": "optional",
    "status": "active",
    "telegram_id": 123456789,
    "telegram_username": "optional",
    "subscription": null
  },
  "is_new_user": true
}
```

`token_type` must match the existing mobile auth contract exactly.

Do not introduce Telegram-specific casing or a Telegram-only response variant.

## Requires 2FA Response

```json
{
  "requires_2fa": true,
  "method": "totp",
  "tfa_token": "short-lived-signed-token"
}
```

## Proposed 2FA Completion Endpoint

`POST /api/v1/mobile/auth/2fa/complete`

Request:

```json
{
  "tfa_token": "short-lived-signed-token",
  "code": "123456"
}
```

Success response:

- same `AuthResponse` as above

Internal FastAPI router path after the `/api/v1` prefix:

- `POST /mobile/auth/2fa/complete`

## Authenticated Linking Endpoint

`POST /api/v1/mobile/auth/telegram/link`

Authorization:

- requires an existing CyberVPN mobile access token

Request:

```json
{
  "id_token": "Telegram OIDC JWT"
}
```

Success:

```json
{
  "linked": true,
  "provider": "telegram",
  "telegram_username": "optional"
}
```

Errors:

| HTTP | Code | Meaning |
|---|---|---|
| 401 | `UNAUTHORIZED` | current user is not authenticated |
| 409 | `TELEGRAM_IDENTITY_ALREADY_LINKED` | Telegram identity belongs to another user |
| 400 | `INVALID_TELEGRAM_ID_TOKEN` | token is invalid |

Important rule:

Linking must never create a new user.

Login may create a new user.

## Error Responses

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `INVALID_TELEGRAM_ID_TOKEN` | token malformed or unsupported |
| 401 | `TELEGRAM_ID_TOKEN_SIGNATURE_INVALID` | signature verification failed |
| 401 | `TELEGRAM_ID_TOKEN_CLAIMS_INVALID` | issuer, audience, time or subject invalid |
| 409 | `TELEGRAM_IDENTITY_ALREADY_LINKED` | identity belongs to another user |
| 409 | `PHONE_NUMBER_CONFLICT` | phone returned by Telegram conflicts with another account under explicit phone policy |
| 429 | `RATE_LIMITED` | abuse or repeated failures |

## Validation Requirements

Backend must:

- verify JWT signature using Telegram JWKS
- accept only supported signing algorithm
- verify `iss = https://oauth.telegram.org`
- verify `aud = TELEGRAM_OIDC_CLIENT_ID`
- verify `exp`
- verify `iat` within acceptable clock skew
- verify `sub` is present and non-empty
- reject tokens that fail any of the above checks

Phase 1 recommendation:

- Phase 1 does not require backend-managed `nonce`
- this is based on the current public SDK examples, which do not document `nonce` or `state`
- re-evaluate `nonce` support only if official SDK API documentation exposes it later

## JWT Header Validation

Backend must:

- reject missing `kid`
- reject unsupported `alg`
- reject `alg=none`
- select the JWKS key by `kid`
- refresh JWKS on unknown `kid`
- reject the token if the key is still unknown after refresh

## Recommended Internal Components

- `TelegramOidcSettings`
- `TelegramDiscoveryClient`
- `TelegramJwksClient`
- `TelegramIdTokenValidator`
- `MobileTelegramOidcUseCase`
- `MobileTelegramIdentityResolver`

## Claim Handling

Relevant supported Telegram claims from discovery and docs:

- `sub`
- `name`
- `preferred_username`
- `picture`
- `phone_number`
- `iss`
- `aud`
- `iat`
- `exp`

Recommendation:

- `sub` becomes the primary external identity key
- numeric Telegram user ID remains a compatibility field if present in the token payload
- `phone_number` remains optional and never becomes the sole primary key

## JWKS Caching

Recommended backend behavior:

- cache JWKS in memory or shared cache
- refresh on cache miss or unknown `kid`
- use short TTL plus background refresh
- fail closed if signature cannot be validated

## Rate Limiting

Apply dedicated rate limiting to:

- `POST /api/v1/mobile/auth/telegram/oidc`
- `POST /api/v1/mobile/auth/telegram/link`
- `POST /api/v1/mobile/auth/2fa/complete`

## Device Session Integration

On successful Telegram OIDC login:

- create or update device record
- issue first-party `access_token` and `refresh_token`
- bind session to `device_id`
- persist platform, app version and push token

## Backward Compatibility

- legacy endpoint stays available during migration
- new app versions call `/api/v1/mobile/auth/telegram/oidc`
- old app versions continue using `/api/v1/mobile/auth/telegram/callback`

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
- Telegram OIDC discovery: <https://oauth.telegram.org/.well-known/openid-configuration>
