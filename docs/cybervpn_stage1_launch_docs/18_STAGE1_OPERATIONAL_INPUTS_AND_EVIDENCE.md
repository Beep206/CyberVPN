> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации inputs: 2026-05-03
> Статус: operational inputs and evidence checklist for S1 Controlled Public Beta.

# Stage 1 Operational Inputs and Evidence Checklist

## Purpose

Этот документ фиксирует конкретные операционные данные, правила evidence и provider-specific payment status mapping для Stage 1. Он дополняет `17_STAGE1_APPROVED_DECISION_LOG.md` и должен использоваться вместе с `06_STAGE1_IMPLEMENTATION_BACKLOG.md`, `07_STAGE1_ACCEPTANCE_GATES.md` и `08_STAGE1_GO_LIVE_RUNBOOK.md`.

Правило: если значение здесь является placeholder, оно должно иметь запись в `19_STAGE1_TECH_DEBT_REGISTER.md` и не может считаться production evidence.

## 1. Responsible roles

Для Stage 1 не требуются ФИО или личные документы в репозитории. Достаточно operational handle/role.

| Responsibility | Assigned value | S1 status | Evidence required |
|---|---|---|---|
| Primary on-call/support owner | `@Sasha_Beep` | Assigned | Test P0/P1 alert acknowledgement |
| Backup on-call/support owner | `@Sasha_Beep` | Assigned | Backup acknowledgement path tested |
| First admin bootstrap owner | `@Sasha_Beep` | Assigned | Redacted bootstrap transcript + audit event |
| Finance/ops backup | `@Sasha_Beep` | Assigned | Refund/reconciliation access matrix |

Risk note: primary and backup currently point to the same handle. This is acceptable for solo-founder S1 beta only if the go-live record explicitly accepts the single-person coverage risk. It should be split before S2 Public Release 1.0.

## 2. Alert and support contacts

| Channel | Value | Purpose | Evidence required |
|---|---|---|---|
| Private Telegram alert channel | `-5173727789` | P0/P1 operational alerts | Test alert delivered and acknowledged |
| Backup alert email | `backup@cyber-vpn.net` | Backup alert delivery | Test email delivered |
| Support email | `support@cyber-vpn.net` | User support intake | Test inbound ticket/email received |
| Refund/support contact | `refund@cyber-vpn.net` | Refund and payment issue intake | Test refund request route |

Allowed additional observability emails under `cyber-vpn.net`:

- `alerts@cyber-vpn.net`
- `ops@cyber-vpn.net`
- `security@cyber-vpn.net`
- `abuse@cyber-vpn.net`
- `privacy@cyber-vpn.net`
- `noreply@cyber-vpn.net`

## 3. DNS and TLS route behavior

| Route | S1 behavior | Evidence required |
|---|---|---|
| `https://cyber-vpn.net` | Primary public site/cabinet domain | DNS A/AAAA/CNAME, TLS, HTTPS response, security headers |
| `https://cyber-vpn.org` | Mirror/redirect to `https://cyber-vpn.net` | DNS/TLS, redirect evidence, no duplicate cookie ambiguity |
| `https://admin.cyber-vpn.net` | Primary admin domain | DNS/TLS, protected access, admin 2FA/RBAC/audit |
| `https://admin.cyber-vpn.org` | Redirect to `https://admin.cyber-vpn.net` | DNS/TLS, redirect evidence, no independent admin session surface |

S1 recommendation: canonical cookies and OAuth callbacks should prefer `.cyber-vpn.net`. The `.org` mirror should not create a second independent auth surface unless a later decision explicitly approves it.

## 4. Payment provider readiness placeholders

Owner approved provider set:

- PayRam
- NOWPayments
- CryptoBot
- Telegram Stars for Telegram Bot/Mini App only
- Digiseller for users from Russia
- YooKassa for users from Russia

These providers are approved for S1 scope, but all remain disabled until evidence exists. The mappings below are documentation-derived placeholders and must be validated against real sandbox/production callbacks before enablement.

### Source references used for placeholder mappings

| Provider | Official/current source used |
|---|---|
| PayRam | https://docs.payram.com/api-integration/payments-api/payment-status and https://docs.payram.com/support/faq/api-integration-faqs |
| NOWPayments | https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses |
| CryptoBot / Crypto Pay | https://help.send.tg/en/articles/10279948-crypto-pay-api |
| Telegram Stars | https://core.telegram.org/bots/payments-stars and https://core.telegram.org/bots/api#refundstarpayment |
| Digiseller | https://my.digiseller.com/inside/api_payment.asp |
| YooKassa | https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process and https://yookassa.ru/developers/using-api/webhooks |

## 5. Canonical CyberVPN payment states

| Canonical state | Meaning | Provisioning behavior |
|---|---|---|
| `created` | CyberVPN payment/order was created | No VPN access |
| `pending` | Provider has not confirmed final payment | No paid VPN access |
| `requires_action` | User/provider action required | No paid VPN access |
| `paid` | Provider final success is verified | Provision or extend VPN access |
| `paid_reconciliation_required` | Amount/provider metadata needs review, but minimum success criteria may be met | Provision only if provider amount >= expected and policy allows; always alert finance/support |
| `failed` | Provider final failure | No paid VPN access |
| `cancelled` | User/provider cancelled or payment expired as cancellation | No paid VPN access |
| `expired` | Payment window expired | No paid VPN access |
| `refunded` | Payment fully refunded | Revoke/adjust access according to refund policy |
| `partially_refunded` | Payment partially refunded | Manual review |
| `disputed` | Dispute/chargeback opened | Manual review, possible access hold |
| `orphaned` | Payment cannot be attached to a verified user/order | Manual review queue |
| `reconciliation_required` | Provider/CyberVPN mismatch | Manual review queue |

Only `paid` may automatically provision paid access. `paid_reconciliation_required` may provision only when the provider status proves the expected amount or more was received and the risk is accepted by provider-specific policy.

## 6. Provider-specific status mapping

Implementation note, 2026-05-04: local provider status mapping from official documentation is implemented and tested in `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`. Local webhook idempotency contract and duplicate-webhook ASGI proof are implemented and tested in `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`. These mappings still remain disabled for production until each provider has real sandbox/prod callback samples, signature verification evidence, durable Redis/DB idempotency persistence, amount/currency checks and refund/reconciliation evidence.

### PayRam placeholder mapping

Implementation update, 2026-05-07: local PayRam readiness guardrails are tested in `109_STAGE1_PAY_013_PAYRAM_READINESS_EVIDENCE.md`. PayRam remains disabled until real account, credentials, callback/status-poll, refund/reconciliation and payment->provisioning evidence exists.

| PayRam status | CyberVPN state | Final? | S1 behavior |
|---|---|---:|---|
| `OPEN` | `pending` | No | Poll/reconcile; no paid access |
| `FILLED` | `paid` | Yes | Verify reference, amount and `API-Key`; provision |
| `OVER_FILLED` | `paid_reconciliation_required` | Yes | Manual review by default; auto-access only if explicit policy and valid amount evidence accept overpayment |
| `PARTIALLY_FILLED` | `reconciliation_required` | No for access | Do not provision by default; support/finance review |
| `CANCELLED` / `CANCELED` | `expired` or `cancelled` | Yes | No access; user may retry |
| unknown | `reconciliation_required` | No | No access; alert ops |

Implementation notes:

- Store PayRam `reference_id` and provider invoice/payment identifiers.
- Validate webhook `API-Key` before processing.
- Use idempotency key: provider + reference/payment id + normalized status.
- Tech debt: replace this placeholder with real account callback samples.

### NOWPayments placeholder mapping

Implementation update, 2026-05-07: local NOWPayments readiness guardrails are tested in `110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md`. NOWPayments remains disabled until real account, credentials, signed IPN/status-poll, refund/reconciliation and payment->provisioning evidence exists.

| NOWPayments status | CyberVPN state | Final? | S1 behavior |
|---|---|---:|---|
| `waiting` | `pending` | No | Await deposit; no access |
| `confirming` | `pending` | No | Await blockchain confirmations; no access |
| `confirmed` | `pending` | No | Await `finished`; no access |
| `sending` | `processing` | No | Await settlement; no access |
| `finished` | `paid` | Yes | Provision after signature/IPN verification and amount check |
| `partially_paid` | `reconciliation_required` | Provider says funds received but underpaid | No automatic access by default; support/finance review |
| `wrong_asset_confirmed` | `reconciliation_required` | No for access | No automatic access; manual resolution |
| `failed` | `failed` | Yes | No access; support if funds were debited |
| `expired` | `expired` | Yes | No access; user may retry |
| `cancelled` / `canceled` | `cancelled` | Yes | No access; refund only if separately performed |
| `refunded` | `refunded` | Yes | Revoke/adjust access according to refund policy |
| unknown | `reconciliation_required` | No | No access; alert ops |

Implementation notes:

- For VPN subscription sales, do not configure underpaid payments to auto-become `finished` unless owner explicitly accepts that business risk.
- Verify IPN signature/header according to the provider integration before state changes.
- Tech debt: confirm exact callback payload and signature behavior with the live NOWPayments account.

### CryptoBot / Crypto Pay placeholder mapping

| Crypto Pay invoice status | CyberVPN state | Final? | S1 behavior |
|---|---|---:|---|
| `active` | `pending` | No | No paid access |
| `paid` | `paid` | Yes | Verify webhook/API signature and invoice payload; provision |
| `expired` | `expired` | Yes | No access; user may retry |
| unknown | `reconciliation_required` | No | No access; alert ops |

Implementation notes:

- Use `@CryptoTestnetBot` and testnet API before production.
- Verify `crypto-pay-api-signature` for webhooks.
- Crypto Pay webhooks emit `invoice_paid`; reconciliation should still be able to call `getInvoices`.
- Store `invoice_id`, `hash`, `payload`, `paid_at`, `paid_asset`, `paid_amount` where available.
- Tech debt: define refund/dispute behavior for CryptoBot before production enablement.

### Telegram Stars placeholder mapping

| Telegram event/object | CyberVPN state | Final? | S1 behavior |
|---|---|---:|---|
| invoice sent with `currency="XTR"` | `created` | No | No access |
| `pre_checkout_query` received | `requires_action` | No | Validate payload and answer within 10 seconds; no access |
| `successful_payment` message received | `paid` | Yes | Store `telegram_payment_charge_id`; provision |
| no `successful_payment` after pre-checkout/order timeout | `cancelled` or `expired` | Yes after timeout | No access |
| successful `refundStarPayment` | `refunded` | Yes | Revoke/adjust access according to refund policy |

Implementation notes:

- Inside Telegram Bot/Mini App digital-goods flows, use Telegram Stars only.
- Do not deliver VPN access from `pre_checkout_query`; deliver only after `successful_payment`.
- Bot/Mini App must support payment support flow such as `/paysupport` or equivalent.
- Tech debt: replace Stars pricing placeholders with tested `XTR` tariff mapping.

### Digiseller placeholder mapping

| Digiseller status | CyberVPN state | Final? | S1 behavior |
|---|---|---:|---|
| `wait` | `pending` | No | No access |
| `paid` | `paid` | Yes | Verify signature, amount, currency and invoice id; provision |
| `canceled` | `cancelled` | Yes | No access |
| `refunded` | `refunded` | Yes | Revoke/adjust access according to refund policy |
| `error` | `failed` | Yes | No access; support if user reports debit |
| unknown | `reconciliation_required` | No | No access; alert ops |

Implementation notes:

- Verify Digiseller signature for status callbacks.
- Store `invoice_id`, `seller_id`, `amount`, `currency`, `integrator`, `amount_out`, `currency_out` where available.
- Callback handling must be idempotent by `invoice_id`.
- Local S1 guardrails are completed in `111_STAGE1_PAY_015_DIGISELLER_READINESS_EVIDENCE.md`: docs-only samples cannot enable Digiseller, `paid` is the only normal automatic-access status, `refunded` is support review, sorted-field HMAC-SHA256 is required, and duplicate callbacks do not repeat side effects.
- Tech debt: confirm exact Digiseller seller account, product/payment model, delivery behavior, callback/status samples, refund/dispute evidence and payment->provisioning evidence before enabling the Russia path.

### YooKassa placeholder mapping

| YooKassa payment status/event | CyberVPN state | Final? | S1 behavior |
|---|---|---:|---|
| `pending` | `pending` | No | Await user/provider action; no access |
| `waiting_for_capture` | `requires_action` | No | Prefer `capture=true` for S1; if two-stage is used, capture before access |
| `payment.waiting_for_capture` | `requires_action` | No | Webhook event for two-stage capture; no access before capture |
| `succeeded` / `payment.succeeded` | `paid` | Yes | Provision after webhook/API verification and amount check |
| `canceled` / `payment.canceled` | `cancelled` | Yes | No access; user may retry |
| `refund.succeeded` | `refunded` | Yes | Revoke/adjust access according to refund policy; support/finance review |
| unknown | `reconciliation_required` | No | No access; alert ops |

Implementation notes:

- For S1, default to one-stage payments (`capture=true`) unless a later decision approves two-stage capture.
- Webhook processing must verify payment id, amount, currency, metadata/order id and current provider state.
- Local S1 guardrails are completed in `112_STAGE1_PAY_016_YOOKASSA_READINESS_EVIDENCE.md`: docs-only samples cannot enable YooKassa, `succeeded` / `payment.succeeded` are the only normal automatic-access statuses, provider status/IP recheck is required for webhooks, `waiting_for_capture` is no-access, `refund.succeeded` is support review, and duplicate webhooks do not repeat side effects.
- Tech debt: final shop/account, webhook/status samples, receipt/fiscalization handling, refund/reconciliation proof and payment->provisioning evidence must be resolved before public Russia production use.

## 7. Orphan payment policy

S1 rule: no unresolved `paid-but-no-access` or orphan payment may be older than 24 hours.

Implementation note, 2026-05-04: local orphan payment / paid-but-no-access policy, SLA thresholds and dashboard summary are implemented and tested in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`. This closes the local contract only; paid beta still requires real admin/support queue, audit trail and alert delivery evidence.

| Scenario | Required S1 behavior |
|---|---|
| Payment is paid, user/order not found | Mark `orphaned`; create manual review item; alert support/finance |
| Payment is paid, provisioning failed | Preserve `paid`; queue provisioning retry; alert if VPN not ready within threshold |
| Provider webhook arrives twice | Idempotent no-op after first processed status transition |
| Provider final success after CyberVPN timeout | Reopen reconciliation; do not silently discard |
| Payment amount/currency mismatch | `reconciliation_required`; no automatic access unless provider policy allows |
| User reports debit but provider status is non-final | Create support ticket; reconcile via provider dashboard/API |

Escalation thresholds:

- 15 minutes: alert for paid payment without VPN-ready state.
- 1 hour: P1 support/ops escalation.
- 24 hours: P0 launch blocker until resolved or explicitly accepted by owner.

## 8. Remnawave staging/prod evidence

Current repository findings:

- Local compose exists at `infra/docker-compose.yml` with Remnawave backend `remnawave/backend:2.7.4`, PostgreSQL 17.7, Valkey 8.1 and monitoring/exporter services.
- Staging smoke script exists at `infra/scripts/remnawave-staging-smoke.sh`.
- This WSL environment currently does not have the `docker` command available, so local Docker evidence could not be executed here.

Important distinction:

- Local Docker proof is useful for development evidence.
- It does not replace S1 staging/prod evidence.

Required S1 Remnawave evidence:

| Evidence | Required before |
|---|---|
| Staging Remnawave health and connected test node | First S1 rollout |
| Production Remnawave health and connected production node | Go-live |
| Backend health reports DB/Redis/Remnawave healthy | Staging and production gates |
| Trial provisioning smoke | Staging gate |
| Paid provisioning smoke | Staging and production low-value gate |
| Provisioning retry after simulated Remnawave outage | Go-live |
| Expiry + 72h grace + disable behavior | Local product/worker proof exists in `44_STAGE1_VPN_007_EXPIRY_GRACE_DISABLE_EVIDENCE.md` and `98_STAGE1_PROD_005_GRACE_PERIOD_BEHAVIOR_EVIDENCE.md`; durable worker plus staging/prod disable evidence required before go-live |
| Remnawave backup/export/rebuild proof | Go-live |

Recommended command family once Docker/hosts are available:

```bash
REMNAWAVE_BASE_URL=...
REMNAWAVE_API_TOKEN=...
API_BASE_URL=...
EXPECTED_NODE_NAME=...
ADMIN_LOGIN=...
ADMIN_PASSWORD=...
SMOKE_USER_LOGIN=...
SMOKE_USER_PASSWORD=...
infra/scripts/remnawave-staging-smoke.sh
```

Evidence output must be redacted before being committed or attached to the evidence pack.

## 9. Production topology evidence

Owner-approved S1 topology:

```text
Public internet
  -> edge/reverse proxy/TLS/WAF where available
    -> frontend/customer cabinet container
    -> admin container behind stricter access controls
    -> backend API container
    -> Telegram Bot/Mini App backend callbacks

Private network only
  -> managed PostgreSQL 17.x
  -> dedicated Valkey/Redis
  -> worker/scheduler container
  -> Remnawave production control-plane API
  -> monitoring/exporters
```

S1 placement rules:

- PostgreSQL is managed, private-only, production separate from staging.
- Valkey/Redis is private-only, production separate from staging, not durable source of truth.
- Backend, bot, worker, frontend and admin may run as containers.
- Remnawave API is private/internal only.
- Public ingress is limited to site/cabinet, API endpoints that must be public, Telegram/payment webhooks and protected admin domain.
- No floating `main` deploys; deploy only immutable tag or commit SHA.

Required topology evidence:

- deploy diagram;
- ingress allowlist;
- public endpoint inventory;
- private dependency inventory;
- secrets inventory without values;
- rollback command/procedure;
- backup/restore evidence;
- monitoring target list.

## 10. Clean DB migration gate

Before Stage 1 implementation and before go-live:

1. Create empty staging database.
2. Apply all backend migrations from zero.
3. Verify seed/bootstrap prerequisites.
4. Run smoke queries for auth, payments, subscription, admin, audit and legal tables.
5. Save redacted migration output to evidence.

Acceptance:

- no manual SQL patch required for clean install;
- migration order deterministic;
- first admin bootstrap can run only after clean migrations;
- pre-deploy production backup is taken before production migrations.

## 11. First admin bootstrap rule

Owner-approved S1 rule:

- no default admin;
- no committed password;
- no permanent public bootstrap endpoint;
- one-time protected bootstrap only after clean migrations;
- first role: `owner/super_admin`;
- mandatory 2FA before admin access;
- audit event required;
- bootstrap disabled after use.

Assigned bootstrap owner: `@Sasha_Beep`.

Evidence:

- redacted bootstrap command/request;
- redacted created admin identifier;
- admin 2FA enforcement proof;
- audit log event;
- proof that bootstrap path is disabled after use.

## 12. Legal public data owner-approved closure

Owner decision says legal seller is `individual founder/owner`. Owner-approved S1 legal/text/public-copy closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.

| Field | Current value | Status |
|---|---|---|
| Legal seller display name | `individual founder/owner` category; sensitive public identity details outside repo | Owner-approved for S1 text |
| Jurisdiction/country | Not expanded in repo public copy | Owner-approved for S1 text; handle external provider/legal evidence outside repo if required |
| Public legal contact | `support@cyber-vpn.net` | Owner-approved text; mailbox proof remains operational evidence |
| Refund contact | `refund@cyber-vpn.net` | Owner-approved text; mailbox/provider proof remains operational evidence |
| Privacy contact | `privacy@cyber-vpn.net` | Owner-approved text; mailbox proof remains operational evidence |
| Abuse contact | `abuse@cyber-vpn.net` | Owner-approved text; mailbox/enforcement proof remains operational evidence |

Sensitive identity, banking, tax and provider credentials must not be stored in the repository.

## 13. Final legal/text pack closure

The following legal/text/public-copy items are closed for S1 owner approval in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`:

- Terms of Service;
- Privacy Policy;
- Acceptable Use Policy;
- Refund Policy;
- Cookie Policy;
- bounded S1 no-logs/privacy wording stance;
- law enforcement request boundary;
- abuse complaint boundary;
- manual S1 export/delete support procedure.

Related non-text evidence remains tracked in the corresponding provider, support, security, observability and infrastructure workstreams.

## 14. Backup and restore evidence

Owner-approved policy:

- daily encrypted PostgreSQL backups;
- 14-day retention;
- pre-deploy backup before production migrations/releases;
- off-host storage;
- RPO <=24h;
- RTO <=4h;
- Remnawave backup/export/rebuild strategy;
- Redis/Valkey is not durable source of truth.

Required drill:

1. Take backup from staging/prod-like database.
2. Restore into a clean environment.
3. Run backend health and core read smoke.
4. Confirm admin/support cannot see secrets in restored logs.
5. Record RPO/RTO observed.
6. Save redacted transcript.

## 15. Rollback evidence

Rollback must be a tested procedure, not a theoretical note.

Minimum rollback evidence:

- frontend/admin rollback to previous immutable tag;
- backend rollback or forward-fix strategy for schema-compatible changes;
- worker rollback or queue pause/resume;
- payment kill switch tested;
- registration kill switch tested;
- trial/provisioning kill switches tested;
- Remnawave outage procedure tested;
- user-facing status message prepared.

## 16. Observability evidence

S1 should cover more than the minimum because observability is a core launch-critical area.

Required observability coverage:

| Area | Required telemetry |
|---|---|
| API | 5xx rate, latency p50/p95/p99, request volume, auth failures |
| Auth | registration failures, login failures, OTP/magic failures, OAuth linking conflicts, admin 2FA failures |
| Payments | provider webhook failures, invalid signatures, duplicate webhook count, paid-but-no-access lag, orphan payments, refund/dispute states |
| Provisioning | trial/pay -> VPN ready latency, Remnawave API errors, retry queue age, failed credential generation |
| Worker/scheduler | queue depth, oldest job age, retry count, dead-letter/reconciliation items |
| PostgreSQL | availability, connection count, storage, replication/backup state if available, slow queries |
| Valkey/Redis | availability, memory, evictions, queue keys, connection count |
| Remnawave | API health, node connected count, node offline alerts, subscription/config delivery errors |
| Frontend/admin | JS errors, route errors, checkout/auth UI errors, source maps if enabled and safe |
| Telegram | bot webhook errors, Mini App auth failures, pre-checkout timeout/failure, successful payment event count |
| Legal/support | support ticket volume, refund requests, abuse/privacy requests |
| Security/privacy | secret/PII redaction tests, suspicious auth/payment rates, admin privileged action audit |

Alert destinations:

- primary: Telegram channel `-5173727789`;
- backup: `backup@cyber-vpn.net`;
- optional operational aliases: `alerts@cyber-vpn.net`, `ops@cyber-vpn.net`, `security@cyber-vpn.net`.

Minimum alert tests before go-live:

- synthetic P0 alert reaches Telegram and backup email;
- payment webhook failure alert;
- invalid payment signature alert;
- paid-but-no-access alert;
- orphan payment alert;
- Remnawave down alert;
- node offline alert;
- worker queue stuck alert;
- backup failure alert;
- high API 5xx alert;
- Sentry/exception alert with PII redaction proof.

Implementation note, 2026-05-06: local S1 Prometheus alert rules, Alertmanager Telegram/email routing and synthetic delivery-test procedure are implemented and validated in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. This closes the local contract only; go-live still requires live Telegram message proof, backup email proof and Alertmanager API evidence.

## 17. Dirty worktree and launch scope map

S1 best-practice rule for 2025-2026:

- build and deploy from a specific commit SHA or immutable release/tag;
- protect the release branch;
- avoid floating `main` for production deploys;
- map every runtime change to an `S1-*` backlog ID;
- explicitly exclude experimental runtime from the S1 deploy surface;
- keep release evidence tied to source revision, artifact digest and deployment record.

Recommended branch/tag policy:

```text
Branch: release/stage1-controlled-public-beta
Docs freeze tag: stage1-docs-freeze.1
Staging/beta tags: stage1-beta-rc.N
Production tags: stage1-beta-live.N
Deploy reference: immutable tag or commit SHA only
```

Launch scope map categories:

| Category | Meaning | S1 rule |
|---|---|---|
| `launch-critical` | Required for S1 runtime | Must have backlog ID, tests/evidence and owner-approved scope |
| `supporting-docs` | Docs/runbooks/evidence | Can ship with docs pack; no runtime effect |
| `disabled-runtime` | Code exists but feature is off | Must have feature flag/route guard and no public entry point |
| `experimental` | Helix/Verta/Beep/native/partner/GitOps mature path | Must not be deployed or exposed in S1 unless re-approved |
| `generated-artifacts` | Coverage/build/output/cache | Must not be mixed into release source |
| `secrets-sensitive` | Env/secrets/private configs | Must not be committed; evidence must be redacted |

Required dirty worktree evidence:

```bash
git status --short
git diff --name-status
git diff --stat
git ls-files --others --exclude-standard
```

Required scope table before first `stage1-beta-rc.N`:

| Path/module | Category | Backlog ID | Runtime included? | Evidence |
|---|---|---|---|---|
| `backend/` | `launch-critical` if S1 API enabled | `S1-BE-*`, `S1-PAY-*`, `S1-VPN-*` | TBD | Tests/evidence |
| `frontend/` | `launch-critical` if public site/cabinet enabled | `S1-FE-*` | TBD | Build/UI evidence |
| `admin/` | `launch-critical` if admin enabled | `S1-ADM-*` | TBD | Access/RBAC/2FA evidence |
| `services/telegram-bot/` | `launch-critical` if Telegram flow enabled | `S1-TG-*` | TBD | Bot/Mini App evidence |
| `services/task-worker/` | `launch-critical` if worker enabled | `S1-PAY-*`, `S1-VPN-*`, `S1-PROD-*` | TBD | Queue/job evidence |
| `infra/docker-compose.yml` | `supporting-docs` / deployment reference | `S1-INFRA-*` | TBD | Compose/config evidence |
| `partner/` | `experimental` / Stage 3 | `S1-P3-PARTNER-*` | No | Exclusion proof |
| `cybervpn_mobile/` | `experimental` / Stage 4 | `S1-P3-NATIVE-*` | No | Exclusion proof |
| `services/helix-*` | `experimental` / Stage 6 | `S1-P3-HELIX-*` | No | Feature flag/exclusion |
| `platform-gitops/` | later platform maturity | `S1-P3-GITOPS-*` | No unless already used | Exclusion or explicit evidence |

Reference basis:

- GitHub immutable releases document release/tag immutability and release attestations.
- GitHub protected branches provide controls for protected branches and status/deployment requirements.
- SLSA source requirements treat a source revision as a logically immutable repository snapshot and require controls that prevent release tags from being updated.
- Git release tags should prefer annotated/signed tags for release points where possible.

## 18. Home lab non-critical option

The home server option is allowed only as a non-critical lab/evidence resource. It may be used for local Docker/Remnawave smoke, staging-like tests, restore drills, secondary monitoring copies, device labs, security scans and experimental S6/S7 work.

It must not become a production dependency for customer login, payments, webhooks, provisioning, production databases, production Remnawave, production admin, primary alerting or VPN exit nodes while 5-hour home power outages are possible.

Detailed stage-by-stage usage is defined in `20_HOME_LAB_NON_CRITICAL_OPTION.md`.
