> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Статус: owner decision packet перед реализацией Stage 1.

# Stage 1 Owner Decision Packet

## Purpose

Этот файл фиксирует owner answers по решениям из `11_STAGE1_REVIEW_CHECKLIST.md`. Ответы записаны 2026-05-03 и являются входом S0 decision freeze для **Controlled Public Beta CyberVPN / B2C contour**.

## Business decisions

| ID | Decision | Owner answer | Remaining implementation/evidence rule | Blocks |
|---|---|---|---|---|
| DEC-S1-001 | Main public domain | Primary domain `cyber-vpn.net`; mirror `cyber-vpn.org` | DNS/TLS/CORS/cookie/OAuth/webhook evidence required | DNS, TLS, CORS, cookies, OAuth, webhooks, legal pages |
| DEC-S1-002 | Admin domain/protection model | `admin.cyber-vpn.net`; mirror `admin.cyber-vpn.org` | Protected admin access, admin 2FA and RBAC evidence required | Admin security, CORS/cookies, support/admin operations |
| DEC-S1-003 | Production hosting topology | Simple Controlled Hybrid Container Topology for S1 | Topology diagram, ingress list, secrets inventory and rollback path required | Deploy, secrets, rollback, backups |
| DEC-S1-004 | Production PostgreSQL location | Managed PostgreSQL 17.x, private-only, separate from staging, separate DB/users for CyberVPN and Remnawave | Backup/restore evidence before go-live | DB migrations, backups, RPO/RTO |
| DEC-S1-005 | Production Redis/Valkey location | Dedicated private Valkey/Redis for queues/cache/rate limits, production separate from staging, no public access | Monitoring, memory policy and critical job recovery from PostgreSQL required | Workers, rate limits, queues, sessions/cache |
| DEC-S1-006 | Production Remnawave location | Dedicated production Remnawave control-plane, private/internal API, separate from staging | Provisioning and backup evidence before go-live | Paid/trial provisioning |
| DEC-S1-007 | Staging Remnawave location | Separate staging Remnawave with test nodes/providers, same production contract, disposable data | Smoke/evidence before S1 rollout | E2E testing and provisioning evidence |
| DEC-S1-008 | Primary payment provider | PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, YooKassa for users from Russia. First live paid-path candidate for S1: CryptoBot / Crypto Pay | `S1-PAY-001` selection is recorded in `125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md` and `infra/payments/stage1-primary-payment-provider.json`; `S1-PAY-002` local CryptoBot sandbox runtime contract is recorded in `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md` and `infra/payments/stage1-cryptobot-sandbox-contract.json`; `S1-PAY-003` local production credential inventory is recorded in `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md` and `infra/payments/stage1-cryptobot-production-credentials-contract.json`. Each provider must pass real account, credentials, webhook/status/refund/reconciliation evidence before enablement; documentation-derived placeholder mappings are in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`; replacement debt is in `19_STAGE1_TECH_DEBT_REGISTER.md`; at least one live path is required for paid beta | Paid beta, webhooks, refunds, reconciliation |
| DEC-S1-009 | Telegram Stars launch status | Enable only for Telegram Bot/Mini App paid flow and only after evidence | Bot token, Stars setup, XTR pricing, successful payment and refund/reconciliation behavior must be proven | Telegram paid flow |
| DEC-S1-010 | Payment provider accounts owner | Payment accounts belong to legal seller/project owner, finance/ops backup `@Sasha_Beep`, limited technical access, audited refunds/reconciliation, approved secrets storage | Access matrix and secret storage evidence required before go-live; single-person coverage risk must be accepted for S1 or split | Credentials, legal seller, refunds |
| DEC-S1-011 | Legal seller / company/person | Individual founder/owner | S1 legal/text/public-copy approval is closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; sensitive identity/payment/tax details stay outside repo | Terms, Privacy, Refund, provider account ownership |
| DEC-S1-012 | Grace period duration | 72 hours | Expiry/grace worker and user-facing state must match this value | Expiry jobs, support templates, UI states |
| DEC-S1-013 | First-week success metric | 95%+ successful `trial/pay -> VPN ready`, median provisioning <=60s, p95 <=5min, zero unresolved paid-but-no-access/orphan payments older than 24h | Metrics/dashboard and daily review evidence required | Monitoring, go/no-go, support load |
| DEC-S1-014 | On-call/support owner | Primary launch-week on-call/support owner `@Sasha_Beep`; backup `@Sasha_Beep`; alerts to private Telegram channel `-5173727789` + backup email `backup@cyber-vpn.net`; primary owner can pause registration/payments/trial/provisioning and initiate rollback; P0 ack <=15min, P1 <=1h, beta first response <=12h | Alert delivery, backup email and support escalation test required before go-live; single-person coverage risk must be accepted for S1 or split | Incidents, support SLA, alerts |
| DEC-S1-015 | Backup retention/RPO/RTO | Daily encrypted PostgreSQL backups retained 14 days, pre-deploy backup, off-host storage, RPO <=24h, RTO <=4h; Remnawave backup/export/rebuild required; Redis/Valkey is not durable source of truth | Restore drill evidence required before go-live | DR readiness, go-live gate |
| DEC-S1-016 | First admin bootstrap owner | Bootstrap owner `@Sasha_Beep`; first production admin via one-time protected bootstrap after clean migrations; role `owner/super_admin`; mandatory 2FA; audit event; bootstrap disabled after use; no default credentials, committed password or permanent public endpoint | Redacted bootstrap evidence required before go-live | Admin access, RBAC, audit log |
| DEC-S1-017 | Launch candidate branch/tag | Branch `release/stage1-controlled-public-beta`; tags `stage1-beta-rc.N`, `stage1-beta-live.N`; optional `stage1-docs-freeze.1`; deploy by immutable tag/commit SHA only | Dirty worktree inventory and launch-critical/excluded scope map required before first tag; every runtime change must reference `S1-*` backlog ID | Release freeze, rollback, evidence |
| DEC-S1-018 | Whether referral/promo/gift are enabled in Stage 1 | Disabled by default: `REFERRAL_ENABLED=false`; public referral/promo/gift hidden/gated; no rewards, payouts, gift purchase or checkout discounts; manual audited support grants allowed | Enable later only with kill switch, limits, anti-abuse, idempotency, payment/refund tests, support workflow and legal copy evidence | Fraud risk, UI scope, backend flags |
| DEC-S1-019 | Whether OAuth providers are enabled in Stage 1 | Enable email/login + password, Telegram identity/linking, Magic link/OTP, OAuth only Google and GitHub | Google/GitHub still require credentials, callback URLs, state protection, linking tests and support conflict flow before public enablement | Auth scope, account conflicts, security |
| DEC-S1-020 | Whether autoprolongation is promised in Stage 1 | Do not promise autoprolongation in S1. Use manual renewal plus expiry reminders/renewal invoice links if tested. No automatic charge, saved recurring payment method or "renews automatically" copy | True autoprolongation only later with provider recurring support, user consent, cancel flow, failed-renewal handling, idempotency, refund policy and staging/prod evidence | Pricing copy, subscription jobs, support |

## Items still requiring concrete operational values

The following policies are approved, but concrete production values still must be filled before go-live evidence can pass:

1. Provider credentials and account readiness for each approved payment provider.
2. Provider-specific callback samples replacing documentation-derived placeholder mappings.
3. Alert delivery evidence for Telegram channel `-5173727789` and `backup@cyber-vpn.net`.
4. Support/refund mailbox evidence for `support@cyber-vpn.net` and `refund@cyber-vpn.net`.
5. Staging/production Remnawave URLs and health evidence.
6. Production infrastructure provider/project/account names.
7. Legal/text/public-copy approval is closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; remaining related evidence is mailbox/provider/deployed workflow proof, not legal-copy drafting.
8. Explicit S1 acceptance of single-person coverage risk or assignment of separate backup handles.

These must be recorded in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`, `19_STAGE1_TECH_DEBT_REGISTER.md` and the evidence pack before go-live.

## Recommended owner approval wording

```text
I approve Stage 1 as Controlled Public Beta CyberVPN for B2C contour only.
Implementation must follow 06_STAGE1_IMPLEMENTATION_BACKLOG.md task IDs.
The following decisions are approved:
- DEC-S1-001 ...
- DEC-S1-020 ...
The following blockers remain external dependencies and must be closed before go-live:
- ...
Owner:
Date:
```

## If owner cannot answer all decisions now

The safe fallback is:

1. Approve documents only as draft baseline.
2. Allow implementation planning and code audit only.
3. Do not start payment, provisioning, domain, legal, production deploy or public rollout tasks.
4. Keep public beta blocked until the missing decision gets an owner answer and evidence requirement.
