> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Backlog ID: `S1-INFRA-006`
> Статус: inventory/policy completed for implementation entry. Does not replace `S1-INFRA-007` secrets scan or production secret store evidence.

# S1-INFRA-006 Secrets Inventory And Policy

## Purpose

Этот документ закрывает документационную часть `S1-INFRA-006`: инвентарь secret-surface без значений, правила разделения secrets по service/environment, interim storage policy до зрелого OpenBao/provider secret store, и draft rotation runbook.

Важно: этот документ не доказывает, что в репозитории нет leaked secrets. Это отдельная задача `S1-INFRA-007`. Также он не доказывает production credentials readiness для payment providers, Remnawave, OAuth, Telegram или mail providers.

## References Used

| Source | Why it matters for S1 |
|---|---|
| OWASP Secrets Management Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html | Centralization, least privilege, lifecycle, rotation, audit and incident response principles |
| Docker Compose secrets docs, https://docs.docker.com/compose/how-tos/use-secrets/ | Compose can mount secrets per service and avoid broad environment-variable exposure where images support file-based secrets |
| OpenBao KV secrets engine docs, https://openbao.org/docs/secrets/kv/ | Target-state generic secret storage with versioning options for S7 maturity or earlier if ready |
| NIST SP 800-57 Part 1 Rev. 5, https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final | General key-management policy, protection and lifecycle reference |

## Acceptance Result

| `S1-INFRA-006` requirement | Result | Evidence / note |
|---|---|---|
| Secrets separated by service and environment | Defined | Canonical paths and service matrix are recorded below |
| No production secrets in repo | Not proven here | Must be proven by `S1-INFRA-007`; tracked `infra/APIToken.txt` is a critical secret-sensitive artifact to remediate |
| Secrets inventory without values | Completed | This document records file paths, key names/classes and ownership only |
| Interim storage policy | Completed | See `S1 Interim Storage Policy` |
| Rotation runbook draft | Completed | See `Rotation Runbook Draft` |

## Evidence Commands

The inventory was collected with value-redacted commands. The outputs used only file paths and environment variable names.

```bash
git ls-files | rg '(^|/)(\.env|.*\.env|.*\.env\.example|.*vault.*\.yml|.*secret.*|.*credentials.*|APIToken\.txt|.*key.*\.pem|.*\.key)$'
find . -path './node_modules' -prune -o -path './.git' -prune -o -type f \( -name '.env' -o -name '.env.*' -o -name '*.env' -o -name '*.env.example' -o -name '*vault*.yml*' -o -name '*secret*' -o -name '*credentials*' -o -name 'APIToken.txt' \) -print
awk -F= '/^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/{print FILENAME ":" $1}' <redacted-env-file-list>
```

No secret values were printed into this evidence file.

## Current Local Secret-Sensitive Files

| Path | Git state observed | S1 meaning |
|---|---|---|
| `.env.example` | tracked | Root template. Contains AI provider key names; values must remain placeholders only |
| `backend/.env` | ignored/local | Local secret-bearing backend config. Must never be reused for staging/prod |
| `backend/.env.example` | tracked | Backend template. Must contain placeholders only |
| `frontend/.env.local` | ignored/local | Local frontend config. Must not contain private runtime secrets; public `NEXT_PUBLIC_*` only when browser-safe |
| `infra/.env` | ignored/local | Local Remnawave/infra secret-bearing config. Local/dev only |
| `infra/.env.example` | tracked | Infra template. Must contain placeholders only |
| `infra/APIToken.txt` | tracked | Critical finding: secret-sensitive token artifact is tracked despite `.gitignore`. Must be handled in `S1-INFRA-007`: rotate if ever valid, remove from Git tracking/history as required, and replace with approved secret storage |
| `infra/subscription/.env` | ignored/local | Local subscription-service Remnawave API token surface |
| `infra/subscription/.env.example` | tracked | Subscription-service template |
| `services/task-worker/.env` | ignored/local | Local worker secret-bearing config. Previous local smoke used a Remnawave token from here without printing its value |
| `services/task-worker/.env.example` | tracked | Worker template |
| `services/telegram-bot/.env` | ignored/local | Local bot secret-bearing config |
| `services/telegram-bot/.env.example` | tracked | Bot template |
| `admin/.env.example`, `frontend/.env.example`, `partner/.env.example` | untracked in current snapshot | Template surfaces exist locally but are not part of the current tracked baseline; decide inclusion during scope/freeze |
| `cybervpn_mobile/.env`, `cybervpn_mobile/.env.example` | local/untracked in current snapshot | Mobile is out of S1 runtime. Treat as secrets-sensitive and deferred to S4 |
| `.venv`, `target`, `htmlcov` matches | ignored/generated | Not canonical secret source, but scan tools must exclude or separately quarantine generated artifacts |

## Canonical Secret Naming And Storage Paths

S1 must use separate secret namespaces per environment and service. No secret may be shared between `local`, `staging` and `production`.

| Environment | Namespace pattern | Rule |
|---|---|---|
| Local dev | `local/<developer>/<service>/<key>` | May use ignored `.env` files. Tokens are disposable and never promoted |
| Staging | `stage1/staging/<service>/<key>` | Separate DB, Redis, Remnawave, bot, OAuth apps and payment test credentials |
| Production | `stage1/production/<service>/<key>` | Production-only credentials. No staging fallback. No value in Git, docs, screenshots, chat or issue tracker |
| CI | `ci/<workflow>/<purpose>/<key>` | CI-only secrets for builds/scans/releases. Production deploy secrets may only be available to protected deploy jobs |
| Evidence | `evidence/<date>/<gate>` | No values. Only key names, redacted screenshots and command output |

Target-state for S7 is OpenBao or provider-native secret stores with least-privilege read policies. S1 may use a simpler interim model if it is documented, access-limited, encrypted, auditable and backed by `S1-INFRA-007` scan evidence.

## Service Secret Inventory

| Surface | Secret/config classes | Observed key names/classes | S1 owner | S1 storage rule |
|---|---|---|---|---|
| Backend API | DB, Redis, JWT/session, TOTP encryption, OAuth, Remnawave, webhook, payment tokens, Telegram bot auth/Mini App/Stars token, Telegram internal secret, growth-code hash secret, Sentry | `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `TOTP_ENCRYPTION_KEY`, `OAUTH_TOKEN_ENCRYPTION_KEY`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_SECRET`, `REMNAWAVE_TOKEN`, `REMNAWAVE_WEBHOOK_SECRET`, `CRYPTOBOT_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_BOT_INTERNAL_SECRET`, `GROWTH_CODE_HASH_SECRET`, `SENTRY_DSN` | `@Sasha_Beep` | Runtime-only secret store/env. No browser exposure. Prod Swagger/CORS/cookie values must align with domains |
| Frontend customer app | API URLs, public observability, server-only auth transaction secrets | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_ENV`, `NEXT_PUBLIC_SENTRY_DSN`, `OAUTH_TRANSACTION_SECRET`, `PENDING_2FA_SECRET`, `SENTRY_DSN` | `@Sasha_Beep` | Only `NEXT_PUBLIC_*` may enter browser bundle. Server-only values must remain runtime-only |
| Admin app | API URLs, observability, admin 2FA/OAuth transaction secrets, Telegram internal link secret | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `FRONTEND_OBSERVABILITY_INTERNAL_SECRET`, `OAUTH_TRANSACTION_SECRET`, `PENDING_2FA_SECRET`, `TELEGRAM_BOT_INTERNAL_SECRET`, `SENTRY_DSN` | `@Sasha_Beep` | Admin domain protected; no secret visible in client bundle, logs or screenshots |
| Partner app | Same class as frontend/admin, but out of S1 public runtime | `NEXT_PUBLIC_API_URL`, `FRONTEND_OBSERVABILITY_INTERNAL_SECRET`, `OAUTH_TRANSACTION_SECRET`, `PENDING_2FA_SECRET`, `TELEGRAM_BOT_INTERNAL_SECRET`, `SENTRY_DSN` | `@Sasha_Beep` | Keep disabled/deferred until S3 unless explicitly re-approved |
| Telegram bot / Mini App | Bot token, bot identity, webhook secret, backend API key/internal secret, Redis, payment provider tokens, Telegram Stars/YooKassa toggles, Sentry | `BOT_TOKEN`, `BOT_USERNAME`, `TELEGRAM_BOT_STAGING_USERNAME`, `TELEGRAM_BOT_PRODUCTION_USERNAME`, `WEBHOOK_SECRET_TOKEN`, `BACKEND_API_KEY`, `AUTH_BACKEND_INTERNAL_SECRET`, `REDIS_URL`, `REDIS_PASSWORD`, `CRYPTOBOT_TOKEN`, `YOOKASSA_SECRET_KEY`, `SENTRY_DSN` | `@Sasha_Beep` | Separate staging and production bots. Telegram Stars paid flow only after evidence |
| Task worker / scheduler | DB, Redis queue, Remnawave API token, Telegram token, email provider API keys, metrics protection, payment token | `DATABASE_URL`, `REDIS_URL`, `REMNAWAVE_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `BREVO_API_KEY`, `RESEND_API_KEY`, `SMTP_SERVERS`, `CRYPTOBOT_TOKEN`, `METRICS_PROTECT`, `SENTRY_DSN` | `@Sasha_Beep` | Worker gets only secrets required for jobs it runs. Redis is not durable source of truth |
| Remnawave control plane | JWT auth/API token secrets, database, Telegram notification token, metrics/Grafana, API tokens | `JWT_AUTH_SECRET`, `JWT_API_TOKENS_SECRET`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `GRAFANA_ADMIN_PASSWORD`, `METRICS_PASS` | `@Sasha_Beep` | Separate staging/prod Remnawave; private/internal API; API tokens never committed |
| Remnawave subscription service | Remnawave API token and panel URL | `REMNAWAVE_API_TOKEN`, `REMNAWAVE_PANEL_URL` | `@Sasha_Beep` | Local-only now; production token must live in approved secret store |
| PostgreSQL 17 | DB users/passwords, app DB URLs, Remnawave DB URLs, backup encryption keys | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, backup encryption passphrase/key | `@Sasha_Beep` | Managed private-only production DB; separate DB/users for CyberVPN and Remnawave |
| Valkey/Redis | Redis URL/password, DB index, queue/cache/rate limit credentials | `REDIS_URL`, `REDIS_PASSWORD`, `REDIS_HOST`, `REDIS_PORT`, `REMNASHOP_REDIS_PASSWORD` | `@Sasha_Beep` | Private-only. Not durable source of truth. Rotate with queue drain/retry plan |
| Payment providers | Provider API keys, webhook/callback signing secrets, shop IDs, test/prod credentials | PayRam/NOWPayments/CryptoBot/Telegram Stars/Digiseller/YooKassa credential classes; observed `CRYPTOBOT_TOKEN`, `CRYPTOBOT_NETWORK`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_SHOP_ID`; CryptoBot S1 production credential inventory is in `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md` | Legal seller/project owner; finance/ops backup `@Sasha_Beep` | Provider disabled until real credentials, secret-store, webhook/status/idempotency evidence exist |
| OAuth and magic link | Google/GitHub client secrets, OAuth encryption, email provider API keys, SMTP credentials | `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_SECRET`, `OAUTH_TOKEN_ENCRYPTION_KEY`, `RESEND_API_KEY`, `BREVO_API_KEY`, `SMTP_SERVERS` | `@Sasha_Beep` | Separate staging/prod OAuth apps and redirect URIs. Discord/Twitter not enabled in S1 |
| Observability | Sentry DSNs/tokens, internal smoke secrets, Grafana/admin credentials, alert integration credentials | `SENTRY_DSN`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `FRONTEND_OBSERVABILITY_INTERNAL_SECRET`, `TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET`, `GRAFANA_ADMIN_PASSWORD` | `@Sasha_Beep` | Public browser DSNs allowed only as DSNs; auth tokens and internal smoke secrets are runtime/CI-only |
| OpenBao / node fleet / IaC | OpenBao address/roles, wrapping TTL, vault source files, Terraform/cloud credentials | `OPENBAO_ADDRESS`, `OPENBAO_*`, vault files, cloud/provider credentials | `@Sasha_Beep` | Target-state/S7 maturity. Do not block S1 if interim policy is accepted and evidence is clean |
| Helix / Verta / Beep private transports | Internal auth, manifest signing, node bootstrap, adapter tokens, Remnawave token | `HELIX_INTERNAL_AUTH_TOKEN`, `HELIX_MANIFEST_SIGNING_KEY`, `HELIX_REMNAWAVE_TOKEN`, `INTERNAL_AUTH_TOKEN`, `MANIFEST_SIGNING_KEY`, `ADAPTER_TOKEN` | `@Sasha_Beep` | Out of S1 production. Keep disabled and treat existing local secrets as lab-only |
| Native/mobile/desktop | Sentry DSNs/tokens, API base URL, certificate pins, platform credentials | `SENTRY_DSN`, `DESKTOP_SENTRY_DSN`, `VITE_SENTRY_DSN`, `CERT_FINGERPRINTS` | `@Sasha_Beep` | Out of S1 runtime unless explicitly pulled forward. S4/S5 only |

## S1 Interim Storage Policy

### Mandatory Rules

1. No production secret value may be committed to Git, pasted into docs, pasted into chat, stored in screenshots, included in Sentry context, or exposed through frontend bundles.
2. Local/dev secrets are disposable and must never be reused in staging or production.
3. Staging and production must use different DB users, Redis credentials, Remnawave API tokens, bot tokens, OAuth apps, payment credentials, webhook secrets and JWT/TOTP/encryption keys.
4. Every production secret must have an owner, a storage location, a rotation method and a last-rotated evidence entry.
5. Support/admin UI must never display provider secrets, OAuth tokens, TOTP seeds, Remnawave API tokens, raw subscription URLs or raw config links unless a separate redaction-reviewed support flow explicitly permits a masked value.
6. Evidence files may include key names and redacted command output only.

### Allowed Storage During S1 Implementation

| Context | Allowed | Not allowed |
|---|---|---|
| Local development | Ignored `.env` files with `0600` permissions and local-only values | Reusing local secrets in staging/prod; committing ignored files |
| Local Docker smoke | Local `.env` and disposable local tokens | Treating local smoke tokens as staging/prod evidence |
| Staging before OpenBao maturity | Provider secret manager, encrypted deployment variables, or root-owned env files outside repo with restricted SSH access | Shared production credentials; public access to secret files |
| Production before OpenBao maturity | Provider-native secret store or controlled root-owned runtime env files outside repo; encrypted password-manager backup under project owner | Secrets in repo checkout, CI logs, Compose files, screenshots or frontend build output |
| CI/CD | Protected GitHub Actions secrets/variables scoped to deploy jobs | Production secrets available to pull request workflows |
| Home lab | Non-critical lab/dev secrets only, or short-lived staging credentials for evidence work | Primary production secret authority or the only copy of production secrets |

For containerized S1 services, use per-service env injection at deploy time. Where images support file-based secrets, prefer file-mounted secrets similar to Docker Compose `/run/secrets/<name>` instead of broad environment variables. If environment variables are unavoidable, logs and process dumps must be treated as secret-sensitive.

### Target-State

OpenBao or provider-native secrets should become the standard for S7 and may be pulled earlier if it does not slow S1. The repository already has OpenBao-related surfaces and Helm `ExternalSecret` templates, but S1 can proceed with the interim policy as long as `S1-INFRA-007`, frontend bundle scan and go-live evidence are clean.

## Rotation Runbook Draft

### Standard Rotation Procedure

1. Classify the secret: service, environment, blast radius, dependent services, rollback method.
2. Open a rotation record with backlog/evidence ID.
3. Pause risky flows if needed: payments, registration, trial, provisioning or admin bootstrap.
4. Generate a new value with approved entropy or provider UI.
5. Store the new value in the approved secret store only.
6. Deploy to dependent services by immutable tag/commit SHA.
7. Verify health and functional smoke tests.
8. Revoke the old value.
9. Confirm logs/Sentry/evidence do not contain either value.
10. Record redacted evidence: key name, owner, rotation time, services restarted, tests passed, old value revoked.

### Emergency Rotation Procedure

Trigger emergency rotation if a secret is exposed, suspected exposed, committed, printed in logs, included in screenshots, shared to an unintended person, or if an account with access is compromised.

1. Stop or pause affected flows immediately.
2. Rotate the exposed secret before further debugging.
3. Revoke the old credential at the provider/source.
4. Search logs, CI, Sentry and repository history for related exposure.
5. Rotate adjacent secrets if the exposed one could grant access to them.
6. Create incident evidence and add a regression rule to `S1-INFRA-007`.

### Secret-Class Rotation Notes

| Secret class | Normal rotation | Emergency impact |
|---|---|---|
| JWT/session secrets | Before production go-live and after suspected exposure; scheduled at least quarterly after S1 unless dual-key rotation is implemented | Existing sessions/tokens may be invalidated. Plan forced logout or short maintenance |
| TOTP/encryption keys | Rotate before production if generated in local/dev; after suspected exposure. Long-term rotation needs dual-read/re-encrypt design | May require admin reset/re-encryption procedure. Do not rotate blindly without recovery plan |
| OAuth client secrets | Rotate on provider-account change, exposure, callback-domain change, or before prod if generated/tested insecurely | Login failures until app and provider are synchronized |
| Telegram bot token | Rotate through BotFather on exposure or environment split; separate staging/prod bots | Bot stops receiving updates until redeployed and webhook reset |
| Remnawave API tokens | Rotate before staging/prod rollout and after any local/tracked exposure. Environment-specific only | Provisioning may fail until backend/worker/subscription service are updated |
| Remnawave JWT/API token secrets | Rotate before production if local secrets were reused; environment-specific | Control-plane sessions/API tokens may break. Restart and smoke test required |
| Payment provider keys/webhook secrets | Rotate before paid beta if any setup artifact was exposed; rotate on finance/ops access changes; scheduled quarterly if provider supports | Payment callbacks can fail. Disable provider path until webhook verification passes |
| DB passwords | Rotate with managed DB user/password rotation; app deploy must be coordinated | API/worker/Remnawave outage if services are not updated atomically |
| Redis/Valkey credentials | Rotate with queue drain/retry plan; Redis remains non-durable | Background jobs/rate-limit/cache may fail. Rebuild critical jobs from PostgreSQL |
| Email provider API keys/SMTP credentials | Rotate on provider-account changes, suspected exposure or sender-domain changes | OTP/magic link delivery may fail until verified |
| Observability tokens/internal smoke secrets | Rotate after exposure and before public evidence screenshots if values appeared in logs | Smoke probes or source-map upload may fail until CI/runtime updated |
| Helix/Verta/Beep/private transport secrets | Lab-only during S1; rotate before S6 beta and after any exposure | No S1 production impact if private transports remain disabled |

## Open Findings For `S1-INFRA-007`

| Finding | Severity | Required next action |
|---|---|---|
| `infra/APIToken.txt` is tracked even though `.gitignore` blocks `APIToken.txt` | Critical | Run secrets scan, rotate if ever valid, remove from tracking/history as needed, replace with approved secret store and record evidence |
| Several ignored local `.env` files exist | High | Confirm they are local/dev only, check permissions, scan values locally without printing them, rotate anything reused outside local dev |
| Frontend/admin/partner template files are partly untracked in current snapshot | Medium | Decide if templates are launch-critical and either track sanitized examples or exclude them explicitly |
| Mobile/desktop/private-transport secret surfaces exist but are out of S1 | Medium | Keep disabled/deferred and ensure scans do not miss them |
| `backend/scripts/generate_secrets.py` prints generated secrets to terminal | Medium | Use only in controlled local terminal; never pipe output to logs/evidence/CI; prefer direct secret-store insertion later |

## Completion Statement

`S1-INFRA-006` is complete for S1 implementation entry as a documented secret model, redacted inventory and rotation policy. It is not complete as a production proof until:

- `S1-INFRA-007` scan/remediation is clean or accepted with explicit evidence;
- `S1-FE-010` local frontend bundle/env scan is clean in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`; repeat on RC/staging/production deployed artifacts;
- production/staging credentials are created and stored through the approved process;
- `infra/APIToken.txt` is remediated and any related token is rotated if it was valid outside local dev.

Next ID to execute: `S1-INFRA-007` - secrets scan and remediation evidence.
