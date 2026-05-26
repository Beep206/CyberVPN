# Cabinet API Hotfix Post-Deploy Smoke

Timestamp: `2026-05-26T18:15Z`

Runtime tag: `main-a1610ea2-cabinet-api-20260526T180345Z`

## Scope

- Customer web cookie realm for cabinet profile, usage, notifications and anti-phishing endpoints.
- Slash and non-slash pricing catalog route compatibility.
- Settings links that previously triggered cross-origin RSC preflight from `my.cyber-vpn.net` to `cyber-vpn.net`.
- Remnawave invite provisioning when Remnawave returns an existing Telegram user as a one-item list.

## Public Endpoint Smoke

Verified through the public `my.cyber-vpn.net` path with a short-lived customer-scope smoke token. Token values were not stored.

```text
200 https://my.cyber-vpn.net/api/v1/users/me/profile bytes=195
200 https://my.cyber-vpn.net/api/v1/users/me/usage bytes=362
200 https://my.cyber-vpn.net/api/v1/security/antiphishing bytes=13
200 https://my.cyber-vpn.net/api/v1/users/me/notifications bytes=115
200 https://my.cyber-vpn.net/api/v1/plans?channel=web bytes=12932
```

## Local Origin Contract Smoke

Verified against the backend origin with `Host: my.cyber-vpn.net`.

```text
200 /api/v1/users/me/profile bytes=195
200 /api/v1/users/me/usage bytes=362
200 /api/v1/security/antiphishing bytes=13
200 /api/v1/users/me/notifications bytes=115
200 /api/v1/plans?channel=web bytes=12932
200 /api/v1/plans/?channel=web bytes=12932
```

## Invite Provisioning Repair

The failed invite redemption for the internal Telegram beta user had already created the entitlement grant before Remnawave provisioning failed. After the code fix, the existing Remnawave user was reused and updated instead of creating a duplicate.

```text
status=repaired
telegram_user=internal_beta_user
created=False
remnawave_user=existing
upstream_status=active
traffic_limit_bytes=2147483648
subscription_url_set=True
```

