> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-03
> Статус: working execution plan for S1. Не заменяет `06_STAGE1_IMPLEMENTATION_BACKLOG.md`, а упорядочивает его в последовательность выполнения.

# Stage 1 Execution Plan and Work Queue

## Purpose

Этот документ показывает полный список предстоящих работ по S1 Controlled Public Beta в порядке выполнения. Цель — двигаться максимально далеко без затрат на серверы, отделяя local/no-cost work от задач, которые требуют внешней инфраструктуры, реальных credentials или go-live evidence.

Главное правило: каждая runtime-задача должна ссылаться на `S1-*` backlog ID из `06_STAGE1_IMPLEMENTATION_BACKLOG.md`.

## Status Legend

| Status | Meaning |
|---|---|
| `NOW / no-cost` | Можно делать сейчас локально без оплаты серверов |
| `DOCKER` | Можно делать после включения Docker |
| `EXTERNAL ACCOUNT` | Нужны аккаунты провайдеров, почта, Telegram bot или OAuth apps |
| `PAID / MANAGED INFRA` | Нужны VPS/managed DB/domain/DNS/TLS/production-like infra |
| `GO-LIVE ONLY` | Нельзя считать закрытым до реального staging/prod evidence |
| `DEFERRED` | Не входит в S1 runtime |

## Execution Overview

| Order | Work package | Backlog IDs | Status |
|---:|---|---|---|
| 1 | Repo/release boundary and dirty worktree scope map | `S1-REL-001`...`S1-REL-005` | `NOW / no-cost` |
| 2 | Local Docker/Remnawave smoke | `S1-INFRA-009`, `S1-VPN-012` | `DOCKER` |
| 3 | Secrets inventory and scans | `S1-INFRA-006`, `S1-INFRA-007`, `S1-FE-010` | `NOW / no-cost` |
| 4 | Clean DB migration and first-admin bootstrap path | `S1-BE-001`, `S1-BE-002`, `S1-ADM-003`, `S1-ADM-004` | `NOW / no-cost` + `DOCKER` |
| 5 | Backend hardening and API boundaries | `S1-BE-003`...`S1-BE-008` | `NOW / no-cost` |
| 6 | Auth and account linking | `S1-AUTH-001`...`S1-AUTH-007` | `NOW / no-cost` + `EXTERNAL ACCOUNT` |
| 7 | Payment state machine with mocks/fixtures | `S1-PAY-004`...`S1-PAY-010`, `S1-PAY-012`, `S1-PAY-017` | `NOW / no-cost` |
| 8 | Provider-specific readiness | `S1-PAY-001`...`S1-PAY-003`, `S1-PAY-011`, `S1-PAY-013`...`S1-PAY-016` | `EXTERNAL ACCOUNT` |
| 9 | Trial, subscription, pricing and grace policy | `S1-PROD-001`...`S1-PROD-007` | `NOW / no-cost` |
| 10 | Remnawave provisioning logic | `S1-VPN-003`...`S1-VPN-009` | `NOW / no-cost` + `DOCKER` |
| 11 | Frontend customer cabinet and marketing | `S1-FE-001`...`S1-FE-010` | `NOW / no-cost` |
| 12 | Telegram Bot and Mini App | `S1-TG-001`...`S1-TG-008` | `NOW / no-cost` + `EXTERNAL ACCOUNT` |
| 13 | Admin and support operations | `S1-ADM-*`, `S1-SUP-*` | `NOW / no-cost` |
| 14 | Legal/privacy/abuse final pack | `S1-LEGAL-*`, `TD-S1-LEGAL-*` | `Owner-approved legal/text closure`; operational evidence remains in other workstreams |
| 15 | Observability scaffolding | `S1-OBS-*` | `NOW / no-cost` + later real alert evidence |
| 16 | Local QA, dependency/security checks and evidence drafts | `S1-QA-001`, `S1-QA-002`, `S1-REL-006`, `S1-REL-007` | `NOW / no-cost` |
| 17 | External staging/prod infra and real evidence | `S1-INFRA-002`...`S1-INFRA-005`, `S1-QA-003`, `S1-QA-004` | `PAID / MANAGED INFRA` |
| 18 | Controlled public beta go-live | `G3`...`G6`, `S1-REL-006`, `S1-REL-007` | `GO-LIVE ONLY` |

## Work Package 1 — Repo / Release Boundary

| Task | IDs | What we do | Output |
|---|---|---|---|
| Confirm release policy | `S1-REL-001` | Ensure branch/tag policy is recorded: `release/stage1-controlled-public-beta`, `stage1-beta-rc.N`, `stage1-beta-live.N` | Release policy note |
| Dirty worktree inventory | `S1-REL-002` | Run `git status`, changed-file inventory, untracked inventory | Scope evidence |
| Launch-critical/excluded map | `S1-REL-002` | Categorize repo paths: launch-critical, supporting-docs, disabled-runtime, experimental, generated, secrets-sensitive | Launch scope map |
| Decision log consistency check | `S1-REL-003` | Confirm all active decisions point to `17`, `18`, `19`, `20`, `21` docs | Decision consistency note |
| Go/no-go authority | `S1-REL-004` | Confirm stop authority and emergency pause powers | Governance note |
| Release notes template | `S1-REL-005` | Completed locally: reusable RC/live release notes template and sample created; real filled release notes remain required per candidate | `78_STAGE1_REL_005_RELEASE_NOTES_TEMPLATE_EVIDENCE.md` |

Current status: completed for the 2026-05-03 snapshot in `22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md`.

Current status: `S1-REL-002` was repeated on 2026-05-09 in `22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md`. The worktree has `965` dirty entries: `612` tracked modified entries and `353` untracked actual files. No dirty top-level partner/mobile/desktop/TV/Helix/GitOps runtime directories matched the exclusion scan. The follow-up `S1-INFRA-007` current-tree secrets/baseline review is now closed locally; RC tagging still requires a fresh scope map after any additional implementation changes.

Current status: `S1-REL-005` release notes template completed in `78_STAGE1_REL_005_RELEASE_NOTES_TEMPLATE_EVIDENCE.md`. This closes the reusable template requirement only; every actual RC/live candidate must still fill the template with current tag/commit, evidence, known issues, rollback notes and owner go/no-go approval.

Current status: `S1-INFRA-009` completed in `23_STAGE1_INFRA_009_LOCAL_DOCKER_COMPOSE_EVIDENCE.md`.

Current status: `S1-VPN-012` completed as local control-plane smoke in `24_STAGE1_VPN_012_LOCAL_REMNAWAVE_SMOKE_EVIDENCE.md`.

Current status: `S1-VPN-012` connected local node smoke completed in `25_STAGE1_VPN_012_LOCAL_REMNAWAVE_NODE_EVIDENCE.md`.

Current status: `S1-INFRA-006` redacted secrets inventory, interim storage policy and rotation runbook draft completed in `26_STAGE1_INFRA_006_SECRETS_INVENTORY_AND_POLICY.md`.

Current status: `S1-INFRA-007` revalidated on 2026-05-09 in `27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md`: current-tree findings from the repeated `S1-REL-002` snapshot were reviewed, easy test/public-copy false positives were reduced, the accepted baseline is redacted (`77` findings, `77 REDACTED` secret fields), and the baseline-enforced scan returns `no leaks found`. First RC/go-live still requires remote history replacement/owner push decision and token rotation if applicable.

Current status: `S1-BE-001` revalidated again on 2026-05-09 in `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md` as item 5 of the five-task owner batch. A clean PostgreSQL 17.7 database reaches the single Alembic head `20260423_p27_partner_events`, creates 120 public tables, contains the S1-critical tables and seeds S1-sensitive DB config default-off (`referral.enabled=false`, `wallet.withdrawal_enabled=false`). Managed staging/prod PostgreSQL and backup/restore evidence remain open.

Current status: `S1-BE-002` revalidated on 2026-05-09 in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md`. After a clean PostgreSQL 17.7 schema replay, the protected direct CLI created exactly one `owner/super_admin` with TOTP enabled, wrote `admin.bootstrap.first_admin_created`, and rejected the second run with `bootstrap_locked`. The direct CLI path was hardened so it works as `uv run python scripts/bootstrap_first_admin.py` without relying on `PYTHONPATH`. Staging/prod bootstrap, admin login/2FA browser evidence and backup/restore evidence remain open before go-live.

Current status: `S1-BE-003` revalidated on 2026-05-09 in `30_STAGE1_BE_003_API_ROUTE_BOUNDARY_EVIDENCE.md` as item 1 of the five-task owner batch. Current local route inventory is 603 HTTP routes, 2 WebSocket routes, 0 `needs-review`, and all WebSocket routes depend on `ws_authenticate`. Staging/prod ingress proof, deployed Swagger public-off proof, deployed CORS/cookie/CSRF/rate-limit proof and durable webhook idempotency persistence evidence remain open.

Current status: `S1-BE-004` local Swagger/OpenAPI public-off proof completed in `31_STAGE1_BE_004_SWAGGER_PUBLIC_OFF_EVIDENCE.md`. Deployed staging/prod curl/screenshot evidence remains open before go-live.

Current status: `S1-BE-005` local CORS/cookie config proof completed in `32_STAGE1_BE_005_CORS_COOKIE_CONFIG_EVIDENCE.md`. Deployed DNS/TLS/redirect/CORS curl/Set-Cookie evidence remains open before go-live.

Current status: `S1-BE-006` local CSRF assessment and production-mode mitigation proof completed in `33_STAGE1_BE_006_CSRF_ASSESSMENT_EVIDENCE.md`. Deployed HTTPS/browser auth-cookie evidence remains open before go-live.

Current status: `S1-BE-007` local auth/payment/trial/referral/support rate-limit policy and ASGI 429 proof completed in `34_STAGE1_BE_007_RATE_LIMIT_POLICY_EVIDENCE.md`. Deployed Redis/ingress/edge evidence remains open before go-live.

Current status: `S1-BE-008` local canonical status/error contract and ASGI serialization proof completed in `35_STAGE1_BE_008_STATUS_ERROR_CONTRACT_EVIDENCE.md`. Endpoint migration, UI/support rendering, provider-specific mapping and deployed evidence remain open before go-live.

Current status: `S1-PAY-004` local official-doc provider status mapping, paid-access gate and fixture proof completed and revalidated on 2026-05-08 in `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`. Real provider callback/signature evidence remains open before enabling any paid provider.

Current status: `S1-PAY-005` local provider webhook signature/authenticity contract completed and revalidated on 2026-05-08 in `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`. Real provider callback signatures, credential storage, provider status/API rechecks and live route evidence remain open before enabling any paid provider.

Current status: `S1-PAY-006` local provider webhook idempotency contract and duplicate-webhook ASGI proof completed and revalidated on 2026-05-08 in `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`. Durable Redis/DB persistence and live provider duplicate callback evidence remain open before enabling paid providers.

Current status: `S1-PAY-007` local orphan payment / paid-but-no-access policy, SLA thresholds, dashboard summary proof and integration regression completed and revalidated on 2026-05-08 in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`. Real admin/support queue, audit trail and alert delivery evidence remain open before paid beta.

Current status: `S1-VPN-003` local VPN protocol allowlist completed in `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md`. Staging/prod Remnawave profile/inbound, node and provisioning evidence remain open before go-live.

Current status: `S1-VPN-004` local trial provisioning through a mockable S1 Remnawave gateway completed in `40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md`. Real staging/prod trial activation evidence remains open before beta.

Current status: `S1-VPN-005` local paid provisioning create/extend contract through a mockable S1 Remnawave gateway completed in `41_STAGE1_VPN_005_PAID_PROVISIONING_EVIDENCE.md`. Payment webhook integration, retry behavior and real staging/prod paid provisioning evidence remain open before beta.

Current status: `S1-VPN-006` local Remnawave outage/retry contract completed in `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md`. Durable PostgreSQL/worker retry queue, alert delivery and real staging/prod outage recovery evidence remain open before beta.

Current status: `S1-PAY-008` local payment -> provisioning failure contract completed and revalidated on 2026-05-08 in `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`. Durable webhook idempotency, live provider callbacks/signatures, real support queue/alerts and staging/prod Remnawave evidence remain open before paid beta.

Current status: `S1-PAY-009` local refund/dispute process, provider posture, backend role gates, 2FA reviewer gate, lifecycle tests and official-doc recheck completed and revalidated on 2026-05-08 in `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`. Real provider refund/dispute evidence remains open before enablement.

Current status: `S1-PROD-001` local canonical trial 3 days / 1 device policy contract completed in `47_STAGE1_PROD_001_TRIAL_POLICY_EVIDENCE.md`. Staging/prod Remnawave activation, deployed UI/API screenshots and edge/Redis rate-limit evidence remain open before beta.

Current status: `S1-PROD-002` local paid beta plan matrix completed in `48_STAGE1_PROD_002_PAID_PLAN_MATRIX_EVIDENCE.md`. Deployed pricing API/UI, owner production price approval and real payment provider quote/invoice evidence remain open before paid beta.

Current status: `S1-PROD-003` local public/private plan visibility guards completed in `49_STAGE1_PROD_003_PLAN_VISIBILITY_EVIDENCE.md`. Deployed web/Mini App/Telegram Bot API evidence, pricing screenshot and admin-only hidden-plan proof remain open before beta.

Current status: `S1-PROD-004` local currency display rule completed in `50_STAGE1_PROD_004_LOCAL_CURRENCY_DISPLAY_EVIDENCE.md`. USD remains billing source of truth; RUB is display-only estimate for Russian locale; checkout request currency remains USD/XTR as intended. Deployed provider invoice/currency evidence remains open before paid beta.

Current status: `S1-PROD-007` local promo/gift/referral disabled-by-default kill switches completed in `52_STAGE1_PROD_007_GROWTH_KILL_SWITCH_EVIDENCE.md`. Public promo/gift/referral and checkout-code discount flows are fail-closed across backend APIs, checkout, Mini App bootstrap, dashboard and Mini App UI; deployed flag/API/UI rejection evidence remains open before beta.

Current status: `S1-TG-001` local staging/prod Telegram Bot identity config and S1 command/menu startup surface completed in `53_STAGE1_TG_001_STAGING_BOT_CONFIG_EVIDENCE.md`. External BotFather account creation, real token storage, `getMe`, webhook and deployed Telegram client screenshots remain open before beta.

Current status: `S1-TG-002` local production Telegram Bot token path completed in `54_STAGE1_TG_002_PRODUCTION_BOT_TOKEN_PATH_EVIDENCE.md`. External BotFather production bot, real token storage, redacted `getMe`, webhook and rotation evidence remain open before beta.

Current status: `S1-TG-003` local Telegram Bot commands/menu/onboarding smoke coverage completed in `55_STAGE1_TG_003_COMMANDS_MENU_ONBOARDING_EVIDENCE.md`. Live Telegram client screenshots, real BotFather/getMe and deployed staging webhook/polling evidence remain open before beta.

Current status: `S1-TG-004` local Mini App cabinet route smoke and screenshots completed in `56_STAGE1_TG_004_MINIAPP_CABINET_EVIDENCE.md`. Real Telegram client screenshots and deployed staging evidence remain open before beta.

Current status: `S1-TG-005` local Telegram auth/linking completed in `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`. Mini App initData validation, bot-link, magic-link, Telegram OAuth callback, no-silent-merge and account conflict handling are covered locally. Real BotFather/domain/token, real Telegram client initData, webhook and deployed HTTPS evidence remain open before beta.

Current status: `S1-TG-006` local Telegram notification contract completed in `58_STAGE1_TG_006_TELEGRAM_NOTIFICATIONS_EVIDENCE.md`. Expiry/payment/provisioning queue rows, disabled/unlinked fail-closed behavior, HTML escaping and existing queue processor delivery are covered locally. Real BotFather/token/webhook/client rendering and provider/provisioning integration evidence remain open before beta.

Current status: `S1-TG-007` local Telegram rate limiting completed in `59_STAGE1_TG_007_TELEGRAM_RATE_LIMITING_EVIDENCE.md`. Bot message/callback anti-spam, settings-backed limits, fail-closed Redis behavior, dispatcher wiring and Mini App/backend linkage are covered locally. Real deployed Redis/webhook/client evidence remains open before beta.

Current status: `S1-TG-008` local Telegram first-line support triage and backend escalation intake completed in `60_STAGE1_TG_008_AI_SUPPORT_ESCALATION_EVIDENCE.md`. Deterministic no-cost support triage, safe redaction, bot-created backend staff-note escalation and fallback references are covered locally. Real deployed bot/admin queue/alert/SLA evidence remains open before beta.

Current status: `S1-ADM-001` local admin domain/access protection completed in `62_STAGE1_ADM_001_ADMIN_ACCESS_PROTECTION_EVIDENCE.md`. Backend wrong-host admin API protection, production settings validation and admin mirror redirect are covered locally. Real DNS/TLS/ingress/private-access/browser evidence remains open before go-live.

Current status: `S1-ADM-002` local admin RBAC matrix completed in `63_STAGE1_ADM_002_RBAC_MATRIX_EVIDENCE.md`. Owner/super_admin, support, operator/ops and finance role separation is covered in pure permission tests and FastAPI dependency pipeline tests. Real deployed admin persona/UI proof remains open before go-live.

Current status: `S1-ADM-003` local admin 2FA enforcement completed in `64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`. Production config now fails closed unless `ADMIN_2FA_REQUIRED=true`, protected admin role/permission dependencies reject users without TOTP, and 2FA setup-style routes remain reachable for enrollment. Real deployed browser/API persona proof remains open before go-live.

Current status: `S1-ADM-004` local privileged admin audit logging completed in `65_STAGE1_ADM_004_PRIVILEGED_AUDIT_LOG_EVIDENCE.md`. Sensitive admin mutations now use required audit logging with sanitized details, invite token fingerprints and no raw config links/passwords/tokens. Real deployed audit-log/persona proof remains open before go-live.

Current status: `S1-ADM-005` local payment attempts view completed in `66_STAGE1_ADM_005_PAYMENT_ATTEMPTS_VIEW_EVIDENCE.md`. Support/finance/admin-safe status views, raw provider redaction, review/SLA signals and reusable frontend view contract are covered locally. Real deployed admin persona/UI/API and provider payment evidence remain open before go-live.

Current status: `S1-ADM-006` local manual subscription operations completed in `67_STAGE1_ADM_006_MANUAL_SUBSCRIPTION_OPS_EVIDENCE.md`. Manual grant/extend is role-gated by `SUBSCRIPTION_CREATE`, audit-logged, safe-response-only and covered by reusable frontend operator/admin panel tests. Real deployed admin persona/UI/API and staging/prod Remnawave grant/extend evidence remain open before go-live.

Current status: `S1-ADM-007` local credential regeneration admin integration completed in `68_STAGE1_ADM_007_CREDENTIAL_REGENERATION_ADMIN_EVIDENCE.md`. The admin customer-detail action, OpenAPI/admin client contract and safe result summary are covered locally. Real deployed admin browser/persona proof, staging/prod audit-log retrieval and real Remnawave credential regeneration evidence remain open before paid beta.

Current status: `S1-SUP-001` local support ticket path completed in `69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`. Telegram/email/web/bot/admin support-ticket references, queue/SLA mapping, redaction and public support contact profile are covered locally. Real mailbox/web delivery, live bot transcript, admin queue/timeline and alert/SLA evidence remain open before go-live.

Current status: `S1-SUP-002` local support template catalog completed in `70_STAGE1_SUP_002_SUPPORT_TEMPLATES_EVIDENCE.md`. Failed payment, paid-no-access, VPN not connecting, expired subscription and refund request templates are tested with sensitive-data guardrails and conservative payment/refund/autorenewal wording. Owner/legal text approval is closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; provider/live support workflow evidence remains open before go-live.

Current status: `S1-SUP-003` local support escalation process completed in `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`. AI/support -> finance/ops/owner routing, P0/P1 SLA, paid-no-access 24h P0 escalation and sensitive-data guardrails are covered locally. Deployed admin/support queue, alert delivery and human SLA acknowledgement evidence remain open before go-live.

Current status: `S1-LEGAL-001` Terms of Service is owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; local candidate evidence remains in `72_STAGE1_LEGAL_001_TERMS_OF_SERVICE_EVIDENCE.md`.

Current status: `S1-LEGAL-002` Privacy Policy is owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; local candidate evidence remains in `73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`.

Current status: `S1-LEGAL-003` Acceptable Use Policy is owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; local candidate evidence remains in `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md`.

Current status: `S1-LEGAL-004` Refund Policy is owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; local candidate evidence remains in `75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md`.

Current status: `S1-LEGAL-005` Cookie Policy is owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; local candidate evidence remains in `76_STAGE1_LEGAL_005_COOKIE_POLICY_EVIDENCE.md`.

Current status: `S1-LEGAL-006`...`S1-LEGAL-009` are closed for S1 owner-approved legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.

Current status: `S1-FE-010` frontend bundle/env scan is completed locally in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`. Production Next.js build passed with controlled public/private canaries; no private canary/local private env values were found in scanned client/static or server app artifacts. Sentry frontend release injection was hardened to public release metadata only. RC/staging/production deployed artifact scan remains required before go-live.

Current status: `S1-PAY-009` refund/dispute process is completed locally in `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`. Customer refund request path exists, finance/admin reviewer gate is enforced for refund/dispute state changes, support/operator/viewer are denied from finance mutations, and provider refund posture is documented. Real provider refund/dispute/reconciliation evidence remains required before enabling any paid provider.

Current status: `S1-PAY-010` wallet/payment history verification is completed locally in `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`. Authenticated customer scoping, safe frontend payment-history params, raw provider-field non-rendering and default-off withdrawal/payout request creation and UI are covered locally. Deployed UI screenshots and real provider payment-history evidence remain required before paid beta/go-live.

Current status: `S1-PAY-010` was revalidated on 2026-05-08 with local Docker DB/Redis integration tests, frontend wallet/payment-history tests, lint, dependency audit, secret scan and static dangerous-pattern scan. DB/Redis containers were stopped after the verification run.

Current status: `S1-PAY-012` reconciliation job is completed locally in `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md`. Backend-authoritative reconciliation scans payment attempts, canonical payments and order settlement links; the worker runs it through a header-secret-protected internal endpoint every 15 minutes; output is redacted and actionable for support/finance. Real provider reconciliation samples, deployed manual review queue and alert delivery evidence remain required before paid beta/go-live.

Current status: `S1-PAY-017` provider placeholder replacement is completed locally in `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md`. Documentation-only provider samples now have a typed evidence registry, redacted fixture and enablement guardrails; real provider-account samples remain required before any paid provider is enabled.

Current status: `S1-VPN-009` usage/traffic display is completed locally in `85_STAGE1_VPN_009_USAGE_DISPLAY_EVIDENCE.md`. Backend usage API and Mini App bootstrap now expose explicit availability metadata; web and Mini App UI mark unavailable usage instead of displaying zero/unlimited as authoritative. Staging/prod Remnawave usage correctness and deployed UI screenshots remain required before go-live.

Current status: `S1-VPN-010` node/region inventory is completed locally in `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`. The S1 catalogue defines 12 country-level startup regions, activation tiers, node-slot template and public visibility rules aligned with the current Remnawave `country_code` API contract. Real staging/prod provider/node/monitoring evidence remains required before any region is shown as live.

Current status: `S1-VPN-011` Torrent/P2P/TOR node traffic policy is completed locally in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`. Torrent/P2P is restricted by default, Remnawave Torrent Blocker is documented as the S1 plugin path after evidence, and no dedicated native TOR blocker addon/plugin was found in current official Remnawave node-plugin docs. TOR control remains disabled by default until separate egress/shared-list/custom-routing evidence exists.

Current status: `S1-QA-001` local critical E2E gate is completed in `88_STAGE1_QA_001_CRITICAL_E2E_LOCAL_EVIDENCE.md`. Backend/frontend/admin/bot/worker critical slices pass locally; real staging/prod provider, Remnawave, VPN client connection, alert, backup/restore and rollback evidence remain required before go-live.

Current status: `S1-QA-002` local dependency audit is completed in `89_STAGE1_QA_002_DEPENDENCY_AUDIT_EVIDENCE.md`. Root/frontend/admin npm audits have no high/critical findings, backend/bot/worker Python lock exports are clean, and rebuilt local S1 Python service images have no high/critical findings after Alpine base-image remediation. Final RC artifact/image scans remain required before go-live.

Current status: `S1-REL-006` local rollback dry-run/proof is completed in `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md`. Release-pointer rollback passed in 31ms locally, rollback target compose config validates, and backend/admin runtime rollback controls pass locally. Staging/prod rollback against final RC artifacts remains required before go-live.

Current status: `S1-REL-007` evidence pack assembly is completed locally in `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`. The pack structure under `evidence_pack/stage1/` now indexes payments, vpn, db, security, observability, release, legal-support and scope-map evidence, while keeping provider/staging/prod/backup/observability/go-live gaps explicit.

Current status: `S1-QA-003` local PostgreSQL backup proof is completed in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md`. Backup config now uses `.dump` custom-format artifacts and 14-day retention; an on-demand local backup was created and verified with `pg_restore --list`.

Current status: `S1-QA-003` was revalidated on 2026-05-09. Local PostgreSQL container was healthy, fresh on-demand backup `20260509T063942Z` was created with `prodrigestivill/postgres-backup-local:17`, `.dump` custom format and 14-day retention, `pg_restore --list` returned `1817` lines, Ansible backup settings tests passed, backup artifacts stayed under ignored `.tmp/`, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. Managed/private staging or production backup evidence, encryption/off-host retention proof and provider restore path remain external before go-live.

Current status: `S1-QA-004` local PostgreSQL restore drill is completed in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`. The S1-QA-003 `.dump` restored into a clean disposable DB in `11s`, `SELECT 1` passed, `159` public tables were visible and the restore DB was removed. Managed staging/prod backup/restore, encrypted off-host storage, production RPO/RTO and Remnawave backup/export/rebuild evidence remain required before go-live.

Current status: `S1-QA-004` was revalidated on 2026-05-09 against fresh backup `20260509T063942Z`. `pg_restore --list` returned `1817` lines, the dump restored into clean disposable DB `s1_qa_004_restore_drill` in `13s`, `SELECT 1` returned `1`, `159` public tables and `2` expected schemas were visible, key S1 tables were visible, the restore DB was dropped, `remnawave-db` was stopped, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. Managed/private staging or production restore evidence, RPO/RTO proof and Remnawave backup/export/rebuild evidence remain external before go-live.

Current status: `S1-OBS-001` Sentry critical projects/config is completed locally in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`. Frontend, admin, backend, Telegram Bot and task-worker config contracts and focused tests pass. Live Sentry project provisioning, DSN injection, test-event screenshots, source-map proof and alert routing remain required before go-live.

Current status: `S1-OBS-001` was revalidated on 2026-05-09 as a local/no-cost live-evidence follow-up. Sentry environment presence check confirmed `SENTRY_URL`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`, DSNs and releases are missing in this workspace, and `sentry-cli` is not installed. Repo validator, frontend/admin Sentry config tests, backend Sentry privacy tests, Telegram Bot Sentry/before-send tests and task-worker observability tests passed. Live Sentry project provisioning, redacted DSN injection, source-map upload, safe test events and alert routing remain external go-live evidence.

Current status: `S1-OBS-002` PII scrubbing is completed locally in `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`. Frontend, admin, backend, Telegram Bot and task-worker Sentry redaction tests pass, backend log sanitization covers S1 OAuth/Telegram/payment/config values, and `scripts/validate-sentry-privacy.py` passes. Live Sentry org scrubbers/replay/deployed log proof remain required before go-live.

Current status: `S1-OBS-002` was revalidated on 2026-05-09 as a local/no-cost live PII scrubbing evidence follow-up. Frontend/admin redaction tests, backend Sentry/log sanitization tests, Telegram Bot before-send redaction test, task-worker observability test, `scripts/validate-sentry-privacy.py`, `scripts/validate-s1-sentry-critical-projects.py`, targeted lint/ruff and dependency/security scans passed. The workspace has no live Sentry URL/token/org/project/DSNs/releases or `sentry-cli`, so live Sentry org scrubbers, prevent-IP setting, replay masking, safe event samples and deployed log samples remain external go-live evidence.

Current status: `S1-OBS-003` metrics/dashboards is completed locally in `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md`. Stage 1 Grafana dashboard, Prometheus recording rules, worker reconciliation metrics and static contract validation cover API/auth/payments/provisioning/worker/DB/Redis/Remnawave. Deployed Grafana screenshots/live targets remain required before go-live.

Current status: `S1-OBS-003` was revalidated on 2026-05-09 as a local/no-cost live metrics/dashboard evidence follow-up. Dashboard/rule validator, Prometheus/Alertmanager tooling validation, backend observability asset contract tests, task-worker paid reconciliation metric tests, targeted ruff, Python compile and JSON validation passed. The workspace has no live `PROMETHEUS_URL`, `GRAFANA_URL`, Grafana token/API key or `ALERTMANAGER_URL`, and no containers are running, so deployed Grafana screenshots, live Prometheus targets and production-like metric samples remain external go-live evidence.

Current status: `S1-OBS-004` alerts is completed locally in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Stage 1 Prometheus alert rules, Alertmanager Telegram/email routing, local validation and synthetic delivery-test procedure exist. Live Telegram/email delivery evidence remains required before go-live.

Current status: `S1-OBS-004` was revalidated on 2026-05-09 as a local/no-cost alert delivery evidence follow-up. Alert rule/routing validation, Prometheus/Alertmanager tooling validation, backend alerting contract tests, syntax checks, high/critical npm audit threshold and Python dependency audits passed. The workspace has no live `ALERTMANAGER_URL`, Telegram receiver token/chat env, SMTP receiver env or running Alertmanager, so live Telegram/email delivery remains external go-live evidence.

Current status: `S1-PROD-005` grace-period behavior is completed locally in `98_STAGE1_PROD_005_GRACE_PERIOD_BEHAVIOR_EVIDENCE.md`. Paid access enters 72h self-service grace, disables at the approved boundary, trial has no paid grace, and missing Remnawave UUID moves to support/reconciliation. Durable worker and staging/prod Remnawave evidence remain required before beta.

Current status: `S1-FE-002` dashboard states are completed locally in `99_STAGE1_FE_002_DASHBOARD_STATES_EVIDENCE.md`. Customer dashboard now renders explicit access/payment/provisioning state cards for active/trial/grace/expired/payment/provisioning paths, with local screenshot, focused tests and production frontend build proof. Deployed staging/RC screenshots and real provider/Remnawave transition evidence remain required before go-live.

Current status: `S1-FE-003` config delivery UI is completed locally in `100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md`. The customer server-access UI now exposes QR, subscription copy/open and browser-generated config download actions with masked preview, delivery-payload fallback, focused tests and production frontend build proof. Deployed staging/RC screenshots, real Remnawave payload and real VPN client import evidence remain required before go-live.

Current status: `S1-FE-004` devices page is completed locally in `101_STAGE1_FE_004_DEVICES_PAGE_EVIDENCE.md`. The authenticated `/settings#devices` surface now shows active devices/sessions, entitlement-derived device limit, remaining/over-limit state and safe revoke actions. Deployed staging/RC screenshots and real backend/Remnawave/device enforcement evidence remain required before go-live.

Current status: `S1-FE-005` wallet page is completed locally in `102_STAGE1_FE_005_WALLET_PAGE_EVIDENCE.md`. The authenticated `/wallet` surface now shows recent customer-scoped payment history, hides raw provider fields and keeps withdrawal UI disabled by default. Deployed staging/RC screenshots, real provider payment records and final RC artifact scan remain required before go-live.

Current status: `S1-FE-006` referral/promo/gift UI gating is completed locally in `103_STAGE1_FE_006_GROWTH_UI_GATES_EVIDENCE.md`. Public growth UI now requires the master evidence gate plus specific feature flags, and web/Mini App referral/promo/gift/checkout-code surfaces remain hidden or paused by default. Deployed screenshots, final public env inventory and RC artifact scan remain required before go-live.

Current status: `S1-FE-007` operator/admin surface audit is completed locally in `104_STAGE1_FE_007_OPERATOR_SURFACE_AUDIT_EVIDENCE.md`. The customer dashboard policy hides analytics/monitoring/users/partner, nav remains customer-only, and `/servers` keeps config delivery while removing operator metrics and the stats API call. Deployed staging/RC browser evidence remains required before go-live.

Current status: `S1-FE-008` platform guides are completed locally in `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`. The public `/devices` hub now covers Android, iOS, Windows, macOS, Linux and Telegram Mini App setup paths with safe QR/subscription URL/config wording and no native app/autorenewal overpromise. Deployed screenshots and real Remnawave/client import evidence remain required before go-live.

Current status: `S1-FE-009` i18n critical-path validation is completed locally in `106_STAGE1_FE_009_I18N_CRITICAL_PATH_EVIDENCE.md`. All 39 enabled locales are runtime fallback-complete for 18 S1 critical message files; `en-EN` and `ru-RU` are the directly reviewed S1 launch locales. Secondary locales remain fallback-supported, not fully translated, until separate human locale review.

Current status: `S1-FE-001` marketing critical pages are completed locally in `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`. Pricing/features/devices/help/status/legal route files exist, EN/RU copy has no placeholders/stale domains/unsupported S1 public claims, canonical domain is `cyber-vpn.net`, and production build passed. Deployed staging/RC screenshots, mirror/redirect proof and final artifact/domain evidence remain required before go-live.

Current status: `S1-PAY-011` Telegram Stars contract readiness is completed locally in `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md`. XTR-only flow, pre-checkout non-grant behavior, successful-payment confirmation, charge-id storage, refundStarPayment client and refund reconciliation are covered. Real BotFather/test/prod Stars invoice, successful payment, support/refund/reconciliation and Remnawave provisioning evidence remain required before enabling Stars.

Current status: `S1-PAY-011` was revalidated on 2026-05-08 against official Telegram Bot API 10.0 docs. Backend, bot and frontend targeted tests/lints passed; Stars subscriptions/autoprolongation remain explicitly out of S1 scope; root npm high `fast-uri` was remediated with a lockfile-only forward update.

Current status: `S1-PAY-013` PayRam readiness is completed locally in `109_STAGE1_PAY_013_PAYRAM_READINESS_EVIDENCE.md`. PayRam `FILLED`/underpaid/overpaid/cancelled status behavior, `API-Key` webhook guard, payload idempotency and provider-evidence gate are covered; real PayRam account, credentials, callbacks/status-poll, refund/reconciliation and provisioning evidence remain required before enabling PayRam.

Current status: `S1-PAY-013` was revalidated on 2026-05-08 against current PayRam official docs. Create-payment, status-poll, webhook, FAQ and SDK docs were checked; backend targeted and integrated payment security tests passed; PayRam remains disabled until real instance/account, credential, callback/status-poll, refund/reconciliation and provisioning evidence exists.

Current status: `S1-PAY-014` NOWPayments readiness is completed locally in `110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md`. NOWPayments `finished`/partial/wrong-asset/refund status behavior, `x-nowpayments-sig` HMAC-SHA512 guard, payload idempotency and provider-evidence gate are covered; real NOWPayments account, credentials, IPN/status-poll, refund/reconciliation and provisioning evidence remain required before enabling NOWPayments.

Current status: `S1-PAY-014` was revalidated on 2026-05-08 against current NOWPayments official docs. Payment status, API/endpoints, IPN setup and integration guide docs were checked; backend targeted and integrated payment security tests passed; NOWPayments remains disabled until real account, credential, IPN/status-poll, refund/reconciliation and provisioning evidence exists.

Current status: `S1-PAY-015` Digiseller readiness is completed locally in `111_STAGE1_PAY_015_DIGISELLER_READINESS_EVIDENCE.md`. Digiseller `paid`/`wait`/`canceled`/`refunded`/`error` behavior, sorted-field HMAC-SHA256 guard, payload idempotency and provider-evidence gate are covered; real Digiseller seller account, product/payment model, credentials, callback/status-poll, refund/reconciliation and provisioning evidence remain required before enabling Digiseller.

Current status: `S1-PAY-015` was revalidated on 2026-05-08 against current official Digiseller docs. Payment callback/status fields, `USD`/`RUB`/`EUR` currency contract, sorted-field HMAC-SHA256 signature, seller API token/invoice lookup and refund-policy requirements were checked; backend targeted and integrated payment security tests passed. Digiseller remains disabled until real seller account, product, credential, callback/status-poll, refund/reconciliation and provisioning evidence exists.

Current status: `S1-PAY-016` YooKassa readiness is completed locally in `112_STAGE1_PAY_016_YOOKASSA_READINESS_EVIDENCE.md`. YooKassa `pending`/`waiting_for_capture`/`succeeded`/`canceled`, webhook event, provider recheck, refund and provider-evidence gates are covered; real YooKassa shop/account, credentials, webhook/status-poll, refund/reconciliation, receipt/fiscalization and provisioning evidence remain required before enabling YooKassa.

Current status: `S1-PAY-016` was revalidated on 2026-05-08 against current official YooKassa docs. Payment lifecycle, webhook event/authenticity, API idempotency, refund and receipt/fiscalization docs were checked; backend targeted and integrated payment security tests passed. YooKassa remains disabled until real shop/account, credential, webhook/status-poll, refund/reconciliation, receipt/fiscalization and provisioning evidence exists.

Current status: `S1-AUTH-001` registration kill switch is completed locally in `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md`. Public new-account creation is blocked across web password, mobile password, magic link/OTP, OAuth, Telegram Web/Mini App, mobile Telegram/OIDC and Telegram Bot bootstrap when `REGISTRATION_ENABLED=false`; existing-account login remains allowed. Deployed staging/prod toggle proof remains required before go-live.

Current status: `S1-AUTH-001` was revalidated on 2026-05-08. Focused registration/security tests and expanded auth regression tests passed; FastAPI error-handling and pytest monkeypatch references were rechecked. Deployed staging/prod toggle proof remains required before go-live.

Current status: `S1-AUTH-002` email/login password flow is completed locally in `114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md`. Register -> OTP verify -> login by email/username -> refresh rotation -> logout/replay rejection and secure session-cookie behavior are covered with local Docker-backed PostgreSQL/Valkey proof. Deployed HTTPS/browser cookie proof and real email-provider evidence remain required before go-live.

Current status: `S1-AUTH-002` was revalidated on 2026-05-08. Focused email/password tests, existing auth integration regression, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. Local PostgreSQL/Valkey containers remain running for `S1-AUTH-003`.

Current status: `S1-AUTH-003` magic link/OTP flow is completed locally in `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md`. Magic-link request/dispatch, token login, OTP login, HTTP-only session cookies, OTP replay rejection, request/resend rate limits and cryptographically secure OTP generation are covered with local Docker-backed PostgreSQL/Valkey proof. Real email-provider/sender-domain proof and deployed HTTPS/browser evidence remain required before go-live.

Current status: `S1-AUTH-003` was revalidated on 2026-05-08. Focused magic-link/OTP tests, existing auth-flow regression, MagicLinkService/routes regression, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. Local PostgreSQL/Valkey containers remain running for `S1-AUTH-004`.

Current status: `S1-AUTH-004` admin 2FA is completed locally in `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md`. Protected admin role/permission surfaces fail closed without TOTP, valid TOTP-enabled admins pass, 2FA completion/lifecycle regressions pass, and sensitive finance/support gates share the same 2FA posture. Deployed browser/API persona proof and target-environment first-admin/TOTP evidence remain required before go-live.

Current status: `S1-AUTH-004` was revalidated on 2026-05-09. Production settings + admin 2FA/RBAC/access protection, generic 2FA lifecycle, sensitive finance/support admin gates, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. The stale production settings test fixture was updated to use a non-placeholder provider token, matching current payment credential guardrails. `S1-AUTH-005` is already covered locally by `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`.

Current status: `S1-AUTH-006` OAuth provider scope is completed locally in `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md`. Backend defaults, runtime route gate, trusted-email auto-link gate, tests and docs restrict S1 OAuth to Google/GitHub only; real Google/GitHub provider apps, credentials, callbacks and browser evidence remain required before public enablement.

Current status: `S1-AUTH-006` was revalidated on 2026-05-09. OAuth provider scope/security/integration/use-case regression, ruff, backend dependency audit, high/critical npm audit threshold, secret scan and static dangerous-pattern scan passed. Google/GitHub/RFC PKCE official docs were rechecked; no Docker containers were started.

Current status: `S1-AUTH-007` delete/export data path is completed locally in `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md`. Authenticated privacy requests for `account_deletion` and `data_export` now route to `s1_privacy_rights_review` with privacy contact, owner/audit guardrails, redaction and frontend API/MSW coverage; deployed mailbox/support queue evidence remains required before go-live.

Current status: `S1-AUTH-007` was revalidated on 2026-05-09. Backend route/support/privacy regression, OpenAPI export, frontend API/MSW tests, generated API types, ruff/eslint, backend dependency audit, high/critical npm audit threshold, lockfile-only forward audit remediation, secret scan and dangerous-pattern scan passed. The previous frontend high audit finding was removed; only the moderate Next/PostCSS advisory remains because npm's force fix proposes a breaking Next.js downgrade.

Current status: `S1-INFRA-008` edge WAF/rate limiting is completed locally in `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`. Cloudflare/equivalent baseline, webhook no-challenge exceptions, admin protection requirement and non-HTTP surface exclusions are covered. Real DNS/TLS/WAF/rate-limit/security-event evidence remains required before go-live.

Current status: `S1-INFRA-001` production topology is completed locally in `120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md`. Simple Controlled Hybrid Container Topology, component placement, public/private ingress, private dependencies, data authority and home-lab boundary are documented in `infra/topology/stage1-production-topology.json`. Real staging/prod provider, deploy, DNS/TLS, protected ingress and origin/network evidence remain required before go-live.

Current status: `S1-INFRA-001` was revalidated on 2026-05-09. Production topology validator, JSON parse check, topology summary check, dependent staging/production/DNS/TLS/protected-ingress validators, 24 infra contract tests, ruff, high/critical dependency audit threshold, secret scan and dangerous-pattern scan passed. Live staging/prod provider, origin/network, DNS/TLS, protected ingress and image digest evidence remain external before go-live.

Current status: `S1-INFRA-002` staging environment contract is completed locally in `121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md`. The contract requires separate staging DB, Valkey/Redis, Remnawave, Telegram bot, sandbox/test payments, no production credentials/data, no home-lab staging authority and a concrete staging health/evidence checklist. Real external staging deploy/health proof remains required before first rollout.

Current status: `S1-INFRA-002` was revalidated on 2026-05-09. Staging validator, JSON parse check, staging summary check, dependent production topology/production/DNS/TLS/protected-ingress validators, 24 infra contract tests, ruff, high/critical dependency audit threshold, secret scan and dangerous-pattern scan passed. Real external staging host, DNS/TLS, public origins, private DB/Valkey/Remnawave, BotFather/test-provider credentials, health and E2E evidence remain external before first rollout.

Current status: `S1-INFRA-003` production environment deployability contract is completed locally in `122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md`. The contract requires no staging credentials/state, immutable tag/SHA deploys, separate managed/private production services, protected ingress, kill switches and external production evidence before go-live. Real external production deploy/health proof remains required before controlled public beta traffic.

Current status: `S1-INFRA-003` was revalidated on 2026-05-09. Production environment validator, JSON parse check, production summary check, dependent production topology/staging/DNS/TLS/protected-ingress validators, 24 infra contract tests, ruff, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. External production host, public origins, managed DB/Valkey, Remnawave, bot, payment, observability, backup/restore, rollback and health evidence remain external before go-live.

Current status: `S1-INFRA-004` DNS/TLS contract is completed locally in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`. The contract defines `.net` primary, `.org` redirects, admin mirror redirect, `api.cyber-vpn.net`, `https://cyber-vpn.net/status`, TLS requirements, webhook/OAuth no-challenge requirements and live evidence commands. Real DNS/TLS/redirect/admin-protection proof remains required before go-live.

Current status: `S1-INFRA-004` was revalidated on 2026-05-09. DNS/TLS validator, JSON parse check, DNS/TLS summary check, production environment/protected-ingress/edge-WAF validators, 27 infra contract tests, ruff, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. No-cost live probes are blocker evidence: apex `.net`/`.org` DNS and apex certificates exist, but required `www`/`api`/`admin` hosts, HTTP->HTTPS redirects, `/status`, admin protection and webhook/OAuth no-challenge proof are not live-proven.

Current status: `S1-INFRA-005` protected ingress contract is completed locally in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`. The contract forbids direct-public backend/admin origins, requires protected admin access before login, keeps Remnawave/PostgreSQL/Valkey/observability private and preserves webhook/OAuth no-challenge paths. Real edge/reverse-proxy/firewall/admin-access proof remains required before go-live.

Current status: `S1-INFRA-005` was revalidated on 2026-05-09. Protected ingress validator, JSON parse check, ingress summary check, DNS/TLS/edge-WAF/production-environment validators, 27 infra contract tests, ruff, high/critical dependency audit threshold, backend dependency audit, secret scan and dangerous-pattern scan passed. No-cost live probes are blocker evidence: `api.cyber-vpn.net`, `admin.cyber-vpn.net` and `admin.cyber-vpn.org` do not resolve from this workspace, customer-domain admin route probes did not complete, and webhook/OAuth no-challenge behavior is not live-proven.

Current status: `S1-PAY-001` primary payment provider selection is completed locally in `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`. CryptoBot / Crypto Pay is the first live paid-path candidate; real provider account, credentials, sandbox/testnet and production callback evidence remain open before paid beta.

Current status: `S1-PAY-002` CryptoBot sandbox/testnet runtime contract is completed locally in `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`. Backend and task-worker support fixed mainnet/testnet endpoints and production rejects testnet; real `@CryptoTestnetBot` credentials, invoice samples and callback evidence remain open before paid beta.

Current status: `S1-PAY-003` CryptoBot production credential inventory is completed locally in `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`. Required production keys, runtime consumers, placeholder guards and no-repo-values policy are documented/tested; real provider account, secret-store and callback evidence remain open before paid beta.

Current status: owner-requested five-task batch completed locally/revalidated: `S1-BE-003`, `S1-REL-002`, `S1-INFRA-002`, `S1-INFRA-004`, `S1-BE-001`. Live staging/DNS/ingress evidence remains external; local Docker containers were removed after the batch.

Current next step: `S1-BE-002` (repeat first-admin bootstrap on the current target environment/staging path when available).

## Work Package 2 — Local Docker / Remnawave Smoke

| Task | IDs | What we do | Output |
|---|---|---|---|
| Verify Docker availability | `S1-INFRA-009` | Check Docker/Compose works in WSL | Command output |
| Validate compose config | `S1-INFRA-009` | Run compose config/services checks for `infra/docker-compose.yml` | Compose evidence |
| Start local stack | `S1-INFRA-009` | Bring up Remnawave/PostgreSQL/Valkey and required local services | Local health evidence |
| Run local Remnawave smoke | `S1-VPN-012` | Use local or adapted smoke commands/scripts | Local smoke output |
| Run local connected node smoke | `S1-VPN-012` | Register local node and verify `/api/nodes` reports connected state | Local node evidence |
| Record limitation | `TD-S1-VPN-003` | Mark this as local/dev proof, not staging/prod proof | Evidence note |

This package does not close production/staging Remnawave gates. It prepares implementation confidence and local evidence only. Current local result: Remnawave control-plane/API smoke passed through Caddy proxy/TLS; local node registration/connectivity passed; provisioning evidence remains open.

## Work Package 3 — Secrets and Static Safety

| Task | IDs | What we do | Output |
|---|---|---|---|
| Secrets inventory without values | `S1-INFRA-006` | List required secrets by service/env | Redacted inventory |
| Secrets scan | `S1-INFRA-007` | Scan repo for leaked secrets, enforce durable baseline and document remaining RC blockers | Completed locally in `27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md` |
| Frontend env/bundle scan | `S1-FE-010` | Verify public bundle/env does not expose secrets | Completed locally in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`; repeat on RC/staging/production deployed artifact |
| Secret storage policy | `S1-INFRA-006` | Define interim storage until OpenBao maturity | Policy note |
| Rotation runbook draft | `S1-INFRA-006` | JWT/TOTP/OAuth/Remnawave/payment secret rotation draft | Runbook |

## Work Package 4 — Clean DB and Admin Bootstrap

| Task | IDs | What we do | Output |
|---|---|---|---|
| Clean DB migration dry-run | `S1-BE-001` | Apply all migrations from empty local DB | Revalidated locally in `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md` |
| Migration failure inventory | `S1-BE-001` | Record broken/order-dependent migrations if any | Fix list |
| First admin bootstrap design | `S1-BE-002` | Ensure one-time protected bootstrap, no default password, no permanent public endpoint | Completed locally in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md` |
| Admin 2FA enforcement | `S1-AUTH-004`, `S1-ADM-003` | Completed locally: protected admin role/permission surfaces reject admins without TOTP | `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md` and `64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`; deployed browser/API persona proof still required |
| Audit bootstrap event | `S1-ADM-004` | Ensure bootstrap creates audit event | Local audit evidence in `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md`; staging/prod evidence still required |

## Work Package 5 — Backend API Boundaries

| Task | IDs | What we do | Output |
|---|---|---|---|
| Public/internal route audit | `S1-BE-003` | Identify public, user, admin and internal endpoints | Completed locally in `30_STAGE1_BE_003_API_ROUTE_BOUNDARY_EVIDENCE.md` |
| Swagger public-off policy | `S1-BE-004` | Ensure OpenAPI/Swagger is disabled or protected in production mode | Completed locally in `31_STAGE1_BE_004_SWAGGER_PUBLIC_OFF_EVIDENCE.md` |
| CORS/cookie config review | `S1-BE-005` | Align with `cyber-vpn.net` primary and `.org` redirect behavior | Completed locally in `32_STAGE1_BE_005_CORS_COOKIE_CONFIG_EVIDENCE.md` |
| CSRF assessment | `S1-BE-006` | Assess cookie flows and mitigation | Completed locally in `33_STAGE1_BE_006_CSRF_ASSESSMENT_EVIDENCE.md` |
| Rate limits | `S1-BE-007` | Auth/payment/trial/support/referral rate limit review | Completed locally in `34_STAGE1_BE_007_RATE_LIMIT_POLICY_EVIDENCE.md` |
| Edge WAF/rate limiting | `S1-INFRA-008` | Cloudflare/equivalent edge baseline, webhook no-challenge exceptions, admin edge protection and non-HTTP exclusions | Completed locally in `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`; real DNS/TLS/WAF/security-event proof still required |
| Canonical status/error model | `S1-BE-008` | Align backend/UI states for auth/payment/provisioning/support | Completed locally in `35_STAGE1_BE_008_STATUS_ERROR_CONTRACT_EVIDENCE.md` |

## Work Package 6 — Auth and Account Linking

| Task | IDs | What we do | Output |
|---|---|---|---|
| Registration kill switch | `S1-AUTH-001` | Completed locally: public new-account creation pauses safely while existing login remains available | `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md`; deployed toggle proof still required |
| Email/login password flow | `S1-AUTH-002` | Completed locally: register/verify/login/refresh/logout/session-cookie proof | `114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md`; deployed HTTPS/browser/email-provider evidence still required |
| Magic link/OTP | `S1-AUTH-003` | Completed locally: request/dispatch/token-login/OTP-login/replay/rate-limit proof | `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md`; real email-provider and deployed HTTPS/browser proof still required |
| Admin 2FA | `S1-AUTH-004` | Completed locally: protected admin auth gates require TOTP | `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md`; deployed admin persona proof still required |
| Telegram identity linking | `S1-AUTH-005`, `S1-TG-005` | Completed locally: no-silent-merge, idempotent same-identity linking and controlled conflict response | `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`; real Telegram/deployed evidence still required |
| Google/GitHub OAuth scope | `S1-AUTH-006` | Completed locally: Google/GitHub are hard-gated for S1; deferred providers fail closed | `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md`; real provider callback evidence later |
| Delete/export path | `S1-AUTH-007`, `S1-LEGAL-009` | Completed locally: authenticated privacy request route, support escalation and frontend API/MSW path exist | `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md`; deployed `privacy@` mailbox/support queue proof still required |

Google/GitHub production enablement waits for external OAuth apps and callback evidence.

## Work Package 7 — Payments With Mocks and Fixtures

| Task | IDs | What we do | Output |
|---|---|---|---|
| Canonical payment model | `S1-PAY-004` | Implement/verify canonical states from `18` | Completed locally in `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md` |
| Provider mapping fixtures | `S1-PAY-004`, `S1-PAY-017` | Fixtures for PayRam, NOWPayments, CryptoBot, Telegram Stars, Digiseller, YooKassa | Completed locally in `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`; real callback samples still required |
| Signature verification hooks | `S1-PAY-005` | Completed locally: CryptoBot, NOWPayments, PayRam, Telegram Stars, Digiseller and YooKassa authenticity/recheck contracts | `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`; real provider samples still required |
| Webhook idempotency | `S1-PAY-006` | Duplicate webhook must not duplicate transaction/subscription/provisioning | Completed locally in `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`; durable persistence/live provider evidence still required |
| Orphan payment policy | `S1-PAY-007` | Manual review state, 15m alert, 1h P1, 24h P0 rule | Completed locally in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`; real admin/support queue and alert delivery evidence still required |
| Payment -> provisioning failure | `S1-PAY-008` | Completed locally: paid state preserved, retry queued, duplicate webhook does not duplicate provisioning | `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`; durable/live provider evidence still required |
| Refund/dispute process | `S1-PAY-009` | Completed locally: customer refund request, finance/admin role gate, support/operator denied from finance mutation, provider posture documented | `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`; real provider refund/dispute evidence still required |
| Wallet/payment history verification | `S1-PAY-010` | Completed locally: authenticated customer payment history, no frontend `user_uuid`, raw provider fields hidden, withdrawal/payout request creation and UI default-off | `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; deployed screenshots and real provider evidence still required |
| Telegram Stars contract readiness | `S1-PAY-011` | Completed locally: XTR-only flow, pre-checkout non-grant rule, successful-payment confirmation, charge-id storage, refundStarPayment client and refund reconciliation | `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md`; real BotFather/test/prod Stars evidence still required |
| Reconciliation job | `S1-PAY-012` | Completed locally: redacted backend report + internal worker task detect stale/mismatched payment states | `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md`; real provider/admin queue/alert evidence still required |
| Provider placeholder replacement | `S1-PAY-017` | Completed locally: evidence registry + documentation fixture + guardrails preventing docs-only provider enablement | `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md`; real provider-account samples still required |

This package can be done without real provider accounts. It does not enable production payments.

## Work Package 8 — Provider Readiness

| Task | IDs | What we do | Output |
|---|---|---|---|
| Choose first live path | `S1-PAY-001` | Completed locally: CryptoBot / Crypto Pay selected as first live paid-path candidate; paid beta still blocked until provider account/credential/sandbox/prod callback evidence | `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`; `infra/payments/stage1-primary-payment-provider.json` |
| Sandbox/test credentials | `S1-PAY-002` | Completed locally: CryptoBot runtime testnet mode and production guard configured; real `@CryptoTestnetBot` credentials/samples remain external | `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`; provider evidence |
| Production credentials inventory | `S1-PAY-003` | Completed locally: inventory without values and production placeholder guards; real secret-store evidence remains external | `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`; provider evidence |
| PayRam readiness | `S1-PAY-013` | Replace placeholder mapping with real callback/API samples | Provider evidence |
| NOWPayments readiness | `S1-PAY-014` | Local guardrails completed; attach real IPN/API/refund/reconciliation samples before enablement | `110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md`; provider evidence |
| CryptoBot readiness | Provider evidence | Replace placeholder mapping with testnet/prod invoice samples | Provider evidence |
| Telegram Stars readiness | `S1-PAY-011` | Local contract completed; attach real XTR pricing, successful payment and refund/support flow before enablement | `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md`; Telegram account evidence |
| Digiseller readiness | `S1-PAY-015` | Local guardrails completed; attach real seller account/product/callback/status/refund/reconciliation samples before enablement | `111_STAGE1_PAY_015_DIGISELLER_READINESS_EVIDENCE.md`; provider evidence |
| YooKassa readiness | `S1-PAY-016` | Local guardrails completed; attach real shop/account/webhook/status/refund/reconciliation and receipt/fiscalization evidence before enablement | `112_STAGE1_PAY_016_YOOKASSA_READINESS_EVIDENCE.md`; provider evidence |

This package waits on external accounts/credentials.

## Work Package 9 — Trial, Subscription, Pricing

| Task | IDs | What we do | Output |
|---|---|---|---|
| Trial 3 days / 1 device | `S1-PROD-001` | Completed locally: canonical policy, API visibility, entitlement snapshot, duplicate-account rejection and visible copy | `47_STAGE1_PROD_001_TRIAL_POLICY_EVIDENCE.md` |
| Plans | `S1-PROD-002`, `S1-PROD-003` | `S1-PROD-002` completed locally for Basic/Plus/Pro/Max x 30/90/180/365; `S1-PROD-003` completed locally for public/private visibility guards across web, Mini App and Telegram Bot | `48_STAGE1_PROD_002_PAID_PLAN_MATRIX_EVIDENCE.md`, `49_STAGE1_PROD_003_PLAN_VISIBILITY_EVIDENCE.md` |
| Currency display | `S1-PROD-004` | Display conversion only, no billing contradiction | UI screenshots |
| Grace period 72h | `S1-PROD-005` | Completed locally: expired paid access enters 72h self-service grace, then disables at the boundary; trial has no paid grace | `98_STAGE1_PROD_005_GRACE_PERIOD_BEHAVIOR_EVIDENCE.md` |
| Add-ons off unless proven | `S1-PROD-006` | Completed locally: add-ons default-off across public catalogs, checkout/use cases, Mini App, Telegram Bot catalog and web pricing display | `51_STAGE1_PROD_006_ADDONS_KILL_SWITCH_EVIDENCE.md` |
| Promo/gift/referral off | `S1-PROD-007` | Completed locally: `REFERRAL_ENABLED=false`, public promo/gift/referral APIs gated, checkout code discounts blocked, dashboard/Mini App UI hidden, manual audited grants only | `52_STAGE1_PROD_007_GROWTH_KILL_SWITCH_EVIDENCE.md` |

## Work Package 10 — Remnawave Provisioning Logic

| Task | IDs | What we do | Output |
|---|---|---|---|
| Protocol decision | `S1-VPN-003` | Completed locally: `vless-reality-raw` default, `vless-reality-xhttp` alternate; Helix/Verta/Beep remain off | `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md` |
| Gateway/client boundary | `S1-VPN-004`...`S1-VPN-006` | Completed locally through mockable Remnawave gateway, paid/trial contracts and retry behavior | `40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md`, `41_STAGE1_VPN_005_PAID_PROVISIONING_EVIDENCE.md`, `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md` |
| Trial provisioning | `S1-VPN-004` | Completed locally through mockable S1 Remnawave gateway; real staging/prod trial evidence still required | `40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md` |
| Paid provisioning | `S1-VPN-005` | Completed locally through mockable S1 Remnawave gateway; payment webhook integration, retry behavior and real staging/prod paid evidence still required | `41_STAGE1_VPN_005_PAID_PROVISIONING_EVIDENCE.md` |
| Retry behavior | `S1-VPN-006` | Completed locally: Remnawave outage queues retry, later succeeds, exhaustion dead-letters | `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md` |
| Expiry/grace disable | `S1-VPN-007` | Completed locally: paid access disables only after 72h grace; trial disables at expiry; durable DB/worker and staging/prod proof still required | `44_STAGE1_VPN_007_EXPIRY_GRACE_DISABLE_EVIDENCE.md` |
| Credential regeneration | `S1-VPN-008` | Completed locally as backend/API and reusable frontend support-widget contract: dedicated permission, required audit, safe response/log/UI payloads; staging/prod and deployed admin-page proof still required | `43_STAGE1_VPN_008_CREDENTIAL_REGENERATION_EVIDENCE.md` |
| Usage display | `S1-VPN-009` | Completed locally: authoritative Remnawave usage is displayable only when marked available; fallback snapshots are shown as unavailable | `85_STAGE1_VPN_009_USAGE_DISPLAY_EVIDENCE.md`; staging/prod usage correctness evidence still required |
| Node list/regions | `S1-VPN-010` | Completed locally: 12 country-level startup regions, activation tiers, node-slot template and public visibility rules aligned with the current API country-code grouping | `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`; real staging/prod provider/node/monitoring evidence still required |
| Torrent/P2P/TOR node policy | `S1-VPN-011` | Completed locally: Torrent/P2P restricted by default, Remnawave Torrent Blocker enablement contract documented, TOR native-addon finding recorded, and TOR future-control placeholder defined | `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`; real staging/prod plugin/provider/webhook/alert evidence still required |

Production/staging Remnawave evidence waits on real staging/prod environment.

## Work Package 11 — Frontend Customer Cabinet and Marketing

| Task | IDs | What we do | Output |
|---|---|---|---|
| Critical marketing pages | `S1-FE-001` | Completed locally in `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`; deployed screenshots/domain proof still required | Content audit/build evidence |
| Dashboard states | `S1-FE-002` | Active/trial/grace/expired/payment/provisioning states | Completed locally in `99_STAGE1_FE_002_DASHBOARD_STATES_EVIDENCE.md`; deployed screenshots/real transitions still required |
| Config delivery UI | `S1-FE-003` | QR/sub URL/config file; no raw URL logging | Completed locally in `100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md`; deployed screenshots/real Remnawave payload and VPN client import evidence still required |
| Devices page | `S1-FE-004` | Completed locally: authenticated `/settings#devices` devices/limits/actions surface with entitlement-derived limit and safe revoke actions | `101_STAGE1_FE_004_DEVICES_PAGE_EVIDENCE.md`; deployed screenshots and real backend/Remnawave/device enforcement evidence still required |
| Wallet page | `S1-FE-005` | Completed locally: `/wallet` safe recent payment history from customer-scoped API with raw provider fields hidden and withdrawal UI default-off | `102_STAGE1_FE_005_WALLET_PAGE_EVIDENCE.md`; deployed screenshots, real provider records and final RC artifact scan still required |
| Referral/promo/gift hidden | `S1-FE-006` | Completed locally: public growth UI is fail-closed by default and requires master evidence approval plus specific flags | `103_STAGE1_FE_006_GROWTH_UI_GATES_EVIDENCE.md`; deployed screenshots, final public env inventory and RC artifact scan still required |
| Hide operator surfaces | `S1-FE-007` | Completed locally: analytics/monitoring/users/partner hidden and `/servers` is customer-safe without operator metrics | `104_STAGE1_FE_007_OPERATOR_SURFACE_AUDIT_EVIDENCE.md`; deployed browser evidence still required |
| Platform guides | `S1-FE-008` | Completed locally: public `/devices` setup guides cover Android/iOS/Windows/macOS/Linux/Telegram Mini App with safe config-delivery wording | `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`; deployed screenshots and real client import proof still required |
| Critical i18n audit | `S1-FE-009` | Completed locally: 39 enabled locales are fallback-complete for critical S1 namespaces; EN/RU reviewed as S1 launch locales | `106_STAGE1_FE_009_I18N_CRITICAL_PATH_EVIDENCE.md`; deployed browser spot-checks and RC rerun still required |
| Bundle/env scan | `S1-FE-010` | No secrets in client bundle | Local scan evidence in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`; final deployed artifact scan still required |

## Work Package 12 — Telegram Bot and Mini App

| Task | IDs | What we do | Output |
|---|---|---|---|
| Staging bot | `S1-TG-001` | Completed locally: separate staging/prod bot identity config, S1 commands/menu startup surface and command entrypoints | `53_STAGE1_TG_001_STAGING_BOT_CONFIG_EVIDENCE.md`; BotFather/getMe/webhook evidence still required |
| Production bot token path | `S1-TG-002` | Completed locally: backend/worker vault keys, production token path and redacted inventory without values | `54_STAGE1_TG_002_PRODUCTION_BOT_TOKEN_PATH_EVIDENCE.md`; BotFather/getMe/webhook evidence still required |
| Commands/menu/onboarding | `S1-TG-003` | Completed locally: `/start`, `/menu`, `/connect`, `/plans`, `/trial`, `/support`, `/paysupport`, startup commands and menu button are covered | `55_STAGE1_TG_003_COMMANDS_MENU_ONBOARDING_EVIDENCE.md`; live Telegram screenshots/deployed evidence still required |
| Mini App cabinet | `S1-TG-004` | Completed locally: home/plans/payments/devices/profile/wallet render as light cabinet in mobile viewport with screenshots and route text dumps | `56_STAGE1_TG_004_MINIAPP_CABINET_EVIDENCE.md`; real Telegram initData/client/deployed evidence still required |
| Telegram auth/linking | `S1-TG-005` | Completed locally: Mini App initData, bot-link, magic-link, callback conflict handling and no-silent-merge tests | `57_STAGE1_TG_005_TELEGRAM_AUTH_LINKING_EVIDENCE.md`; real Telegram/deployed evidence still required |
| Notifications | `S1-TG-006` | Completed locally: expiry/payment/provisioning queue contract and mocked delivery path | `58_STAGE1_TG_006_TELEGRAM_NOTIFICATIONS_EVIDENCE.md`; real Telegram/provider/provisioning evidence still required |
| Rate limiting | `S1-TG-007` | Completed locally: anti-spam/rate abuse controls for Bot and Mini App/backend linkage | `59_STAGE1_TG_007_TELEGRAM_RATE_LIMITING_EVIDENCE.md`; deployed Redis/webhook/client evidence still required |
| AI support escalation | `S1-TG-008`, `S1-SUP-003` | Completed locally: deterministic no-cost first-line triage, safe redaction and bot-created backend staff-note escalation | `60_STAGE1_TG_008_AI_SUPPORT_ESCALATION_EVIDENCE.md`; real admin/support queue, alerts and SLA evidence still required |

Real Telegram production evidence waits on bot token and public webhook endpoint.

## Work Package 13 — Admin and Support

| Task | IDs | What we do | Output |
|---|---|---|---|
| Admin access protection | `S1-ADM-001` | Completed locally: backend wrong-host admin API protection, production settings validation and admin mirror redirect | `62_STAGE1_ADM_001_ADMIN_ACCESS_PROTECTION_EVIDENCE.md`; deployed DNS/TLS/ingress/private-access evidence still required |
| RBAC matrix | `S1-ADM-002` | Completed locally: owner/super_admin, support, operator/ops and finance permissions separated | `63_STAGE1_ADM_002_RBAC_MATRIX_EVIDENCE.md`; deployed persona/UI proof still required |
| Admin 2FA | `S1-ADM-003` | Completed locally: protected admin role/permission surfaces reject users without TOTP and production config requires `ADMIN_2FA_REQUIRED=true` | `64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`; deployed browser/API persona proof still required |
| Audit log | `S1-ADM-004` | Completed locally: sensitive admin mutations use required audit logging and sanitized details | `65_STAGE1_ADM_004_PRIVILEGED_AUDIT_LOG_EVIDENCE.md`; deployed audit-log/persona proof still required |
| Payment attempts view | `S1-ADM-005` | Completed locally: support/finance safe payment status view with role gates and raw provider redaction | `66_STAGE1_ADM_005_PAYMENT_ATTEMPTS_VIEW_EVIDENCE.md`; deployed persona/real provider evidence still required |
| Manual subscription ops | `S1-ADM-006` | Completed locally: `SUBSCRIPTION_CREATE` gated grant/extend, required audit and safe reusable frontend panel | `67_STAGE1_ADM_006_MANUAL_SUBSCRIPTION_OPS_EVIDENCE.md`; deployed persona/real Remnawave evidence still required |
| Credential regeneration | `S1-ADM-007` | Completed locally: OpenAPI/admin client/customer-detail action with reason-gated dialog and safe summary | `68_STAGE1_ADM_007_CREDENTIAL_REGENERATION_ADMIN_EVIDENCE.md`; deployed admin browser/persona and real Remnawave evidence still required |
| Support ticket path | `S1-SUP-001` | Completed locally: Telegram/email/web/bot/admin ticket reference, queue/SLA and redaction contract | `69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`; deployed mailbox/web/bot/admin queue/alert evidence still required |
| Support templates | `S1-SUP-002` | Completed locally: failed payment, no access, refund, expired, VPN not connecting templates with sensitive-data guardrails; owner/legal text approval closed | `70_STAGE1_SUP_002_SUPPORT_TEMPLATES_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; provider/live workflow evidence still required |
| Escalation process | `S1-SUP-003` | Completed locally: AI/support -> finance/ops/owner rules, P0/P1 SLA, paid-no-access 24h P0 escalation and sensitive-data guardrails | `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`; deployed queue/alert/human SLA evidence still required |

## Work Package 14 — Legal, Privacy, Abuse

| Task | IDs | What we do | Output |
|---|---|---|---|
| Terms | `S1-LEGAL-001` | Owner-approved for S1 legal/text closure; local Terms candidate remains implementation evidence | `72_STAGE1_LEGAL_001_TERMS_OF_SERVICE_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| Privacy | `S1-LEGAL-002` | Owner-approved for S1 legal/text closure; local Privacy Policy candidate remains implementation evidence | `73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| AUP | `S1-LEGAL-003` | Owner-approved for S1 legal/text closure; local AUP candidate remains implementation evidence | `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| Refund | `S1-LEGAL-004` | Owner-approved for S1 legal/text closure; local Refund Policy candidate remains implementation evidence | `75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| Cookie | `S1-LEGAL-005` | Owner-approved for S1 legal/text closure; local Cookie Policy candidate remains implementation evidence | `76_STAGE1_LEGAL_005_COOKIE_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| No-logs validation | `S1-LEGAL-006` | Owner-approved S1 wording stance: no absolute no-logs overpromise; operational metadata disclosed where used | `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| Law enforcement | `S1-LEGAL-007` | Owner-approved request intake, verification, minimum disclosure and audit boundary | `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| Abuse complaint | `S1-LEGAL-008` | Owner-approved abuse intake, safe evidence handling and owner/ops escalation boundary | `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` |
| Export/delete | `S1-LEGAL-009`, `S1-AUTH-007` | Owner-approved manual S1 support/privacy export-delete procedure; local request route/escalation exists and automation can still be deferred | `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`, `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md` |

Legal/text/public-copy placeholders are closed for S1 owner approval in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`. Real mailboxes, provider behavior, cookie inventory, PII scrubbing and deployed workflow proof remain tracked as operational/security/provider evidence.

## Work Package 15 — Observability

| Task | IDs | What we do | Output |
|---|---|---|---|
| Sentry projects/config | `S1-OBS-001` | Completed locally for frontend/admin/backend/bot/worker; live project/test-event evidence later | `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md` |
| PII scrubbing | `S1-OBS-002` | Completed locally for Sentry/log S1 sensitive values | `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md` |
| Metrics/dashboards | `S1-OBS-003` | Completed locally: API/auth/payments/provisioning/worker/DB/Redis/Remnawave dashboard/rule contract exists; deployed Grafana screenshot/live target proof remains before go-live | `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` |
| Alerts | `S1-OBS-004` | Completed locally: Alertmanager routes to Telegram `-5173727789` and `backup@cyber-vpn.net`; live delivery proof remains | `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md` |
| Paid-but-no-access alert | `S1-PAY-007`, `S1-OBS-004` | 15m alert, 1h P1, 24h P0 covered by local rules; real delivery proof remains | `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md` |
| Backup/restore alerts | `S1-QA-003`, `S1-QA-004`, `S1-OBS-004` | Backup stale and restore evidence expired rules exist; real metrics/live delivery proof remains | `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md` |

Local scaffolding can be done now; real alert delivery evidence waits on actual alert channels/mail setup.

## Work Package 16 — QA, Security, Local Evidence

| Task | IDs | What we do | Output |
|---|---|---|---|
| Critical E2E local | `S1-QA-001` | Completed locally: backend/frontend/admin/bot/worker critical slices pass; real staging/prod provider/Remnawave/client connection evidence still required | `88_STAGE1_QA_001_CRITICAL_E2E_LOCAL_EVIDENCE.md` |
| Dependency audit | `S1-QA-002` | Completed locally: npm high/critical clean, Python lock-export audits clean, local S1 Python images rebuilt/scanned high/critical clean after Alpine remediation; repeat on final RC images/artifacts | `89_STAGE1_QA_002_DEPENDENCY_AUDIT_EVIDENCE.md` |
| Backup local proof | `S1-QA-003` | Completed locally: `.dump` custom-format backup created with 14-day retention and verified by `pg_restore --list` | `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md` |
| Restore local drill | `S1-QA-004` | Completed locally: S1-QA-003 `.dump` restored into a clean disposable DB, smoke queries passed, restore DB dropped and resources stopped | `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md` |
| Rollback dry-run draft | `S1-REL-006` | Completed locally: release-pointer rollback, compose config validation and runtime rollback controls passed; repeat on staging/prod RC artifacts | `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md` |
| Evidence pack structure | `S1-REL-007` | Completed locally: `payments/`, `vpn/`, `db/`, `security/`, `observability/`, `release/`, `legal-support/`, `scope-map/` README structure and root index assembled | `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md`, `evidence_pack/stage1/README.md` |

## Work Package 17 — External Staging / Production Unlock

These tasks are intentionally delayed until we decide to spend money or use external managed services.

| Task | IDs | Requires | Output |
|---|---|---|---|
| Real staging environment | `S1-INFRA-002` | External host or accepted staging infra | Local contract complete in `121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md`; external staging health evidence still required |
| Production environment | `S1-INFRA-003` | External production host/managed services | Local contract complete in `122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md`; external production deploy/health evidence still required |
| DNS/TLS | `S1-INFRA-004` | DNS access, domains, edge/TLS provider | Local contract complete in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; live DNS/TLS/redirect/admin-protection evidence still required |
| Protected ingress | `S1-INFRA-005` | Reverse proxy/edge/WAF/IP allowlist | Local contract complete in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`; external edge/reverse-proxy/firewall/admin-access evidence still required |
| Managed PostgreSQL | `S1-INFRA-003`, `S1-QA-003`, `S1-QA-004` | Managed DB/provider | Backup/restore evidence |
| Private Valkey/Redis | `S1-INFRA-003`, `S1-OBS-003` | Managed/private Redis or equivalent | Monitoring evidence |
| Real Remnawave staging/prod | `S1-VPN-001`, `S1-VPN-002` | External hosts/control-plane | Health/provisioning evidence |
| Real payment credentials | `S1-PAY-002`, `S1-PAY-003`, provider tasks | Provider accounts | Provider evidence |
| Real Telegram webhook | `S1-TG-001`, `S1-TG-002` | Public webhook endpoint | Bot evidence |

Home server may support lab/staging-like work, but must not become production critical path while 5-hour power outages are possible.

## Work Package 18 — Go-Live Gates

| Gate | What must be true | Output |
|---|---|---|
| G0 Document Approval | Docs, decisions, operational inputs and tech debt accepted | Implementation allowed |
| G1 Repo/RC Freeze | Dirty worktree mapped, experimental excluded, RC branch/tag ready | RC allowed |
| G2 Local/Integration | Critical local/integration tests pass | Staging deploy allowed |
| G3 Staging E2E | Full staging flow works with separate services | Beta candidate |
| G4 Security/Legal/Ops | Legal/text owner approval closed, secrets clean, backups/rollback/alerts ready | Public beta allowed |
| G5 Controlled Public Beta | Real users, metrics monitored, support loop works | Stabilization evidence |
| G6 S1 Production Operation | Core flow stable; decision to proceed to S2 | S2 planning |

## What We Should Do First

Immediate order:

1. `S1-TG-001` — completed locally: staging/prod Telegram Bot identity config and command/menu startup surface.
2. `S1-TG-002` — completed locally: production Telegram Bot token path and secrets inventory without values.
3. `S1-TG-003` — completed locally: Telegram Bot commands, menu, onboarding and support smoke evidence.
4. `S1-TG-004` — completed locally: Mini App home/plans/payments/devices/profile/wallet route evidence.
5. `S1-TG-005` — completed locally: Telegram auth/linking/no-silent-merge evidence.
6. `S1-TG-006` — Telegram notifications evidence.

This path gives maximum progress without paying for servers.

## Work Explicitly Not Started in S1

| Area | Status |
|---|---|
| Partner public portal | `DEFERRED` to S3 |
| Partner payouts | `DEFERRED` to S3 |
| Mobile store release | `DEFERRED` to S4 |
| Desktop production release | `DEFERRED` to S5 |
| Android TV production release | `DEFERRED` to S5 |
| Helix/Verta/Beep production/default transport | `DEFERRED` to S6 |
| Full GitOps/Talos/Kubernetes maturity | `DEFERRED` to S7 unless already justified |
| Public referral/promo/gift flows | Disabled in S1 |
| Autoprolongation | Not promised in S1 |

## 2026-05-09 Current Ordered Batch Status

The owner-requested ordered batch was completed locally/revalidated:

| Order | ID | Result | Evidence |
|---:|---|---|---|
| 6 | `S1-BE-002` | PASS locally: clean DB first-admin bootstrap creates one `owner/super_admin`, TOTP enabled, audit event written, repeat bootstrap rejected | `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md` |
| 7 | `S1-BE-003` | PASS locally: 603 HTTP routes, 2 WebSocket routes, `needs-review=0`, route-boundary tests pass | `30_STAGE1_BE_003_API_ROUTE_BOUNDARY_EVIDENCE.md` |
| 8 | `S1-AUTH-001` | PASS locally: registration kill switch and auth regression suite pass | `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md` |
| 9 | `S1-AUTH-002` | PASS locally: email/password registration, OTP activation, login, refresh, logout and cookie checks pass | `114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md` |
| 10 | `S1-AUTH-003` | PASS locally: magic link/OTP generation, verification, replay rejection, resend and rate-limit checks pass | `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md` |

Resource note: `remnawave-db` and `remnawave-redis` were started only for `S1-AUTH-002`/`S1-AUTH-003` and stopped after this batch.

Next ID to execute: `S1-AUTH-004` - admin 2FA verification.

## 2026-05-09 Auth/VPN Ordered Batch Status

The next owner-requested ordered batch was completed locally/revalidated:

| Order | ID | Result | Evidence |
|---:|---|---|---|
| 11 | `S1-AUTH-004` | PASS locally: admin 2FA role/permission gate, 2FA lifecycle integration, finance/support gates and ruff passed | `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md` |
| 12 | `S1-AUTH-006` | PASS locally: Google/GitHub OAuth provider boundary and deferred-provider fail-closed regression passed | `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md` |
| 13 | `S1-AUTH-007` | PASS locally: backend privacy request route, OpenAPI export, frontend API/MSW tests and generated API types passed | `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md` |
| 14 | `S1-VPN-001` | PASS-PARTIAL locally: Remnawave control-plane, local TLS/proxy and authorized nodes API smoke passed; real external staging remains required | `128_STAGE1_VPN_001_REMNAWAVE_STAGING_CONTROL_PLANE_EVIDENCE.md` |
| 15 | `S1-VPN-003` | PASS locally: S1 protocol allowlist tests and ruff passed | `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md` |

Resource note: `remnawave-db`, `remnawave-redis`, `remnawave` and `caddy` were started only for integration/control-plane checks and stopped after the batch.

Next ID to execute: `S1-VPN-004` - trial provisioning.

## 2026-05-09 VPN/Payment/QA/Ingress Ordered Batch Status

The next owner-requested ordered batch was completed locally/revalidated:

| Order | ID | Result | Evidence |
|---:|---|---|---|
| 16 | `S1-VPN-004` | PASS locally: trial provisioning through mockable S1 Remnawave gateway, 12 tests and ruff passed | `40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md` |
| 17 | `S1-PAY-002` | PASS locally: CryptoBot sandbox/testnet contract validator, backend tests, infra tests, task-worker tests and ruff passed | `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md` |
| 18 | `S1-QA-003` | PASS locally: fresh custom-format `.dump` backup `20260509T112917Z`, 14-day retention and `pg_restore --list` proof | `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md` |
| 19 | `S1-QA-004` | PASS locally: fresh restore drill from `20260509T112917Z` backup into disposable DB, smoke queries passed, DB dropped | `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md` |
| 20 | `S1-INFRA-005` | PASS locally/PARTIAL live: protected-ingress contract validators/tests passed; live API/admin hosts still not resolved/proven | `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md` |

Resource note: `remnawave-db` was started only for backup/restore and stopped after `S1-QA-004`. No containers remained running after the batch.

Next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.

## 2026-05-09 RC / Go-No-Go Ordered Status

The next owner-requested ordered steps were evaluated:

| Order | Step | Result | Evidence |
|---:|---|---|---|
| 31 | `stage1-beta-rc.N` | BLOCKED for real tag: candidate would be `stage1-beta-rc.1`, but release branch is missing and current worktree is dirty | `129_STAGE1_STEP_31_RC_TAG_EVIDENCE.md` |
| 32 | `Owner go/no-go` | Prepared, not owner-signed: recommendation is `NO-GO_FOR_CONTROLLED_BETA_LAUNCH`; conditional go only for RC tag preparation after scope/commit/tag work | `130_STAGE1_STEP_32_OWNER_GO_NO_GO_EVIDENCE.md` |

Next ordered step: owner must sign or override the go/no-go decision before `33. Controlled beta cohort launch`.

## 2026-05-09 Release/Frontend/QA Ordered Batch Status

The next owner-requested ordered batch was completed locally/revalidated:

| Order | ID | Result | Evidence |
|---:|---|---|---|
| 26 | `S1-REL-006` | PASS locally: release-pointer rollback, compose config, backend/admin rollback controls and safety tests passed | `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md` |
| 27 | `S1-FE-010` | PASS locally: production frontend build, private canary scan, high-confidence secret scan, source-map count, Sentry regression test and targeted lint passed | `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md` |
| 28 | `S1-QA-002` | PASS locally: npm high/critical threshold, Python lock-export audits, Docker Scout high/critical image scans and container `pip check` passed | `89_STAGE1_QA_002_DEPENDENCY_AUDIT_EVIDENCE.md` |
| 29 | `S1-REL-002` | PASS inventory: current worktree remains broad but excluded partner/mobile/desktop/TV/extension/Helix/Verta/Beep/GitOps runtime scan has no matches | `22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md` |
| 30 | `S1-REL-007` | PASS locally: evidence-pack README structure, relative links and stale next-step scan passed | `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md` |

Resource note: no long-lived containers were left running. Docker Scout indexed local images, and `docker run --rm ... pip check` containers exited and were removed automatically.

Batch final checks passed: `git diff --check` on touched evidence docs, current-tree Gitleaks baseline-enforced scan (`no leaks found`), strict targeted assignment-style secret scan, targeted dangerous-pattern scan and root `npm audit --omit=dev --audit-level=high`. Residual npm finding remains the already-known moderate Next/PostCSS advisory where `npm audit fix --force` proposes a prohibited breaking downgrade.

Live evidence still required before go-live: staging/prod rollback on real RC artifacts, deployed frontend artifact/CDN scan, final RC image scans, owner-approved pre-RC dirty worktree scope map and final evidence pack snapshot.

Next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.

## 2026-05-09 Infra/Observability Ordered Batch Status

The next owner-requested ordered batch was completed locally/revalidated:

| Order | ID | Result | Evidence |
|---:|---|---|---|
| 21 | `S1-INFRA-008` | PASS locally: edge WAF/rate-limit baseline validator, 3 contract tests and ruff passed | `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md` |
| 22 | `S1-OBS-001` | PASS locally: Sentry critical project/config validator, frontend/admin tests, backend Sentry privacy tests, bot Sentry/before-send tests and worker observability test passed | `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md` |
| 23 | `S1-OBS-002` | PASS locally: frontend/admin Sentry privacy tests, backend Sentry/log sanitization tests, bot/worker redaction tests, privacy validator, lint and ruff passed | `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md` |
| 24 | `S1-OBS-003` | PASS locally: observability dashboard/rule validator, Prometheus/Alertmanager tooling, backend contract tests, worker reconciliation metrics tests, ruff, Python compile and dashboard JSON validation passed | `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md` |
| 25 | `S1-OBS-004` | PASS locally: alerting validator, Prometheus/Alertmanager tooling, backend alerting contract tests, shell syntax checks and Python compile passed | `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md` |

Resource note: no long-lived containers were started for this batch. `validate-observability-tooling.sh` used its validation tooling path and left no containers running.

Batch final checks passed: `git diff --check` on touched evidence docs, current-tree Gitleaks baseline-enforced scan (`no leaks found`), backend/Telegram Bot/task-worker `pip-audit` (`No known vulnerabilities found`), high/critical root `npm audit` threshold and targeted dangerous-pattern scan. Residual npm finding remains the already-known moderate Next/PostCSS advisory where `npm audit fix --force` proposes a prohibited breaking downgrade.

Live evidence still required before go-live: real edge WAF/security-event proof, live Sentry project/DSN/test-event/source-map evidence, deployed Grafana/Prometheus target evidence, and Telegram/email alert delivery proof.

Next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
