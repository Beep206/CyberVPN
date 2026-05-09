> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-011`
> Статус: PASS for local/no-cost Telegram Stars contract readiness revalidation. Real BotFather/test-environment/production Stars evidence remains required before enablement.

# S1-PAY-011 Telegram Stars Readiness Evidence

## Purpose

`S1-PAY-011` verifies the local CyberVPN contract for Telegram Stars before the provider can be enabled in the Telegram Bot or Mini App paid flow.

This task does not claim that Telegram Stars is production-ready. It proves that the local code follows the required Stars payment semantics and records the remaining external evidence that must be attached before public enablement.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-010`. Official Telegram Bot API documentation was rechecked against Bot API 10.0 dated 2026-05-08. The existing S1 contract remains valid: Telegram Stars checkout is XTR-only, pre-checkout is validation only, access is delivered only after `successful_payment`, and refunds require `telegram_payment_charge_id`. S1 still does not enable Telegram Stars subscriptions/autoprolongation.

## Official Telegram Requirements Checked

| Requirement | Source | CyberVPN S1 rule |
|---|---|---|
| Digital goods/services inside Telegram Bot/Mini App must use Telegram Stars with `currency="XTR"` | <https://core.telegram.org/bots/payments-stars> | Telegram Bot/Mini App Stars checkout is `XTR` only |
| `pre_checkout_query` must be answered within 10 seconds, but it is not payment proof | <https://core.telegram.org/bots/payments-stars> and <https://core.telegram.org/bots/api#answerprecheckoutquery> | Pre-checkout validates only; it never grants VPN access |
| Digital access must be delivered only after `successful_payment` | <https://core.telegram.org/bots/payments-stars> | Backend confirms and provisions only after `successful_payment` |
| Stars invoice links use empty `provider_token`, `currency="XTR"` and exactly one price item | <https://core.telegram.org/bots/api#createinvoicelink> | Mini App invoice-link helper sends Stars-only payload |
| `telegram_payment_charge_id` is present on `SuccessfulPayment` and required for refunds | <https://core.telegram.org/bots/api#successfulpayment> | Backend stores the Telegram charge ID on confirmation |
| Refunds use `refundStarPayment(user_id, telegram_payment_charge_id)` | <https://core.telegram.org/bots/api#refundstarpayment> | Finance/admin refund execution calls `refundStarPayment` |
| Bots must provide purchase support for disputes | <https://core.telegram.org/bots/payments-stars> | `/paysupport` exists locally; real paid/refund support transcript remains required |
| Bot API 10.0 includes Stars transaction/subscription-related fields | <https://core.telegram.org/bots/api> | S1 keeps Stars subscriptions/autoprolongation disabled; any `subscription_period` support is a later task and requires separate consent/cancel/failure evidence |

## Local Contract Confirmed

| Area | Local result |
|---|---|
| Payment state mapping | `pre_checkout_query` maps to processing and never allows paid access; `successful_payment` is the only Stars paid state that unlocks paid access |
| Telegram Bot invoice | Bot sends invoice with `currency="XTR"` and empty `provider_token` |
| Mini App invoice link | Backend helper calls Telegram `createInvoiceLink` with `provider_token=""`, `currency="XTR"` and one `prices` item |
| Payload binding | Invoice payload uses `stars:<payment_id>:<telegram_id>` and rejects invalid payment/user payloads |
| Confirmation | Bot calls backend confirmation only from `successful_payment`; backend stores `telegram_payment_charge_id` and then runs post-payment processing |
| Idempotency | Existing S1 idempotency tests cover Telegram Stars `successful_payment.telegram_payment_charge_id` as the provider identity |
| Refund execution | Backend refund client calls `refundStarPayment` and treats already-refunded responses as idempotent success |
| Refund reconciliation | Backend can reconcile refund state from Stars transaction evidence by `telegram_payment_charge_id` |
| Support | `/paysupport` and support escalation are locally proven in `60_STAGE1_TG_008_AI_SUPPORT_ESCALATION_EVIDENCE.md` |

## Files Added Or Used

```text
backend/tests/security/test_stage1_telegram_stars_readiness.py
backend/src/presentation/api/v1/telegram/routes.py
backend/src/presentation/api/v1/payments/telegram_stars.py
backend/src/infrastructure/payments/telegram_stars/client.py
backend/src/application/use_cases/refunds/update_refund.py
backend/src/application/use_cases/refunds/reconcile_telegram_stars_refund.py
services/telegram-bot/src/handlers/payment.py
services/telegram-bot/src/services/api_client.py
backend/pyproject.toml
backend/uv.lock
```

## Verification Commands

| Check | Result |
|---|---|
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_telegram_stars_readiness.py -q --no-cov` | PASS: 5 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_telegram_stars_readiness.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_webhook_signature_verification.py tests/unit/infrastructure/payments/telegram_stars/test_client.py tests/unit/application/use_cases/refunds/test_reconcile_telegram_stars_refund.py tests/unit/application/use_cases/refunds/test_update_refund.py -q --no-cov` | PASS: 77 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_telegram_stars_readiness.py tests/unit/infrastructure/payments/telegram_stars/test_client.py tests/unit/application/use_cases/refunds/test_reconcile_telegram_stars_refund.py -q --no-cov` | PASS: 10 tests after npm lockfile CVE remediation |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check tests/security/test_stage1_telegram_stars_readiness.py src/presentation/api/v1/payments/telegram_stars.py src/infrastructure/payments/telegram_stars/client.py src/application/use_cases/refunds/reconcile_telegram_stars_refund.py src/presentation/api/v1/telegram/routes.py src/presentation/api/v1/payments/routes.py` | PASS |
| `cd services/telegram-bot && uv run pytest tests/unit/test_handlers/test_payment.py tests/unit/test_api_client.py::TestTelegramStarsAPIClient -q` | PASS: 9 tests |
| `cd services/telegram-bot && uv run ruff check src/handlers/payment.py src/services/api_client.py src/services/payment_stars.py tests/unit/test_handlers/test_payment.py tests/unit/test_api_client.py` | PASS |
| `cd frontend && npm run test:run -- src/lib/api/__tests__/payments-stars.test.ts` | PASS: 1 file, 2 tests |
| `cd frontend && npm run test:run -- src/lib/api/__tests__/payments-stars.test.ts src/lib/api/__tests__/payments.test.ts` | PASS: 2 files, 20 tests after npm lockfile CVE remediation |
| `cd frontend && npm run lint -- src/lib/api/__tests__/payments-stars.test.ts src/lib/api/payments.ts` | PASS |
| `cd backend && uv run python -c "import mako; print(mako.__version__)"` | PASS: `1.3.12` |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable services/telegram-bot` | PASS: no known vulnerabilities found; cache warnings only |
| `npm audit fix --package-lock-only` | PASS: closed root high `fast-uri` advisory via lockfile-only forward update; no package downgrade |
| `npm audit --omit=dev --audit-level=high` | PASS: high/critical threshold clean after lockfile remediation; existing moderate `postcss` via Next remains tracked because force fix proposes a breaking/downgrade path |
| `cd frontend && npm audit --omit=dev --audit-level=high` | PASS: high/critical threshold clean; existing moderate `postcss` via Next remains tracked |
| High-confidence secret scan over new S1-PAY-011 test/evidence files | PASS: no matches |
| Static dangerous-pattern scan over new S1-PAY-011 test/evidence files | PASS: no matches |
| `git diff --check` over touched S1-PAY-011 code/docs | PASS |
| Stale next-step scan for `S1-PAY-011` as current/next task | PASS: no matches in source docs after update |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | PASS: no running containers reported |

## 2026-05-08 Verification

| Check | Result |
|---|---|
| Official Telegram docs recheck | PASS: Bot API 10.0 reviewed; S1 contract unchanged for one-time Stars checkout/refund |
| XTR-only invoice contract | PASS: bot and Mini App helpers use `currency="XTR"`, empty `provider_token` and one price item |
| Pre-checkout non-grant rule | PASS: local mapping keeps `pre_checkout_query` processing/non-final and never grants VPN access |
| Successful-payment grant rule | PASS: `successful_payment` is the only Stars paid state that unlocks paid access |
| Payload binding | PASS: `stars:<payment_id>:<telegram_id>` parsing rejects invalid/mismatched payloads |
| Refund path | PASS: refund client calls `refundStarPayment(user_id, telegram_payment_charge_id)` and treats already-refunded as idempotent success |
| Refund reconciliation | PASS: local refund reconciliation uses Stars transaction evidence and `telegram_payment_charge_id` |
| Stars subscriptions/autoprolongation | PASS: not enabled in S1; `subscription_period` remains out of scope |
| Backend tests | PASS: targeted 5 passed; combined payment/provider regression 77 passed; post-audit focused pack 10 passed |
| Telegram bot tests | PASS: 9 passed |
| Frontend Stars API tests | PASS: 2 passed; post-audit combined payment API pack 20 passed |
| Lint | PASS: backend, bot and frontend targeted lint passed |
| Dependency audit | PASS: backend and bot `pip-audit`; root/frontend npm high/critical threshold clean after `fast-uri` lockfile remediation |
| Secret scan | PASS: no live Telegram bot token, invoice URL, charge id or provider secret found in S1-PAY-011 scope |
| Static dangerous-pattern scan | PASS: no unsafe runtime matches |
| Docker runtime state | PASS: no containers were started for this task |

## Dependency Security Note

During the final S1-PAY-011 security pass, backend dependency audit reported `mako 1.3.11 / CVE-2026-44307`, fixed in `1.3.12`.

This task upgraded the backend dependency constraint and lockfile:

```text
backend/pyproject.toml: mako>=1.3.12
backend/uv.lock: mako 1.3.12
```

This is a forward-only security update and does not change the Telegram Stars runtime contract.

The 2026-05-08 revalidation also closed a root npm high advisory for `fast-uri <=3.1.0` through `npm audit fix --package-lock-only`, resolving the root lockfile to `fast-uri 3.1.2`. This is a lockfile-only forward remediation and does not change the Telegram Stars runtime contract.

## Real Evidence Still Required Before Enabling Telegram Stars

Telegram Stars must remain disabled or hidden for public paid flow until all items below are attached as redacted evidence:

1. Real staging/test bot identity and BotFather/getMe proof.
2. Telegram Stars test-environment or production low-value invoice proof with `currency="XTR"`.
3. Real `pre_checkout_query` sample where backend accepts valid invoice data.
4. Real `successful_payment` sample with stored `telegram_payment_charge_id`.
5. Duplicate `successful_payment` or retry proof showing no duplicate subscription/provisioning.
6. Real payment -> VPN provisioning proof through Remnawave.
7. Real `/paysupport` transcript for a Stars payment issue and admin/support queue visibility.
8. Real `refundStarPayment` result or refund reconciliation proof using `getStarTransactions`.
9. Alert/reconciliation evidence for paid-but-no-access/orphan Stars cases.
10. Final production secret inventory without exposing `TELEGRAM_BOT_TOKEN` or webhook secret values.

## Security Notes

- No real Telegram bot token, user payment ID, invoice URL or charge ID was committed.
- Test values are redacted synthetic values only.
- Stars payment confirmation remains backend-authoritative and requires the internal Telegram bot secret header.
- Pre-checkout validation does not mutate payment state to completed and does not trigger provisioning.
- Telegram Stars are allowed only for Telegram Bot/Mini App paid flow, not as a general web checkout provider.

## Acceptance Result

`S1-PAY-011` is **completed locally** for Telegram Stars contract readiness.

Telegram Stars is still **not enabled for live paid beta** until real Telegram/BotFather/payment/refund/reconciliation evidence is attached.

Next ID to execute after `S1-PAY-011`: `S1-PAY-013` - PayRam readiness if enabled.
