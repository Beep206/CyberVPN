# CFLOW-004 Post-Deploy Visibility Smoke

Date: `2026-05-28T14:02:00Z`
Release tag: `cflow-004-20260528T135404Z`
Scope: `backend,frontend`

## Runtime Flags

The production client capability contract was available from both public API routes:

```text
200 https://api.cyber-vpn.net/api/v1/client/capabilities
200 https://my.cyber-vpn.net/api/v1/client/capabilities
```

Relevant capability values:

```json
{
  "growth": {
    "checkout_code_discounts": true,
    "gift_codes": true,
    "growth_hub": true,
    "invites": true,
    "promo_codes": true,
    "referral": true
  },
  "partner": {
    "applications": true,
    "attribution": true,
    "codes": true,
    "event_backbone": true,
    "payouts": true,
    "portal": true,
    "reporting": true,
    "settlement_sandbox": true,
    "storefronts": true,
    "webhooks": true
  },
  "payments": {
    "autorenewal": false,
    "cryptobot": false,
    "manual_invoice": true,
    "telegram_stars": true,
    "web_checkout": false
  },
  "subscriptions": {
    "addons": true,
    "multi_subscription": true,
    "paid_provisioning": false,
    "selected_subscription_required": true,
    "trial": true,
    "upgrade": true
  }
}
```

`paid_provisioning=false`, `web_checkout=false`, and `cryptobot=false` remain intentional until live paid provider evidence is approved.

## Public Route Smoke

```text
200 0.622776 https://api.cyber-vpn.net/healthz
200 0.686040 https://api.cyber-vpn.net/api/v1/client/capabilities
200 0.627862 https://my.cyber-vpn.net/api/v1/client/capabilities
200 0.938791 https://cyber-vpn.net/ru-RU/pricing
200 0.914897 https://my.cyber-vpn.net/ru-RU/dashboard
200 0.966154 https://my.cyber-vpn.net/ru-RU/subscriptions
200 0.968855 https://my.cyber-vpn.net/ru-RU/referral
200 0.872357 https://cyber-vpn.net/ru-RU/miniapp/plans
200 0.817914 https://cyber-vpn.net/ru-RU/miniapp/referral
```

## Visibility Text Smoke

Public pricing HTML contained add-on traffic markers:

```text
30 GB
50 GB
100 GB
gift
```

Web cabinet referral/subscriptions HTML contained enabled growth/add-on surfaces:

```text
Add-ons
Gift
Инвайт
Подарок
Промо
Рефералы
Реферальная
```

Mini App plans/referral HTML contained enabled growth surfaces:

```text
Gift
Инвайт
Инвайты
Подарок
Подарочная
Подарочные
Промо
Реферальная
```

## Runtime Health

Remote compose status after deployment:

```text
cybervpn-backend    cflow-004-20260528T135404Z    healthy
cybervpn-frontend   cflow-004-20260528T135404Z    healthy
cybervpn-nats       nats:2.12.7-alpine            healthy
```

Backend/frontend logs checked for the deployment window: no `traceback`, `exception`, `error`, `critical`, or `failed` entries were found.

