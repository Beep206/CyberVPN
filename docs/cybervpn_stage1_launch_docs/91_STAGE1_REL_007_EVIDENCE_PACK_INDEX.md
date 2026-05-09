> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-05
> Backlog ID: `S1-REL-007`
> Статус: PASS for local/no-cost evidence pack assembly. Not a go-live clearance.

# S1-REL-007 Evidence Pack Index

## Purpose

`S1-REL-007` assembles the Stage 1 evidence pack structure and index.

This closes the local/no-cost evidence-pack assembly step: evidence is grouped by launch gate area, local proof is separated from staging/prod proof, and remaining blockers are visible before any go-live decision.

This does **not** mean Stage 1 is ready to launch. The pack still contains open external/provider/staging/prod evidence gaps, especially payments, Remnawave, managed backup/restore, observability, DNS/TLS, deployed admin/support flows and final RC artifact proof.

## Pack Location

Canonical Stage 1 pack index:

```text
docs/cybervpn_stage1_launch_docs/91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md
```

Category structure:

```text
docs/cybervpn_stage1_launch_docs/evidence_pack/stage1/
  README.md
  infra/README.md
  payments/README.md
  vpn/README.md
  db/README.md
  security/README.md
  frontend/README.md
  observability/README.md
  release/README.md
  legal-support/README.md
  scope-map/README.md
```

Combined launch pack:

```text
docs/cybervpn_stage1_launch_docs/CYBERVPN_STAGE1_LAUNCH_PACK_COMBINED.md
```

## Category Index

| Category | Pack README | Current status | Go-live blocker summary |
|---|---|---|---|
| Infrastructure | `evidence_pack/stage1/infra/README.md` | Simple Controlled Hybrid Container Topology, S1 staging environment contract, S1 production deployability contract, S1 DNS/TLS contract and S1 protected ingress contract are documented locally with component/service placement, ingress, private dependencies, data authority, home-lab boundary, staging separation rules, no-staging-credentials production rules, approved domain behavior and protected backend/admin ingress boundaries | Real staging/prod provider, deploy, managed PostgreSQL/Valkey, live DNS/TLS, protected ingress, origin/network details and final topology/staging/production health evidence |
| Payments | `evidence_pack/stage1/payments/README.md` | Local contracts and provider-placeholder guardrails exist | Real provider accounts, credentials, sandbox/prod callback samples, signatures, status rechecks, refund/dispute/reconciliation evidence |
| VPN / Remnawave | `evidence_pack/stage1/vpn/README.md` | Local Remnawave smoke, local node smoke, mockable provisioning contracts and product grace-period proof exist | Separate staging/prod Remnawave, real nodes/profiles/inbounds, real trial/paid provisioning, durable expiry worker, VPN client connection and Remnawave backup/export/rebuild evidence |
| DB / Bootstrap / Backups | `evidence_pack/stage1/db/README.md` | Local clean migration, first-admin bootstrap, PostgreSQL backup and local restore drill evidence exists | Managed staging/prod PostgreSQL migration/bootstrap/backup/restore, production RPO/RTO, encrypted off-host storage and Remnawave backup proof |
| Security | `evidence_pack/stage1/security/README.md` | Local secrets scan, API boundary, Swagger/CORS/CSRF/rate-limit, edge WAF baseline, dependency, bundle/env and auth-flow checks exist | Production secret store, remote history/token decision, deployed HTTPS/cookie proof, real edge/WAF/rate-limit/security-event proof, real email-provider proof, final RC scans and PII/log redaction proof |
| Frontend | `evidence_pack/stage1/frontend/README.md` | Local customer dashboard state matrix, config-delivery UI, devices/limits/actions, wallet safe payment-history, public growth UI gate, operator-surface hiding, platform-guide proof and i18n critical-path audit exist | Deployed staging/RC screenshots, real backend/payment/Remnawave state transitions, real device enforcement, real provider wallet records, final public growth env inventory, real VPN client import, deployed locale spot-checks and final artifact scan |
| Observability | `evidence_pack/stage1/observability/README.md` | Sentry local config, PII scrubbing, metrics/dashboard and alert routing contracts exist | Live Sentry proof, deployed Grafana screenshots/live targets, live alerts to Telegram/email and sample incident traces |
| Release | `evidence_pack/stage1/release/README.md` | Branch/tag policy, dirty worktree scope map, release notes template and local rollback dry-run exist | Final RC tag/commit, owner go/no-go, staging/prod rollback and final evidence pack snapshot |
| Legal / Support | `evidence_pack/stage1/legal-support/README.md` | Owner-approved legal/text closure plus local support path/templates/escalation evidence exists | Deployed support/mailbox delivery, human SLA acknowledgement, provider-specific refund/support workflow and admin/support queue proof |
| Scope Map | `evidence_pack/stage1/scope-map/README.md` | Current dirty worktree scope map exists | Re-run immediately before RC tag and approve launch-critical/excluded map |

## Evidence State Model

| State | Meaning |
|---|---|
| `LOCAL_PASS` | Tested or reviewed locally without paid hosting or live external provider credentials |
| `STRUCTURE_READY` | Evidence slot and required proof are documented, but the real environment/provider proof is not present yet |
| `EXTERNAL_BLOCKED` | Requires provider account, DNS, hosting, managed DB/Redis, real Telegram/BotFather, Sentry/Grafana or similar external setup |
| `GO_LIVE_BLOCKER` | Must be closed before S1 Controlled Public Beta go-live |
| `DEFERRED` | Not required for S1, tracked for later stages |

## Gate Coverage Summary

| Gate area | Local/no-cost evidence | Current Stage 1 launch posture |
|---|---|---|
| Documentation and decisions | `00`...`21`, `79` | Strong enough for continued implementation |
| Infrastructure topology/staging/production/DNS/ingress | `120`, `121`, `122`, `123`, `124` | S1 Simple Controlled Hybrid Container Topology, staging environment contract, production deployability contract, DNS/TLS contract and protected ingress contract are selected and machine-readable locally | Real staging/prod provider/deploy/DNS/TLS/ingress/origin/staging/production health evidence still required |
| Local Docker/Remnawave | `23`, `24`, `25` | Useful local proof, not staging/prod readiness |
| Secrets/static security | `26`, `27`, `80`, `89` | Local checks passed; final RC and production secret-store evidence still required |
| Backend/API/security contracts | `28`...`35`, `62`...`65` | Local proof exists; deployed HTTPS/host/persona proof still required |
| Payments | `36`, `37`, `38`, `45`, `46`, `81`, `82`, `83`, `84`, `108`, `109`, `110` | Local contracts and Telegram Stars/PayRam/NOWPayments provider-specific guardrails exist; paid beta blocked until at least one real provider path is proven |
| Trial/plans/growth gates | `47`...`52`, `98` | Local policy/UI/API/grace-period contracts exist; deployed evidence still required |
| VPN/provisioning | `39`...`44`, `85`, `86`, `87` | Local/mockable contracts exist; real staging/prod Remnawave proof still required |
| Telegram/Mini App | `53`...`60` | Local bot/Mini App contracts exist; real BotFather/token/webhook/client proof still required |
| Admin/support/legal | `62`...`79` | Local/owner-approved proof exists; deployed support/mailbox/persona evidence still required |
| Auth/account | `113`, `114`, `115`, `116` | Local public-registration kill switch, email/password register/verify/login/refresh/logout proof, magic link/OTP request/login/replay/rate-limit proof and admin 2FA auth-gate proof exist | Deployed registration toggle, HTTPS/browser cookie, real email-provider/sender-domain and admin browser/API persona proof still required |
| Frontend customer surfaces | `80`, `99`, `100`, `101`, `102`, `103`, `104`, `105`, `106` | Local bundle/env scan, customer dashboard-state proof, config-delivery UI proof, devices/limits/actions proof, wallet safe payment-history proof, public growth UI gate proof, operator/admin surface hiding proof, platform-guide coverage proof and i18n critical-path audit exist | Deployed RC artifact scan, screenshots with real backend/payment/Remnawave/device/wallet/growth-gate/operator-hidden/platform-guide/locale states, real provider payment records, final public env inventory, real VPN client import and deployed locale spot-checks still required |
| QA/release | `88`, `89`, `90`, `91`, `92`, `93` | Local critical E2E/dependency/rollback/pack structure/backup/restore proof exists; deployed go-live gates still open |
| Observability | `94`, `95`, `96`, `97` | Local Sentry config, PII scrubbing, metrics/dashboard and alert routing contracts exist; live proof remains open |

## Hard Blockers Still Visible in the Pack

The evidence pack intentionally keeps these blockers open:

1. No real paid provider path is proven yet.
2. Staging/prod Remnawave is not proven yet.
3. Production topology, staging contract, production deployability contract, DNS/TLS contract and protected ingress contract are selected locally, but staging/prod deployment, live DNS/TLS and protected ingress are not proven yet.
4. Managed staging/prod PostgreSQL backup/restore, encrypted off-host storage and production RPO/RTO are not proven yet.
5. Live observability, deployed dashboards and live alert delivery are not proven yet.
6. Staging/prod rollback against final RC artifacts is not proven yet.
7. Final RC artifact/image scans are not present yet.
8. Pre-RC dirty worktree scope map has not been re-run yet.
9. Deployed dashboard-state screenshots with real backend/payment/Remnawave transitions are not present yet.
10. Deployed config-delivery screenshot and real QR/subscription/config import evidence are not present yet.
11. Deployed devices screenshot with real backend sessions, entitlement device limit and enforcement proof is not present yet.
12. Deployed platform-guide screenshots and real generated Remnawave payload import proof are not present yet.
13. Deployed locale spot-checks for EN/RU and at least one RTL fallback-supported locale are not present yet.
14. Deployed marketing critical-page screenshots and `.net` primary / `.org` mirror proof are not present yet.

## Verification Commands

| Check | Result |
|---|---|
| Category README files exist under `evidence_pack/stage1/` | PASS: root plus 10 category READMEs exist |
| Relative links from category READMEs to canonical evidence docs | PASS: all checked targets resolve to existing files |
| Stale next-step scan for `S1-REL-007` as current/next task | PASS: no stale next-step references in source docs |
| `git diff --check` on touched docs and pack files | PASS |
| Running containers after task | PASS: no running Compose services reported |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory via `next` remains tracked, and `audit fix --force` was not applied because it proposes a breaking/downgrade path |
| Backend `uv export` + `pip-audit` | PASS: no known vulnerabilities found |
| Secret-pattern scan over new pack/index docs | PASS: no matches |
| Dangerous-pattern scan over new pack/index docs | PASS: no matches |

## Acceptance Result

`S1-REL-007` is **completed locally** as an evidence pack assembly/index task.

The pack is now usable for planning, review and go/no-go preparation. It is not sufficient for go-live until the open external/staging/prod evidence slots are filled.

Updated after `S1-FE-001`: frontend evidence pack now includes `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md` for local marketing critical-page content review. Re-run `S1-REL-007` evidence-pack validation on the immutable RC tag after deployed screenshots/domain proof are attached.

Updated after `S1-PAY-011`: payments evidence pack now includes the 2026-05-08 revalidation of `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md` for local Telegram Stars contract readiness. Real Telegram/BotFather/payment/refund/reconciliation/provisioning evidence is still required before Stars can be enabled.

Updated after `S1-PAY-013`: payments evidence pack now includes `109_STAGE1_PAY_013_PAYRAM_READINESS_EVIDENCE.md` for local PayRam readiness guardrails. Real PayRam account/credential/callback/status/refund/reconciliation/provisioning evidence is still required before PayRam can be enabled.

Updated after 2026-05-08 `S1-PAY-013` revalidation: PayRam create-payment, status-poll, webhook, FAQ and SDK docs were rechecked; backend PayRam and integrated payment security tests passed. Real PayRam instance/account/credential/callback/status/refund/reconciliation/provisioning evidence remains required before PayRam can be enabled.

Updated after `S1-PAY-014`: payments evidence pack now includes `110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md` for local NOWPayments readiness guardrails. Real NOWPayments account/credential/IPN/status/refund/reconciliation/provisioning evidence is still required before NOWPayments can be enabled.

Updated after 2026-05-08 `S1-PAY-014` revalidation: NOWPayments payment status, API/endpoints, IPN setup and integration guide docs were rechecked; backend NOWPayments and integrated payment security tests passed. Real NOWPayments account/credential/IPN/status/refund/reconciliation/provisioning evidence remains required before NOWPayments can be enabled.

Updated after `S1-PAY-015`: payments evidence pack now includes `111_STAGE1_PAY_015_DIGISELLER_READINESS_EVIDENCE.md` for local Digiseller readiness guardrails. Real Digiseller seller account/product/credential/callback/status/refund/reconciliation/provisioning evidence is still required before Digiseller can be enabled.

Updated after 2026-05-08 `S1-PAY-015` revalidation: Digiseller payment callback/status fields, `USD`/`RUB`/`EUR` currency contract, sorted-field HMAC-SHA256 signature, seller API token/invoice lookup and refund-policy docs were rechecked; backend Digiseller and integrated payment security tests passed. Real Digiseller seller account/product/credential/callback/status/refund/reconciliation/provisioning evidence remains required before Digiseller can be enabled.

Updated after `S1-PAY-016`: payments evidence pack now includes `112_STAGE1_PAY_016_YOOKASSA_READINESS_EVIDENCE.md` for local YooKassa readiness guardrails. Real YooKassa shop/account/credential/webhook/status/refund/reconciliation/receipt/provisioning evidence is still required before YooKassa can be enabled.

Updated after 2026-05-08 `S1-PAY-016` revalidation: YooKassa payment lifecycle, webhook event/authenticity, API idempotency, refund and receipt/fiscalization docs were rechecked; backend YooKassa and integrated payment security tests passed. Real YooKassa shop/account/credential/webhook/status/refund/reconciliation/receipt/provisioning evidence remains required before YooKassa can be enabled.

Updated after `S1-AUTH-001`: auth/security evidence pack now includes `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md` for the local public registration kill switch. Deployed staging/prod toggle proof remains required before go-live.

Updated after 2026-05-08 `S1-AUTH-001` revalidation: focused registration/security tests and expanded auth regression tests passed; FastAPI error-handling and pytest monkeypatch references were rechecked. Deployed staging/prod toggle proof remains required before go-live.

Updated after `S1-AUTH-002`: auth/security evidence pack now includes `114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md` for the local email/password register/verify/login/refresh/logout flow and session-cookie proof. Deployed HTTPS/browser cookie and real email-provider proof remain required before go-live.

Updated after 2026-05-08 `S1-AUTH-002` revalidation: focused email/password tests, existing auth integration regression, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. Local PostgreSQL/Valkey remained available for the next magic-link/OTP task.

Updated after `S1-AUTH-003`: auth/security evidence pack now includes `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md` for the local magic-link/OTP request, dispatch, token-login, OTP-login, replay rejection and rate-limit proof. Real email provider, sender-domain and deployed HTTPS/browser proof remain required before enabling passwordless login in S1.

Updated after 2026-05-08 `S1-AUTH-003` revalidation: focused magic-link/OTP tests, existing auth-flow regression, MagicLinkService/routes regression, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. Local PostgreSQL/Valkey remained available for the next admin 2FA task.

Updated after `S1-AUTH-004`: auth/security evidence pack now includes `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md` for the local admin 2FA auth-gate proof. Deployed admin browser/API persona and target-environment first-admin/TOTP evidence remain required before go-live.

Updated after 2026-05-09 `S1-AUTH-004` revalidation: production settings + admin 2FA/RBAC/access protection, generic 2FA lifecycle, sensitive finance/support admin gates, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. The production settings test fixture now uses a non-placeholder provider token for successful production-config cases, matching current payment credential guardrails.

Updated after `S1-AUTH-006`: auth/security evidence pack now includes `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md` for the local Google/GitHub-only OAuth provider boundary. Real Google/GitHub provider apps, secrets, callbacks and browser evidence remain required before public enablement.

Updated after 2026-05-09 `S1-AUTH-006` revalidation: OAuth provider scope/security/integration/use-case regression, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. Google/GitHub/RFC PKCE official docs were rechecked; no Docker containers were started.

Updated after `S1-AUTH-007`: auth/security and legal-support evidence now include `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md` for the local account deletion/data export privacy request path. Deployed `privacy@` mailbox, support queue, identity verification, owner review and human SLA evidence remain required before go-live.

Updated after 2026-05-09 `S1-AUTH-007` revalidation: backend route/support/privacy regression, OpenAPI export, frontend API/MSW tests, generated API types, ruff/eslint, backend dependency audit, high/critical npm audit threshold, lockfile-only forward audit remediation, secret scan and dangerous-pattern scan passed. The previous frontend high audit finding was removed; only moderate Next/PostCSS remains tracked because npm's force fix proposes a breaking Next.js downgrade.

Updated after `S1-INFRA-008`: security evidence now includes `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md` for the local Cloudflare/equivalent edge WAF/rate-limit baseline. Real DNS/TLS, admin protection, WAF/rate-limit transcripts, webhook no-challenge proof and Security Events export remain required before go-live.

Updated after `S1-INFRA-001`: infrastructure evidence now includes `120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md` and `infra/topology/stage1-production-topology.json` for the local Simple Controlled Hybrid Container Topology. Real staging/prod provider, deploy, DNS/TLS, protected ingress and origin/network evidence remain required before go-live.

Updated after 2026-05-09 `S1-INFRA-001` revalidation: production topology validator, JSON parse check, topology summary check, dependent staging/production/DNS/TLS/protected-ingress validators, 24 infra contract tests, ruff, high/critical dependency audit threshold, secret scan and dangerous-pattern scan passed. Live staging/prod provider, origin/network, DNS/TLS, protected ingress and image digest evidence remain external before go-live.

Updated after `S1-INFRA-002`: infrastructure evidence now includes `121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md` and `infra/topology/stage1-staging-environment.json` for the local staging environment contract. Real external staging deploy, public origins, provider/test credentials, health checks and E2E evidence remain required before first rollout.

Updated after 2026-05-09 `S1-INFRA-002` revalidation: staging validator, JSON parse check, staging summary check, dependent production topology/production/DNS/TLS/protected-ingress validators, 24 infra contract tests, ruff, high/critical dependency audit threshold, secret scan and dangerous-pattern scan passed. Real external staging host, DNS/TLS, public origins, private DB/Valkey/Remnawave, BotFather/test-provider credentials, health and E2E evidence remain external before first rollout.

Updated after `S1-INFRA-003`: infrastructure evidence now includes `122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md` and `infra/topology/stage1-production-environment.json` for the local production deployability contract. Real external production deploy, public origins, provider/live credentials, health checks, backup/restore, rollback and observability evidence remain required before controlled public beta traffic.

Updated after 2026-05-09 `S1-INFRA-003` revalidation: production environment validator, JSON parse check, production summary check, dependent production topology/staging/DNS/TLS/protected-ingress validators, 24 infra contract tests, ruff, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. External production host, public origins, managed DB/Valkey, Remnawave, bot, payment, observability, backup/restore, rollback and health evidence remain external before go-live.

Updated after `S1-INFRA-004`: infrastructure evidence now includes `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md` and `infra/dns/stage1-dns-tls-contract.json` for the local DNS/TLS contract. Real DNS provider/zone access, live DNS resolution, TLS certificate, redirects, status route, admin protection and webhook/OAuth no-challenge evidence remain required before go-live.

Updated after 2026-05-09 `S1-INFRA-004` revalidation: DNS/TLS validator, JSON parse check, DNS/TLS summary check, production environment/protected-ingress/edge-WAF validators, 27 infra contract tests, ruff, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. No-cost live probes are blocker evidence: apex `.net`/`.org` DNS and apex certificates exist, but required `www`/`api`/`admin` hosts, HTTP->HTTPS redirects, `/status`, admin protection and webhook/OAuth no-challenge proof are not live-proven.

Updated after `S1-INFRA-005`: infrastructure evidence now includes `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md` and `infra/ingress/stage1-protected-ingress-contract.json` for the local protected ingress contract. Real edge route inventory, reverse-proxy/firewall proof, admin access protection and webhook/OAuth no-challenge probes remain required before go-live.

Updated after 2026-05-09 `S1-INFRA-005` revalidation: protected ingress validator, JSON parse check, ingress summary check, DNS/TLS/edge-WAF/production-environment validators, 27 infra contract tests, ruff, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. No-cost live probes are blocker evidence: `api.cyber-vpn.net`, `admin.cyber-vpn.net` and `admin.cyber-vpn.org` do not resolve from this workspace, customer-domain admin route probes did not complete, and webhook/OAuth no-challenge behavior is not live-proven.

Updated after 2026-05-09 `S1-QA-003` revalidation: local PostgreSQL backup evidence now includes fresh backup `20260509T063942Z` under ignored `.tmp/`, custom-format `.dump` artifact, 14-day retention, `pg_restore --list` integrity output with `1817` lines, clean compose config and Ansible backup setting tests. Managed/private staging or production backup evidence, encrypted off-host retention, provider restore path and production RPO/RTO proof remain required before go-live.

Updated after 2026-05-09 `S1-QA-004` revalidation: local PostgreSQL restore drill now uses fresh backup `20260509T063942Z`, restores into clean disposable DB `s1_qa_004_restore_drill` in `13s`, verifies `SELECT 1`, `159` public tables, `2` expected schemas and key S1 tables, drops the restore DB and stops `remnawave-db`. Managed/private staging or production restore evidence, RPO/RTO proof and Remnawave backup/export/rebuild evidence remain required before go-live.

Updated after 2026-05-09 `S1-OBS-001` revalidation: local Sentry critical project/config contract remains valid for `web-frontend`, `web-admin`, `backend-api`, `telegram-bot` and `task-worker`. The workspace has no live `SENTRY_URL`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`, runtime DSNs, releases or `sentry-cli`, so live Sentry project provisioning, redacted DSN injection, source-map upload, safe test events and alert routing remain external go-live evidence.

Updated after 2026-05-09 `S1-OBS-002` revalidation: local Sentry/log PII scrubbing remains valid for frontend, admin, backend, Telegram Bot and task-worker. Frontend/admin redaction tests, backend Sentry/log sanitization tests, bot and worker redaction tests, privacy baseline validation, S1 Sentry contract validation, targeted lint/ruff and dependency/security scans passed. The workspace has no live Sentry URL/token/org/project/DSNs/releases or `sentry-cli`, so live Sentry org scrubbers, prevent-IP setting, replay masking, safe event samples and deployed log samples remain external go-live evidence.

Updated after 2026-05-09 `S1-OBS-003` revalidation: local metrics/dashboard evidence remains valid for the Stage 1 Grafana dashboard, Prometheus recording rules, scrape job wiring, Prometheus/Alertmanager tooling and task-worker paid reconciliation metrics. The workspace has no live Prometheus/Grafana/Alertmanager endpoints or Grafana token/API key, and no containers are running, so deployed Grafana screenshots, live Prometheus targets and production-like metric samples remain external go-live evidence.

Updated after 2026-05-09 `S1-OBS-004` revalidation: local alert routing evidence remains valid for Stage 1 Prometheus rules, Alertmanager Telegram/email receivers, P0/P1/critical/warning routes, paid-but-no-access escalation and backup/restore stale evidence alerts. The workspace has no live `ALERTMANAGER_URL`, Telegram receiver token/chat env, SMTP receiver env or running Alertmanager, so live Telegram/email delivery proof remains external go-live evidence.

Updated after 2026-05-09 `S1-REL-002` repeat gate and follow-up `S1-INFRA-007`: dirty worktree inventory and launch scope map were refreshed in `22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md`; the current-tree Gitleaks findings were classified/remediated/baselined in `27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md`; the accepted baseline is redacted and the baseline-enforced scan returns `no leaks found`. RC still needs a fresh scope map and secrets scan after additional implementation changes.

Updated after `S1-PAY-001`: payments evidence now includes `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md` and `infra/payments/stage1-primary-payment-provider.json` for the local first paid-path selection. CryptoBot / Crypto Pay is the first S1 live paid-path candidate; real provider account, credentials, sandbox/testnet, production callback, refund/reconciliation and payment-to-provisioning evidence remain required before paid beta.

Updated after `S1-PAY-002`: payments evidence now includes `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md` and `infra/payments/stage1-cryptobot-sandbox-contract.json` for the local CryptoBot sandbox/testnet runtime contract. Backend and task-worker can select fixed official mainnet/testnet endpoints, production rejects testnet, and paid beta remains blocked until real `@CryptoTestnetBot` credentials, invoice samples, callback signatures and payment-to-provisioning evidence exist.

Updated after `S1-PAY-003`: payments evidence now includes `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md` and `infra/payments/stage1-cryptobot-production-credentials-contract.json` for the local CryptoBot production credential inventory without values. Backend, task-worker and Telegram Bot reject placeholder/test CryptoBot tokens in production, and fake CryptoBot token generation was removed from the backend secret generator. Paid beta remains blocked until real provider account, secret-store, callback and payment-to-provisioning evidence exist.

Updated after `S1-PAY-004`: payments evidence now includes the 2026-05-08 revalidation of `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`. Provider status mapping remains local/official-doc evidence; real provider callback samples remain required before enablement.

Updated after `S1-PAY-005`: payments evidence now includes the 2026-05-08 revalidation of `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`. Provider webhook authenticity remains local evidence; real provider callback signatures and status/API rechecks remain required before enablement.

Updated after `S1-PAY-006`: payments evidence now includes the 2026-05-08 revalidation of `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`. Provider webhook idempotency remains local evidence; durable Redis/DB persistence and real duplicate provider callbacks remain required before enablement.

Updated after `S1-PAY-007`: payments evidence now includes the 2026-05-08 revalidation of `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`. Orphan payment / paid-but-no-access handling remains local evidence; real admin/support queue, audit trail and alert delivery remain required before paid beta.

Updated after `S1-PAY-008`: payments evidence now includes the 2026-05-08 revalidation of `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`. Payment -> provisioning failure handling remains local evidence; durable webhook idempotency, live provider callbacks/signatures, real support queue/alerts and staging/prod Remnawave evidence remain required before paid beta.

Updated after `S1-PAY-009`: payments evidence now includes the 2026-05-08 revalidation of `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`. Refund/dispute handling remains local evidence; real provider refund/dispute evidence remains required before enablement.

Updated after `S1-PAY-010`: payments evidence now includes the 2026-05-08 revalidation of `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`. Wallet/payment-history handling remains local evidence; deployed screenshots and real provider payment-history evidence remain required before paid beta.

Updated after `S1-BE-001` revalidation on 2026-05-09: local clean PostgreSQL 17.7 migration evidence now proves the updated migration chain reaches `20260423_p27_partner_events`, creates 120 public tables and seeds S1-sensitive DB config default-off. Staging/managed PostgreSQL migration evidence remains external before go-live.

Updated after `S1-BE-002` revalidation on 2026-05-09: local first-admin bootstrap now proves the protected direct CLI creates exactly one `owner/super_admin` with TOTP enabled after a clean schema replay, writes the bootstrap audit event, and rejects repeat bootstrap with `bootstrap_locked`. The direct CLI entrypoint was hardened to run without `PYTHONPATH`. Staging/prod bootstrap, browser/API admin 2FA login and backup/restore evidence remain external before go-live.

Updated after the owner-requested five-task batch on 2026-05-09:

- `S1-BE-003` route boundary revalidated: 603 HTTP routes, 2 WebSocket routes, 0 `needs-review`, 4 targeted tests passed.
- `S1-REL-002` scope map revalidated: 965 dirty entries, 612 tracked modified, 353 untracked, no excluded top-level partner/mobile/desktop/TV/Helix/GitOps runtime path detected.
- `S1-INFRA-002` staging environment contract revalidated: validator passed, 24 dependent infra tests passed; real staging remains external.
- `S1-INFRA-004` DNS/TLS contract revalidated: static contract passed; live probes still show required subdomain DNS, redirect, API/admin/webhook/OAuth evidence as blockers.
- `S1-BE-001` clean migration revalidated: PostgreSQL 17.7, single head `20260423_p27_partner_events`, 120 tables, S1 default-off config confirmed; disposable container removed.

Updated after the 2026-05-09 ordered auth/backend batch:

- `S1-BE-002` first-admin bootstrap revalidated: disposable PostgreSQL 17.7 clean schema replay, one `owner/super_admin`, TOTP enabled, bootstrap audit event written, repeat bootstrap rejected with `bootstrap_locked`, 19 targeted tests passed.
- `S1-BE-003` route boundary revalidated again: 603 HTTP routes, 2 WebSocket routes, 0 `needs-review`, 4 targeted tests passed.
- `S1-AUTH-001` registration kill switch revalidated: 83 auth/security tests passed.
- `S1-AUTH-002` email/password flow revalidated: 5 focused tests, 7 focused+integration tests and ruff passed.
- `S1-AUTH-003` magic link/OTP flow revalidated: 5 focused tests, 4 integration auth-flow tests, 30 focused/service/integration tests and ruff passed.
- Local `remnawave-db` and `remnawave-redis` were started only for auth integration tests and stopped after the batch.

Updated after the 2026-05-09 ordered auth/VPN batch:

- `S1-AUTH-004` admin 2FA revalidated: 48 production/settings/admin boundary tests passed, 12 Docker-backed 2FA lifecycle integration tests passed after DB/Redis startup, 15 finance/support gate tests passed, ruff passed.
- `S1-AUTH-006` OAuth provider scope revalidated: 87 Google/GitHub-only provider-boundary tests passed and ruff passed.
- `S1-AUTH-007` privacy delete/export path revalidated: backend route/support/privacy tests passed, OpenAPI path check passed, contract regression passed, frontend API/MSW tests passed and generated API types refreshed.
- `S1-VPN-001` evidence pack now includes `128_STAGE1_VPN_001_REMNAWAVE_STAGING_CONTROL_PLANE_EVIDENCE.md` for local Remnawave control-plane smoke; real external staging Remnawave remains required.
- `S1-VPN-003` protocol allowlist revalidated: 29 tests passed and ruff passed.
- Local `remnawave-db`, `remnawave-redis`, `remnawave` and `caddy` were stopped after the batch.
- Batch final checks passed: `git diff --check`, current-tree Gitleaks baseline-enforced scan (`no leaks found`), backend `pip-audit` (`No known vulnerabilities found`), high/critical `npm audit` threshold. Residual npm finding remains the already-known moderate Next/PostCSS advisory where `npm audit fix --force` proposes a prohibited breaking downgrade.

Next ID to execute: `S1-VPN-004` as the next item after the ordered auth/VPN batch.

Updated after the 2026-05-09 ordered VPN/payment/QA/ingress batch:

- `S1-VPN-004` trial provisioning revalidated: 12 backend tests passed and ruff passed; real staging/prod Remnawave trial evidence remains required.
- `S1-PAY-002` CryptoBot sandbox/testnet contract revalidated: root validator passed, backend tests passed, infra tests passed, task-worker tests passed and ruff passed; real `@CryptoTestnetBot` credentials and callback samples remain required.
- `S1-QA-003` local backup revalidated with fresh backup `20260509T112917Z`, `.dump` custom format, 14-day retention, `1376583` bytes, SHA-256 `14ef02e7ab00f2ebee504f806cc36b5921c2df2fae1f9baf07a9ac5340802791` and `1817` `pg_restore --list` lines.
- `S1-QA-004` restore drill revalidated from fresh backup `20260509T112917Z`: restored into disposable `s1_qa_004_restore_drill` in `7s`, `SELECT 1`, `159` public tables, `2` expected schemas and key table visibility passed, restore DB dropped.
- `S1-INFRA-005` protected ingress revalidated: root validators passed, 6 focused tests passed, 27 combined infra tests passed and ruff passed. No-cost live probes still show API/admin subdomains unresolved and customer-domain admin route behavior unproven.
- Batch final checks passed: `git diff --check`, current-tree Gitleaks baseline-enforced scan, backend `pip-audit`, high/critical `npm audit` threshold and targeted secret/dangerous-pattern scans. Residual npm finding remains the tracked moderate Next/PostCSS advisory where `npm audit fix --force` proposes a prohibited breaking downgrade.
- Local Docker resources were stopped after backup/restore; no containers remained running.

Next ordered step superseded by the owner-approved 1-33 launch sequence: after item `30. S1-REL-007`, execute `31. stage1-beta-rc.N`.

Updated after the 2026-05-09 ordered infra/observability batch:

- `S1-INFRA-008` edge WAF/rate-limit baseline revalidated: root validator passed, 3 focused contract tests passed and ruff passed. Real edge/DNS/TLS/WAF/rate-limit/security-event evidence remains external before go-live.
- `S1-OBS-001` Sentry critical project/config revalidated: env readiness inventory confirmed no live Sentry credentials/DSNs/CLI in this workspace; repository validator, frontend/admin Sentry contract tests, backend Sentry privacy tests, Telegram Bot Sentry/before-send tests and worker observability test passed.
- `S1-OBS-002` PII scrubbing revalidated: frontend/admin Sentry privacy tests, backend Sentry/log sanitization tests, bot before-send redaction, worker observability, privacy validator, targeted lint and ruff passed.
- `S1-OBS-003` metrics/dashboards revalidated: dashboard/rule validator, Prometheus/Alertmanager tooling validation, backend observability asset contract tests, task-worker paid reconciliation metric tests, targeted ruff, Python compile and dashboard JSON validation passed.
- `S1-OBS-004` alerts revalidated: env readiness inventory confirmed no live Alertmanager/Telegram/SMTP delivery target in this workspace; alerting validator, Prometheus/Alertmanager tooling validation, backend alerting contract tests, shell syntax checks and Python compile passed.
- Batch final checks passed: `git diff --check` on touched evidence docs, current-tree Gitleaks baseline-enforced scan (`no leaks found`), backend/Telegram Bot/task-worker `pip-audit` (`No known vulnerabilities found`), high/critical root `npm audit` threshold and targeted dangerous-pattern scan. Residual npm finding remains the already-known moderate Next/PostCSS advisory where `npm audit fix --force` proposes a prohibited breaking downgrade.
- No long-lived containers were started for this batch, and no containers remained running after validation.

Next ordered step superseded by the owner-approved 1-33 launch sequence: after item `30. S1-REL-007`, execute `31. stage1-beta-rc.N`.

Updated after the 2026-05-09 ordered release/frontend/QA batch:

- `S1-REL-006` rollback dry-run revalidated: release pointer rollback passed in `30ms`, compose config validated, backend Mini App/admin rollback controls passed, admin rollback UI/API tests passed and registration/payment/provisioning safety tests passed.
- `S1-FE-010` frontend bundle/env scan revalidated: production build generated `2801` static pages, private canary env values were absent from scanned build artifacts, high-confidence secret scan passed, static source-map count was `0`, Sentry config tests and targeted lint passed.
- `S1-QA-002` dependency audit revalidated: root/frontend/admin npm audits pass the high/critical threshold, backend/Telegram Bot/task-worker runtime and all-groups Python lock exports are clean, local S1 Python service images report `0C / 0H` in Docker Scout and container `pip check` passes.
- `S1-REL-002` dirty worktree scope map revalidated: current snapshot remains `965` status entries, `612` tracked modified entries, `353` untracked porcelain entries and `534` untracked actual files; excluded partner/mobile/desktop/TV/extension/Helix/Verta/Beep/GitOps runtime scan has no matches.
- `S1-REL-007` evidence pack validation revalidated: root plus 10 category README files exist, relative README links resolve, and no stale `S1-REL-007` next-step references were found.
- Batch final checks passed: `git diff --check` on touched evidence docs, current-tree Gitleaks baseline-enforced scan (`no leaks found`), strict targeted assignment-style secret scan, targeted dangerous-pattern scan and root `npm audit --omit=dev --audit-level=high`. Residual npm finding remains the already-known moderate Next/PostCSS advisory where `npm audit fix --force` proposes a prohibited breaking downgrade.

Next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.

Updated after the 2026-05-09 RC/go-no-go evaluation:

- Step `31. stage1-beta-rc.N` was checked in `129_STAGE1_STEP_31_RC_TAG_EVIDENCE.md`. The candidate tag is `stage1-beta-rc.1`, but the real tag was not created because the release branch `release/stage1-controlled-public-beta` is missing and the worktree is dirty.
- Step `32. Owner go/no-go` was prepared in `130_STAGE1_STEP_32_OWNER_GO_NO_GO_EVIDENCE.md`. The recommended decision is `NO-GO_FOR_CONTROLLED_BETA_LAUNCH`, with a conditional go only for preparing a real RC after owner-approved scope/commit/tag work.

Next ordered step: owner must sign or override the go/no-go decision before `33. Controlled beta cohort launch`.
