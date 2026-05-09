> CyberVPN Launch Program
> Evidence ID: S1-VPN-003
> Date: 2026-05-04
> Status: local contract proof complete; real Remnawave staging/prod profile evidence still required

# S1-VPN-003 Protocol List Evidence

## Purpose

This document closes the local implementation/evidence part of `S1-VPN-003`: define the Stage 1 VPN protocol list for Controlled Public Beta and keep private/experimental transports out of the customer runtime.

It does not close `S1-VPN-001` or `S1-VPN-002`. Real staging and production Remnawave instances still need their own inbound/profile, node, backup and provisioning evidence.

## Decision

Stage 1 uses Remnawave as the authoritative VPN provisioning control-plane. The customer-visible S1 allowlist is deliberately narrow:

| Profile ID | Protocol | Transport/network | Security | Default | Customer-visible | S1 role |
|---|---|---|---|---:|---:|---|
| `vless-reality-raw` | `vless` | `raw` / `tcp` compatibility alias | `reality` | yes | yes | Default compatibility profile for subscription URL, QR and config delivery |
| `vless-reality-xhttp` | `vless` | `xhttp` | `reality` | no | yes | Mandatory alternate S1 profile for supported clients/networks |

The backend treats Xray `tcp` as a compatibility alias for `raw`. Unknown Remnawave/Xray protocol, transport or security values are not provisioned.

## Disabled in S1

These profiles/protocols are explicitly disabled and must not appear as paid/trial provisioning targets or customer-facing choices in S1:

| Profile/protocol | S1 status | Revisit stage |
|---|---|---|
| `wireguard` | disabled | S4 or later with mobile/native readiness |
| `openvpn` | disabled | S5 device expansion if justified |
| `vmess` | disabled | S2+ only if there is a proven need |
| `trojan` | disabled | S2+ only if there is a proven need |
| `shadowsocks` | disabled | S2+ only if there is a proven need |
| `hysteria2` | disabled | S5+ only after support/playbook readiness |
| `tuic` | disabled | S5+ only after support/playbook readiness |
| `helix` | disabled/default-off | S6 private transport beta |
| `verta` | disabled/default-off | S6 private transport beta |
| `beep` | disabled/default-off | S6 private transport beta |

Additional VLESS transports such as `ws`, `grpc`, `kcp` and `httpupgrade` are not S1 customer profiles unless a later decision adds them with tests, guides, support copy and kill switches.

## Implementation Evidence

Code contract:

- `backend/src/presentation/api/shared/stage1_vpn_protocols.py`
- `backend/src/presentation/api/shared/__init__.py`

Tests:

- `backend/tests/security/test_stage1_vpn_protocols.py`

The contract exposes:

- enabled S1 profile list;
- single default profile resolution;
- disabled profile list;
- Remnawave/Xray field mapping from `protocol` + `transport` + `security`;
- safe support/customer summary without subscription URLs, config links, tokens or secrets;
- ASGI serialization proof for a route-shaped response.

## Test Evidence

Targeted command:

```bash
ENVIRONMENT=test SKIP_TEST_DB_BOOTSTRAP=1 DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test REDIS_URL=redis://localhost:6379/15 REMNAWAVE_TOKEN=test-remnawave-token JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough CRYPTOBOT_TOKEN=test-cryptobot-token PYTHONPATH=backend PYENV_VERSION=3.13.11 python -m pytest backend/tests/security/test_stage1_vpn_protocols.py -q --no-cov
```

Result:

```text
29 passed in 0.08s
```

Style command:

```bash
PYENV_VERSION=3.13.11 python -m ruff check backend/src/presentation/api/shared/stage1_vpn_protocols.py backend/src/presentation/api/shared/__init__.py backend/tests/security/test_stage1_vpn_protocols.py
```

Result:

```text
All checks passed!
```

Broader S1 backend regression pack:

```text
243 passed in 12.58s
```

## Source Notes

The local decision is aligned with official docs used as references:

- Remnawave Config Profiles: `https://docs.rw/docs/learn-en/config-profiles/`
- Xray transport configuration: `https://xtls.github.io/en/config/transport.html`

Remnawave Config Profiles are Xray-core configuration templates for Nodes, including inbounds and node assignment. Xray transport docs define `streamSettings.network` values including `raw`, `xhttp`, `kcp`, `grpc`, `ws`, `httpupgrade` and note that `tcp` is a compatibility alias for `raw`.

## Remaining Work Before Real Beta

This task permits implementation of mock/local provisioning logic, but go-live remains blocked until:

1. staging Remnawave has the approved profiles/inbounds configured and evidenced;
2. production Remnawave has the approved profiles/inbounds configured and evidenced;
3. trial provisioning creates access using the allowlisted profile only;
4. paid provisioning creates or extends access using the allowlisted profile only;
5. Remnawave outage/retry behavior is tested;
6. QR/subscription URL/config delivery is sanitized in logs and support tooling;
7. user setup guides reference only the approved S1 profiles.

## 2026-05-09 Ordered Batch Revalidation

`S1-VPN-003` was re-run as item 15 in the owner-requested ordered batch.

Verification:

```text
cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_vpn_protocols.py -q --no-cov
Result: 29 passed in 0.10s

PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_vpn_protocols.py src/presentation/api/shared/__init__.py tests/security/test_stage1_vpn_protocols.py
Result: All checks passed
```

The local protocol allowlist remains accepted: `vless-reality-raw` is the default S1 profile, `vless-reality-xhttp` is the alternate S1 profile, and non-S1/private transports remain disabled. Real staging/prod Remnawave profile/inbound/node evidence remains open.
