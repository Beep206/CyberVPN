# Customer Growth Notification Delivery Runbook

This runbook covers the repaired customer growth notification lifecycle:

- customer delivery preferences
- customer troubleshooting and guided repair
- support escalation and admin resolution
- automatic recovery after preferences, contact data, or Telegram link changes
- delivery forensics and rollout evidence

## Primary Dashboard

Use Grafana dashboard `customer-growth-notification-delivery`.

Primary signals:
- support escalations in the last 24 hours
- customer recovery requests in the last 24 hours
- repairs completed in the last 24 hours
- deliveries recovered in the last 24 hours
- unresolved backlog delta in the last 24 hours
- recovery ratio in the last 24 hours

## Alert Triage Order

1. `CustomerGrowthNotificationUnresolvedBacklogHigh`
Check whether escalations are accumulating faster than repair or support resolution. Review blocked `email` and `telegram` deliveries first, then inspect `paused` or `revoked` admin actions.

2. `CustomerGrowthNotificationRecoveryRatioLow`
Check whether the repaired delivery flow is closing enough of the escalations it receives. Validate recent `preferences_reenabled`, `contact_data_corrected`, `telegram_linked`, and `support_resolved` transitions before widening rollout.

## Immediate Checks

Run:

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=sum(customer_growth:notification_support_escalations:increase24h)'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=sum(customer_growth:notification_repairs_completed:increase24h)'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=sum(customer_growth:notification_support_resolutions:increase24h)'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=sum(customer_growth:notification_deliveries_recovered:increase24h)'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=sum(customer_growth:notification_unresolved_backlog_delta:24h)'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=avg(customer_growth:notification_recovery_ratio:24h)'
```

Check:
- whether failures are isolated to `email`, `telegram`, or operator-controlled `in_app` closure notices
- whether recent customer repairs are being replayed automatically
- whether admin pause or revoke actions are leaving issues stranded
- whether support resolved a delivery without a resulting `delivery_recovered` event

## Conformance Gate

Run:

```bash
npm run conformance:customer-growth-notifications
```

This conformance verifies:
- repaired customer flows for `preferences_reenabled`, `contact_data_corrected`, and `telegram_linked`
- admin resolution flow for `support_resolved`
- customer and admin API contracts remain in sync with OpenAPI and generated types
- rollout assets remain present and valid

## Rollout Evidence

Initialize a proof pack:

```bash
npm run evidence:customer-growth-notifications:init -- 2026-04-22 staging growth-notification-rollout-run01 R2 "pending owner"
```

Use template:
- `docs/evidence/customer-growth/templates/customer-growth-notification-rollout-evidence-template.md`
- `docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_STAGING_ROLLOUT_RUNBOOK.md`

Capture:
- conformance logs
- admin delivery detail export for recovered and unresolved examples
- customer troubleshooting screenshots from rewards hub or miniapp
- dashboard screenshots for unresolved backlog and recovery ratio
- final rollout decision and divergence register

## Rollout Checklist

Before enabling the repaired lifecycle on a live environment:

- customer growth notification conformance workflow is green
- OpenAPI and generated frontend/admin types are in sync
- dashboard `customer-growth-notification-delivery` is available
- alerts `CustomerGrowthNotificationUnresolvedBacklogHigh` and `CustomerGrowthNotificationRecoveryRatioLow` are loaded
- `npm run staging:customer-growth-notifications:smoke` passes against the active staging window
- at least one recovered case and one support-resolved case are exported into the evidence pack
- rollback owner and support owner are online for the rollout window

## Escalation

- `warning` alerts: backend owner + customer growth owner + support operations
- if unresolved backlog keeps growing for the full rollout window: pause further rollout, capture evidence, and keep the repaired lifecycle behind the current ring

Do not widen customer-growth notification rollout without an evidence pack showing both recovered and support-resolved examples.

## Governance Gate

Required CI gate:

- `All Customer Growth Notification Checks Passed`

Companion governance docs:

- `docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_GITHUB_PROTECTION_HANDOFF.md`
- `docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_STAGING_ROLLOUT_RUNBOOK.md`
