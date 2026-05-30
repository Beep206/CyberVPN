# Public Commercial Catalog API

Status: W4 implementation contract for CYBA-163.

The public commercial API exposes read-only context and catalog surfaces under
`/api/v1/catalog`. It does not create payment sessions, activate subscriptions,
or accept client-submitted prices as trusted checkout input.

## Endpoints

- `POST /api/v1/catalog/context`
  - Resolves `uiLocale`, `displayCountry`, `pricingCountry`, `paymentCountry`,
    `currency`, confidence, selectable countries/currencies, payment method
    availability and a cache key.
- `GET /api/v1/catalog`
  - Returns the public plan catalog for `web`, `miniapp`, or `telegram_bot`.
  - Query inputs: `channel`, `country`, `currency`, `uiLocale`, `urlLocale`,
    optional `storefrontKey`.

## Price Safety

Catalog responses include display prices for rendering. Checkout handoff data is
kept separate in each billing period's `quote` object and includes only:

- `planId`
- `planCode`
- `billingPeriodDays`
- `currency`
- `catalogItemKey`
- `contextCacheKey`

Downstream quote and checkout work must re-read backend catalog state by these
identifiers. Clients must not submit `amount`, `price`, or `visiblePrice` as
trusted inputs.

## Visibility Rules

The endpoint applies the Stage 1 public paid plan policy:

- public families: `basic`, `plus`, `pro`, `max`
- public terms: `30`, `90`, `180`, `365` days
- public channels: `web`, `miniapp`, `telegram_bot`

Hidden, inactive, internal, development, test and admin-only plans remain
excluded from this public surface.
