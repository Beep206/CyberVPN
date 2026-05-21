# STAGE1-RENT-14 Owner Device Validation And Cohort-2 Trial Expansion

Date: `2026-05-20T19:12:26Z`

Stage: `S1 - Controlled Public Beta`

Scope: preflight for owner device validation and very small cohort-2 trial-only expansion after `STAGE1-RENT-13`.

Owner: `@Sasha_Beep`

## Result

```text
PASS_PREFLIGHT_PENDING_OWNER_DEVICE_CONFIRMATION
```

RENT-14 cannot be fully closed by server-side automation because the first acceptance item is real owner-device validation inside Telegram/Mini App and a real user VPN client.

## Current Decision

```text
GO for owner device validation.
GO for preparing cohort-2 trial-only expansion.
NO-GO for inviting cohort-2 until owner device validation is confirmed.
NO-GO for paid beta.
NO-GO for global public registration.
```

## Production Runtime Preflight

All rented `prod-app-1` Stage 1 containers are running and healthy:

- admin;
- backend;
- frontend;
- PostgreSQL;
- PostgreSQL exporter;
- Redis exporter;
- Remnawave;
- Remnawave PostgreSQL;
- Remnawave Valkey;
- scheduler;
- Telegram bot;
- Valkey;
- worker.

Public probes from `prod-app-1`:

| Target | Result |
|---|---:|
| `https://api.cyber-vpn.net/health` | `200` |
| `https://api.cyber-vpn.net/api/v1/plans/?channel=miniapp` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `200` |
| `https://cyber-vpn.net/ru-RU/miniapp/plans` | `200` |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200` |

Edge:

```text
HTTP/3/QUIC preserved.
UDP 443 and TCP 443 are published by Caddy.
```

## Runtime Gates

Backend runtime flags:

```text
payments_enabled=False
cryptobot_enabled=None
telegram_stars_enabled=True
stage1_addons_enabled=False
stage1_paid_provisioning_enabled=False
stage1_trial_provisioning_enabled=True
registration_enabled=False
registration_invite_required=True
referral_enabled=False
promo_codes_enabled=False
gift_codes_enabled=False
```

Interpretation:

```text
Trial-only cohort can continue.
Paid/growth/global registration expansion remains blocked.
```

## Owner Trial State

Redacted production DB counts:

```text
mobile_users_total=1
trial_active_users=1
trial_expired_users=0
remnawave_linked_users=1
subscription_url_present=1
payments_total=0
```

Protected Telegram Bot config endpoint:

```json
{
  "http_code": 200,
  "client_type": "vless",
  "config_present": true,
  "config_length": 267
}
```

No raw Telegram ID, config URL, VLESS link, JWT, Remnawave token or provider secret is stored in this evidence.

## Observability Preflight

Home Prometheus firing alerts after swap tuning:

```text
none
```

Stage 1-specific firing alert count:

```text
0
```

Public endpoint probes:

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

Home ops health:

```text
GitLab /users/sign_in: HTTP 200
cybervpn-gitlab: healthy
Swap used: 883Mi
Firing alerts: none
```

## Owner Device Validation Checklist

Owner must validate from Telegram on a real device:

1. Open `@C_y_b_e_r_VPN_Bot`.
2. Open the Mini App menu.
3. Confirm Home does not redirect to normal web login.
4. Confirm Profile shows the Telegram-linked user, not `Guest User`.
5. Confirm Home shows active trial or trial-ready state consistently.
6. Confirm config is available from Home/Profile.
7. Import or open the VPN config/subscription in a real client.
8. Connect through the client.
9. Confirm traffic exits through the production VPN node.
10. Report any no-config, failed-connect, language mix, visual regression or support issue before adding cohort-2 users.

## Cohort-2 Expansion Gate

Cohort-2 may start only after owner confirms device validation.

Allowed cohort-2 scope:

```text
1-3 manually selected trial-only users.
No paid checkout.
No global registration.
No referrals/promo/gift/add-ons.
No public marketing expansion.
```

Monitoring during cohort-2:

- Telegram Bot and Mini App auth/config errors;
- backend errors;
- worker/scheduler failures;
- Remnawave provisioning failures;
- VPN node TCP probes;
- public endpoint probes;
- Sentry/Loki new error patterns;
- support contacts;
- any no-config or failed-connect case.

Pause rule:

```text
If one user reaches active trial without usable config, pause trial provisioning and investigate before adding another user.
```

## Recommended Next Stage

```text
STAGE1-RENT-14A: Owner Device Confirmation And Cohort-2 User List
```
