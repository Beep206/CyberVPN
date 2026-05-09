> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-003`
> Статус: PASS for local/no-cost production credential inventory. Real provider account and secret-store evidence remain required before paid beta.

# S1-PAY-003 CryptoBot Production Credentials Evidence

## Purpose

`S1-PAY-003` фиксирует production credential contract для выбранного первого paid path: CryptoBot / Crypto Pay.

Эта задача не записывает реальные production secrets в репозиторий. Она закрывает безопасную локальную часть: какие секреты нужны, где они должны храниться, какие runtime-компоненты их получают, какие placeholder/test значения запрещены и какие реальные evidence нужны до paid beta.

## Official Contract Checked

Источник: <https://help.send.tg/en/articles/10279948-crypto-pay-api>.

| Item | S1 value |
|---|---|
| Production provider | CryptoBot / Crypto Pay |
| Token source | `@CryptoBot` app / Crypto Pay token |
| API auth transport | `Crypto-Pay-API-Token` request header |
| Production API | `https://pay.crypt.bot/api` |
| Production network config | `CRYPTOBOT_NETWORK=mainnet` |

## Credential Inventory Without Values

Canonical machine-readable contract: `infra/payments/stage1-cryptobot-production-credentials-contract.json`.

| Name | Secret? | Production value policy | Runtime consumers |
|---|---:|---|---|
| `CRYPTOBOT_TOKEN` | Yes | Real provider token from legal seller/project owner account; stored only in approved production secret store or restricted runtime env; value never appears in repo/evidence | backend API, task-worker, Telegram bot only if CryptoBot gateway is enabled there |
| `CRYPTOBOT_NETWORK` | No | Must be `mainnet` in production; `testnet` is rejected | backend API, task-worker, Telegram bot if enabled |

## Runtime Guards Added

| Component | Guard |
|---|---|
| Backend API | Production rejects `CRYPTOBOT_NETWORK=testnet`; production rejects short/placeholder/test `CRYPTOBOT_TOKEN` |
| Task worker | Production rejects `CRYPTOBOT_NETWORK=testnet`; production rejects short/placeholder/test `CRYPTOBOT_TOKEN` |
| Telegram Bot | Production rejects placeholder/test `CRYPTOBOT_TOKEN` when CryptoBot gateway is enabled |
| Secret generator | No longer prints a fake generated `CRYPTOBOT_TOKEN`; it now tells operator to get the token from CryptoBot/Crypto Pay |

## What Is Proven Locally

| Check | Result |
|---|---|
| Machine-readable production credential contract validates | PASS |
| Backend production placeholder token is rejected | PASS |
| Backend production provider-shaped token is accepted | PASS |
| Task-worker production placeholder token is rejected | PASS |
| Task-worker production provider-shaped token is accepted | PASS |
| Telegram Bot production placeholder token is rejected | PASS |
| Telegram Bot production provider-shaped token is accepted | PASS |
| Fake/generated CryptoBot production token output removed from `generate_secrets.py` | PASS |

## What Is Still External

Paid beta remains blocked until these redacted artifacts exist:

1. CryptoBot production app/account ownership proof without secret values.
2. Production `CRYPTOBOT_TOKEN` stored in approved secret store, with no value disclosure.
3. Runtime env proof that backend receives `CRYPTOBOT_TOKEN` and `CRYPTOBOT_NETWORK=mainnet`.
4. Runtime env proof that task-worker receives `CRYPTOBOT_TOKEN` and `CRYPTOBOT_NETWORK=mainnet` if reconciliation/verification jobs use CryptoBot.
5. Runtime env proof that Telegram Bot receives `CRYPTOBOT_TOKEN` only if CryptoBot gateway is enabled for that surface.
6. Secret access matrix showing legal seller/project owner and limited technical runtime access.
7. Rotation and emergency revoke procedure.
8. Production callback/webhook registration proof without token values.
9. Low-value production smoke or approved provider account proof before real paid beta traffic.

## Explicit Non-Goals

This task does not:

- create a real CryptoBot account;
- create or store a real production token;
- reveal secret values;
- enable paid beta;
- prove production callbacks;
- prove refund/reconciliation;
- replace `S1-PAY-004`...`S1-PAY-017` provider evidence gates.

## Files Added Or Updated

```text
backend/scripts/generate_secrets.py
backend/src/config/settings.py
backend/tests/security/test_stage1_cryptobot_sandbox_runtime.py
services/task-worker/src/config.py
services/task-worker/tests/test_stage1_cryptobot_sandbox_config.py
services/telegram-bot/src/config.py
services/telegram-bot/tests/unit/test_main.py
infra/payments/stage1-cryptobot-production-credentials-contract.json
scripts/validate_s1_cryptobot_production_credentials.py
infra/tests/test_stage1_cryptobot_production_credentials.py
docs/cybervpn_stage1_launch_docs/127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md
```

## Verification Commands

| Check | Result |
|---|---|
| `python scripts/validate_s1_cryptobot_production_credentials.py` | PASS |
| `cd backend && uv run pytest tests/security/test_stage1_cryptobot_sandbox_runtime.py -q --no-cov` | PASS |
| `cd backend && uv run pytest ../infra/tests/test_stage1_cryptobot_production_credentials.py -q --no-cov` | PASS |
| `cd backend && uv run ruff check src/config/settings.py src/infrastructure/payments/cryptobot/client.py scripts/generate_secrets.py tests/security/test_stage1_cryptobot_sandbox_runtime.py ../scripts/validate_s1_cryptobot_production_credentials.py ../infra/tests/test_stage1_cryptobot_production_credentials.py` | PASS |
| `cd services/task-worker && uv run pytest tests/test_stage1_cryptobot_sandbox_config.py -q` | PASS |
| `cd services/task-worker && uv run ruff check src/config.py tests/test_stage1_cryptobot_sandbox_config.py` | PASS |
| `cd services/telegram-bot && uv run pytest tests/unit/test_main.py -q` | PASS |
| `cd services/telegram-bot && uv run ruff check src/config.py tests/unit/test_main.py` | PASS |
| `git diff --check -- <touched S1-PAY-003 files>` | PASS |
| High-confidence secret scan over touched S1-PAY-003 files | PASS |
| Static dangerous-pattern scan over touched S1-PAY-003 files | PASS |
| Root/frontend production dependency audit | PASS for high/critical; existing low/moderate advisories remain outside this task |
| Backend/task-worker dependency audit | PASS: no known vulnerabilities found |
| Running containers after task | PASS: no S1-PAY-003 containers started |

## Acceptance Result

`S1-PAY-003` is **completed locally** as a production credential inventory and runtime guard task.

Paid beta is still **blocked** until real CryptoBot account/secret-store/callback evidence is attached without secret values.

Next ID superseded by `36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md`, `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
