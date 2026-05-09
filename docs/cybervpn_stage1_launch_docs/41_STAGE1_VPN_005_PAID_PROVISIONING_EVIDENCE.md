> CyberVPN Launch Program
> Evidence ID: S1-VPN-005
> Date: 2026-05-04
> Status: local contract evidence completed; staging/prod Remnawave evidence still required before beta.

# S1-VPN-005 Paid Provisioning Evidence

## Scope

`S1-VPN-005` proves the local paid provisioning contract for Controlled Public Beta:

1. a paid order can create new Remnawave-backed VPN access;
2. a paid order can extend existing VPN access from the current future expiry;
3. non-final/non-paid payment states cannot trigger provisioning;
4. the contract uses only the approved S1 VPN profile allowlist from `39_STAGE1_VPN_003_PROTOCOL_LIST_EVIDENCE.md`;
5. returned metadata is safe for backend/admin/support surfaces and does not leak subscription URLs, configs, provider secrets or tokens.

This evidence is deliberately local/mockable. It does not prove real staging/prod Remnawave behavior.

## Code Added

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/subscriptions/stage1_paid_provisioning.py` | Provider-neutral S1 paid provisioning request/result/service contract |
| `backend/src/infrastructure/remnawave/stage1_paid_gateway.py` | Remnawave adapter for create/update paid VPN access |
| `backend/tests/security/test_stage1_paid_provisioning.py` | Component and feature-level tests for paid provisioning |

## Contract

| Rule | S1 behavior |
|---|---|
| Order eligibility | `order_status=committed` only |
| Settlement eligibility | `settlement_status=paid` only |
| Non-final statuses | rejected before provisioning |
| Refund/failure statuses | rejected before provisioning |
| New paid access | starts from `provisioning_requested_at` |
| Existing active access | extends from `current_access_expires_at` when it is in the future |
| Profile allowlist | `vless-reality-raw` default; `vless-reality-xhttp` alternate |
| Disabled profiles | `wireguard`, `openvpn`, `vmess`, `trojan`, `shadowsocks`, `hysteria2`, `tuic`, `helix`, `verta`, `beep` rejected |
| Runtime gate | `STAGE1_PAID_PROVISIONING_ENABLED=false` by default |
| Safe serialization | no subscription URL, raw config, provider payment id, secret or token in `to_safe_dict()` |

## Remnawave Notes

The adapter uses the existing `RemnawaveUserGateway.create()` and `RemnawaveUserGateway.update()` boundaries. It sends:

| CyberVPN field | Remnawave-facing field |
|---|---|
| `email` | `email` |
| `telegram_id` | `telegramId` via gateway normalization |
| `access_expires_at` | `expireAt` via gateway normalization |
| `traffic_limit_bytes` | `trafficLimitBytes` via gateway normalization |
| `traffic_limit_strategy` | `trafficLimitStrategy` |
| `device_limit` | `hwidDeviceLimit` via gateway normalization |

Official documentation checked on 2026-05-04:

- Remnawave API specification: https://docs.rw/api/
- Remnawave Users guide: https://docs.rw/docs/learn-en/users/
- Remnawave HWID device limit: https://docs.rw/docs/features/hwid-device-limit/

Important limitation: local tests prove the CyberVPN contract and adapter payload shape. They do not prove that a real staging/prod Remnawave instance accepts every payload combination, especially unlimited paid traffic represented as `trafficLimitBytes=null`. That remains a staging/prod evidence item.

## Test Evidence

Command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/security/test_stage1_paid_provisioning.py -q --no-cov
```

Result:

```text
collected 16 items
backend/tests/security/test_stage1_paid_provisioning.py ................ [100%]
16 passed in 0.06s
```

## What Was Verified

| Check | Result |
|---|---|
| New paid order creates access from provisioning time | Passed |
| Existing active access is extended from future expiry | Passed |
| Pending/processing/refunded/failed settlement statuses rejected | Passed |
| Draft/cancelled/failed order statuses rejected | Passed |
| Disabled VPN profile rejected | Passed |
| XHTTP S1 alternate profile accepted | Passed |
| Remnawave adapter uses create for new users | Passed |
| Remnawave adapter uses update for existing users | Passed |
| Unlimited traffic intent is preserved as `traffic_limit_bytes=None` in local adapter payload | Passed |
| Safe serialization hides subscription URL/config/provider payment id/secrets/tokens | Passed |
| Contract serializes through local ASGI route | Passed |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| Staging Remnawave paid create user | Open |
| Staging Remnawave paid extend existing user | Open |
| Staging Remnawave unlimited traffic behavior if used | Open |
| Production Remnawave paid low-risk smoke | Open |
| Payment webhook -> paid provisioning integration | Closed locally by `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`; durable/live provider/staging evidence remains open |
| Remnawave outage -> retry queue | Local retry contract completed in `42_STAGE1_VPN_006_PROVISIONING_RETRY_EVIDENCE.md`; durable worker/staging/prod outage evidence remains open |
| Admin/support paid-but-no-access escalation evidence | Open; tied to orphan policy and support/admin work |

## Conclusion

`S1-VPN-005` is locally complete for implementation confidence. It is not a go-live approval for paid VPN access until real staging/prod Remnawave provisioning, provider-paid event integration, retry behavior and support escalation evidence are attached.
