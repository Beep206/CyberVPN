# S1-OBS-002 — PII Scrubbing Evidence

Date: 2026-05-06  
Revalidated: 2026-05-09  
Task ID: `S1-OBS-002`  
Scope: local/no-cost Sentry and log redaction proof for S1 critical surfaces  
Result: completed locally and revalidated; live Sentry org/project scrub-rule proof remains required before go-live

## Decision

For S1 Controlled Public Beta, observability must not expose:

- cookies, `Set-Cookie`, bearer tokens or internal observability headers;
- Telegram webhook secret headers and Mini App `initData` / `tgWebAppData`;
- OAuth access/refresh/id tokens, auth codes and state;
- TOTP/OTP/password values;
- provider payment identifiers, invoice/checkout identifiers and raw payment payloads;
- Remnawave/OpenBao/NATS/OpenTofu markers;
- VPN config material such as `vless://`, `vmess://`, `trojan://`, `ss://`, WireGuard/config/subscription URLs;
- email, username and IP address in Sentry `user` context.

Safe operational identifiers may remain where needed, for example internal `user.id`, `provider_name`, queue name, region and request id.

## Implementation Completed

- Extended frontend and admin `scrubSentryEvent` to redact sensitive `extra` and `contexts` values, not only request/user fields.
- Added frontend/admin value-level filtering for pasted VPN config URLs and S1 sensitive query-style strings.
- Added `x-telegram-bot-api-secret-token` to frontend/admin/backend/bot Sentry header redaction.
- Extended backend, task-worker and Telegram Bot Sentry scrubbers with S1 markers for OAuth, TOTP, Telegram init data, checkout, invoice and value-level config URL detection.
- Extended backend log sanitization for S1 OAuth/Telegram/payment query parameters, internal/Telegram secret headers and config-delivery path parameters.
- Updated `docs/observability/sentry/privacy-baseline.json` and `07-privacy-pii-scrubbing-and-replay-policy.md` with the S1 redaction classes.

## Redaction Matrix

| Surface | Sentry event scrubbed | Log/path scrubbed | Notes |
|---|---:|---:|---|
| Frontend web / Mini App | Yes | N/A in this task | Browser request/user/extra/context redaction; replay still uses `maskAllText` and `blockAllMedia` from S1-OBS-001 |
| Admin web | Yes | N/A in this task | Admin payment/support contexts filtered; safe action/provider names can remain |
| Backend API | Yes | Yes | Sentry `before_send`, transaction URL stripping and backend logging utilities covered |
| Telegram Bot | Yes | Support text redaction already existed; Sentry redaction extended | Webhook secret header and Telegram payload/init data covered |
| Task worker | Yes | N/A in this task | Worker extra/context payloads covered before Sentry export |

## Validation

| Command | Result |
|---|---|
| `cd frontend && npm run test:run -- src/shared/lib/__tests__/sentry-privacy.test.ts src/__tests__/sentry-config.test.ts` | PASS: 2 files, 10 tests |
| `cd admin && npm run test:run -- src/shared/lib/__tests__/sentry-privacy.test.ts src/__tests__/sentry-config.test.ts` | PASS: 2 files, 10 tests |
| `cd backend && uv run pytest tests/unit/test_sentry_privacy.py tests/unit/shared/test_logging_sanitization.py -q --no-cov` | PASS: 5 tests |
| `cd services/telegram-bot && uv run pytest tests/unit/test_main.py::test_before_send_scrubs_sensitive_fields -q --no-cov` | PASS: 1 test |
| `cd services/task-worker && uv run pytest tests/unit/test_observability.py -q --no-cov` | PASS: 1 test |
| `python3 scripts/validate-sentry-privacy.py` | PASS: 20 privacy baseline expectations validated |
| `python3 scripts/validate-s1-sentry-critical-projects.py` | PASS: S1 Sentry critical project contract still valid |
| `cd frontend && npm run lint -- src/shared/lib/sentry-privacy.ts src/shared/lib/__tests__/sentry-privacy.test.ts` | PASS |
| `cd admin && npm run lint -- src/shared/lib/sentry-privacy.ts src/shared/lib/__tests__/sentry-privacy.test.ts` | PASS |
| `cd backend && uv run ruff check src/shared/observability.py src/shared/logging/sanitization.py tests/unit/test_sentry_privacy.py tests/unit/shared/test_logging_sanitization.py` | PASS |
| `cd services/telegram-bot && uv run ruff check src/main.py tests/unit/test_main.py` | PASS |
| `cd services/task-worker && uv run ruff check src/observability.py tests/unit/test_observability.py` | PASS |

## 2026-05-09 Revalidation

This revalidation was run as the `S1-OBS-002` live PII scrubbing evidence follow-up. No live Sentry organization/token/project/DSN values or `sentry-cli` are available in this local/no-cost workspace, so this proves the repository privacy/redaction contract only. It does not prove live Sentry server-side scrubber settings or deployed event/log redaction.

Environment presence check was performed without printing secret values:

```text
SENTRY_URL=missing
SENTRY_AUTH_TOKEN=missing
SENTRY_ORG=missing
SENTRY_PROJECT=missing
NEXT_PUBLIC_SENTRY_DSN=missing
SENTRY_DSN=missing
SENTRY_RELEASE=missing
NEXT_PUBLIC_SENTRY_RELEASE=missing
sentry-cli=missing
```

Revalidation results:

| Check | Result |
|---|---|
| `cd frontend && npm run test:run -- src/shared/lib/__tests__/sentry-privacy.test.ts src/__tests__/sentry-config.test.ts` | PASS: `2` files, `10` tests |
| `cd admin && npm run test:run -- src/shared/lib/__tests__/sentry-privacy.test.ts src/__tests__/sentry-config.test.ts` | PASS: `2` files, `10` tests |
| `cd backend && uv run pytest tests/unit/test_sentry_privacy.py tests/unit/shared/test_logging_sanitization.py -q --no-cov` | PASS: `5` tests |
| `cd services/telegram-bot && uv run pytest tests/unit/test_main.py::test_before_send_scrubs_sensitive_fields -q --no-cov` | PASS: `1` test |
| `cd services/task-worker && uv run pytest tests/unit/test_observability.py -q --no-cov` | PASS: `1` test |
| `python3 scripts/validate-sentry-privacy.py` | PASS: `20` privacy baseline expectations validated |
| `python3 scripts/validate-s1-sentry-critical-projects.py` | PASS: S1 critical Sentry contract still valid |
| Frontend/Admin targeted lint | PASS |
| Backend/Bot/Worker targeted `ruff check` | PASS |

## Live Evidence Readiness Matrix

| Live evidence item | Current state | Required go-live evidence |
|---|---|---|
| Sentry org scrubber settings | Not available locally | Export/screenshot proving default scrubbers and S1 custom rules are enabled |
| Prevent IP storage | Not available locally | Sentry setting or equivalent org/project proof attached |
| Replay masking | Local SDK config only | Live replay setting/screenshots proving auth/payment/admin text is masked or disabled |
| Safe Sentry events | Not possible without live DSNs | One safe event per S1 critical surface showing no raw cookies, auth headers, config URLs, payment IDs, email or IP |
| Deployed backend logs | Not available locally | Redacted staging/prod log sample for auth/payment/provisioning/config-delivery path |
| Provider/Telegram payloads | Local scrubber tests only | Live or staged event samples showing Telegram init data, webhook secrets and provider payloads are filtered |

## Demo

| Component | Feature | Status |
|---|---|---|
| Frontend/Admin | Browser Sentry event PII/config/payment redaction | PASS |
| Backend API | Sentry `before_send`, transaction URL stripping and log sanitization | PASS |
| Telegram Bot | Webhook secret, Telegram payload and support/config redaction | PASS |
| Task worker | Payment/OAuth/TOTP/support/config context redaction | PASS |
| Privacy baseline | Repo-wide Sentry privacy baseline validator | PASS |
| Live Sentry | Org scrubbers, prevent-IP, replay masking, real events and deployed logs | BLOCKED externally: credentials/CLI/organization are not present in this workspace |

## Official Documentation Used

- Sentry JavaScript options: `https://docs.sentry.io/platforms/javascript/configuration/environments/`
- Sentry JavaScript data collection notes: `https://docs.sentry.io/platforms/javascript/guides/remix/data-management/data-collected/`
- Sentry Python options: `https://docs.sentry.io/platforms/python/configuration/options/`

## Security Review

| Check | Result |
|---|---|
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate advisories remain unrelated and tracked elsewhere |
| Secret scan over touched code/docs | PASS: no Sentry DSN, private key, GitHub token or OpenAI-style key patterns found |
| Dangerous runtime pattern scan over touched code | PASS: no matches |

2026-05-09 revalidation security checks:

| Check | Result |
|---|---|
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate Next/PostCSS advisory remains tracked because the force fix proposes a breaking downgrade path |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `backend/` | PASS: no known vulnerabilities found |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `services/telegram-bot/` | PASS: no known vulnerabilities found |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `services/task-worker/` | PASS: no known vulnerabilities found |
| Secret-pattern scan over updated `S1-OBS-002` source docs | PASS: no matches |
| Dangerous-pattern scan over updated `S1-OBS-002` source docs | PASS: no matches |

## Not Proven Yet

This evidence is local and repository-level. Before go-live, attach:

- live Sentry org/project server-side scrubber settings matching `privacy-baseline.json`;
- proof that "Prevent Storing IP Addresses" or equivalent Sentry setting is enabled;
- one forced non-sensitive event per S1 surface visible in Sentry without raw cookies, auth headers, config URLs, payment IDs or user email/IP;
- one redacted backend log sample from deployed staging/production path;
- confirmation that Sentry replay captures no auth/payment/admin text beyond masked placeholders.

## Acceptance Result

`S1-OBS-002` is **completed locally and revalidated on 2026-05-09** as Sentry/log PII scrubbing proof.

Go-live remains blocked by live Sentry scrub-rule proof, deployed dashboard/live target proof and live Telegram/email alert delivery.

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-OBS-002` as item `23` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| `npm --prefix frontend run test:run -- src/shared/lib/__tests__/sentry-privacy.test.ts src/__tests__/sentry-config.test.ts` | PASS: `2` files, `10` tests |
| `npm --prefix admin run test:run -- src/shared/lib/__tests__/sentry-privacy.test.ts src/__tests__/sentry-config.test.ts` | PASS: `2` files, `10` tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_sentry_privacy.py tests/unit/shared/test_logging_sanitization.py -q --no-cov` | PASS: `5` tests |
| `cd services/telegram-bot && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_main.py::test_before_send_scrubs_sensitive_fields -q --no-cov` | PASS: `1` test |
| `cd services/task-worker && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_observability.py -q --no-cov` | PASS: `1` test |
| `python3 scripts/validate-sentry-privacy.py` | PASS: `20` privacy baseline expectations validated |
| `python3 scripts/validate-s1-sentry-critical-projects.py` | PASS |
| Frontend/admin targeted lint | PASS |
| Backend/bot/worker targeted `ruff check` | PASS |

`S1-OBS-003` was completed locally in `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md`, and `S1-OBS-004` was completed locally in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`.

Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
