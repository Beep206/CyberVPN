> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Technical Specification

## Target architecture for Stage 1

Stage 1 architecture should be deliberately smaller than the full target-state platform.

The canonical S1 topology spec is `120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md`; the machine-readable topology contract is `infra/topology/stage1-production-topology.json`. The S1 staging environment contract is `121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md`; its machine-readable contract is `infra/topology/stage1-staging-environment.json`. The S1 production environment deployability contract is `122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md`; its machine-readable contract is `infra/topology/stage1-production-environment.json`. The S1 DNS/TLS contract is `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; its machine-readable contract is `infra/dns/stage1-dns-tls-contract.json`. The S1 protected ingress contract is `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`; its machine-readable contract is `infra/ingress/stage1-protected-ingress-contract.json`. Together they fix the Simple Controlled Hybrid Container Topology: application services run as containers, durable state lives in managed/private services, Remnawave API stays private/internal, staging and production are separate, staging uses disposable data/test credentials, production uses no staging credentials/state, public DNS/TLS follows the approved `.net` primary / `.org` redirect policy, backend/admin ingress is exposed only through approved protected entrypoints, and home-lab hardware is allowed only for non-critical lab/evidence/device-testing work.

```text
Visitor/User
  -> Frontend marketing site / customer cabinet
  -> Telegram Bot / Mini App
  -> Backend API /api/v1
       -> PostgreSQL
       -> Redis/Valkey / Task queue
       -> Payment providers / webhooks
       -> Remnawave API
       -> Worker / scheduler
       -> Admin workspace
       -> Observability / audit / logs
```

## Required runtime components

| Component | Stage 1 status | Notes |
|---|---|---|
| Backend API | Required | Core authority for auth, payments, subscription, provisioning state |
| Frontend customer cabinet | Required | Web-first and mobile-friendly |
| Marketing site | Required | Pricing/features/devices/help/legal/status |
| Telegram Bot | Required | Main early channel together with website |
| Telegram Mini App | Required | Lightweight cabinet: plans/payments/devices/profile/wallet; referral surfaces gated/default-off in S1 |
| Worker/scheduler | Required | Reconciliation, expiry/renewal, provisioning retry, notifications, cleanup |
| PostgreSQL | Required | Production DB with backups and restore drill |
| Redis/Valkey | Required | Queue/cache/rate limit if current architecture requires it |
| Remnawave staging/prod | Required | Authoritative VPN provisioning backend |
| Admin workspace | Required | Restricted, RBAC, 2FA, audit |
| Partner portal | Disabled | Next stages only |
| Native mobile/desktop/TV | Disabled | Next stages only |
| Helix/Verta/Beep | Disabled/default-off | Beta/canary only in later stage |
| NATS | Optional | Not required for S1 if Redis/TaskIQ sufficient |
| Kubernetes/Talos/GitOps | Optional | Do not block S1 unless already production-ready |
| OpenBao | Preferred/target | Secret management must be production-safe even if interim approach is used |

## Environments

Stage 1 requires at minimum:

| Environment | Purpose | Requirements |
|---|---|---|
| Local | Developer iteration | No production credentials, mock/sandbox integrations |
| Staging | Full end-to-end proof | Separate DB, Redis, Remnawave, Telegram bot, payment sandbox/test mode |
| Production | Controlled public beta | Separate domains, DB, Redis, Remnawave, secrets, monitoring, backups |

Strict rules:

- Staging and production credentials must never be shared.
- Payment webhook secrets must be environment-specific.
- Telegram bot tokens must be environment-specific.
- Remnawave staging and production must be separate.
- CORS origins must be allowlisted per environment.
- OAuth callback URLs must be registered per environment.
- Frontend public env must never contain secrets.

## Domain model decisions required before implementation

| ID | Decision | Status from questionnaire | Stage 1 requirement |
|---|---|---|---|
| S1-DOM-001 | Main public domain | Approved | Primary: `cyber-vpn.net`; mirror/redirect: `cyber-vpn.org`; local DNS/TLS contract exists in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; local protected ingress contract exists in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`; live DNS/TLS/CORS/cookies/OAuth/Telegram/payment webhook evidence required |
| S1-DOM-002 | Admin domain | Approved | Primary: `admin.cyber-vpn.net`; mirror redirect: `admin.cyber-vpn.org`; must be protected by private network/IP allowlist or equivalent, with admin 2FA/RBAC/audit; local DNS/TLS contract exists in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; local protected ingress contract exists in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md` |
| S1-DOM-003 | Partner domain | Unknown | Not required for S1, may remain disabled |
| S1-DOM-004 | Status page route | Public `/status` desired | Canonical S1 status endpoint is `https://cyber-vpn.net/status`; separate status subdomain is not required for S1; must not expose internal secrets |

## Auth and account requirements

### Required auth methods for Stage 1

- email/password or login/password;
- magic link/OTP if credentials/email provider and rate limits are ready;
- Telegram Bot/Mini App link;
- OAuth providers for S1 are limited to Google and GitHub, and only when credentials, callback URLs, state protection and linking policy tests are ready. Other OAuth providers remain disabled/default-off.

### 2FA

- Ordinary users: 2FA supported.
- Admins: 2FA required.

### Registration

- Public registration desired.
- Must have kill switch: `REGISTRATION_ENABLED=false` or equivalent. Local S1 implementation/evidence is complete in `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md`; deployed staging/prod toggle proof remains required before go-live.
- Invite codes may be kept available as throttle/fallback.

### Account linking policy

A safe account linking policy is mandatory because Telegram, email/password, magic link and OAuth can create identity conflicts.

Mandatory rules:

- No silent merge between Telegram and email accounts if either side is already linked to another user.
- Telegram auth/linking must match existing users by validated `telegram_id`, not by provider email.
- Merge/link only after proof of control of both sessions or verified email/provider identity.
- All account linking conflicts must be logged as security/audit events.
- Support-assisted merge must be role-gated.

## Payment specification

### Provider strategy

The owner-approved Stage 1 provider set is PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, and YooKassa for users from Russia. Provider approval does not equal production enablement: each provider must pass the readiness matrix before it is visible to users.

Provider-specific placeholder mappings based on current provider documentation are recorded in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`. They are not final production evidence. Real sandbox/production callback samples, credentials, signatures, idempotency tests and reconciliation behavior must replace them before each provider is enabled; the replacement work is tracked in `19_STAGE1_TECH_DEBT_REGISTER.md`.

| Provider | Stage 1 default | Enable condition |
|---|---|---|
| PayRam | Disabled until ready | Account, sandbox/prod provider access setup, PayRam `paymentState` samples, webhook header validation, status mapping, idempotency, refund/dispute and reconciliation evidence |
| NOWPayments | Disabled until ready | Account, sandbox/prod provider access setup, IPN authenticity evidence, `finished`/underpaid/wrong-asset policy, status mapping, idempotency, refund/dispute and reconciliation evidence |
| CryptoBot | Disabled until ready | Account/app token, testnet/prod invoice samples, `crypto-pay-api-signature` verification, invoice status mapping, idempotency, refund/dispute and reconciliation evidence |
| Telegram Stars | Telegram-only, disabled until ready | Telegram Bot/Mini App paid flow evidence, Stars/XTR pricing, `successful_payment`, stored `telegram_payment_charge_id`, refund/reconciliation behavior |
| Digiseller | Russia segment only, disabled until ready | Account, credentials, callback signature/status mapping, duplicate callback idempotency, refund/dispute and reconciliation evidence |
| YooKassa | Russia segment only, disabled until ready | Account/shop, credentials, webhook events, `succeeded`/`canceled` status mapping, fiscalization/receipt decision, refund/dispute and reconciliation evidence |
| Manual payments | Disabled unless explicitly documented | Support and reconciliation flow approved |

### Payment invariants

- Payment provider webhook must verify signature/secret.
- Webhook handling must be idempotent.
- Payment final statuses must be provider-specific and documented in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`, then proven by real evidence before enablement.
- Duplicate webhook must not duplicate wallet transaction/subscription/provisioning.
- Paid payment state must never be lost because Remnawave/provisioning failed.
- Orphan payment policy is required before production: no unresolved `paid-but-no-access` or orphan payment may be older than 24 hours.
- Refund and dispute behavior must be documented before enabled.
- Reconciliation job must be available for payment mismatch cases.

### Minimum payment states

Recommended canonical states:

- `created`;
- `pending`;
- `requires_action`;
- `paid`;
- `failed`;
- `cancelled`;
- `refunded`;
- `partially_refunded`;
- `disputed`;
- `expired`;
- `orphaned`;
- `reconciliation_required`.

Provider-specific mapping baseline:

| Provider | Automatic paid access allowed only on | Manual review / no automatic access |
|---|---|---|
| PayRam | `FILLED`; `OVER_FILLED` only if amount >= expected and policy accepts overpayment | `OPEN`, `PARTIALLY_FILLED`, `CANCELLED`/`CANCELED`, unknown |
| NOWPayments | `finished` | `waiting`, `confirming`, `confirmed`, `sending`, `partially_paid`, `wrong_asset_confirmed`, `failed`, `expired`, `refunded`, unknown |
| CryptoBot | invoice `paid` | `active`, `expired`, unknown |
| Telegram Stars | `successful_payment` update only | invoice sent, `pre_checkout_query`, timeout/no receipt, refund |
| Digiseller | `paid` | `wait`, `canceled`, `refunded`, `error`, unknown |
| YooKassa | `succeeded` / `payment.succeeded` | `pending`, `waiting_for_capture`, `canceled` / `payment.canceled`, unknown |

Provider-specific mapping details live in `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`.

## Subscription and wallet requirements

- Subscription state is backend-authoritative.
- Wallet/payment history must show user-facing transactions.
- Wallet payout/withdrawal functionality must be disabled for ordinary B2C users in Stage 1.
- Partner earnings/withdrawals are out of scope.
- Grace period is required and set by owner decision to 72 hours.
- Autoprolongation cannot be promised unless the payment provider supports it and evidence exists.

## Remnawave provisioning specification

### Authority

Remnawave is the authoritative backend for VPN access in Stage 1. Helix does not replace it.

### Required environments

- Remnawave staging.
- Remnawave production.

### Provisioning flow

1. Backend receives trial activation or final paid payment.
2. Backend creates/updates subscription state.
3. Backend/worker creates or updates user/access in Remnawave.
4. Backend stores sanitized provisioning state.
5. User receives QR-code, subscription URL and config file.
6. Usage/traffic may be shown if Remnawave integration supports accurate data.

For trial activation, the local S1 contract is defined in `40_STAGE1_VPN_004_TRIAL_PROVISIONING_EVIDENCE.md`: trial provisioning uses a mockable Remnawave gateway, default profile `vless-reality-raw`, 3-day duration, 1 device, 2 GiB traffic limit and `NO_RESET` traffic reset strategy. Public runtime provisioning is gated by `STAGE1_TRIAL_PROVISIONING_ENABLED` and must be enabled only after staging/prod Remnawave profile evidence exists.

For paid access, the local S1 contract is defined in `41_STAGE1_VPN_005_PAID_PROVISIONING_EVIDENCE.md`: paid provisioning is allowed only for `order_status=committed` and `settlement_status=paid`, creates new Remnawave-backed access when no upstream user exists, and extends from the current future access expiry when the user already has active access. Local payment -> provisioning failure handling is defined in `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`: paid state is preserved, retry is queued and duplicate webhooks do not duplicate provisioning. Public runtime provisioning is gated by `STAGE1_PAID_PROVISIONING_ENABLED=false` by default and must be enabled only after provider-paid evidence, durable webhook/retry persistence and staging/prod Remnawave evidence exist.

For Remnawave outage handling, the local S1 contract is defined in `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md`: a failed trial/paid provisioning attempt creates a `stage1_provisioning_retry` job, paid attempts preserve `payment_state=paid`, retries use capped exponential backoff, later success marks access `ready`, and exhausted retries move to dead-letter/reconciliation. Production S1 must back this contract with durable PostgreSQL/worker processing; Redis/Valkey must not be the source of truth for critical provisioning jobs.

### Startup region inventory

The local S1 startup region catalogue is defined in `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`.

The current public network API groups live Remnawave nodes by `country_code`, so S1 uses 12 country-level regions with preferred launch cities:

| S1 region ID | Country code | Preferred city/provider region | Launch posture |
|---|---|---|---|
| `s1-de-fra` | `DE` | Frankfurt / Falkenstein / Nuremberg | Primary |
| `s1-nl-ams` | `NL` | Amsterdam | Primary |
| `s1-fi-hel` | `FI` | Helsinki | Primary |
| `s1-pl-waw` | `PL` | Warsaw | Primary |
| `s1-gb-lon` | `GB` | London | Secondary |
| `s1-fr-par` | `FR` | Paris | Secondary |
| `s1-us-nyc` | `US` | New York / Ashburn | Secondary |
| `s1-ca-tor` | `CA` | Toronto | Secondary |
| `s1-sg-sin` | `SG` | Singapore | Primary |
| `s1-jp-tyo` | `JP` | Tokyo | Secondary |
| `s1-tr-ist` | `TR` | Istanbul | Canary |
| `s1-kz-ala` | `KZ` | Almaty | Canary |

Inactive planned regions must not be advertised as live. Any public region must have real staging/prod Remnawave node evidence, monitoring evidence and support-visible status before it appears in customer UI or marketing copy.

### Node traffic policy

The local S1 Torrent/P2P/TOR node policy is defined in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`.

S1 rules:

- Torrent/P2P is restricted by default on live S1 nodes.
- CyberVPN must not advertise Torrent/P2P availability unless a specific node is provider-approved and explicitly evidenced.
- Remnawave Torrent Blocker may be used only after node prerequisites are proven: plugin-capable Remnawave Panel/Node, required Xray-core version, `cap_add: NET_ADMIN`, `nftables`, supported Linux kernel, inbound sniffing and admin/report evidence.
- Torrent Blocker is an abuse-control mechanism, not a perfect guarantee; reports must feed support/admin review before permanent enforcement unless immediate harm requires emergency action.
- No dedicated Remnawave-native TOR blocker plugin/addon is currently documented in the official Remnawave node-plugin docs checked for S1.
- TOR control is disabled by default for S1. If a provider requires TOR restrictions, use separately evidenced `egressFilter`, `sharedLists` and/or custom Xray routing. Do not overload Torrent Blocker `includeRuleTags` for TOR without explicit upstream support and staging proof.
- Backup/fallback nodes must inherit the same or stricter node traffic policy before traffic is shifted.

### Failure behavior

| Failure | Required behavior |
|---|---|
| Remnawave API down | Keep payment/subscription state, queue provisioning retry, alert ops |
| Provisioning partial success | Mark as `provisioning_reconciliation_required`, do not issue duplicate credentials blindly |
| Subscription renewed but Remnawave not updated | Retry/reconciliation/support escalation |
| Subscription expired | Apply grace period, then worker disables access |
| Credential regeneration | Admin/support role-gated, audit-logged, config links sanitized |

### Protocols

Stage 1 enabled customer-visible Remnawave/Xray profiles are:

| Profile ID | Protocol | Transport/network | Security | Default | Rule |
|---|---|---|---|---:|---|
| `vless-reality-raw` | `vless` | `raw` / `tcp` compatibility alias | `reality` | yes | Default S1 subscription URL, QR and config delivery profile |
| `vless-reality-xhttp` | `vless` | `xhttp` | `reality` | no | Mandatory alternate S1 profile for supported clients/networks |

S1 provisioning must reject unknown or disabled protocol/transport/security combinations. `wireguard`, `openvpn`, `vmess`, `trojan`, `shadowsocks`, `hysteria2`, `tuic`, `helix`, `verta` and `beep` are disabled/default-off for Stage 1. Additional VLESS transports such as `ws`, `grpc`, `kcp` and `httpupgrade` are not S1 customer profiles unless a later decision adds tests, support guides, legal/support copy and kill switches.

Source of local contract/evidence: `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md`.

## Admin requirements

Admin workspace must support Stage 1 operations without exposing dangerous functions broadly.

Required:

- Separate admin domain or private/protected access.
- 2FA required.
- RBAC enabled.
- Audit log for privileged actions.
- IP allowlist or equivalent edge protection strongly recommended.
- First admin bootstrap procedure.
- Support/finance/ops role separation.

Dangerous functions must be role-gated and audit-logged:

- Manual subscription grant/extension.
- User disable/delete.
- Credential regeneration.
- Refunds.
- Payment reconciliation override.
- System config/launch controls.
- Promo/gift/referral mass actions.
- Partner payouts, if code exists, must remain disabled.

## Backend/API requirements

- Public endpoints must be allowlisted.
- Admin/internal endpoints must be protected.
- Swagger/OpenAPI must be disabled publicly in production.
- CORS origins must match selected production/staging domains.
- Cookie domain and secure settings must be verified.
- CSRF must be evaluated for cookie-based flows.
- Auth/payment/trial/referral/support rate limits must be implemented or accepted as known risk.
- DB migrations must pass on a clean database.
- First admin user creation must be documented and tested.
- Worker retry/dead-letter behavior must be documented.

## Worker/scheduler requirements

Mandatory Stage 1 jobs:

- Payment reconciliation.
- Provisioning retries.
- Subscription expiry.
- Grace period handling.
- Renewal processing where supported.
- User notifications for expiry/payment/provisioning where enabled.
- Cleanup/reporting minimum.

Jobs that should remain disabled unless explicitly approved:

- Partner reporting.
- Partner payouts.
- Advanced growth campaigns.
- Broad notification campaigns.
- Helix audits if Helix is out of scope.
- Advanced analytics pipelines not needed for beta.

## Observability requirements

Stage 1 observability should cover the whole B2C control path, not only the minimum health checks.

Launch-critical telemetry:

- API health, request volume, latency p50/p95/p99 and 5xx rate.
- Auth failures, registration failures, OTP/magic link failures, OAuth linking conflicts and admin 2FA failures.
- Payment webhook failures, invalid signatures, duplicate webhook count, provider status mismatches, orphan payments and paid-but-no-access lag.
- Provisioning success rate, trial/pay -> VPN ready latency, Remnawave API errors, retry queue age and failed credential generation.
- Worker queue depth, oldest job age, retry count, dead-letter/reconciliation items.
- Remnawave health, connected node count, node offline alerts and config/subscription delivery errors.
- PostgreSQL health, connection count, storage, backup status and slow queries where available.
- Valkey/Redis health, memory, evictions, connection count and queue keys.
- Frontend/admin JS errors, checkout/auth UI errors and route errors.
- Telegram bot webhook errors, Mini App auth failures, pre-checkout failures and successful payment event count.
- Support/legal events: refund requests, abuse/privacy requests and support ticket volume.
- Security/privacy telemetry: PII redaction tests, suspicious auth/payment rates and privileged admin audit actions.

Alert destinations:

- primary Telegram alert channel: `-5173727789`;
- backup email: `backup@cyber-vpn.net`;
- optional operational aliases: `alerts@cyber-vpn.net`, `ops@cyber-vpn.net`, `security@cyber-vpn.net`.

Sentry projects should be separate where practical:

- `backend-api`;
- `web-frontend`;
- `web-admin`;
- `telegram-bot`;
- `task-worker`;
- partner/native only when enabled.

The S1 local Sentry config contract is recorded in `94_STAGE1_OBS_001_SENTRY_PROJECTS_CONFIG_EVIDENCE.md`; live Sentry projects, DSNs, source-map proof and safe test events are still required before go-live.

PII scrubbing must be verified live.

## Security requirements

- No production secrets in repo.
- Secrets scan before launch.
- Frontend bundle/env scan before launch.
- OAuth tokens, TOTP secrets, provider secrets and raw config links must not appear in logs.
- Config/subscription URLs must be redacted from support/admin logs except where explicitly needed and protected.
- Production backups encrypted.
- JWT/TOTP/OAuth/Remnawave/payment secret rotation process documented.
- Admin access restricted.
- Abuse policy documented.
- Torrent/P2P/TOR node traffic policy is documented in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`; real Remnawave plugin/provider/webhook/alert evidence is still required before enablement on staging/production nodes.

## Backup and DR requirements

- Managed PostgreSQL 17.x backup configured with daily encrypted backups retained 14 days.
- Pre-deploy PostgreSQL backup configured before production migrations/releases.
- PostgreSQL backups stored off-host; RPO <=24h, RTO <=4h.
- Remnawave backup/export/rebuild strategy configured.
- Restore drill completed before Stage 1 go-live.
- Backup storage location selected.
- Redis/Valkey is not durable source of truth for S1; critical jobs must recover from PostgreSQL/payment provider/Remnawave state.
- JWT secret compromise runbook available.

## Infrastructure recommendation for Stage 1

Use the owner-approved Simple Controlled Hybrid Container Topology for S1:

- One controlled production backend deployment.
- Managed PostgreSQL 17.x, private-only, separate from staging, with separate DB/users for CyberVPN and Remnawave.
- Dedicated private Valkey/Redis for queues/cache/rate limits, separate from staging, no public access.
- Dedicated production Remnawave control-plane with private/internal API, separate from staging.
- Separate staging stack.
- Reverse proxy/TLS with controlled ingress as defined by `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`.
- Backend protected from unnecessary direct public exposure.
- Public domains: `cyber-vpn.net` as canonical primary; `cyber-vpn.org` as mirror/redirect to the primary.
- Admin domains: `admin.cyber-vpn.net` as canonical primary; `admin.cyber-vpn.org` redirects to the primary admin domain and must not create an independent admin session surface.
- Admin protected by subdomain + 2FA/RBAC/audit/IP allowlist or equivalent.
- Cloudflare/edge WAF/rate limiting if available, but do not make complex platform migration the bottleneck.

Kubernetes/Talos/GitOps/OpenBao can be target-state, but Stage 1 success is measured by working B2C flow, security and rollback—not by platform complexity.

## Home lab option

A home dedicated computer may be used as a non-critical lab/staging-like/evidence/device-testing machine. It must not host production critical services if home power outages can last up to 5 hours.

Production critical components such as public site/cabinet, backend API, Telegram/payment webhooks, production PostgreSQL, production Valkey/Redis, production Remnawave control-plane, admin production, DNS/TLS edge, VPN exit nodes and primary monitoring/alerts must remain outside the home server unless a later decision explicitly accepts the risk.

Detailed rules are recorded in `20_HOME_LAB_NON_CRITICAL_OPTION.md`.
