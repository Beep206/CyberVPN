> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Review Checklist for Owner Approval

## Purpose

Этот чеклист нужен, чтобы владелец проекта проверил первый пакет документов и вернул правки до реализации. После утверждения реализация Stage 1 должна идти строго по утверждённым документам.

## 1. Confirm Stage 1 definition

Mark each item:

- [ ] Stage 1 = Controlled Public Beta, not full public release.
- [ ] Stage 1 scope includes B2C only.
- [ ] Website + web cabinet are included.
- [ ] Telegram Bot + Mini App are included.
- [ ] Trial is included: 3 days / 1 device / available to all.
- [ ] At least one payment provider must be production-ready before paid beta.
- [ ] Remnawave is authoritative VPN backend.
- [ ] Partner portal is not public in Stage 1.
- [ ] Partner payouts are disabled in Stage 1.
- [ ] Mobile/desktop/Android TV are not required in Stage 1.
- [ ] Helix/Verta/Beep are disabled/default-off in Stage 1.

## 2. Business decisions to fill before implementation

The recommended answers below are the engineering baseline for **Controlled Public Beta CyberVPN / B2C contour**. The owner answers were recorded on 2026-05-03 and are now the active S0 decision-freeze inputs for Stage 1 implementation planning.

| ID | Decision | Recommended beta answer | Owner answer | Blocks |
|---|---|---|---|---|
| DEC-S1-001 | Main public domain | Select one canonical product domain before implementation | Primary domain: `cyber-vpn.net`; mirror: `cyber-vpn.org` | DNS, TLS, CORS, cookies, OAuth, webhooks |
| DEC-S1-002 | Admin domain/protection model | Separate `admin.<main-domain>` protected by IP allowlist or private access, mandatory admin 2FA and RBAC | Admin domain: `admin.cyber-vpn.net`; mirror: `admin.cyber-vpn.org`; protected admin access, mandatory 2FA/RBAC | Admin security, support operations |
| DEC-S1-003 | Production hosting topology | Simple controlled topology: separate staging/prod, containerized backend/worker/bot, persistent Postgres/Valkey, separate Remnawave, reverse proxy/TLS, monitoring | Simple Controlled Hybrid Container Topology for S1 | Deploy, rollback, secrets, backups |
| DEC-S1-004 | Production PostgreSQL location | Managed Postgres or dedicated production DB host with automated backups; not local Docker; not shared with staging | Managed PostgreSQL 17.x, private-only, separate from staging, with separate DB/users for CyberVPN and Remnawave, plus mandatory backup/restore evidence before S1 go-live | Migrations, backups, RPO/RTO |
| DEC-S1-005 | Production Redis/Valkey location | Dedicated production Redis/Valkey, private network only, no public exposure | Dedicated private Valkey/Redis for queues/cache/rate limits, production separate from staging, no public access, with monitoring, memory policy and recovery of critical jobs from PostgreSQL | Workers, queues, rate limits, cache/session behavior |
| DEC-S1-006 | Production Remnawave location | Separate production Remnawave instance, protected admin/API, backed up and monitored | Dedicated production Remnawave control-plane, private/internal API, separate from staging, with provisioning and backup evidence before go-live | VPN provisioning |
| DEC-S1-007 | Staging Remnawave location | Separate staging Remnawave instance matching production contract | Separate staging Remnawave instance with test nodes/providers, same production contract, disposable data, mandatory smoke/evidence before S1 rollout | E2E staging evidence |
| DEC-S1-008 | Primary payment provider | One production-ready provider minimum; additional providers gated by evidence | Approved S1 provider set: PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, YooKassa for users from Russia. `S1-PAY-001` selects CryptoBot / Crypto Pay as the first live paid-path candidate in `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md` and `infra/payments/stage1-primary-payment-provider.json`; each provider remains gated by account, credentials, webhook/status/refund/reconciliation evidence before enablement. Documentation-derived placeholder mappings are in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`; replacement debt is in `19_STAGE1_TECH_DEBT_REGISTER.md`; local provider-specific guardrails currently exist for Telegram Stars, PayRam, NOWPayments, Digiseller and YooKassa in `108`, `109`, `110`, `111` and `112` | Paid beta, refunds, reconciliation |
| DEC-S1-009 | Telegram Stars launch status | Optional; enable only if bot token, Stars setup, XTR pricing and refund behavior are proven | Telegram Stars enabled only for Telegram Bot/Mini App paid flow and only after evidence | Telegram paid flow |
| DEC-S1-010 | Payment provider accounts owner | Name owner/finance person or legal entity controlling provider accounts and reconciliation | Payment accounts belong to legal seller/project owner, finance/ops backup `@Sasha_Beep`, limited technical access, audited refunds/reconciliation, secrets stored through approved process | Credentials, legal seller, refunds |
| DEC-S1-011 | Legal seller / company/person | Must be provided by owner/legal before public paid beta | Individual founder/owner; public seller display/jurisdiction/legal copy remain placeholders tracked as tech debt | Terms, Privacy, Refund, provider ownership |
| DEC-S1-012 | Grace period duration | 24 hours baseline unless owner chooses otherwise | 72 hours | Expiry jobs, UI states, support templates |
| DEC-S1-013 | First-week success metric | 95%+ successful `trial/pay -> VPN ready`, median provisioning under 60 seconds, zero unresolved paid orphan payments older than 24h | 95%+ successful `trial/pay -> VPN ready`, median provisioning <=60s, p95 <=5min, zero unresolved paid-but-no-access/orphan payments older than 24h | Go/no-go, monitoring, support load |
| DEC-S1-014 | On-call/support owner | Name one primary owner and one backup for launch week; define alert destination | Primary `@Sasha_Beep`, backup `@Sasha_Beep`. Alerts go to private Telegram channel `-5173727789` + backup email `backup@cyber-vpn.net`. Primary owner can pause registration/payments/trial/provisioning and initiate rollback. P0 ack <=15min, P1 <=1h, beta support first response <=12h. Go-live blocked until alert delivery and test support escalation are proven; single-person coverage risk must be accepted for S1 or split | Incident response, support SLA |
| DEC-S1-015 | Backup retention/RPO/RTO | Daily Postgres backups retained 14 days, pre-deploy backup, RPO <= 24h, RTO <= 4h, restore drill before go-live | Daily encrypted PostgreSQL backups retained 14 days, pre-deploy backup before production migrations/releases, off-host storage, RPO <=24h, RTO <=4h, Remnawave backup/export/rebuild strategy required, restore drill evidence required before go-live. Redis/Valkey is not durable source of truth for S1 | DR readiness |
| DEC-S1-016 | First admin bootstrap owner | Name owner/ops person; one-time bootstrap, audit event, 2FA enforced, bootstrap disabled/locked after use | Bootstrap owner `@Sasha_Beep`. First production admin is created only via one-time protected bootstrap after clean migrations; role `owner/super_admin`; mandatory 2FA before admin access; audit event required; bootstrap disabled after use; no default credentials, no committed password, no permanent public bootstrap endpoint. Go-live blocked until redacted bootstrap evidence exists | Admin access, audit, RBAC |
| DEC-S1-017 | Launch candidate branch/tag | Branch `release/stage1-controlled-public-beta`; tags `stage1-beta-rc.N` and `stage1-beta-live.N` | Use `release/stage1-controlled-public-beta`; staging/beta tags `stage1-beta-rc.N`; production tags `stage1-beta-live.N`; optional `stage1-docs-freeze.1`. Deploy only by immutable tag/commit SHA, never floating `main`. No tag until dirty worktree inventory and launch-critical/excluded scope map are approved. Every runtime change must reference an `S1-*` backlog ID | Release freeze, rollback |
| DEC-S1-018 | Whether referral/promo/gift are enabled in Stage 1 | Disabled by default; enable only with kill switch, limits, anti-abuse and support evidence | Disabled by default. `REFERRAL_ENABLED=false`; public referral, promo and gift flows hidden/gated; no rewards, no payouts, no gift purchase, no checkout discounts from codes. Manual audited support grants are allowed. Enable later only with kill switch, limits, anti-abuse, idempotency, payment/refund tests, support workflow and legal copy evidence | Fraud risk, UI/backend scope |
| DEC-S1-019 | Whether OAuth providers are enabled in Stage 1 | Email/password plus Telegram identity/linking if ready. Other OAuth providers disabled until credentials/callbacks/linking policy are proven | Enable email/login + password, Telegram identity/linking, Magic link/OTP, OAuth only: Google, GitHub | Auth scope, account conflict policy |
| DEC-S1-020 | Whether autoprolongation is promised in Stage 1 | Do not promise autoprolongation unless chosen provider supports it and evidence exists | Do not promise autoprolongation in S1. Use manual renewal plus expiry reminders/renewal invoice links if tested. No automatic charge, no saved recurring payment method, no "renews automatically" copy. Enable true autoprolongation only later with provider recurring support, user consent, cancel flow, failed-renewal handling, webhook idempotency, refund policy and staging/prod evidence | Pricing copy, subscription jobs, support |

## 3. Payment approval checklist

- [x] Primary payment provider selected locally: CryptoBot / Crypto Pay is first live paid-path candidate in `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`; paid beta remains blocked until account/credentials/sandbox/production callback evidence exists.
- [x] CryptoBot sandbox/test runtime contract exists locally in `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`: backend and task-worker support `CRYPTOBOT_NETWORK=testnet` outside production, production rejects testnet, and arbitrary provider base URLs are blocked.
- [ ] Real CryptoBot sandbox/test credentials and provider samples exist (`@CryptoTestnetBot` account, paid/expired/failure invoice samples, callback signature evidence).
- [x] CryptoBot production credential inventory without values exists locally in `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`: required keys, runtime consumers, placeholder guards and no-repo-values policy are documented/tested.
- [ ] Real CryptoBot production provider account and secret-store evidence exist without secret values.
- [ ] Webhook endpoint registered for staging.
- [ ] Webhook endpoint registered for production.
- [ ] Signature verification tested.
- [ ] Duplicate webhook tested.
- [x] Status mapping documented locally in `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`; provider placeholder replacement guardrails completed in `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md`; real provider-account samples remain required before paid enablement.
- [x] Telegram Stars contract readiness tested locally in `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md`: XTR-only flow, pre-checkout non-grant rule, successful-payment confirmation, charge-id storage and refund client are covered; real BotFather/test/prod Stars payment/refund/support/provisioning evidence remains required before enablement.
- [x] PayRam readiness guardrails tested locally in `109_STAGE1_PAY_013_PAYRAM_READINESS_EVIDENCE.md`: `FILLED` paid status, underpaid/overpaid/cancelled handling, `API-Key` webhook authenticity, idempotency and provider-evidence blockers are covered; real PayRam account, credentials, callback/status-poll, refund/reconciliation and provisioning evidence remains required before enablement.
- [x] NOWPayments readiness guardrails tested locally in `110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md`: `finished` paid status, partial/wrong-asset/refund handling, `x-nowpayments-sig` HMAC-SHA512 authenticity, idempotency and provider-evidence blockers are covered; real NOWPayments account, credentials, IPN/status-poll, refund/reconciliation and provisioning evidence remains required before enablement.
- [ ] Orphan payment policy approved.
- [x] Refund Policy completed for S1 legal/text owner approval in `75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md` and `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; provider refund evidence and support/admin workflow evidence remain provider/support gates.
- [x] Acceptable Use Policy completed for S1 legal/text owner approval in `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md` and `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; abuse mailbox, node/provider torrent evidence and enforcement proof remain support/ops gates.
- [ ] Dispute/chargeback process approved or disabled if provider does not support.
- [x] Reconciliation job tested locally in `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md`; real provider reconciliation samples, deployed manual review queue and alert delivery remain paid beta/go-live gates.
- [ ] User receipt/invoice/notification behavior documented.

## 4. Remnawave/provisioning approval checklist

- [ ] Remnawave staging deployed.
- [ ] Remnawave production deployed.
- [ ] Stage 1 protocol list approved.
- [ ] XHTTP requirement confirmed.
- [ ] Helix/Verta/Beep disabled/default-off.
- [x] 12 startup regions listed locally in `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`; real staging/prod provider/node/monitoring evidence remains open.
- [x] Torrent/P2P/TOR node traffic policy documented locally in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`; real Remnawave plugin/provider/webhook/alert evidence remains open before enablement.
- [ ] Backup/fallback nodes policy approved.
- [ ] Trial provisioning tested.
- [ ] Paid provisioning tested.
- [ ] Remnawave outage retry tested.
- [x] Expiry/grace disable tested locally for worker contract; durable DB/worker and staging/prod evidence remains open.
- [x] Credential regeneration role-gated and audit-logged locally for backend/API, reusable frontend support-widget contract and admin customer-detail integration; staging/prod Remnawave and deployed admin browser/persona evidence remains open.
- [x] Config links sanitized in credential-regeneration response/audit/log contract.
- [x] Manual subscription grant/extend is role-gated and audit-logged locally for backend/API plus reusable frontend operator/admin panel contract; deployed admin persona and real Remnawave evidence remains open.

## 5. Auth/account approval checklist

- [x] Public registration toggle tested locally in `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md`; deployed staging/prod proof remains required before go-live.
- [x] Email/login password flow approved locally in `114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md`; deployed HTTPS/browser cookie and real email-provider evidence remains required before go-live.
- [x] Magic link/OTP flow approved locally in `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md`; real email-provider, sender-domain and deployed HTTPS/browser evidence remains required before enabling passwordless login.
- [x] Telegram auth/link flow approved locally for backend/client contract; real Telegram client and deployed staging evidence remains open.
- [x] Email linking policy for Telegram users approved locally: no silent email merge; explicit verified-email/session proof or support escalation required.
- [x] OAuth providers selected and locally gated for Stage 1 in `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md`: Google and GitHub only; credentials/callbacks/browser evidence remains required before public enablement.
- [x] Account conflict policy approved locally: provider identity conflicts return controlled errors and same-identity retries are idempotent.
- [x] Admin 2FA enforced locally for role/permission-protected admin API surfaces in `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md`; deployed browser/API persona proof remains required before go-live.
- [ ] User 2FA supported.
- [ ] Delete/export data path approved.

## 6. Frontend/Telegram approval checklist

- [x] Marketing critical pages reviewed locally for S1: pricing/features/devices/help/legal/status route files exist, EN/RU public copy has no placeholders/stale domains/unsupported S1 claims, and canonical domain is `cyber-vpn.net` in `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`; deployed staging/RC screenshots and domain proof remain required.
- [ ] Pricing page and checkout do not conflict.
- [ ] Local currency display rule approved.
- [ ] Dashboard state matrix approved.
- [ ] Devices page approved.
- [ ] Wallet/payment history approved. Local authenticated-customer scoping, no raw provider-field rendering and default-off withdrawal/payout UI evidence exists in `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; deployed screenshots and real provider evidence are still required.
- [ ] Referral page gated or approved.
- [x] Platform guides reviewed. Local public `/devices` guide coverage exists for Android, iOS, Windows, macOS, Linux and Telegram Mini App in `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`; deployed screenshots and real Remnawave/client import evidence are still required.
- [ ] Mini App critical flows tested. Local home/plans/payments/devices/profile/wallet route smoke and screenshots exist in `56_STAGE1_TG_004_MINIAPP_CABINET_EVIDENCE.md`; real Telegram initData/client/deployed staging evidence is still required.
- [ ] Bot menu/onboarding/support flows tested. Local command/menu/onboarding smoke coverage exists in `55_STAGE1_TG_003_COMMANDS_MENU_ONBOARDING_EVIDENCE.md`; live Telegram client/BotFather/deployed staging evidence is still required.
- [ ] Production Telegram Bot token path approved. Local redacted inventory exists in `54_STAGE1_TG_002_PRODUCTION_BOT_TOKEN_PATH_EVIDENCE.md`; real BotFather/token/getMe/webhook evidence is still required.
- [ ] Telegram expiry/payment/provisioning notifications tested. Local S1 queue contract and mocked delivery evidence exists in `58_STAGE1_TG_006_TELEGRAM_NOTIFICATIONS_EVIDENCE.md`; real Telegram client rendering, worker delivery and provider/provisioning integration evidence is still required.
- [ ] Telegram Bot/Mini App anti-spam tested. Local bot message/callback throttling and backend Mini App rate-limit linkage evidence exists in `59_STAGE1_TG_007_TELEGRAM_RATE_LIMITING_EVIDENCE.md`; deployed Redis/webhook/client evidence is still required.
- [ ] Telegram support first-line escalation tested. Local deterministic first-line triage, safe redaction and backend support staff-note intake evidence exists in `60_STAGE1_TG_008_AI_SUPPORT_ESCALATION_EVIDENCE.md`; local support escalation runbook contract exists in `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`; deployed bot/admin queue/alert/SLA evidence is still required.
- [x] Critical-path i18n reviewed locally for S1 fallback-complete EN/RU launch posture; deployed browser spot-checks and RC rerun still required.

## 7. Admin/support approval checklist

- [ ] Admin domain/protection approved.
- [x] RBAC matrix implemented/tested locally; owner approval and deployed admin persona/UI proof remain required before go-live.
- [x] Admin 2FA enforcement implemented/tested locally; deployed login/UI/API proof remains required before go-live.
- [ ] First admin bootstrap approved.
- [x] Audit log coverage approved locally for sensitive admin mutations; deployed audit-log/persona proof remains required before go-live.
- [ ] Manual subscription operations role-gated.
- [x] Refund/dispute operations role-gated locally in `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`; deployed admin persona, provider refund/dispute and audit retrieval evidence remain required before paid go-live.
- [x] Credential regeneration role-gated for backend/API and wired into admin customer-detail locally.
- [x] Support can inspect safe payment-attempt statuses locally through scoped admin API and reusable UI contract; deployed admin persona/UI/API proof remains required before go-live.
- [x] Support payment-attempt view hides raw provider references, idempotency keys, provider/request snapshots, payment URLs and finance-only wallet/gateway breakdown locally; deployed secret-redaction proof remains required before go-live.
- [x] Local credential-regeneration widget and admin result summary do not render raw subscription URL, short UUID or raw provider errors.
- [x] Support ticket path and AI/bot escalation are tested locally through deterministic safe references, queue/SLA mapping and redaction; deployed mailbox/web/bot/admin queue/alert evidence remains required.
- [x] Support templates implemented/tested locally for failed payment, paid-no-access, VPN not connecting, expired subscription and refund request; owner/legal text approval is closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`, provider/live workflow evidence remains required before go-live.
- [x] Support escalation process implemented/tested locally for AI/support -> finance/ops/owner routing, P0/P1 SLA, paid-no-access 24h P0 escalation and sensitive-data guardrails; deployed admin/support queue, alert delivery and human SLA acknowledgement remain required before go-live.

## 8. Legal/privacy approval checklist

- [x] Terms of Service final for S1 owner-approved legal/text closure; evidence: `72_STAGE1_LEGAL_001_TERMS_OF_SERVICE_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- [x] Privacy Policy final for S1 owner-approved legal/text closure; evidence: `73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- [x] AUP final for S1 owner-approved legal/text closure; evidence: `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- [x] Refund Policy final for S1 owner-approved legal/text closure; evidence: `75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- [x] Cookie Policy final for S1 owner-approved legal/text closure; evidence: `76_STAGE1_LEGAL_005_COOKIE_POLICY_EVIDENCE.md`, `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- [x] No-logs wording stance approved for S1: no absolute overpromise and operational metadata disclosed where used.
- [x] Data retention/manual export-delete procedure documented and approved for S1.
- [x] Abuse runbook approved for S1.
- [x] Law enforcement request policy approved for S1.
- [x] GDPR export/delete procedure approved for S1 manual support path.

## 9. Security/operations approval checklist

- [ ] Secrets management approved.
- [ ] Secrets scan clean.
- [x] Dependency audit passed locally in `89_STAGE1_QA_002_DEPENDENCY_AUDIT_EVIDENCE.md`: no high/critical findings in S1 npm/Python audits or rebuilt local S1 Python service images; repeat on final RC artifacts/images before go-live.
- [x] Frontend bundle/env scan clean locally in `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`; repeat on RC/staging/production deployed artifact before go-live.
- [x] Local critical E2E gate passed in `88_STAGE1_QA_001_CRITICAL_E2E_LOCAL_EVIDENCE.md` for backend, frontend, admin, Telegram Bot and worker critical slices; deployed staging/prod E2E proof remains required before go-live.
- [ ] CORS/cookies/CSRF verified.
- [ ] Swagger disabled publicly.
- [ ] Rate limits tested.
- [x] Admin API wrong-host protection and admin mirror redirect tested locally; deployed DNS/TLS/ingress/private-access proof remains required before go-live.
- [x] Sentry PII scrubbing verified locally in `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`; live Sentry org/deployed proof remains required.
- [x] Metrics/dashboards configured locally in `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md`; deployed Grafana/live target proof remains required.
- [x] Alerts configured locally in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; live Telegram/email delivery test remains required before go-live.
- [x] Backup configured locally in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md`; managed staging/prod encrypted off-host backup and alert evidence remain required before go-live.
- [x] Restore drill completed locally in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`; managed staging/prod restore, production RPO/RTO and Remnawave backup/export/rebuild evidence remain required before go-live.
- [x] Rollback dry-run completed locally in `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md`; staging/prod rollback on final RC artifacts, provider/Remnawave/backup/alert surfaces remains required before go-live.
- [ ] Status page ready.

## 10. Approval decision

```text
Stage: S1 Controlled Public Beta
Documents reviewed:
Decision: Approved / Approved with changes / Blocked
Required changes:
Owner:
Date:
```

## Recommended next action

Review these documents in this order:

1. `02_STAGE1_CHARTER.md`.
2. `01_LAUNCH_ROADMAP.md`.
3. `03_STAGE1_PRD_USER_FLOWS.md`.
4. `04_STAGE1_TECHNICAL_SPEC.md`.
5. `10_STAGE1_RISK_REGISTER.md`.
6. `11_STAGE1_REVIEW_CHECKLIST.md`.
7. Remaining operational documents.

The fastest path to implementation is to fill the decision table in section 2 and mark whether Stage 1 scope is approved or needs changes.
