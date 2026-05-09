> CyberVPN Stage 1 Evidence
> ID: S1-PAY-009
> Date: 2026-05-08
> Scope: local refund/dispute process contract, provider posture and backend role gates; revalidated as active execution step.

# S1-PAY-009 Refund/Dispute Process Evidence

## Result

`S1-PAY-009` is completed locally.

CyberVPN now has an explicit S1 refund/dispute process contract:

- customers may create their own refund requests for their own paid orders;
- support may intake and escalate refund/dispute cases, but cannot approve refunds or change dispute financial state;
- finance, admin, super-admin and owner/super-admin may review refunds and reconcile payment disputes;
- operator/viewer/support roles are denied for refund/dispute state mutation;
- admin 2FA enforcement is applied to the refund/dispute reviewer dependency when `ADMIN_2FA_REQUIRED=true`;
- provider-specific refund execution remains gated by evidence before a provider is enabled.

This closes the local S1 runbook/test requirement. It does not enable any payment provider for live refunds or disputes. Real provider accounts, credentials, sandbox/prod callback samples, refund/support transcripts and reconciliation evidence remain required before each provider is enabled.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-008`. No runtime code changes were required; the existing role gate, provider posture and lifecycle tests still match the S1 refund/dispute safety rule.

## S1 process boundary

| Step | Owner | Rule |
|---|---|---|
| Refund request intake | Customer or support | Customer can request from own order; support can create/escalate a ticket |
| Payment/refund review | Finance/admin | Verify order, payment attempt/payment, provider status, amount/currency, provisioning state and abuse indicators |
| Provider execution | Finance/admin | Disabled until provider-specific refund/support evidence exists; Telegram Stars may use API only after Stars evidence |
| Dispute/chargeback recording | Finance/admin | Record provider reference, subtype, lifecycle status, disputed amount, fee and evidence snapshot |
| Access adjustment | Finance/admin + ops if needed | Full refund normally cancels/disables the related paid period; partial refund may adjust entitlement |
| User communication | Support | No automatic/guaranteed refund promise; no request for sensitive payment/VPN credentials |

## Provider posture for S1

| Provider | S1 refund/dispute mode | Evidence still required before enablement |
|---|---|---|
| PayRam | Provider support or manual payout after finance review | Real dashboard/API refund or wallet-transfer process, wallet-address validation, reference/amount evidence |
| NOWPayments | Provider support or manual payout after finance review | IPN proof, provider support/validation flow, wrong-asset/wrong-network/minimum-amount process |
| CryptoBot / Crypto Pay | Manual finance review | Testnet/prod invoice evidence, approved manual transfer/check/refund workflow, reconciliation proof |
| Telegram Stars | `refundStarPayment` only after Telegram evidence | Stored `telegram_payment_charge_id`, `/paysupport`, XTR flow, refund API result, reconciliation proof |
| Digiseller | Provider API/status reconciliation after evidence | Callback signature, `paid/wait/canceled/refunded/error` samples, refund status workflow |
| YooKassa | Provider API refund after evidence | `succeeded` payment proof, refund idempotency, partial/full support, receipt/fiscal handling |

## Implementation summary

| File | Change |
|---|---|
| `backend/src/presentation/api/shared/stage1_refund_dispute_process.py` | Added S1 role policy, provider refund modes, evidence requirements, forbidden output fields and runbook serializer |
| `backend/src/presentation/api/v1/refunds/routes.py` | `PATCH /api/v1/refunds/{refund_id}` now requires the S1 finance/admin reviewer gate instead of generic operator access |
| `backend/src/presentation/api/v1/payment_disputes/routes.py` | Payment dispute create/list/get now require the S1 finance/admin reviewer gate |
| `backend/tests/security/test_stage1_refund_dispute_process.py` | Added role, provider mode, 2FA and safe runbook tests |
| `backend/tests/integration/test_refund_and_dispute_lifecycle.py` | Extended lifecycle test: support is denied, finance can complete refunds and manage disputes, admin still works |
| `backend/tests/security/test_stage1_route_boundary.py` | Route-boundary regression check now walks nested FastAPI dependencies, so refund/dispute reviewer gates and support payment-attempt gates are classified through their real auth dependency chain |

## Safe data contract

Refund/dispute evidence must include:

- `order_id`;
- `payment_attempt_id` or `payment_id`;
- provider name;
- provider payment reference;
- amount and currency;
- customer reason or dispute reason;
- provider status snapshot;
- finance/admin actor;
- support ticket or audit reference.

Refund/dispute outputs must not expose:

- raw provider payloads;
- payment URLs;
- provider secrets/API keys/webhook signatures;
- wallet private keys;
- full crypto addresses unless operationally required;
- QR codes, subscription URLs or VPN config URLs.

## Official provider notes used

Rechecked on 2026-05-08. No local provider mode change is required; every provider remains disabled for live refunds/disputes until real account, callback/status, refund/support and reconciliation evidence exists.

| Source | S1 rule applied |
|---|---|
| Telegram Stars payment flow and `/paysupport`: <https://core.telegram.org/bots/payments-stars> | Telegram Bot/Mini App digital goods must use Stars inside Telegram; disputes require support, and refunds use `refundStarPayment` after evidence |
| Telegram Bot API `refundStarPayment`: <https://core.telegram.org/bots/api#refundstarpayment> | Stars refund requires `user_id` and `telegram_payment_charge_id` |
| YooKassa refunds: <https://yookassa.ru/developers/payment-acceptance/after-the-payment/refunds> | Refunds are for successful payments and require `payment_id`, amount and idempotency |
| NOWPayments statuses/refunds/IPN: <https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses>, <https://nowpayments.zendesk.com/hc/en-us/articles/18316629513757-Refunds-and-Validation-flow>, <https://nowpayments.zendesk.com/hc/en-us/articles/21395546303389-IPN-and-how-to-setup> | `finished` is the clean paid state; partially paid/cancelled/refund cases require merchant/support handling and signed IPN proof |
| PayRam payment/refund FAQ: <https://docs.payram.com/api-integration/payments-api/payment-status>, <https://docs.payram.com/faqs/general-faqs> | `FILLED` is paid; over/underpayment and refunds require merchant workflow/manual control |
| Crypto Pay API: <https://help.send.tg/en/articles/10279948-crypto-pay-api> | S1 keeps CryptoBot refunds/manual payouts under finance review until real invoice, transfer/check and reconciliation evidence exists |
| Digiseller payment API: <https://my.digiseller.com/inside/api_payment.asp> | Callback/status values include `paid`, `wait`, `canceled`, `refunded`, `error` and require signature verification |

## Commands and results

| Check | Command | Result |
|---|---|---|
| Backend targeted tests | `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_refund_dispute_process.py -q --no-cov` | `11 passed` |
| Backend targeted lint | `cd backend && uv run ruff check src/presentation/api/shared/stage1_refund_dispute_process.py src/presentation/api/v1/refunds/routes.py src/presentation/api/v1/payment_disputes/routes.py tests/security/test_stage1_refund_dispute_process.py tests/integration/test_refund_and_dispute_lifecycle.py` | `All checks passed!` |
| Route-boundary lint | `cd backend && uv run ruff check tests/security/test_stage1_route_boundary.py` | `All checks passed!` |
| Route-boundary regression | `cd backend && uv run pytest tests/security/test_stage1_route_boundary.py -q --no-cov` | `4 passed` |
| Combined S1-PAY-009 regression | `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_refund_dispute_process.py tests/integration/test_refund_and_dispute_lifecycle.py tests/contract/test_refunds_payment_disputes_openapi_contract.py tests/security/test_stage1_route_boundary.py -q --no-cov` | `19 passed` |
| Backend dependency audit | `cd backend && uvx pip-audit --progress-spinner off` | `No known vulnerabilities found` |
| Touched-file secret marker scan | `rg -n '(?i)(api[_-]?key\|secret\|token\|authorization\|password\|private[_-]?key\|payment_url\|checkout_url\|idempotency_key)' ...` | Only policy/test classifier words found; no live credentials |
| Dangerous runtime pattern scan | `rg -n --pcre2 '(?i)(eval\(\|\bexec\(\|shell=True\|subprocess\|os\.system\|raw sql\|\btext\()' ...` | No matches |
| Coverage run observation | Same pytest command without `--no-cov` | Tests passed, but global coverage failed at 49% vs project `fail-under=70`; this is a targeted-test limitation, not a S1-PAY-009 functional failure |

## 2026-05-08 Verification

| Check | Result |
|---|---|
| Official provider documentation recheck | PASS: no local provider mode change required |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_refund_dispute_process.py -q --no-cov` | PASS: 11 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_refund_dispute_process.py tests/integration/test_refund_and_dispute_lifecycle.py tests/contract/test_refunds_payment_disputes_openapi_contract.py tests/security/test_stage1_route_boundary.py -q --no-cov` | PASS: 19 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_refund_dispute_process.py src/presentation/api/v1/refunds/routes.py src/presentation/api/v1/payment_disputes/routes.py tests/security/test_stage1_refund_dispute_process.py tests/integration/test_refund_and_dispute_lifecycle.py tests/security/test_stage1_route_boundary.py` | PASS |
| Customer refund request path | PASS: customer creates own order refund request with idempotency |
| Support denial | PASS: support cannot approve refunds or create/update disputes |
| Finance/admin mutation path | PASS: finance/admin can complete refunds and manage disputes |
| Admin 2FA gate | PASS: reviewer dependency enforces 2FA when configured |
| Safe runbook output | PASS: no raw provider payload, payment URL, secrets, private keys or VPN config URLs |
| Stale next-step scan | PASS: no stale `S1-PAY-009` next-step pointers remain in Stage 1 docs |
| `git diff --check` on touched docs | PASS |
| Trailing whitespace scan on touched code/evidence | PASS: no matches |
| Secret marker scan on touched code/evidence | PASS: no live credentials found; synthetic test token variables and policy words excluded |
| Static dangerous-pattern scan on touched code/evidence | PASS: no runtime matches with word-boundary SQL `text()` detection and documentation rows excluded |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical threshold; existing low/moderate advisories remain outside `S1-PAY-009` |
| Docker runtime state | PASS: no containers were started for this task |

## Security Review Notes

- Refund/dispute financial state mutations are limited to finance/admin/super-admin/owner-super-admin roles.
- Support can intake/escalate but cannot approve refunds or reconcile disputes.
- Admin 2FA is enforced by the reviewer dependency when `ADMIN_2FA_REQUIRED=true`.
- Provider execution remains disabled until provider-specific live evidence exists.
- Backend dependency audit passed with no known vulnerabilities.
- NPM high/critical audit threshold passed; low/moderate frontend/workspace advisories are tracked outside this refund/dispute task and were not fixed with breaking/downgrade changes.
- Static secret and dangerous-pattern scans found no live credentials or unsafe runtime patterns in the touched S1-PAY-009 scope.
- This task did not start Docker containers or require external provider credentials.

## Remaining before paid beta/go-live

| Requirement | Why it remains open |
|---|---|
| Real provider refund evidence per enabled provider | Local role gates do not prove provider-side behavior |
| `refund@cyber-vpn.net` mailbox proof | Public refund contact must receive and route requests |
| Deployed admin/support persona proof | Local API tests do not prove deployed admin UI/API access |
| Provider callback/status/reconciliation samples | Dispute/refund decisions must match real provider state |
| Audit-log retrieval evidence in staging/prod | Local refund outbox actor evidence is not deployed audit evidence |
| Payment path enablement decision | Providers remain disabled until `S1-PAY-001`...`S1-PAY-003`, `S1-PAY-011`, `S1-PAY-013`...`S1-PAY-017` evidence exists |

## Next ID

Next ID superseded by `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
