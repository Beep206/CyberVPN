# Observability and Runbook

## Metrics

Implemented Telegram-specific counters:

- `telegram_native_login_started_total{platform}`
- `telegram_native_login_completed_total{platform}`
- `telegram_native_login_failed_total{platform,reason}`
- `telegram_oidc_token_validation_failed_total{reason}`
- `telegram_oidc_user_created_total`
- `telegram_oidc_user_resolved_total{path}`
- `telegram_oidc_user_link_conflict_total{reason}`
- `telegram_oidc_requires_2fa_total{platform}`
- `telegram_oidc_device_registered_total{platform,action}`

Related funnel metrics already used by the dashboard:

- `auth_flow_events_total{channel="mobile",method="telegram",provider="telegram",step,status}`
- `auth_security_events_total{channel="mobile",method="telegram",provider="telegram",locale,error_type}`

Recommended validation-failure labels:

- `telegram_oidc_token_validation_failed_total{reason="signature_invalid"}`
- `telegram_oidc_token_validation_failed_total{reason="aud_invalid"}`
- `telegram_oidc_token_validation_failed_total{reason="iss_invalid"}`
- `telegram_oidc_token_validation_failed_total{reason="expired"}`
- `telegram_oidc_token_validation_failed_total{reason="jwks_unavailable"}`

Do not include raw identifiers in metric labels.

## Structured Log Events

Implemented backend events:

- `telegram_oidc_validation_started`
- `telegram_oidc_validation_succeeded`
- `telegram_oidc_validation_failed`
- `telegram_oidc_user_resolved`
- `telegram_oidc_requires_2fa`
- `telegram_oidc_device_registered`
- `telegram_oidc_link_succeeded`
- `telegram_oidc_link_conflict`
- `telegram_oidc_link_failed_invalid_token`
- `telegram_oidc_unlink_succeeded`

## Logging Rules

Do not log:

- raw `id_token`
- raw phone number
- access or refresh token
- full secrets

Allowed with care:

- hashed subject
- truncated Telegram numeric id
- internal user UUID
- platform and app version

## Dashboards

Implemented dashboard:

- `infra/grafana/dashboards/telegram-native-login-dashboard.json`

Current sections:

- overview KPIs for starts, completions, failure rate, MFA-required volume, link conflicts, and MFA completion rate
- throughput by platform
- validation failures by reason
- MFA required vs completed
- identity resolution paths
- device registration actions
- link and unlink success activity

Existing related dashboard:

- `infra/grafana/dashboards/auth-dashboard.json`

## Alerts

Implemented Prometheus alerts in `infra/prometheus/rules/auth_alerts.yml`:

- `TelegramNativeLoginFailureRateHigh`
- `TelegramNativeLoginPlatformFailureRateHigh`
- `TelegramOIDCValidationFailuresSpike`
- `TelegramOIDCLinkConflictSpike`

Operational intent:

- login success rate drops below threshold
- validation failures spike
- one platform fails disproportionately
- account-link conflicts spike

## Runbook

### Symptom: All Telegram Logins Fail

Check:

- BotFather client configuration
- backend `TELEGRAM_OIDC_CLIENT_ID`
- backend `TELEGRAM_OIDC_CLIENT_SECRET` if backend-side code exchange was explicitly enabled
- JWKS availability
- `aud` validation
- feature flags

### Symptom: iOS Callback Does Not Return To App

Check:

- Associated Domains capability
- Bundle ID
- Team ID
- BotFather iOS registration
- expected `tg.dev` domain

### Symptom: Android Callback Does Not Return To App

Check:

- Package Name
- SHA-256 fingerprint
- App Link host
- `android:autoVerify`
- release/debug keystore mismatch

### Symptom: User Gets Duplicate Account

Check:

- identity resolution order
- `telegram_subject` population
- legacy `telegram_id` fallback logic
- linking conflicts

### Symptom: TOTP Users Sign In Without Challenge

Check:

- native flow feature flags
- backend pending 2FA branch
- mobile handling of `requires_2fa`

## Support Notes

Support team should know:

- native Telegram login is not the same as legacy Telegram callback flow
- some issues are configuration problems, not user-account problems
- production rollback is feature-flag based
