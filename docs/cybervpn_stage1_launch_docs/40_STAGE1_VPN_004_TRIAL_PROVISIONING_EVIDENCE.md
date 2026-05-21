> CyberVPN Launch Program
> Evidence ID: S1-VPN-004
> Date: 2026-05-04
> Status: local mock provisioning proof complete; rented production trial/client-connect proof complete; controlled public enablement still gated

# S1-VPN-004 Trial Provisioning Evidence

## Purpose

This document closes the local implementation/evidence part of `S1-VPN-004`: trial activation must be able to create VPN access through the S1 Remnawave provisioning contract.

The original local proof showed that the backend has a mockable S1 trial provisioning boundary and that trial activation can call it safely. A later rented production proof also confirmed the real CyberVPN backend, Remnawave control-plane, subscription URL route and VPN node can complete the Stage 1 trial path end to end.

## Decision

S1 trial provisioning uses the protocol allowlist from `S1-VPN-003`:

- default profile: `vless-reality-raw`;
- optional allowlisted profile: `vless-reality-xhttp`;
- disabled profiles are rejected before any gateway call.

S1 trial defaults implemented locally:

| Rule | Value |
|---|---|
| Trial duration | `3` days |
| Device limit | `1` |
| Traffic limit | `2 GiB` |
| Traffic reset strategy | `NO_RESET` |
| Remnawave username | deterministic non-PII `cvpn_t_<first_28_customer_uuid_hex>`; stays within Remnawave 36-character username limit |
| Public runtime gate | `STAGE1_TRIAL_PROVISIONING_ENABLED=false` by default |

The runtime gate is intentionally off by default so local/dev/test environments do not accidentally create upstream Remnawave users. S1 beta environments must explicitly enable it only after Remnawave staging/prod profile evidence exists.

## Implementation Evidence

Code:

- `backend/src/application/use_cases/trial/stage1_trial_provisioning.py`
- `backend/src/application/use_cases/trial/activate_trial.py`
- `backend/src/application/use_cases/trial/__init__.py`
- `backend/src/infrastructure/remnawave/stage1_trial_gateway.py`
- `backend/src/presentation/api/v1/trial/routes.py`
- `backend/src/config/settings.py`
- `backend/.env.example`

Tests:

- `backend/tests/security/test_stage1_trial_provisioning.py`
- `backend/tests/unit/api/v1/test_trial.py`

Implemented behavior:

1. `ActivateTrialUseCase` can receive an injected `Stage1TrialProvisioningGateway`.
2. When the gateway is configured, trial activation calls Remnawave provisioning before local trial state is persisted.
3. The local user receives `remnawave_uuid` and `subscription_url` from the provisioning result.
4. The safe result summary does not expose subscription/config links, tokens or secrets.
5. Disabled S1 profiles are rejected before any gateway call.
6. If the public runtime gate is disabled, existing trial activation behavior remains available for non-provisioning test/dev flows.

## Test Evidence

Targeted command:

```bash
ENVIRONMENT=test SKIP_TEST_DB_BOOTSTRAP=1 DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test REDIS_URL=redis://localhost:6379/15 REMNAWAVE_TOKEN=test-remnawave-token JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough CRYPTOBOT_TOKEN=test-cryptobot-token PYTHONPATH=backend PYENV_VERSION=3.13.11 python -m pytest backend/tests/security/test_stage1_trial_provisioning.py backend/tests/unit/api/v1/test_trial.py -q --no-cov
```

Result:

```text
11 passed in 0.07s
```

Style command:

```bash
PYENV_VERSION=3.13.11 python -m ruff check backend/src/application/use_cases/trial/stage1_trial_provisioning.py backend/src/infrastructure/remnawave/stage1_trial_gateway.py backend/src/application/use_cases/trial/activate_trial.py backend/src/application/use_cases/trial/__init__.py backend/src/presentation/api/v1/trial/routes.py backend/src/config/settings.py backend/tests/security/test_stage1_trial_provisioning.py backend/tests/unit/api/v1/test_trial.py
```

Result:

```text
All checks passed!
```

Broader S1 backend regression pack:

```text
254 passed in 13.13s
```

## Source Notes

The gateway payload follows the existing CyberVPN Remnawave gateway contract and the Remnawave create-user contract shape already represented in `backend/src/infrastructure/remnawave/user_gateway.py`: `expireAt`, `trafficLimitBytes`, `trafficLimitStrategy`, `hwidDeviceLimit`, `email`, `telegramId` and `activeInternalSquads` where available.

Official context:

- Remnawave Config Profiles: `https://docs.rw/docs/learn-en/config-profiles/`
- Remnawave API Specification: `https://docs.rw/api/`

## 2026-05-20 Rented Production Proof

Evidence:

```text
docs/evidence/releases/stage1-rented-prod-07-backend-trial-client-connect-20260520T065023Z.md
```

Result:

- trial activation returned `HTTP 200`;
- Remnawave user was created and active;
- subscription URL host was `api.cyber-vpn.net`;
- Mini App config returned a subscription delivery response;
- subscription fetch returned `HTTP 200`;
- Remnawave generated two real VLESS links for `de-1.cyber-vpn.org`;
- generated TCP Reality link connected through the production VPN node;
- Xray client proof showed proxied egress matched `77.90.13.29`;
- disposable proof user was deleted from CyberVPN and Remnawave;
- `STAGE1_TRIAL_PROVISIONING_ENABLED=false` was restored after the proof.

## Remaining Work Before Real Beta

The following items remain blocking before this can be called real beta evidence:

1. keep `STAGE1_TRIAL_PROVISIONING_ENABLED=false` until the controlled beta launch gate is opened;
2. repeat the proof immediately before enabling the first beta cohort if runtime tags or Remnawave settings changed;
3. keep subscription URL/QR/config delivery logs sanitized;
4. add alerting review for trial provisioning failures and latency in `trial/pay -> VPN ready` metrics;
5. keep the feature kill-switch documented and tested.

## 2026-05-09 Ordered Batch Revalidation

`S1-VPN-004` was re-run as item 16 in the owner-requested ordered batch:

16. `S1-VPN-004`
17. `S1-PAY-002`
18. `S1-QA-003`
19. `S1-QA-004`
20. `S1-INFRA-005`

Verification:

```text
cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_trial_provisioning.py tests/unit/api/v1/test_trial.py -q --no-cov
Result: 12 passed in 0.24s

PYENV_VERSION=3.13.11 uv run ruff check src/application/use_cases/trial/stage1_trial_provisioning.py src/infrastructure/remnawave/stage1_trial_gateway.py src/application/use_cases/trial/activate_trial.py src/application/use_cases/trial/__init__.py src/presentation/api/v1/trial/routes.py src/config/settings.py tests/security/test_stage1_trial_provisioning.py tests/unit/api/v1/test_trial.py
Result: All checks passed
```

Local acceptance remains unchanged: trial provisioning is proven through the mockable S1 Remnawave gateway. Real staging/prod trial activation, subscription URL/QR/config delivery, provisioning latency and alert evidence remain required before go-live.
