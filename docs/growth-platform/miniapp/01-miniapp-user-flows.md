# Mini App User Flows

## Flow: First Open

### Entry Point

`https://t.me/<bot>?startapp=<payload>`

### Steps

1. User opens Telegram Mini App.
2. Frontend reads Telegram runtime and raw init data.
3. Frontend sends raw init data to backend.
4. Backend validates Telegram identity.
5. Backend resolves runtime commercial context.
6. Backend returns bootstrap payload.
7. User sees primary CTA based on subscription or trial status.

### Failure Cases

- invalid or expired init data;
- partner bot suspended;
- stale or failed bootstrap;
- unsupported locale or missing runtime context.

## Flow: Auth and Bootstrap

1. Mini App loads runtime provider.
2. Backend validates identity and session linkage.
3. Backend returns authenticated bootstrap payload.
4. Frontend renders home state without leaving `/miniapp/*`.

Failure cases:

- validation failure;
- session mismatch;
- 2FA-required edge case that must still preserve Mini App return path.

## Flow: Trial Activation

1. User sees `start_trial` CTA.
2. Frontend calls `POST /api/v1/miniapp/trial/activate`.
3. Backend checks trial eligibility and abuse signals.
4. Backend creates trial entitlement or rejects with reason.
5. Frontend refreshes bootstrap and navigates to config or server selection.

Failure cases:

- trial not eligible;
- suspicious user state;
- missing tenant policy;
- concurrency or duplicate request.

## Flow: Plan Selection

1. User opens plans screen.
2. Frontend loads offers and plan presentation for current tenant.
3. User selects plan and optional add-ons.
4. Frontend creates quote request.

Failure cases:

- plan hidden by commercial policy;
- offer expired;
- unsupported combination of plan and add-on.

## Flow: Stars Checkout

1. Frontend calls quote endpoint.
2. Backend validates catalog, pricing, partner attribution, and eligibility.
3. Frontend requests invoice creation.
4. Backend creates Telegram Stars invoice.
5. Frontend calls `Telegram.WebApp.openInvoice`.
6. Telegram closes invoice UI.
7. Frontend refreshes payment status from backend.
8. Backend grants entitlement only after authoritative successful payment.

Failure cases:

- invoice creation failure;
- user cancels invoice;
- payment pending or delayed;
- duplicate webhook or late confirmation.

## Flow: Payment Success

1. Payment success reaches backend.
2. Backend creates or updates order and entitlement.
3. Backend updates payment record and attribution state.
4. Frontend refreshes bootstrap or payment status.
5. User sees config delivery CTA.

## Flow: Payment Cancelled

1. Invoice closes without success.
2. Frontend refreshes payment state.
3. UI shows canceled or pending state.
4. User can retry or choose different plan.

## Flow: Config Delivery

1. User opens config or devices screen.
2. Backend returns tenant-aware service access state.
3. User sees QR, deep links, copy URLs, or device actions.
4. Action is logged as `config_delivered`.

Failure cases:

- no entitlement;
- config generation failure;
- service state degraded;
- device limit reached.

## Flow: Server Selection

1. User opens servers screen.
2. Frontend loads recommended and manual server list from Mini App API.
3. User selects server.
4. Selection updates recommendation state or config context.

Failure cases:

- no available regions;
- stale network intelligence data;
- selected server offline by time of action.

## Flow: Device Management

1. User opens devices screen.
2. Frontend loads active devices and limits.
3. User can inspect, revoke, or create device-specific access.
4. Backend enforces entitlement device rules.

## Flow: Referral Sharing

1. User opens referral screen.
2. Frontend loads signed share payload and share text.
3. User shares via Telegram-native path.
4. Attribution is preserved in `startapp` payload.

Failure cases:

- expired signed payload;
- abuse threshold reached;
- partner campaign disabled.

## Flow: Support

1. User opens support.
2. Frontend shows support routes from runtime context.
3. User can access general support or payment support.

## Flow: Expired Subscription Renewal

1. Bootstrap shows `renew` CTA.
2. User enters plans or checkout.
3. Renewal follows the same quote and invoice flow with current attribution rules.

## Flow: Partner-Branded Entry

1. User opens partner-managed Telegram entry point.
2. Backend resolves partner tenant context.
3. Brand theme, support, and commercial policy are applied.
4. Purchase still flows through shared payment and entitlement core.
