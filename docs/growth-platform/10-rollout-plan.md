# Rollout Plan

## Rollout Principle

Release the platform in controlled stages. Keep the architecture complete, but gate exposure aggressively.

## Stage 1 — Internal Alpha

### Scope

- CyberVPN Mini App only
- no partner bots in public use
- public network pages behind feature flags or internal access

### Exit Criteria

- payment flow passes end-to-end
- config delivery works
- no critical security defects
- bootstrap latency is acceptable
- operator refund and suspend actions are available for internal testing

## Stage 2 — Controlled Beta

### Scope

- public network overview and status visible
- Mini App available to controlled user cohorts
- White-Label provisioning allowed only for a small trusted set
- manual fallback allowed for partner bot onboarding

### Exit Criteria

- provisioning success rate above target threshold
- payment reconciliation stable
- no tenant leakage
- public snapshot freshness alerts stable
- payout hold and release controls available

## Stage 3 — Closed Partner Beta

### Scope

- 3 to 5 trusted partners
- branded Mini App previews
- partner analytics and payout requests visible
- public Speed Map available

### Exit Criteria

- partner launch path works without code or ENV changes
- moderation workflow operational
- no critical partner abuse incidents
- immutable settlement ledger and reversal path validated

## Stage 4 — Public Launch

### Scope

- CyberVPN Mini App fully public
- public network pages and status pages indexed
- White-Label application flow public
- partner widget pilot enabled

### Exit Criteria

- on-call playbooks ready
- support routing in place
- dashboards and alerts cover payment, provisioning, and snapshot freshness

## Feature Flags

- `miniapp_enabled`
- `miniapp_stars_checkout_enabled`
- `public_network_enabled`
- `public_network_dpi_enabled`
- `partner_portal_self_service_enabled`
- `partner_branded_miniapp_enabled`
- `partner_widget_enabled`

## Rollback Plan

### Mini App

- disable purchase actions;
- keep read-only account state if needed;
- fall back to support and renewal messaging.

### White-Label

- stop new applications or provisioning;
- suspend affected partner runtime;
- preserve existing customer access while blocking new checkout if required.

### Network Intelligence

- switch affected pages to stale or degraded state;
- hide unsupported modules such as DPI score or widgets;
- maintain truthful status banner.

## Monitoring Checklist

- payment success and failure rates
- entitlement creation correctness
- provisioning queue state
- snapshot freshness
- public API cache and error rate
- partner tenant isolation alerts
- refund and settlement ledger anomalies
- operator action audit completeness

## Incident Response

- define severity levels by surface;
- identify owner rotation per stage;
- route payment incidents differently from public-data incidents;
- include emergency suspend for partner runtime.

## Launch Checklist

- ADRs accepted
- feature flags configured
- support copy available
- dashboards visible
- rollback rehearsed
- legal and product copy reviewed
