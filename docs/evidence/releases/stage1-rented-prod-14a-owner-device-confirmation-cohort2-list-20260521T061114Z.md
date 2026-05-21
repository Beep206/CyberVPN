# STAGE1-RENT-14A Owner Device Confirmation And Cohort-2 User List

Date: `2026-05-21T06:11:14Z`

Stage: `S1 - Controlled Public Beta`

Scope: owner-device confirmation preflight, Mini App server-side retest, and cohort-2 list gate after `STAGE1-RENT-14`.

Owner: `@Sasha_Beep`

## Result

```text
PASS_SERVER_PROOF_PENDING_OWNER_DEVICE_CONFIRMATION_AND_COHORT2_LIST
```

This step closed the server-side Mini App blocker found during the owner/cohort-2 gate. It does not replace the owner checking the real Telegram Mini App on a real device.

## Current Decision

```text
GO for owner real-device retest.
GO for preparing a 1-3 user cohort-2 trial-only list.
NO-GO for inviting cohort-2 until owner confirms real-device Mini App + VPN client validation.
NO-GO for paid beta.
NO-GO for global public registration.
```

## Blocker Found During 14A

Production Mini App bootstrap still attempted a Remnawave usage lookup by Telegram ID for an already linked owner user.

Observed production symptom:

```text
GET /api/v1/miniapp/bootstrap -> 200 with warning path
Remnawave response validation failed - potential upstream compromise
Failed to fetch user by telegram_id from Remnawave
```

Interpretation:

```text
The owner config path was already valid, but bootstrap usage lookup used the weaker Telegram-ID fallback instead of the local mobile_users.remnawave_uuid bridge.
```

## Hotfix Applied

Changed backend Mini App bootstrap lookup order:

```text
1. Prefer mobile_users.remnawave_uuid.
2. Fall back to telegram_id only when local Remnawave UUID is absent.
```

Files changed:

```text
backend/src/presentation/api/v1/miniapp/routes.py
backend/tests/unit/presentation/api/v1/miniapp/test_routes.py
```

Production deployment:

```text
Source snapshot: /srv/cybervpn/releases/src-stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z/backend
Backend image: cybervpn/cybervpn-backend:stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z
Runtime action: recreated cybervpn-backend only
```

The VPN node was not touched. HTTP/3/QUIC was not disabled.

## Component Checks

Local backend checks:

```text
cd backend && .venv/bin/pytest tests/unit/presentation/api/v1/miniapp/test_routes.py tests/security/test_stage1_trial_provisioning.py -q --no-cov
Result: 29 passed

cd backend && .venv/bin/ruff check src/presentation/api/v1/miniapp/routes.py tests/unit/presentation/api/v1/miniapp/test_routes.py tests/security/test_stage1_trial_provisioning.py
Result: All checks passed
```

Production image build:

```text
docker build cybervpn/cybervpn-backend:stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z
Result: build completed
```

## Production Runtime Checks

Rented production backend:

```text
cybervpn-backend image: cybervpn/cybervpn-backend:stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z
cybervpn-backend state: running healthy
```

Other rented production containers stayed healthy:

```text
admin: running healthy
frontend: running healthy
PostgreSQL: running healthy
PostgreSQL exporter: running healthy
Redis exporter: running healthy
Remnawave: running healthy
Remnawave PostgreSQL: running healthy
Remnawave Valkey: running healthy
scheduler: running healthy
Telegram bot: running healthy
Valkey: running healthy
worker: running healthy
```

HTTP probes:

| Target | Result |
|---|---:|
| `http://127.0.0.1:18080/health` | `ok` |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `200` |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200` |

Production Mini App server-side smoke used a fresh Telegram Mini App initData signature for the existing owner Telegram-linked user. No raw initData, JWT, VLESS link, subscription URL, Telegram bot token or Remnawave token is stored in this evidence.

```json
{
  "auth_status": 200,
  "auth_user_login": "Sasha_Beep",
  "auth_user_email_present": true,
  "bootstrap_status": 200,
  "bootstrap_subscription_status": "trial",
  "bootstrap_usage_unavailable_reason": null,
  "config_status": 200,
  "config_is_found": true,
  "config_source": "remnawave_generated",
  "config_subscription_url_present": true,
  "config_links_count": 2
}
```

Backend logs after the hotfix smoke:

```text
No Remnawave response validation warning.
No Failed to fetch user by telegram_id warning.
No Traceback/ERROR/CRITICAL in the post-deploy sample.
```

Redacted production DB counts:

```text
mobile_users_total=1
telegram_linked_users=1
remnawave_linked_users=1
subscription_url_present=1
payments_total=0
payment_attempts_total=0
```

## Observability Check

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

Home observability host quick health:

```text
/: 10% used
/srv/storage: 1% used
RAM: 17Gi used, 29Gi available
Swap: 899Mi used
Firing alerts: none
```

## Security Review

Checks:

```text
git diff --check
Result: pass

npm audit --audit-level=high
Result: pass for high/critical threshold; 4 pre-existing moderate advisories remain visible

Targeted secret scan over the RENT-14A evidence/doc/backend diff
Result: no matches

Targeted dangerous-pattern scan over changed Mini App backend files
Result: no eval/exec/subprocess/os.system/shell=True matches
```

## Owner Device Confirmation Required

Owner must validate from a real Telegram client and real VPN client:

1. Open `@C_y_b_e_r_VPN_Bot`.
2. Open the Mini App.
3. Confirm Home does not redirect to normal web login.
4. Confirm Profile shows `Sasha_Beep` and the Telegram-local email, not `Guest User`.
5. Confirm Home shows the active trial state.
6. Confirm config/subscription is available.
7. Import/open the config or subscription in a real VPN client.
8. Connect through the production VPN node.
9. Confirm traffic exits through `de-1.cyber-vpn.org`.
10. Report any no-config, failed-connect, language mix, visual regression or support issue before cohort-2 invitations.

## Cohort-2 User List Template

Cohort-2 is limited to 1-3 manually selected trial-only users.

| # | Telegram username or contact | Device/platform | Owner approval | Invite sent | Trial active | Config delivered | Client connected | Support notes |
|---:|---|---|---|---|---|---|---|---|
| 1 | `TBD` | `TBD` | `no` | `no` | `no` | `no` | `no` | `TBD` |
| 2 | `TBD` | `TBD` | `no` | `no` | `no` | `no` | `no` | `TBD` |
| 3 | `TBD` | `TBD` | `no` | `no` | `no` | `no` | `no` | `TBD` |

Allowed scope:

```text
Trial-only.
No paid checkout.
No global registration.
No referrals/promo/gift/add-ons.
No public marketing expansion.
```

Pause rule:

```text
If one cohort-2 user reaches active trial without usable config, pause trial provisioning and investigate before inviting another user.
```

## Recommended Next Stage

```text
STAGE1-RENT-14B: Owner Real-Device Retest And Cohort-2 Invite Execution
```
