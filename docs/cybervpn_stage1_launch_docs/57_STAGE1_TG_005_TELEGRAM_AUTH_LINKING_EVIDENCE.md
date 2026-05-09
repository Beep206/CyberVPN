# 57. Stage 1 Evidence - S1-TG-005 Telegram Auth and Linking

Date: 2026-05-04

Backlog ID: `S1-TG-005`

Related backlog ID: `S1-AUTH-005`

Status: completed locally for backend/client contract, no-silent-merge policy and conflict handling. Real Telegram client, BotFather domain/token, staging webhook and deployed HTTPS evidence remain required before S1 go-live.

## Objective

Prove that Stage 1 Telegram authentication and linking are safe enough for Controlled Public Beta implementation:

- Telegram Mini App `initData` is validated server-side before authentication;
- Telegram bot deep-link token is one-time and maps only to an existing Telegram-linked user;
- Telegram magic-link polling consumes pending sessions and starts a web session;
- authenticated Telegram account linking blocks unsafe account merges;
- Telegram identity is matched by `telegram_id`, not by email;
- malformed Telegram identity data does not create or link accounts.

## Official Docs Checked

| Surface | Source |
|---|---|
| Telegram Mini App `initData` validation and server trust boundary | https://core.telegram.org/bots/webapps |
| Telegram Login Widget authorization fields and HMAC validation | https://core.telegram.org/widgets/login |

## Implemented Policy

| Rule | Local implementation |
|---|---|
| Telegram is not an email proof | `OAuthLoginUseCase` no longer uses email lookup for Telegram auto-linking |
| Telegram auto-link key | Existing users are matched only by `telegram_id` |
| New Telegram user identity | New Telegram OAuth users store `telegram_id` and do not inherit provider email as CyberVPN account email |
| Malformed Telegram ID | Invalid non-numeric Telegram IDs raise `ValueError` before repository writes |
| Provider identity conflict | `AccountLinkingUseCase` rejects provider identity already linked to another user |
| Same user / same identity retry | Linking is idempotent and updates provider metadata without duplicate rows |
| Same user / different identity | Linking a second Telegram identity to the same user is rejected |
| API conflict response | Telegram OAuth callback maps linking conflicts to HTTP `409` instead of uncaught database errors |

## Repository Changes

Backend runtime:

- `backend/src/application/use_cases/auth/oauth_login.py`
  - rejects invalid Telegram IDs;
  - matches Telegram users by `telegram_id`;
  - avoids silent merge by email for Telegram;
  - stores `telegram_id` on newly created Telegram users.
- `backend/src/application/use_cases/auth/account_linking.py`
  - adds explicit provider identity conflict checks;
  - adds same-provider/same-user conflict checks;
  - makes repeated same-identity linking idempotent.
- `backend/src/presentation/api/v1/oauth/routes.py`
  - maps linking `ValueError` to HTTP `409` for Telegram/GitHub/Facebook-style linking callbacks.

Tests:

- `backend/tests/unit/application/use_cases/auth/test_oauth_login.py`
  - added no-silent-merge-by-email and malformed Telegram ID tests.
- `backend/tests/unit/application/use_cases/auth/test_account_linking.py`
  - added account-linking conflict and idempotency tests.
- `backend/tests/unit/api/v1/test_oauth_telegram_linking.py`
  - added Telegram callback success and `409` conflict tests.

No frontend runtime code was changed for this task.

## Evidence Matrix

| Flow | Proof |
|---|---|
| Mini App initData | HMAC, tamper, missing hash, expired/future auth date and invalid JSON tests pass |
| Mini App auth use case | Existing user login, new user auto-registration, `telegram_id` persistence and Remnawave best-effort behavior pass |
| Bot deep-link auth | Generated token exchange, expired token, already-used token, missing user, deactivated user and 2FA pending path pass |
| Telegram magic-link web login | Pending/complete/consume session tests pass; completed status sets auth cookies in local ASGI test |
| Telegram OAuth login | Existing OAuth account, existing `telegram_id` user, new Telegram user, 2FA and token issuance tests pass |
| No silent email merge | Telegram OAuth does not call `get_by_email`; matching is by `telegram_id`; new Telegram user has `email=None` |
| Account linking conflict | Identity already linked elsewhere and different identity for same provider are rejected |
| API conflict behavior | `/api/v1/oauth/telegram/callback` returns `409` on link conflict |
| Frontend client contract | `authApi.telegramMiniApp`, bot-link, Telegram link callback and Mini App auth provider tests pass |

## Local Evidence Commands

Backend OAuth/linking component and API contract suite:

```bash
cd backend
uv run pytest --no-cov \
  tests/unit/application/use_cases/auth/test_oauth_login.py \
  tests/unit/application/use_cases/auth/test_account_linking.py \
  tests/unit/api/v1/test_oauth_telegram_linking.py \
  tests/unit/api/v1/test_oauth_magic_link.py \
  -q
```

Result:

```text
55 passed in 0.54s
```

Backend Telegram Mini App, bot-link and HMAC validation suite:

```bash
cd backend
uv run pytest --no-cov \
  tests/unit/application/use_cases/auth/test_telegram_miniapp.py \
  tests/unit/application/use_cases/auth/test_telegram_bot_link.py \
  tests/integration/api/v1/auth/test_telegram_miniapp_flow.py \
  tests/integration/api/v1/auth/test_telegram_bot_link_flow.py \
  tests/unit/infrastructure/oauth/test_telegram_miniapp.py \
  tests/application/services/test_telegram_auth.py \
  -q
```

Result:

```text
48 passed in 0.52s
```

Frontend Telegram auth client/provider suite:

```bash
cd frontend
npm run test:run -- \
  src/lib/api/__tests__/auth.test.ts \
  src/features/auth/components/__tests__/TelegramMiniAppAuthProvider.test.tsx
```

Result:

```text
Test Files  2 passed (2)
Tests       86 passed (86)
```

Static check for changed Python files:

```bash
cd backend
uv run ruff check \
  src/application/use_cases/auth/oauth_login.py \
  src/application/use_cases/auth/account_linking.py \
  src/presentation/api/v1/oauth/routes.py \
  tests/unit/application/use_cases/auth/test_oauth_login.py \
  tests/unit/application/use_cases/auth/test_account_linking.py \
  tests/unit/api/v1/test_oauth_telegram_linking.py
```

Result:

```text
All checks passed!
```

Diff whitespace check:

```bash
git diff --check
```

Result:

```text
passed with no output
```

Security dependency audit:

```bash
cd frontend
npm audit --audit-level=high
```

Result:

```text
0 high/critical vulnerabilities. npm audit still reports 2 moderate advisories in Next's transitive PostCSS path; the suggested force fix would downgrade Next and is not applied.
```

Python dependency audit:

```bash
cd backend
uvx pip-audit --progress-spinner off
```

Result:

```text
No known vulnerabilities found
```

Focused secret and dangerous-pattern scan:

```bash
rg -n "(BOT_TOKEN|TELEGRAM_BOT_TOKEN|telegram_bot_token|WEBHOOK_SECRET|OAUTH_CLIENT_SECRET|BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9_]{20,})" \
  backend/src/application/use_cases/auth \
  backend/src/presentation/api/v1/oauth \
  backend/tests/unit/application/use_cases/auth \
  backend/tests/unit/api/v1/test_oauth_telegram_linking.py \
  docs/cybervpn_stage1_launch_docs/57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md

rg -n "\\b(eval|exec)\\s*\\(|subprocess\\.|os\\.system\\(|text\\(f\\\"|text\\(f'|\\.raw\\(|innerHTML|dangerouslySetInnerHTML" \
  backend/src/application/use_cases/auth/oauth_login.py \
  backend/src/application/use_cases/auth/account_linking.py \
  backend/src/presentation/api/v1/oauth/routes.py \
  backend/tests/unit/application/use_cases/auth/test_account_linking.py \
  backend/tests/unit/api/v1/test_oauth_telegram_linking.py \
  frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx \
  frontend/src/lib/api/auth.ts
```

Result:

```text
no matches
```

## Security Review Notes

| Check | Result |
|---|---|
| Secret handling | No Telegram bot token, webhook secret, OAuth secret or real `initData` was added |
| Account merge policy | Telegram cannot silently merge into an existing email account |
| Replay/token behavior | Mini App auth date and bot-link one-time token behavior are covered by local tests |
| Conflict behavior | Telegram link conflicts are explicit and user-safe with HTTP `409` |
| Provider token retention | Account-linking path continues using `build_stored_oauth_tokens`; no raw-token logging added |
| Production side effects | Tests use mocks/ASGI/local fixtures only; no BotFather, Telegram, Remnawave or payment provider calls |
| Dependency audit | Python audit clean; frontend audit has no high/critical findings, but tracks existing moderate Next/PostCSS advisory |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| BotFather `/setdomain` and Mini App domain configured for `cyber-vpn.net` staging/prod path | Open |
| Real staging bot token stored through approved secret process | Open |
| Redacted `getMe` and webhook/polling evidence for staging bot | Open |
| Real Telegram client proof with real `Telegram.WebApp.initData` against deployed HTTPS staging | Open |
| Real Telegram Login Widget/account-link callback proof with staging domain | Open |
| Deployed CORS/cookie/CSRF/rate-limit behavior in Telegram browser context | Open |
| Support escalation path for account-link conflicts, including audit/log evidence | Open |
| Production Telegram auth/linking smoke after RC tag | Open |

## Next ID

Next ID to execute: `S1-TG-006` - verify Telegram notifications.
