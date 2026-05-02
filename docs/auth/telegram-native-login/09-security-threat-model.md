# Security Threat Model

## Assets

- Telegram Client Secret
- Telegram `id_token`
- Telegram identity claims
- Mobile access token
- Mobile refresh token
- Device sessions
- User Telegram identity
- Optional phone number claim

## Trust Boundaries

### Telegram SDK Boundary

The native SDK can return an `id_token`, but the app must not treat it as trusted identity without backend verification.

### Mobile Client Boundary

The client is untrusted for identity assertions.

The client may be rooted, intercepted or modified.

### Backend Boundary

Backend is the trust anchor for:

- token validation
- user resolution
- session issuance
- 2FA enforcement

## Threats And Mitigations

### Token Forgery

Risk:

- attacker sends a fake or modified `id_token`

Mitigation:

- verify signature using Telegram JWKS
- only accept supported algorithm
- verify `iss`, `aud`, `exp`, `iat`, `sub`

### Replay Attack

Risk:

- intercepted `id_token` is replayed

Mitigation:

- require valid `exp`
- apply strict `iat` and narrow clock skew
- rate limit by IP, device and user-agent where possible
- monitor repeated identical exchange attempts and anomaly spikes

Important note:

Device binding limits damage after a successful exchange, but does not fully prevent replay of a still-valid Telegram `id_token`.

If SDK `nonce` or `state` support is unavailable, replay mitigation must rely on:

- short token validity window
- strict `exp` and `iat`
- narrow clock skew
- rate limiting
- anomaly metrics for repeated exchange attempts

Phase 0 decision:

- public official SDK examples do not document `nonce` or `state`
- Phase 1 therefore treats them as unavailable unless official SDK API documentation changes

### Deep Link Hijacking

Risk:

- another app intercepts a custom-scheme callback

Mitigation:

- prefer Universal Links / App Links on `tg.dev`
- use custom schemes only as fallback
- verify expected host before handing callback URI to the SDK

### Account Takeover Via Identity Collision

Risk:

- wrong user gets linked because of legacy `telegram_id` or phone-number collision

Mitigation:

- use `sub` as the primary external identity key
- do not auto-link by phone number alone
- reject conflicting Telegram identity links

### 2FA Bypass

Risk:

- Telegram login bypasses TOTP for users who previously enabled it

Mitigation:

- require pending TOTP flow before issuing CyberVPN tokens

### Secret Exposure

Risk:

- Telegram Client Secret leaks into mobile app or logs

Mitigation:

- never embed Client Secret in mobile apps
- keep it only in backend secret storage
- redact from logs and debugging output

### SDK Supply Chain Risk

Risk:

- native SDK dependency changes behavior or artifact source becomes unavailable

Mitigation:

- pin SDK version
- verify dependency source
- monitor official SDK repository changes
- keep feature flag rollback available

### Sensitive Data Leakage In Logs

Risk:

- logs expose raw `id_token`, phone or session tokens

Mitigation:

- never log raw `id_token`
- never log access/refresh tokens
- never log full phone number
- hash or truncate identifiers when operationally needed

## Security Requirements

- Backend validation is mandatory before session creation.
- Unsupported JWT algorithms are rejected.
- JWKS failures fail closed, not open.
- Pending TOTP token must be short-lived and signed.
- Feature flags must allow emergency disablement of native Telegram login.

## Recommended Secure Defaults

- default scopes: `openid profile`
- `phone` disabled by default
- `telegram:bot_access` disabled by default
- App Links / Universal Links preferred in production

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
- Telegram OIDC discovery: <https://oauth.telegram.org/.well-known/openid-configuration>
