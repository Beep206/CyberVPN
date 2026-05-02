# Migration from Legacy Telegram Auth

## Current Legacy Endpoint

`POST /api/v1/mobile/auth/telegram/callback`

Accepts:

```json
{
  "auth_data": "legacy Telegram widget payload",
  "device": {}
}
```

## New OIDC Endpoint

`POST /api/v1/mobile/auth/telegram/oidc`

Accepts:

```json
{
  "id_token": "Telegram OIDC JWT",
  "device": {}
}
```

## Migration Strategy

Do not break the legacy endpoint immediately.

Use dual-stack migration.

## Migration Phases

### Phase 0 — Documentation And Contracts

- finalize docs
- finalize API contract
- finalize feature flag design

### Phase 1 — Backend OIDC Foundation

- add new OIDC endpoint
- add Telegram JWKS validation
- add user resolution logic
- keep legacy endpoint untouched

### Phase 2 — Mobile Native SDK Integration

- add native iOS bridge
- add native Android bridge
- add feature flag `telegram_native_login_enabled`
- when disabled, continue legacy flow

### Phase 3 — Internal And Staging Rollout

- internal builds use native flow
- staging bot/client ID used for full end-to-end validation
- legacy flow remains fallback path

### Phase 4 — Production Limited Rollout

- enable for a small production segment
- monitor success and failure metrics
- keep legacy path for rollback and older app versions

### Phase 5 — Legacy Deprecation

- keep old endpoint for backward compatibility while older mobile app versions remain supported
- remove only after:
  - new app adoption reaches target threshold
  - failure rate is acceptable
  - support confirms no active dependency on legacy path

## Mobile Feature Flag Logic

Recommended flags:

- `telegram_native_login_enabled`
- `telegram_native_login_ios_enabled`
- `telegram_native_login_android_enabled`

Recommended client behavior:

- if native flag is on, use native SDK path
- if native flag is off, use legacy Telegram flow or hide the button according to rollout policy

## Identity Migration

For users created by legacy Telegram flow:

- preserve current `telegram_id`
- populate `telegram_subject` on first successful OIDC login
- continue fallback lookup by legacy `telegram_id` during transition

## Support Window Recommendation

- keep legacy endpoint until unsupported mobile versions are below the chosen threshold
- only remove after explicit cutoff date and release-note communication

## Risks During Migration

- duplicate accounts if identity resolution is wrong
- support confusion if old and new flows behave differently
- 2FA inconsistency if native flow lands before pending TOTP support

## Migration Guardrails

- do not enable native production rollout before backend validation and 2FA flow are complete
- do not remove legacy endpoint before version telemetry proves it is safe

## Migration Metrics

- `legacy_telegram_login_total`
- `native_telegram_login_total`
- `legacy_to_oidc_identity_migrated_total`
- `telegram_duplicate_account_prevented_total`
