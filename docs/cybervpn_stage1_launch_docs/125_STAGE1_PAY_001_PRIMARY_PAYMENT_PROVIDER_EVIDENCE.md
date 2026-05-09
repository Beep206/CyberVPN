> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-001`
> Статус: PASS for local/no-cost provider selection. Real provider account, credentials, sandbox/testnet, production callback and payment-to-provisioning evidence remain required before paid beta.

# S1-PAY-001 Primary Payment Provider Evidence

## Purpose

`S1-PAY-001` выбирает первый live payment path для Stage 1 Controlled Public Beta.

Это не включает платежи в production. Задача закрывает только управленческое и инженерное решение: какой провайдер первым доводим до production-ready состояния, какие остальные провайдеры остаются gated, и какие evidence нужны до paid beta.

## Decision

Первый live paid-path candidate для S1: **CryptoBot / Crypto Pay**.

CryptoBot выбран как первичный кандидат, потому что в текущем монорепозитории под него уже есть самый короткий runtime gap:

| Area | Evidence in repo |
|---|---|
| Checkout creation | `backend/src/application/use_cases/payments/commit_checkout.py` создаёт CryptoBot invoice и payment record with `provider="cryptobot"` |
| Webhook route | `backend/src/presentation/api/v1/webhooks/routes.py` содержит `/webhooks/cryptobot` |
| Provider client | `backend/src/infrastructure/payments/cryptobot/client.py` |
| Signature/authenticity local gate | `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md` |
| Idempotency local gate | `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md` |
| Orphan paid/no-access local policy | `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md` |
| Payment -> provisioning failure handling | `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md` |
| Reconciliation job | `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md` |
| Provider placeholder guardrail | `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md` |

## Provider Readiness Matrix

Canonical machine-readable matrix: `infra/payments/stage1-primary-payment-provider.json`.

| Provider | S1 role | Runtime fit now | Can enable now? | Why |
|---|---|---:|---:|---|
| CryptoBot / Crypto Pay | Primary first live path candidate | Best | No | Checkout/webhook path exists locally, but real account, credentials, testnet/prod callback and provisioning evidence are absent |
| Telegram Stars | Telegram Bot/Mini App secondary path | Good for Telegram only | No | Telegram digital-goods rule requires Stars inside Bot/Mini App, but it is not the universal web checkout path and still needs BotFather/XTR/payment/refund evidence |
| YooKassa | Russia path later | Partial | No | Local guardrails exist, but seller/shop/receipt/fiscalization/status-recheck/refund evidence is required |
| Digiseller | Russia path later | Low | No | Local guardrails exist, but runtime checkout/webhook implementation and seller/product/callback evidence are not ready |
| PayRam | Crypto alternative later | Low | No | Local guardrails exist, but runtime checkout/webhook implementation and provider callback/status/refund evidence are not ready |
| NOWPayments | Crypto alternative later | Low | No | Local guardrails exist, but runtime checkout/webhook implementation and real IPN/status/refund evidence are not ready |

## Official Sources Checked

| Provider | Source | Impact on S1 decision |
|---|---|---|
| CryptoBot / Crypto Pay | <https://help.send.tg/en/articles/10279948-crypto-pay-api> | Crypto Pay supports invoice statuses `active`, `paid`, `expired` and webhook delivery. This matches the existing CyberVPN CryptoBot local path, but provider evidence is still required. |
| Telegram Stars | <https://core.telegram.org/bots/payments-stars> | Digital goods/services inside Telegram Bot/Mini App must use Stars with `XTR`; access is delivered only after `successful_payment`. This makes Stars Telegram-only for S1, not the general web provider. |
| NOWPayments | <https://nowpayments.zendesk.com/hc/en-us/articles/21345824322717-API-and-endpoint-description> | NOWPayments requires API/IPN integration and explicit status handling. It remains an approved later crypto rail, not the first path in this repo. |
| YooKassa | <https://yookassa.ru/developers/using-api/webhooks> | YooKassa webhooks/statuses require provider status/IP authenticity proof and Russia-path receipt/legal evidence. It remains a later Russia path. |

## Selection Rationale

CryptoBot is not chosen because it is “fully ready”. It is chosen because it is the least risky first provider to harden from the current codebase.

The repo already assumes CryptoBot in the generic checkout path. If we choose PayRam, NOWPayments or Digiseller as the first live provider, we add new runtime integration work before we can even start provider evidence. If we choose Telegram Stars first, we can only prove the Telegram Bot/Mini App flow, not the website/web-cabinet paid flow. If we choose YooKassa first, S1 inherits Russia seller/fiscal/receipt complexity before the basic B2C payment-to-VPN path is proven.

## Required Evidence Before CryptoBot Enablement

CryptoBot must remain disabled/not production-cleared until all items below are attached as redacted evidence:

1. CryptoBot app/account ownership proof without secret values.
2. `@CryptoTestnetBot` or provider testnet invoice success/fail/expired samples where available.
3. Production credential storage inventory without values.
4. Production callback/webhook registration proof.
5. Valid `crypto-pay-api-signature` callback proof and invalid signature rejection proof.
6. Duplicate callback proof under durable PostgreSQL/Valkey persistence.
7. Payment `paid` -> subscription/order -> Remnawave provisioning proof.
8. Paid-but-no-access/orphan alert and manual review proof.
9. Refund/manual finance reconciliation proof.
10. Admin/support payment-attempt visibility proof without raw provider secrets.
11. Kill switch and rollback proof for paid flow.

## Explicit Non-Goals

The following are not allowed by this task:

- enabling all owner-approved providers at once;
- enabling paid beta from documentation-only samples;
- enabling any provider without account/credentials evidence;
- issuing paid VPN access from pending, pre-checkout, partial, unresolved or unverified states;
- using Telegram Stars as the general web checkout path;
- promising autoprolongation or recurring billing in S1;
- committing provider secrets, callback payloads with sensitive fields or full payment URLs to repo evidence.

## Files Added Or Updated

```text
infra/payments/stage1-primary-payment-provider.json
infra/payments/README.md
scripts/validate_s1_primary_payment_provider.py
infra/tests/test_stage1_primary_payment_provider.py
docs/cybervpn_stage1_launch_docs/125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md
docs/cybervpn_stage1_launch_docs/evidence_pack/stage1/payments/README.md
```

## Verification Commands

| Check | Result |
|---|---|
| `python scripts/validate_s1_primary_payment_provider.py` | PASS |
| `cd backend && uv run pytest ../infra/tests/test_stage1_primary_payment_provider.py -q --no-cov` | PASS |
| `cd backend && uv run ruff check ../scripts/validate_s1_primary_payment_provider.py ../infra/tests/test_stage1_primary_payment_provider.py` | PASS |
| `git diff --check -- <touched S1-PAY-001 files>` | PASS |
| High-confidence secret scan over touched S1-PAY-001 files | PASS |
| Static dangerous-pattern scan over touched S1-PAY-001 files | PASS |
| Root/frontend production dependency audit | PASS for high/critical; existing moderate `postcss` advisory through `next` remains outside this task |
| Backend dependency audit | PASS: no known vulnerabilities found; local project package skipped because it is not on PyPI |
| Running containers after task | PASS: no S1-PAY-001 containers started |

## Acceptance Result

`S1-PAY-001` is **completed locally** as a provider-selection and readiness-matrix task.

Primary S1 live paid-path candidate: **CryptoBot / Crypto Pay**.

Paid beta is still **blocked** until real provider testnet/production evidence, provider account proof, callback samples and payment-to-provisioning evidence are attached without secret values.

Next ID superseded by `126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`, `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`, `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`, `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
