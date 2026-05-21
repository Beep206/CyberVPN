# STAGE1-RENT-12 - Production Catalog, Support Seed And Beta Expansion Gate

Date: 2026-05-20 18:04:58 UTC

Scope:

- Seed the S1 production subscription catalog on `prod-app-1`.
- Seed the minimum S1 support, storefront, merchant, communication, invoice and billing descriptor records.
- Prove that the public API exposes the approved S1 B2C catalog.
- Re-check the runtime safety gates before expanding the controlled beta.

## Result

```text
PASS_WITH_TRIAL_ONLY_EXPANSION_APPROVED
GO for owner/internal controlled beta expansion with trial/config/support flow.
GO for visible S1 public catalog on web, Telegram Mini App and Telegram Bot surfaces.
NO-GO for public paid beta users until one real payment provider purchase -> webhook -> provisioning -> reconciliation path is proven.
NO-GO for global public registration; invite/manual onboarding remains required.
```

## Production Seed Result

The production pricing seed was applied from the running backend container.

```text
plans_created=28
plans_updated=0
plans_retired=0
addons_created=2
addons_updated=0
```

Database verification:

```text
subscription_plans_total    28
plan_addons_total           2
public_active_plans         16
hidden_active_plans         12
public_plan_matrix basic    4 durations, 30..365 days
public_plan_matrix plus     4 durations, 30..365 days
public_plan_matrix pro      4 durations, 30..365 days
public_plan_matrix max      4 durations, 30..365 days
```

The two add-ons remain present in the catalog database for later phases, but S1 runtime still keeps add-ons disabled with `STAGE1_ADDONS_ENABLED=false`.

## Public Catalog API Evidence

The public plans endpoint returns the approved S1 catalog for all active customer channels:

```text
https://api.cyber-vpn.net/api/v1/plans/?channel=web          count=16
https://api.cyber-vpn.net/api/v1/plans/?channel=miniapp      count=16
https://api.cyber-vpn.net/api/v1/plans/?channel=telegram_bot count=16
```

Visible plan matrix:

| Plan | Durations | Visibility | Active | Sale channels |
|---|---:|---|---|---|
| `basic` | 30, 90, 180, 365 | public | true | web, miniapp, telegram_bot |
| `plus` | 30, 90, 180, 365 | public | true | web, miniapp, telegram_bot |
| `pro` | 30, 90, 180, 365 | public | true | web, miniapp, telegram_bot |
| `max` | 30, 90, 180, 365 | public | true | web, miniapp, telegram_bot |

Frontend route smoke through Cloudflare-proxied user path:

```text
https://cyber-vpn.net/ru-RU/miniapp/plans  HTTP 200
https://cyber-vpn.net/ru-RU/miniapp/home   HTTP 200
https://cyber-vpn.net/pricing              HTTP 307 locale redirect
```

## Support, Merchant And Storefront Seed

Minimum S1 production records are present and active:

```text
support_profile      cybervpn-s1-support        support@cyber-vpn.net    https://cyber-vpn.net/ru-RU/help active
storefront           cybervpn-s1-primary        cyber-vpn.net             CyberVPN Controlled Beta active
merchant_profile     cybervpn-s1-owner          CyberVPN                 CYBERVPN active
invoice_profile      cybervpn-s1-invoice        refund@cyber-vpn.net      active
communication_profile cybervpn-s1-transactional cyber-vpn.net             noreply@cyber-vpn.net active
billing_descriptor   cybervpn-s1-default        CYBERVPN / CYBERVPN S1    active
```

Note: the S1 merchant/legal fields use the already approved project-level CyberVPN placeholder because the owner has closed legal text review as complete for S1. Before paid public release, provider-specific merchant/legal data must be aligned with the actual payment account and seller record.

## Runtime Safety Gates

The running production backend keeps the expected S1 safety flags:

```text
PAYMENTS_ENABLED=false
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=true
STAGE1_ADDONS_ENABLED=false
STAGE1_PAID_PROVISIONING_ENABLED=false
STAGE1_TRIAL_PROVISIONING_ENABLED=true
REGISTRATION_ENABLED=false
REGISTRATION_INVITE_REQUIRED=true
REFERRAL_ENABLED=false
PROMO_CODES_ENABLED=false
GIFT_CODES_ENABLED=false
```

Interpretation:

- Trial provisioning remains allowed.
- Generic/CryptoBot paid checkout remains disabled.
- Telegram Stars remains open only for the Telegram payment surface, but real Stars purchase/provisioning evidence is still missing.
- Add-ons, referrals, promo codes and gift codes remain disabled.
- Global public registration remains paused.

## Observability Gate

Home Prometheus checks after catalog/support seed:

```text
Stage1 firing alerts: 0

blackbox-stage1-public-web:
https://api.cyber-vpn.net/health              probe_success=1
https://admin.cyber-vpn.net/ru-RU/login       probe_success=1
https://cyber-vpn.net/                        probe_success=1
https://www.cyber-vpn.net/                    probe_success=1
https://cyber-vpn.net/en-EN                   probe_success=1
https://cyber-vpn.net/ru-RU/miniapp/home      probe_success=1
https://cyber-vpn.net/ru-RU/miniapp/plans     probe_success=1
https://status.cyber-vpn.net/                 probe_success=1

stage1-vpn-node-tcp:
de-1.cyber-vpn.org:443                        probe_success=1
de-1.cyber-vpn.org:8443                       probe_success=1
```

The VPN node remains node-only. No app, API, admin, support, payment, observability relay or exporter workload was added to `prod-vpn-node-1`.

## Expansion Decision

Approved now:

- owner/internal controlled beta continuation;
- small controlled trial cohort if users are onboarded manually or through an explicitly controlled path;
- user-visible S1 pricing catalog;
- support handling through the S1 support profile and Telegram/support email paths;
- observability/stabilization loop continuation.

Not approved yet:

- public paid beta cohort;
- generic checkout;
- CryptoBot paid checkout;
- public Telegram Stars purchase cohort;
- global public self-registration;
- add-ons, referrals, promo codes, gift codes or checkout discounts.

## Remaining Blockers

1. A real payment path must prove success/failure/duplicate webhook/final-status/reconciliation.
2. A real payment must prove payment -> subscription -> Remnawave provisioning -> config delivery.
3. Telegram Stars must prove real purchase, charge ID handling, `/paysupport`, refund/reconciliation and provisioning before it can be offered beyond controlled owner/internal proof.
4. Invite/manual onboarding must remain the S1 beta control until every public B2C registration surface is invite-controlled.
