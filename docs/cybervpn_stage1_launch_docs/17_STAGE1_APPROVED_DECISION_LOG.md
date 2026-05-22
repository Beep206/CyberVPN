> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации owner answers: 2026-05-03
> Статус: approved owner decision log for S0 Documentation & Decision Freeze. Не является разрешением на production go-live без evidence gates.

# Stage 1 Approved Decision Log

## Purpose

Этот файл фиксирует утверждённые owner answers для Stage 1 Controlled Public Beta. Реализация Stage 1 должна ссылаться на эти решения и на task IDs из `06_STAGE1_IMPLEMENTATION_BACKLOG.md`.

## Approved decisions

| Decision ID | Area | Approved decision | Evidence / implementation impact | Status |
|---|---|---|---|---|
| DEC-S1-001 | Domains | Primary public domain: `cyber-vpn.net`. The `.org` zone is no longer a customer web mirror; for S1 it is reserved for VPN node hostnames and public subscription delivery such as `https://cyber-vpn.org/api/sub/{short_uuid}`. | DNS, TLS, CORS, cookies, OAuth callbacks, payment webhooks and Telegram callbacks must be configured for `.net` customer surfaces. `.org` must not serve the customer web UI except the approved `/api/sub*` subscription delivery path. | Approved |
| DEC-S1-002 | Admin access | Admin domain: `admin.cyber-vpn.net`. `admin.cyber-vpn.org` is not an S1 admin surface and must not serve an independent admin session. | Admin access must be protected with private/IP allowlist or equivalent controls, mandatory admin 2FA, RBAC and audit evidence. | Approved |
| DEC-S1-003 | Production topology | Simple Controlled Hybrid Container Topology for S1. | Separate staging/prod, containerized backend/worker/bot, persistent PostgreSQL/Valkey, separate Remnawave, reverse proxy/TLS, monitoring, backups and rollback evidence. | Approved |
| DEC-S1-004 | Production PostgreSQL | Managed PostgreSQL 17.x, private-only, separate from staging, with separate DB/users for CyberVPN and Remnawave. | Backup/restore evidence is mandatory before S1 go-live. | Approved |
| DEC-S1-005 | Production Valkey/Redis | Dedicated private Valkey/Redis for queues/cache/rate limits, production separate from staging, no public access. | Monitoring, memory policy and recovery of critical jobs from PostgreSQL are required. Redis/Valkey is not durable source of truth. | Approved |
| DEC-S1-006 | Production Remnawave | Dedicated production Remnawave control-plane, private/internal API, separate from staging. | Provisioning and backup evidence are required before go-live. | Approved |
| DEC-S1-007 | Staging Remnawave | Separate staging Remnawave instance with test nodes/providers, same production contract, disposable data. | Smoke/evidence is mandatory before S1 rollout. | Approved |
| DEC-S1-008 | Payments | Approved S1 provider set: PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, YooKassa for users from Russia. First live paid-path candidate for S1: CryptoBot / Crypto Pay. | `S1-PAY-001` selection is recorded in `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md` and `infra/payments/stage1-primary-payment-provider.json`; `S1-PAY-002` local CryptoBot sandbox runtime contract is recorded in `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md` and `infra/payments/stage1-cryptobot-sandbox-contract.json`; `S1-PAY-003` local production credential inventory is recorded in `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md` and `infra/payments/stage1-cryptobot-production-credentials-contract.json`. Each provider remains disabled until real account, credentials, webhook/status/refund/reconciliation evidence exists. Documentation-derived placeholder mappings are in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`; replacement debt is tracked in `19_STAGE1_TECH_DEBT_REGISTER.md`. At least one live payment path is required for paid beta. | Approved with evidence gates |
| DEC-S1-009 | Telegram Stars | Telegram Stars enabled only for Telegram Bot/Mini App paid flow and only after evidence. | Requires Telegram bot setup, Stars/XTR pricing, successful payment flow, idempotency and refund/reconciliation behavior evidence. | Approved with evidence gates |
| DEC-S1-010 | Payment account ownership | Payment accounts belong to legal seller/project owner, with finance/ops backup `@Sasha_Beep`, limited technical access, audited refunds/reconciliation, secrets stored through approved process. | Access matrix and secret storage evidence required before go-live. Single-person backup risk must be accepted for S1 or split before go-live. | Approved with evidence gates |
| DEC-S1-011 | Legal seller | Legal seller is individual founder/owner. | S1 legal/text/public-copy approval is closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; sensitive identity/payment/tax details must stay outside repo. Mailbox/provider/deployed evidence remains outside the legal-text decision. | Approved with legal/text closure |
| DEC-S1-012 | Grace period | Paid subscription grace period: 72 hours. | Expiry/grace jobs, user-facing states, support templates and Remnawave disable behavior must match 72 hours. | Approved |
| DEC-S1-013 | First-week success metric | 95%+ successful `trial/pay -> VPN ready`, median provisioning <=60s, p95 <=5min, zero unresolved paid-but-no-access/orphan payments older than 24h. | Dashboards, daily beta review and go/no-go criteria must track these metrics. | Approved |
| DEC-S1-014 | On-call/support owner | Primary launch-week on-call/support owner: `@Sasha_Beep`; backup: `@Sasha_Beep`. Alerts go to private Telegram alert channel `-5173727789` + backup email `backup@cyber-vpn.net`. Primary owner can pause registration/payments/trial/provisioning and initiate rollback. P0 ack <=15min, P1 <=1h, beta support first response <=12h. | Alert delivery, backup email delivery and support escalation test are required before go-live. Single-person coverage risk must be accepted for S1 or split before go-live. | Approved with evidence gates |
| DEC-S1-015 | Backup retention/RPO/RTO | Daily encrypted PostgreSQL backups retained 14 days, pre-deploy backup before production migrations/releases, off-host storage, RPO <=24h, RTO <=4h. Remnawave backup/export/rebuild strategy required. Redis/Valkey is not durable source of truth. | Restore drill evidence required before go-live. | Approved |
| DEC-S1-016 | First admin bootstrap | First production admin is created only via one-time protected bootstrap by `@Sasha_Beep` after clean migrations; role `owner/super_admin`; mandatory 2FA before admin access; audit event required; bootstrap disabled after use; no default credentials, no committed password, no permanent public bootstrap endpoint. | Redacted bootstrap evidence required before go-live. | Approved with evidence gates |
| DEC-S1-017 | Launch candidate branch/tag | Use `release/stage1-controlled-public-beta`; staging/beta tags `stage1-beta-rc.N`; production tags `stage1-beta-live.N`; optional `stage1-docs-freeze.1`. Deploy only by immutable tag/commit SHA, never floating `main`. | No tag until dirty worktree inventory and launch-critical/excluded scope map are approved. Every runtime change must reference an `S1-*` backlog ID. | Approved |
| DEC-S1-018 | Referral/promo/gift status | Disabled by default. `REFERRAL_ENABLED=false`; public referral, promo and gift flows hidden/gated; no rewards, no payouts, no gift purchase, no checkout discounts from codes. Manual audited support grants are allowed. | Enable later only with kill switch, limits, anti-abuse, idempotency, payment/refund tests, support workflow and legal copy evidence. | Approved |
| DEC-S1-019 | Auth/OAuth scope | Enable email/login + password, Telegram identity/linking, Magic link/OTP, OAuth only Google and GitHub. | Google/GitHub still require credentials, callback URLs, state protection, account-linking tests, 2FA path and support conflict flow before public enablement. All other OAuth providers remain disabled. | Approved with evidence gates |
| DEC-S1-020 | Autoprolongation | Do not promise autoprolongation in S1. Use manual renewal plus expiry reminders/renewal invoice links if tested. No automatic charge, no saved recurring payment method, no "renews automatically" copy. | True autoprolongation only later with provider recurring support, user consent, cancel flow, failed-renewal handling, webhook idempotency, refund policy and staging/prod evidence. | Approved |

## Decision freeze rule

After this decision log is accepted:

- any implementation task must reference an `S1-*` backlog ID;
- any change to domains, payment providers, auth scope, Remnawave topology, legal seller, release branch/tag policy or go-live gates requires a new decision-log entry;
- providers and OAuth flows named here are approved for S1 scope, but not automatically enabled in production without their evidence gates;
- operational details, provider placeholder mappings, evidence checklist and scope-map rules are defined in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`;
- accepted placeholders and deferred items must be tracked in `19_STAGE1_TECH_DEBT_REGISTER.md`;
- Stage 1 go-live remains blocked until `07_STAGE1_ACCEPTANCE_GATES.md` and `08_STAGE1_GO_LIVE_RUNBOOK.md` evidence requirements are satisfied.
