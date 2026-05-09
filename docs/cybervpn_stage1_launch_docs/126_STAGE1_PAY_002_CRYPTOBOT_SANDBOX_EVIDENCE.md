> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-002`
> Статус: PASS for local/no-cost sandbox runtime contract. Real `@CryptoTestnetBot` credentials, invoice samples and callback evidence remain required before paid beta.

# S1-PAY-002 CryptoBot Sandbox/Testnet Evidence

## Purpose

`S1-PAY-002` подготавливает выбранный первый paid path, CryptoBot / Crypto Pay, к sandbox/testnet проверке.

Эта задача не включает live payments. Она закрывает локальную часть: runtime умеет явно переключаться между CryptoBot mainnet и testnet, production не может стартовать с testnet, а evidence фиксирует, какие реальные provider-доказательства ещё нужны.

## Official Contract Checked

Источник: <https://help.send.tg/en/articles/10279948-crypto-pay-api>.

| Item | S1 value |
|---|---|
| Mainnet bot | `@CryptoBot` |
| Testnet bot | `@CryptoTestnetBot` |
| Mainnet API | `https://pay.crypt.bot/api` |
| Testnet API | `https://testnet-pay.crypt.bot/api` |
| Invoice statuses | `active`, `paid`, `expired` |
| Paid webhook update type | `invoice_paid` |

Crypto Pay не документирует отдельный invoice status `cancelled` для invoice flow. Поэтому для acceptance wording `succeed/fail/cancel` в S1 используется такая трактовка:

| Acceptance word | Crypto Pay evidence |
|---|---|
| succeed | Real testnet invoice reaches `paid`; CyberVPN grants access only after verification |
| fail | Invalid token/provider failure/status-recheck sample; CyberVPN does not grant access |
| cancel | `expired` invoice as provider-backed no-payment/cancel-equivalent sample |

## Runtime Changes

Canonical machine-readable contract: `infra/payments/stage1-cryptobot-sandbox-contract.json`.

| Component | Change | Guard |
|---|---|---|
| Backend API | Added `CRYPTOBOT_NETWORK=mainnet|testnet`; CryptoBot client maps to fixed official endpoints | `production` rejects `testnet`; arbitrary base URLs are not allowed |
| Task worker | Added `CRYPTOBOT_NETWORK=mainnet|testnet`; worker CryptoBot client maps to fixed official endpoints | `production` rejects `testnet`; arbitrary base URLs are not allowed |
| Telegram Bot | Existing `CRYPTOBOT_NETWORK` config is recorded as compatible | Bot still delegates checkout authority to backend for S1 paid path |

## What Is Proven Locally

| Check | Result |
|---|---|
| Backend can select CryptoBot testnet endpoint | PASS |
| Backend defaults to CryptoBot mainnet endpoint | PASS |
| Backend production rejects `CRYPTOBOT_NETWORK=testnet` | PASS |
| Backend rejects unknown CryptoBot network | PASS |
| Task worker can select CryptoBot testnet endpoint | PASS |
| Task worker production rejects `CRYPTOBOT_NETWORK=testnet` | PASS |
| Machine-readable sandbox contract validates | PASS |

## What Is Still External

Paid beta remains blocked until these redacted provider-account artifacts exist:

1. `@CryptoTestnetBot` app/account ownership proof without secret values.
2. Testnet credential inventory through approved secret storage, no values in repo.
3. Successful testnet `createInvoice` sample.
4. Testnet invoice `paid` status sample.
5. Testnet invoice `expired` status sample as cancel-equivalent.
6. Invalid token/provider failure sample with no VPN access granted.
7. Valid `crypto-pay-api-signature` callback sample.
8. Invalid signature rejection sample.
9. Duplicate callback/idempotency proof against durable storage.
10. Payment `paid` -> order/subscription -> Remnawave provisioning proof.
11. Paid-but-no-access/orphan manual review proof within 24 hours.

## Explicit Non-Goals

This task does not:

- create real CryptoBot credentials;
- store provider secrets;
- enable paid beta;
- prove production callbacks;
- replace webhook signature/idempotency/reconciliation evidence;
- allow `testnet` in production;
- allow arbitrary CryptoBot API URLs from env.

## Files Added Or Updated

```text
backend/.env.example
backend/src/config/settings.py
backend/src/infrastructure/payments/cryptobot/client.py
backend/tests/security/test_stage1_cryptobot_sandbox_runtime.py
services/task-worker/.env.example
services/task-worker/README.md
services/task-worker/src/config.py
services/task-worker/src/services/cryptobot_client.py
services/task-worker/tests/conftest.py
services/task-worker/tests/test_services.py
services/task-worker/tests/test_stage1_cryptobot_sandbox_config.py
infra/payments/stage1-cryptobot-sandbox-contract.json
scripts/validate_s1_cryptobot_sandbox.py
infra/tests/test_stage1_cryptobot_sandbox.py
docs/cybervpn_stage1_launch_docs/126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md
```

## Verification Commands

| Check | Result |
|---|---|
| `python scripts/validate_s1_cryptobot_sandbox.py` | PASS |
| `cd backend && uv run pytest tests/security/test_stage1_cryptobot_sandbox_runtime.py -q --no-cov` | PASS |
| `cd backend && uv run pytest ../infra/tests/test_stage1_cryptobot_sandbox.py -q --no-cov` | PASS |
| `cd backend && uv run ruff check src/config/settings.py src/infrastructure/payments/cryptobot/client.py tests/security/test_stage1_cryptobot_sandbox_runtime.py ../scripts/validate_s1_cryptobot_sandbox.py ../infra/tests/test_stage1_cryptobot_sandbox.py` | PASS |
| `cd services/task-worker && uv run pytest tests/test_services.py tests/test_stage1_cryptobot_sandbox_config.py -q` | PASS |
| `cd services/task-worker && uv run ruff check src/config.py src/services/cryptobot_client.py tests/conftest.py tests/test_services.py tests/test_stage1_cryptobot_sandbox_config.py` | PASS |
| `git diff --check -- <touched S1-PAY-002 files>` | PASS |
| High-confidence secret scan over touched S1-PAY-002 files | PASS |
| Static dangerous-pattern scan over touched S1-PAY-002 files | PASS |
| Root/frontend production dependency audit | PASS for high/critical; existing moderate `postcss` advisory through `next` remains outside this task |
| Backend dependency audit | PASS: no known vulnerabilities found; local project package skipped because it is not on PyPI |
| Running containers after task | PASS: no S1-PAY-002 containers started |

## Acceptance Result

`S1-PAY-002` is **completed locally** as a CryptoBot sandbox/testnet runtime contract.

Paid beta is still **blocked** until real `@CryptoTestnetBot` credentials, production secret-store proof, testnet invoice success/failure/expired samples and webhook/callback evidence are attached.

Next ID superseded by `127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`, `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`, `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Ordered Batch Revalidation

`S1-PAY-002` was re-run as item 17 in the owner-requested ordered batch.

Verification:

```text
python scripts/validate_s1_cryptobot_sandbox.py
Result: infra/payments/stage1-cryptobot-sandbox-contract.json is valid for S1-PAY-002

cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_cryptobot_sandbox_runtime.py -q --no-cov
Result: 6 passed in 0.05s

PYENV_VERSION=3.13.11 uv run pytest ../infra/tests/test_stage1_cryptobot_sandbox.py -q --no-cov
Result: 4 passed in 0.03s

PYENV_VERSION=3.13.11 uv run ruff check src/config/settings.py src/infrastructure/payments/cryptobot/client.py tests/security/test_stage1_cryptobot_sandbox_runtime.py ../scripts/validate_s1_cryptobot_sandbox.py ../infra/tests/test_stage1_cryptobot_sandbox.py
Result: All checks passed

cd services/task-worker
PYENV_VERSION=3.13.11 uv run pytest tests/test_services.py tests/test_stage1_cryptobot_sandbox_config.py -q
Result: 27 passed in 0.31s

PYENV_VERSION=3.13.11 uv run ruff check src/config.py src/services/cryptobot_client.py tests/conftest.py tests/test_services.py tests/test_stage1_cryptobot_sandbox_config.py
Result: All checks passed
```

Execution note: one initial validator attempt used the wrong working directory and failed to locate `scripts/validate_s1_cryptobot_sandbox.py`. It was re-run from the repository root successfully; the successful root-level validator result is the accepted evidence.

Local acceptance remains unchanged. Real `@CryptoTestnetBot` credentials, invoice lifecycle samples, callback signature samples, duplicate callback/idempotency and payment-to-provisioning evidence remain required before paid beta.
