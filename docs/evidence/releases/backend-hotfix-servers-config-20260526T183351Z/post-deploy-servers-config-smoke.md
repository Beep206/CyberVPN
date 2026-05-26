# Servers And Config Hotfix Post-Deploy Smoke

Timestamp: `2026-05-26T18:38Z`

Initial runtime tag: `main-a0feffef-servers-config-20260526T183351Z`

## Scope

- Allow authenticated customer web sessions to read the customer-visible server list and server stats.
- Allow authenticated customer web sessions to fetch their own VPN configuration through `/api/v1/subscriptions/config/{user_uuid}`.
- Keep management operations on `/servers` protected by admin permissions.
- Verify production admin 2FA stored secret matches the private owner access file without exposing the secret or current code in evidence.

## Public Customer Endpoint Smoke

Verified through the public `my.cyber-vpn.net` path with a short-lived customer-scope smoke token. Token values were not stored.

```text
200 https://my.cyber-vpn.net/api/v1/servers/ bytes=435
200 https://my.cyber-vpn.net/api/v1/servers/stats bytes=62
200 https://my.cyber-vpn.net/api/v1/subscriptions/config/<current-customer-id> bytes=731
```

## VPN Config Contract

```text
isFound=True
client_config_present=True
subscriptionUrl_present=True
links_count=2
```

## Admin 2FA Check

```text
admin_exists=true
role=super_admin
active=True
totp_enabled=True
secret_present=True
local_secret_matches_stored=True
local_current_code_verifies_stored=True
```

