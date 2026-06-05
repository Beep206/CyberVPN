# CYBA-489 Local-Stage Revalidation

Дата проверки: 2026-06-05T05:23:30.488Z

Target: `http://127.0.0.1:18080`
Frontend Origin/Referer: `http://127.0.0.1:13000`
Credential source: protected local secret file key group CYBA451_CUSTOMER_WEB_*

## Summary

- Login/session: 200/200.
- CSRF-sensitive POST with approved Origin reached non-CSRF layer: quote=true, service-state=true, refresh=true.
- Passkey policy with Origin cleared: true.
- Remaining blockers: miniapp_config_missing_subscription_fixture, no_active_trial_expired_subscription_rows, no_non_empty_wallet_transaction_rows, no_non_empty_payment_history_rows.
- Secret value hits in JSON artifact: 0 (credential/token-like scope; *_ROLE and *_REALM excluded).

## Probe Matrix

| Probe | HTTP | Sanitized shape |
|---|---:|---|
| `GET /health` | 200 | {"type":"object","keys":["status"],"status":"ok"} |
| `GET /api/v1/status` | 200 | {"type":"object","keys":["services","status","timestamp","version"],"status":"ok"} |
| `POST /api/v1/auth/login` | 200 | {"type":"object","keys":["audience","auth_realm_id","auth_realm_key","principal_type","requires_2fa","scope_family","tfa_token"],"auth_realm_key":"customer","principal_type":"customer","scope_family":"customer","requires |
| `GET /api/v1/auth/session` | 200 | {"type":"object","keys":["audience","auth_realm_id","auth_realm_key","created_at","current_sign_in_ip","email","id","is_active","is_email_verified","last_login_at","login","principal_type","role","scope_family","sign_in_ |
| `GET /api/v1/auth/devices` | 200 | {"type":"object","keys":["devices","total"],"devices_length":37} |
| `GET /api/v1/subscriptions/active` | 200 | {"type":"object","keys":["auto_renew","expires_at","plan_name","status","traffic_limit_bytes","used_traffic_bytes"],"status":"none"} |
| `GET /api/v1/wallet` | 200 | {"type":"object","keys":["balance","currency","frozen","id"],"currency":"USD","frozen":0,"balance_present":true} |
| `GET /api/v1/wallet/transactions` | 200 | {"type":"array","length":0,"firstKeys":[]} |
| `GET /api/v1/payments/history` | 200 | {"type":"object","keys":["payments"],"payments_length":0} |
| `GET /api/v1/referral/status` | 200 | {"type":"object","keys":["commission_rate","enabled","friend_discount_pct","reward_hold_days"],"enabled":false} |
| `GET /api/v1/miniapp/bootstrap` | 200 | {"type":"object","keys":["devices","featureFlags","freshness","payment","primaryCta","recommendedServer","referral","rollout","runtime","serviceState","session","subscription","support","trial","usage","user","wallet"]} |
| `GET /api/v1/miniapp/config` | 404 | {"type":"object","keys":["detail"],"detail":"Subscription config not found"} |
| `GET /api/v1/entitlements/current` | 200 | {"type":"object","keys":["addons","display_name","effective_entitlements","expires_at","invite_bundle","is_trial","period_days","plan_code","plan_uuid","status"],"status":"none","addons_length":0} |
| `GET /api/v1/customer-subscriptions/` | 200 | {"type":"object","keys":["auth_realm_id","customer_account_id","default_subscription_key","items","limitations","selected_subscription_key"],"items_length":0} |
| `GET /api/v1/client/capabilities` | 200 | {"type":"object","keys":["auth","growth","partner","payments","subscriptions"]} |
| `GET /api/v1/auth/passkeys/policy with Origin` | 200 | {"type":"object","keys":["adminCountsAsMfa","allowedOrigins","authenticationEnabled","browserTimeoutMs","challengeTtlSeconds","conditionalUiEnabled","configuredEnabled","enabled","freshAuthTtlSeconds","globalEnabled","po |
| `GET /api/v1/auth/passkeys/policy without Origin` | 403 | {"type":"object","keys":["detail"],"detail":"Passkey origin is required"} |
| `GET /api/v1/plans/` | 200 | {"type":"array","length":16,"firstKeys":["catalog_visibility","connection_modes","dedicated_ip","devices_included","display_name","duration_days","features","invite_bundle","is_active","name","plan_code","price_rub","pri |
| `POST /api/v1/payments/checkout/quote with Origin` | 200 | {"type":"object","keys":["addon_amount","addons","base_price","code_input","code_resolution","discount_amount","discounts","displayed_price","entitlements_snapshot","gateway_amount","is_zero_gateway","partner_code_id","p |
| `POST /api/v1/access-delivery-channels/current/service-state with Origin` | 200 | {"type":"object","keys":["access_delivery_channel","auth_realm_id","consumption_context","customer_account_id","device_credential","entitlement_snapshot","provider_name","provisioning_profile","purchase_context","service |
| `POST /api/v1/auth/refresh with Origin` | 200 | {"type":"object","keys":["access_token","audience","auth_realm_id","auth_realm_key","expires_in","principal_type","refresh_token","scope_family","token_type"],"auth_realm_key":"customer","principal_type":"customer","scop |

## Handling

No credential, JWT, cookie, config link, subscription URL, payment provider secret, device credential, or raw Telegram initData values are stored in this artifact.
