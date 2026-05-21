# STAGE1-RENT-14B Owner Real-Device Retest And Cohort-2 Invite Execution

Date: `2026-05-21T06:20:40Z`

Stage: `S1 - Controlled Public Beta`

Scope: owner real-device confirmation after `STAGE1-RENT-14A`, and gate for cohort-2 trial-only invite execution.

Owner: `@Sasha_Beep`

## Result

```text
PASS_OWNER_REAL_DEVICE_VALIDATION_PENDING_COHORT2_USER_LIST
```

The owner confirmed the full real-device path:

```text
Telegram Bot -> Mini App/config delivery -> VPN client import -> VPN connect -> public exit IP check
```

## Owner Confirmation

Owner-reported validation:

```text
Mini App works.
Config was received in the Telegram Bot/Mini App flow.
Config was added to a VPN client.
VPN client connected successfully.
whoer.net showed public IP: 77.90.13.29.
Country: Germany / FRG.
Host: 29.13.90.77.hostbrr.com.
Provider/ASN label shown by whoer: GHOSTnet.
Proxy: No.
Anonymizer: No.
Blacklist: No.
Masking score: 90%.
```

Interpretation:

```text
The owner/internal S1 trial user can receive a usable VPN config and route traffic through the production VPN node.
```

No raw config URL, VLESS link, subscription URL, Telegram initData, JWT, Remnawave token or provider credential is stored in this evidence.

## Runtime Confirmation

Rented `prod-app-1` containers checked after owner confirmation:

```text
cybervpn-backend: running healthy
cybervpn-frontend: running healthy
cybervpn-remnawave: running healthy
cybervpn-scheduler: running healthy
cybervpn-telegram-bot: running healthy
cybervpn-worker: running healthy
```

Current backend image:

```text
cybervpn/cybervpn-backend:stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z
```

Production VPN node check:

```text
Hostname: de-1.cyber-vpn.org
TCP listeners: 443 and 8443
Remnawave node process: active
```

The VPN node remains node-only. No app/API/admin/payment/support/observability workloads were added to the VPN node.

## Observability Confirmation

Home Prometheus firing alerts:

```text
[]
```

Public endpoint user-path probes:

| Target | `probe_success` |
|---|---:|
| `https://api.cyber-vpn.net/health` | `1` |
| `https://admin.cyber-vpn.net/ru-RU/login` | `1` |
| `https://cyber-vpn.net/` | `1` |
| `https://www.cyber-vpn.net/` | `1` |
| `https://cyber-vpn.net/ru-RU/miniapp/plans` | `1` |
| `https://cyber-vpn.net/en-EN` | `1` |
| `https://status.cyber-vpn.net/` | `1` |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `1` |

VPN node probes:

| Target | `probe_success` |
|---|---:|
| `de-1.cyber-vpn.org:443` | `1` |
| `de-1.cyber-vpn.org:8443` | `1` |

## Current Decision

```text
GO for preparing cohort-2 invite execution.
GO for 1-3 manually selected trial-only users after owner approves the user list.
NO-GO for paid beta users.
NO-GO for public/global registration.
NO-GO for public marketing expansion.
NO-GO for referrals, promo codes, gift codes, add-ons and partner flows.
```

## Cohort-2 User List Required

Before sending invitations, fill and approve this list:

| # | Telegram username or contact | Device/platform | Owner approval | Invite sent | Trial active | Config delivered | Client connected | Support notes |
|---:|---|---|---|---|---|---|---|---|
| 1 | `TBD` | `TBD` | `no` | `no` | `no` | `no` | `no` | `TBD` |
| 2 | `TBD` | `TBD` | `no` | `no` | `no` | `no` | `no` | `TBD` |
| 3 | `TBD` | `TBD` | `no` | `no` | `no` | `no` | `no` | `TBD` |

Allowed cohort-2 flow:

```text
1. Owner names 1-3 users.
2. Keep public registration paused.
3. Invite one user first.
4. Confirm Telegram/Mini App auth.
5. Confirm trial activation.
6. Confirm config delivery.
7. Confirm real client connection.
8. Watch observability and support.
9. Add the next user only if the previous user has no unresolved no-config or failed-connect issue.
```

Pause rule:

```text
If any cohort-2 user reaches active trial without usable config, pause trial provisioning and investigate before inviting another user.
```

## Security Review

Checks:

```text
git diff --check
Result: pass

Targeted secret scan over RENT-14B documentation updates
Result: no matches

npm audit --audit-level=high
Result: pass for high/critical threshold; 4 pre-existing moderate advisories remain visible
```

## Recommended Next Stage

```text
STAGE1-RENT-15: Cohort-2 Trial Invite Execution And Support Watch
```
