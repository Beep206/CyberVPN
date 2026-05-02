# Mini App API Contracts

## Contract Rules

- all endpoints are authenticated via validated Telegram session or active platform session bound to Mini App context;
- all writes must be idempotent where repeated client actions are likely;
- all responses must include machine-readable error codes;
- Telegram digital goods payment flows assume currency `XTR`.

## Endpoint List

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/miniapp/bootstrap` | Consolidated runtime bootstrap |
| GET | `/api/v1/miniapp/dashboard` | Optional dashboard-specific payload |
| GET | `/api/v1/miniapp/servers` | Recommended and manual server options |
| GET | `/api/v1/miniapp/offers` | Plans and add-ons filtered by runtime context |
| POST | `/api/v1/miniapp/trial/activate` | Trial activation |
| POST | `/api/v1/miniapp/checkout/quote` | Quote generation |
| POST | `/api/v1/miniapp/checkout/invoice` | Telegram Stars invoice creation |
| GET | `/api/v1/miniapp/payments/:id/status` | Payment status refresh |
| GET | `/api/v1/miniapp/devices` | Device summary and actions view |
| GET | `/api/v1/miniapp/config` | Config and access delivery read model |
| GET | `/api/v1/miniapp/referral` | Referral share payload and stats |
| POST | `/api/v1/miniapp/referral/share` | Share event capture |
| POST | `/api/v1/miniapp/events` | Telemetry/event ingest |

## `GET /api/v1/miniapp/bootstrap`

### Response

```ts
type MiniAppBootstrapResponse = {
  session: {
    authenticated: boolean
    userId: string | null
    telegramUserId: string | null
    authRealm: 'customer' | 'partner_customer'
  }
  runtime: {
    surface: 'telegram_miniapp' | 'partner_miniapp'
    tenant: {
      kind: 'platform' | 'partner'
      partnerId?: string
      workspaceId?: string
      storefrontId?: string
      botId?: string
    }
    brand: {
      name: string
      logoUrl?: string
      primaryColor?: string
      supportUrl?: string
    }
    attribution: {
      referralCode?: string
      campaign?: string
      startParam?: string
      source?: string
    }
  }
  freshness: {
    generatedAt: string
  }
}
```

### Error Codes

- `miniapp_invalid_session`
- `miniapp_tenant_unavailable`
- `miniapp_bootstrap_unavailable`

## `POST /api/v1/miniapp/trial/activate`

### Request

```json
{
  "idempotencyKey": "uuid"
}
```

### Response

```json
{
  "status": "activated",
  "entitlementId": "uuid",
  "expiresAt": "2026-05-01T00:00:00Z"
}
```

### Error Codes

- `trial_not_eligible`
- `trial_risk_blocked`
- `trial_already_used`

## `POST /api/v1/miniapp/checkout/quote`

### Request

```json
{
  "planId": "uuid",
  "addons": [
    {
      "addonId": "uuid",
      "qty": 1
    }
  ],
  "idempotencyKey": "uuid"
}
```

### Response

```json
{
  "quoteId": "uuid",
  "currency": "XTR",
  "displayedAmount": 499,
  "partnerAttribution": {
    "partnerId": "uuid",
    "botId": "uuid"
  }
}
```

### Error Codes

- `offer_not_available`
- `pricing_policy_rejected`
- `quote_invalid_state`

## `POST /api/v1/miniapp/checkout/invoice`

### Request

```json
{
  "quoteId": "uuid",
  "idempotencyKey": "uuid"
}
```

### Response

```json
{
  "paymentId": "uuid",
  "invoiceUrl": "https://t.me/$invoice/...",
  "currency": "XTR",
  "expiresAt": "2026-04-21T12:00:00Z"
}
```

### Error Codes

- `invoice_creation_failed`
- `quote_expired`
- `payment_method_not_available`

## `GET /api/v1/miniapp/payments/:id/status`

### Response

```json
{
  "paymentId": "uuid",
  "status": "pending",
  "entitlementActivated": false
}
```

### Status Values

- `pending`
- `paid`
- `cancelled`
- `failed`
- `refunded`

## Telegram Payment Contract Notes

- invoice creation is server-side only;
- client-side `invoiceClosed` is not authoritative for fulfillment;
- `pre_checkout_query` validation must occur in the Telegram bot runtime path;
- `successful_payment` is the authoritative event for delivery;
- recurring Stars subscriptions remain a future feature gate until baseline one-time purchase and renewal flows are stable.

## `GET /api/v1/miniapp/servers`

### Response Shape

```ts
type ServerOption = {
  id: string
  countryCode: string
  city: string
  publicName: string
  status: 'online' | 'degraded' | 'offline'
  latencyMs: number | null
  speedMbps: number | null
  uptimePct30d: number | null
  dpiScore?: number | null
  recommendedReason:
    | 'lowest_latency'
    | 'highest_stability'
    | 'best_dpi_resistance'
    | 'partner_default'
    | 'manual'
}
```

## Auth Requirements

- valid Telegram bootstrap session;
- resolved tenant context;
- anti-replay validation for payment and referral actions.

## Rate Limits

- bootstrap: moderate, per session and IP
- trial activation: strict, per user and abuse window
- quote and invoice creation: strict, per user and idempotency key
- event ingest: batched or limited by session

## Idempotency Rules

- trial activation requires idempotency key
- quote creation should support idempotency where same payload repeats
- invoice creation must be idempotent
- share events should deduplicate obvious retries
