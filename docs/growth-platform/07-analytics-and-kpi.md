# Analytics and KPI

## Analytics Purpose

Analytics must support four outcomes:

- measure acquisition quality;
- measure Mini App conversion;
- measure partner-driven distribution performance;
- prove operational health of public trust surfaces.

## North Star Metrics

### Platform

- paid active customers attributable to the Growth Platform
- partner-attributed recurring revenue
- Mini App paid conversion rate
- public network page to conversion assist rate

## Funnel Families

### Mini App Funnel

Core events:

- `miniapp_opened`
- `miniapp_bootstrap_loaded`
- `miniapp_auth_success`
- `trial_started`
- `checkout_started`
- `miniapp_invoice_opened`
- `payment_success`
- `config_delivered`

Key KPIs:

- open to bootstrap success rate
- bootstrap to trial start rate
- bootstrap to checkout start rate
- checkout start to payment success rate
- payment success to config delivered rate
- median time from open to config delivered

### White-Label Funnel

Core events:

- `partner_application_submitted`
- `partner_application_approved`
- `partner_workspace_created`
- `partner_bot_provisioning_started`
- `partner_bot_active`
- `partner_sale_attributed`
- `partner_payout_requested`

Key KPIs:

- application to approval rate
- approval to active bot rate
- provisioning success rate
- time from approval to first sale
- partner revenue by commercial policy tier

### Network Intelligence Funnel

Core events:

- `network_page_view`
- `public_network_region_clicked`
- `public_network_cta_click`
- `cta_to_miniapp_clicked`
- `widget_loaded`

Key KPIs:

- public page CTR into Mini App
- region detail engagement rate
- widget load volume and source distribution
- conversion assist rate by page and region

## Payment Events

Shared commercial events:

- `checkout_quote_created`
- `invoice_created`
- `invoice_opened`
- `invoice_closed`
- `payment_success`
- `payment_cancelled`
- `payment_failed`
- `refund_requested`
- `refund_completed`

## Retention Metrics

- renewal rate
- subscription expiry recovery rate
- returning Mini App sessions
- device reconfiguration rate
- retention by entry source and partner

## Referral Metrics

- referral shares
- referral opens
- referral-attributed trial starts
- referral-attributed payments
- suspicious referral loop count

## Partner Revenue Metrics

- gross sales by partner
- net payout-ready revenue by partner
- refunds and holds
- active customers per partner
- partner funnel by geography

## Event Payload Requirements

Every event should include:

- `eventName`
- `eventId`
- `occurredAt`
- `surface`
- `locale`
- `userId` or anonymous ID
- `partnerId` if applicable
- `workspaceId` if applicable
- `storefrontId` if applicable
- `botId` if applicable
- `referralCode` if applicable
- `campaign` if applicable
- `requestId` if applicable

## Dashboard Requirements

### Product Dashboard

- Mini App funnel
- network assist funnel
- trial to paid conversion
- revenue by source

### Partner Operations Dashboard

- application queue
- provisioning state distribution
- active bots
- payout queue
- abuse and review flags

### Platform Dashboard

- payment reconciliation health
- snapshot freshness
- tenant isolation alerts
- Stars checkout success rate

## Data Quality Rules

- event names must be stable and versioned if changed;
- payment events must be deduplicated;
- public network metrics must expose freshness;
- partner attribution must not rely on a single client-side signal.
