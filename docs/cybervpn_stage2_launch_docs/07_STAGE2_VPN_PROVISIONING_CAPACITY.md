# Stage 2 VPN Provisioning, Protocols, And Capacity

**Stage:** `S2-STAGE-08`
**Status:** Approved with limits
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 VPN access contract before support/admin operations.

S2 can proceed only if the customer receives a working subscription URL and the operator can prove what protocols, node surface and capacity posture are actually available.

---

## 2. Hard Rules

| Rule | S2 decision |
|---|---|
| Subscription URL domain | Must use `cyber-vpn.org` |
| Subscription URL path | Must use `/api/sub/...` |
| Primary customer config | Must be HTTPS subscription URL, not raw `vless://` |
| Node hostname | Must be `.org`, currently `de-1.cyber-vpn.org` |
| Node role | VPN node only; no app/API/admin/support/payment/observability workloads |
| Required protocols | VLESS Reality RAW/TCP and VLESS Reality XHTTP |
| RU bundle | `Mihomo (RU bundle)` only for `ru_start` / `ru_basic` |

---

## 3. Backend Contract

S2 now has a side-effect-free VPN readiness helper:

```text
backend/src/presentation/api/shared/stage2_vpn_provisioning_capacity.py
```

It evaluates:

1. subscription URL delivery;
2. raw `vless://` primary-config regression;
3. VLESS Reality RAW/TCP presence;
4. VLESS Reality XHTTP presence;
5. `.org` node hostnames;
6. node-only runtime policy;
7. canary/full-public capacity decision;
8. RU Mihomo bundle gating;
9. support reprovisioning steps.

---

## 4. Current Runtime Evidence Summary

| Check | Result |
|---|---|
| `cyber-vpn.org/api/sub/...` route | Reaches Remnawave-style subscription route; fake token returns 404, not redirect |
| HTTP/3/QUIC posture | `alt-svc: h3=":443"` advertised; do not disable HTTP/3/QUIC |
| `de-1.cyber-vpn.org:443` | Reachable |
| `de-1.cyber-vpn.org:8443` | Reachable |
| Remnawave control-plane | Production container healthy |
| Remnawave node inventory | 1 connected node, country `DE`, host `de-1.cyber-vpn.org` |
| Production node runtime | `cybervpn-remnawave-node` only; no app/API/admin/observability workload |
| Subscription templates | `Mihomo (RU bundle)` present |
| External squad | `S1_RU_BUNDLE` present |
| Owner/internal config delivery | Primary config is subscription URL on `cyber-vpn.org`; raw primary `vless://` is false |
| Subscription output | 2 VLESS Reality links; 1 RAW/TCP and 1 XHTTP |

Detailed evidence:

```text
docs/evidence/releases/s2-stage-08-vpn-provisioning-capacity-20260522.md
```

---

## 5. Current Capacity Decision

S2 has exactly one usable production VPN node:

```text
prod-vpn-node-1 / de-1.cyber-vpn.org / DE
```

Decision:

| Scope | Decision | Reason |
|---|---|---|
| S2 constrained public canary | Allowed |
| S2 small invite/public cohort | Allowed with monitoring |
| Unrestricted public opening | Not allowed yet |
| Full marketing push | Not allowed yet |
| Second VPN node | Required before unrestricted public opening |

Conservative planning default:

```text
S2_PUBLIC_CANARY_USERS_PER_CONNECTED_NODE=25
S2_FULL_PUBLIC_MIN_CONNECTED_NODES=2
```

This is not a marketing promise. It is an operational guardrail for the first public-release stage.

---

## 6. When To Add The Second Node

Add `prod-vpn-node-2` before unrestricted public opening, and earlier if any condition appears:

1. beta cohort exceeds 25 active users;
2. node CPU or memory is consistently high;
3. transport errors or support tickets increase;
4. one provider/location becomes a single business risk;
5. paid traffic grows beyond owner-approved risk tolerance;
6. user geography requires another location;
7. maintenance cannot be done without interrupting all users.

Recommended next node:

```text
eu-2.cyber-vpn.org or nl-1.cyber-vpn.org
```

The exact country/provider should be decided from S2 cohort geography and abuse/provider stability.

---

## 7. RU Mihomo Bundle Rule

Only these plan codes may receive the RU Mihomo bundle:

```text
ru_start
ru_basic
```

Non-RU plans must not receive:

```text
Mihomo (RU bundle)
S1_RU_BUNDLE external squad
```

Known limitation remains:

Remnawave `2.7.4` default/base64 subscription output includes XHTTP, but Remnawave Mihomo/Clash generation does not emit XHTTP in the RU bundle without upstream/custom renderer support. Therefore S2 must not promise XHTTP inside Mihomo RU bundle until that renderer proof exists.

---

## 8. Support Reprovisioning Steps

Support/ops may follow this safe order:

```text
check_customer_lifecycle_state
confirm_payment_or_trial_entitlement
confirm_remnawave_uuid_exists
check_subscription_url_uses_cyber_vpn_org
check_provisioning_retry_job_state
retry_or_recreate_remnawave_user_if_authorized
refresh_stored_subscription_url
ask_user_to_refresh_mini_app_or_bot_config
escalate_to_ops_if_node_or_remnawave_unavailable
```

Support must not ask users to paste raw configs, raw subscription URLs, OTP codes, passwords, refresh tokens or Telegram init data into tickets/chats unless an approved redaction path exists.

---

## 9. No-Go Conditions

Do not widen S2 if any condition is true:

1. primary config delivery regresses to raw `vless://`;
2. subscription URL uses `.net` or any non-`.org` customer URL;
3. XHTTP disappears from default subscription output while public copy still promises it;
4. `prod-vpn-node-1` runs app/API/admin/payment/support/observability workloads;
5. Remnawave node inventory has zero connected nodes;
6. subscription route redirects to customer web instead of Remnawave subscription surface;
7. RU bundle applies to non-RU plans;
8. support cannot retry/recreate/reconcile provisioning failures safely;
9. owner wants unrestricted public opening while only one VPN node exists.

---

## 10. Exit Decision

`S2-STAGE-08` is closed for constrained S2 public canary / small invite cohort.

It is not closed for unrestricted full public opening. Before that, add at least one more production VPN node or owner must explicitly risk-accept the single-node SPOF.
