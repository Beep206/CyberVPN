# Mobile Commercial Integration

Status: CYBA-177 read-only mobile integration notes.

## Public Catalog

Mobile reads the backend-owned public commercial catalog from
`/api/v1/catalog/` and maps billing periods into `PlanEntity` for display.
The mobile request uses `channel=web` because the current backend public
catalog policy exposes only `web`, `miniapp`, and `telegram_bot`; no native
mobile sale channel is active in the contract yet.

## Price Safety

The app displays `displayPrice` from the catalog but does not submit price,
amount, or visible-price fields as trusted checkout inputs. Quote identifiers
remain backend-owned in the catalog response. This heartbeat did not change the
purchase/session creation flow.

## IAP State

RevenueCat restore plumbing exists in the app, but the public catalog
integration does not create store products, activate native IAP storefront
logic, or change purchase behavior. `iapStorefrontActive` is therefore
documented as `false` for this read-only integration.

## Guardrails

No production payment data, production secrets, production deploy, native
signing, Remnawave production config, or real customer accounts are required for
this integration.
