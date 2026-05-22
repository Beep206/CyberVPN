# S2 Stage 08 Evidence: VPN Provisioning, Protocols, And Capacity

**Stage:** `S2-STAGE-08`
**Date:** 2026-05-22
**Status:** Passed with limits
**Scope:** CyberVPN Public Release 1.0 VPN provisioning and node capacity

---

## 1. Purpose

This evidence closes the S2 VPN provisioning/protocol/capacity gate for a constrained public canary or small invite cohort.

It does not approve unrestricted public opening. The current production VPN estate has one usable node, so the second node remains required before broad public release/marketing scale unless the owner explicitly risk-accepts the single-node SPOF.

---

## 2. Files Changed

| File | Purpose |
|---|---|
| `backend/src/presentation/api/shared/stage2_vpn_provisioning_capacity.py` | New side-effect-free S2 VPN delivery/capacity contract |
| `backend/src/presentation/api/shared/__init__.py` | Exports S2 VPN readiness symbols |
| `backend/tests/security/test_stage2_vpn_provisioning_capacity.py` | Security/product-policy tests for S2 VPN delivery and capacity |
| `docs/cybervpn_stage2_launch_docs/07_STAGE2_VPN_PROVISIONING_CAPACITY.md` | Stage 2 VPN provisioning/capacity specification |
| `docs/plans/2026-05-22-cybervpn-stage2-public-release-master-plan.md` | Marks `S2-STAGE-08` completed with limits |
| `docs/evidence/releases/s2-stage-08-vpn-provisioning-capacity-20260522.md` | This evidence file |

---

## 3. Runtime DNS And Edge Evidence

Command:

```bash
dig +short cyber-vpn.org A
dig +short de-1.cyber-vpn.org A
dig +short de-1.cyber-vpn.org AAAA
dig +short de-1.node.cyber-vpn.org A
dig +short de-1.node.cyber-vpn.org AAAA
```

Observed:

```text
cyber-vpn.org A -> 45.87.41.146
de-1.cyber-vpn.org A -> 77.90.13.29
de-1.cyber-vpn.org AAAA -> 2a0a:51c1:9:c3::a
de-1.node.cyber-vpn.org A -> 77.90.13.29
de-1.node.cyber-vpn.org AAAA -> 2a0a:51c1:9:c3::a
```

Command:

```bash
curl -skI --connect-timeout 8 https://cyber-vpn.org/api/sub/health-smoke
```

Observed:

```text
HTTP/2 404
alt-svc: h3=":443"; ma=2592000
content-type: application/json; charset=utf-8
```

Interpretation:

1. fake subscription token returns Remnawave-style `404`, not a redirect to `.net`;
2. HTTP/3/QUIC advertisement is present and must not be disabled;
3. subscription delivery is on `.org`.

---

## 4. VPN Node Reachability Evidence

Command:

```bash
nc -vz -w 5 de-1.cyber-vpn.org 443
nc -vz -w 5 de-1.cyber-vpn.org 8443
```

Observed:

```text
de-1.cyber-vpn.org:443 reachable
de-1.cyber-vpn.org:8443 reachable
```

---

## 5. Production Runtime Evidence

### 5.1 `prod-app-1`

Observed healthy runtime containers:

| Service | Image family | Status |
|---|---|---|
| frontend | `cybervpn/cybervpn-frontend:stage1-direct-suburl-refresh-20260522T091303Z` | healthy |
| backend | `cybervpn/cybervpn-backend:stage1-direct-suburl-refresh-20260522T091303Z` | healthy |
| Telegram bot | `cybervpn/cybervpn-telegram-bot:stage1-direct-suburl-refresh-20260522T091303Z` | healthy |
| Remnawave | `remnawave/backend:2.7.4` | healthy |
| Remnawave PostgreSQL | `postgres:17.7-alpine` | healthy |
| Remnawave Valkey | `valkey/valkey:8.1-alpine` | healthy |

Backend public health:

```text
https://api.cyber-vpn.net/health -> {"status":"ok"}
```

### 5.2 `prod-vpn-node-1`

Observed runtime:

```text
hostname: de-1.cyber-vpn.org
container: cybervpn-remnawave-node / remnawave/node:2.7.0 / Up 2 days
```

Observed listening ports:

```text
443/tcp
8443/tcp
22230/tcp
61000/tcp on 127.0.0.1
22/tcp
local DNS/chrony system services
```

Node-only policy:

```text
PASS
```

No app/API/admin/payment/support/GitLab/Grafana/Loki/Sentry/Alertmanager/customer-web workload was observed on `prod-vpn-node-1`.

---

## 6. Remnawave Control-Plane Evidence

Redacted internal Remnawave API checks from the backend container:

```json
{
  "nodes": {
    "total": 1,
    "connected": 1,
    "disabled": 0,
    "countries": ["DE"],
    "hosts": ["de-1.cyber-vpn.org"],
    "versions_present": true
  },
  "templates": {
    "total": 6,
    "mihomo_ru_bundle_present": true,
    "template_types": ["CLASH", "MIHOMO", "SINGBOX", "STASH", "XRAY_JSON"]
  },
  "external_squads": {
    "total": 1,
    "ru_bundle_present": true
  }
}
```

Note:

```text
/api/inbounds returned 404 on the current Remnawave production surface.
```

Therefore XHTTP proof for S2 is taken from the actual subscription output and node runtime, not from `/api/inbounds`.

---

## 7. Subscription Output Evidence

Redacted owner/internal checks:

```json
{
  "users_checked": 2,
  "results": [
    {
      "user": "Sasha_Beep_KZ",
      "primary_client_type": "subscription",
      "primary_is_subscription_url": true,
      "contains_raw_primary_vless": false,
      "subscription_url_host": "cyber-vpn.org",
      "link_count": 2,
      "vless_count": 2,
      "raw_or_tcp_count": 1,
      "xhttp_count": 1,
      "reality_count": 2,
      "hosts": ["de-1.cyber-vpn.org"]
    },
    {
      "user": "Sasha_Beep",
      "primary_client_type": "subscription",
      "primary_is_subscription_url": true,
      "contains_raw_primary_vless": false,
      "subscription_url_host": "cyber-vpn.org",
      "link_count": 2,
      "vless_count": 2,
      "raw_or_tcp_count": 1,
      "xhttp_count": 1,
      "reality_count": 2,
      "hosts": ["de-1.cyber-vpn.org"]
    }
  ]
}
```

Interpretation:

1. primary customer config is subscription URL;
2. subscription URL host is `cyber-vpn.org`;
3. primary config is not raw `vless://`;
4. default subscription output contains VLESS Reality RAW/TCP and VLESS Reality XHTTP;
5. all observed node links use `de-1.cyber-vpn.org`.

---

## 8. Local Test Evidence

Command:

```bash
cd backend
uv run ruff check src/presentation/api/shared/__init__.py src/presentation/api/shared/stage2_vpn_provisioning_capacity.py tests/security/test_stage2_vpn_provisioning_capacity.py
uv run pytest tests/security/test_stage2_vpn_provisioning_capacity.py tests/security/test_stage1_vpn_protocols.py tests/security/test_stage1_trial_provisioning.py tests/security/test_stage1_paid_provisioning.py tests/security/test_stage1_admin_manual_subscription_ops.py tests/security/test_stage1_payment_provisioning_failure.py -q --no-cov
```

Result:

```text
All checks passed!
71 passed in 0.32s
```

Additional config-delivery unit checks:

```bash
cd backend
uv run pytest tests/unit/infrastructure/remnawave/test_subscription_urls.py tests/unit/application/use_cases/subscriptions/test_generate_config.py -q --no-cov
```

Result:

```text
9 passed in 0.21s
```

---

## 9. Capacity Decision

Current production VPN estate:

```text
usable connected nodes: 1
node: de-1.cyber-vpn.org / DE
```

Decision:

| Scope | Decision |
|---|---|
| Constrained S2 public canary | GO |
| Small invite/public cohort | GO with close monitoring |
| Unrestricted public opening | NO-GO until second node or explicit owner risk acceptance |
| Full public marketing push | NO-GO until second node |

Planning guardrail:

```text
S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE=25
S2_FULL_PUBLIC_MIN_CONNECTED_NODES=2
```

This is an operational cap, not a public capacity promise.

---

## 10. Security Review

Checked risks:

1. no raw subscription URL/token is stored in evidence;
2. no raw VLESS URI is stored in evidence;
3. Remnawave token was read only inside runtime environment and not printed;
4. primary delivery is subscription URL, not raw proxy URI;
5. node-only policy is preserved;
6. RU bundle applies only to intended hidden RU plans;
7. support recovery steps do not ask for passwords, OTP codes, raw configs or raw subscription tokens.

---

## 11. Remaining Risks

| Risk | Status | Handling |
|---|---|---|
| Single VPN node SPOF | Accepted only for constrained S2 canary | Add second node before unrestricted public opening |
| `/api/inbounds` 404 | Non-blocking for current S2 evidence | Continue using node inventory, hosts/templates and subscription-output proof unless Remnawave endpoint changes |
| Mihomo XHTTP | Remnawave `2.7.4` does not emit XHTTP in Mihomo RU bundle | Do not promise XHTTP in RU Mihomo bundle until upstream/custom renderer proof exists |
| Live paid provisioning proof | Payment/provider work is separate from this stage | Keep payment proof under S2 payment/runtime stages |

---

## 12. Exit Decision

`S2-STAGE-08` is closed with limits:

```text
GO for constrained S2 public canary / small invite cohort.
NO-GO for unrestricted full public opening with only one VPN node.
```

Next stage:

```text
S2-STAGE-09: Support And Admin Operations
```
