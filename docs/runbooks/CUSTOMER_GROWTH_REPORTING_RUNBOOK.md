# Customer Growth Reporting Runbook

## Scope

This runbook covers `Phase 16 / GC-WB-20` through `Phase 22 / GC-WB-26` customer growth reporting automation:
- scheduled rollup refresh
- scheduled recurring reporting delivery
- reporting subscription and delivery status
- retention cleanup for reporting artifacts
- freshness and stale posture
- repeated refresh failures
- repeated delivery failures
- repeated cleanup failures
- governance conformance, evidence, and rollout gate automation
- governance recovery follow-up automation and overdue handling
- operator verification from admin overview and Prometheus

## Key Signals

- `cybervpn_growth_reporting_refresh_worker_runs_total`
- `cybervpn_growth_reporting_refresh_worker_last_attempt_unixtime`
- `cybervpn_growth_reporting_refresh_worker_last_success_unixtime`
- `cybervpn_growth_reporting_refresh_worker_consecutive_failures`
- `cybervpn_growth_reporting_refresh_worker_last_rows_written`
- `cybervpn_growth_reporting_delivery_worker_runs_total`
- `cybervpn_growth_reporting_delivery_worker_last_attempt_unixtime`
- `cybervpn_growth_reporting_delivery_worker_last_success_unixtime`
- `cybervpn_growth_reporting_delivery_worker_consecutive_failures`
- `cybervpn_growth_reporting_delivery_worker_last_claimed`
- `cybervpn_growth_reporting_delivery_worker_last_delivered`
- `cybervpn_growth_reporting_delivery_worker_last_failed`
- `cybervpn_growth_reporting_cleanup_worker_runs_total`
- `cybervpn_growth_reporting_cleanup_worker_last_attempt_unixtime`
- `cybervpn_growth_reporting_cleanup_worker_last_success_unixtime`
- `cybervpn_growth_reporting_cleanup_worker_consecutive_failures`
- `cybervpn_growth_reporting_cleanup_worker_last_deleted`
- `customer_growth:reporting_refresh_last_success_age_seconds`
- `customer_growth:reporting_refresh_consecutive_failures`
- `customer_growth:reporting_delivery_last_success_age_seconds`
- `customer_growth:reporting_delivery_consecutive_failures`
- `customer_growth:reporting_cleanup_last_success_age_seconds`
- `customer_growth:reporting_cleanup_consecutive_failures`
- `cybervpn_growth_reporting_governance_decisions_total`
- `cybervpn_growth_reporting_governance_subscription_coverage`
- `cybervpn_growth_reporting_governance_gap_subscriptions`
- `cybervpn_growth_reporting_governance_followup_subscriptions`
- `cybervpn_growth_reporting_governance_followup_overdue_subscriptions`
- `cybervpn_growth_reporting_governance_followup_actions_total`
- `cybervpn_growth_reporting_governance_followup_worker_runs_total`
- `cybervpn_growth_reporting_governance_followup_worker_last_attempt_unixtime`
- `cybervpn_growth_reporting_governance_followup_worker_last_success_unixtime`
- `cybervpn_growth_reporting_governance_followup_worker_consecutive_failures`
- `customer_growth:reporting_governance_gap_subscriptions`
- `customer_growth:reporting_recipient_domain_blocked_subscriptions`
- `customer_growth:reporting_governance_followup_last_success_age_seconds`
- `customer_growth:reporting_governance_followup_consecutive_failures`
- `customer_growth:reporting_governance_followup_overdue_subscriptions`

## Admin Checks

1. Open Admin `Growth -> Overview`.
2. Inspect `Reporting Rollups`.
3. Verify:
   - refresh status is `Fresh`
   - latest attempt and latest success are recent
   - latest run is `worker / success`
   - executive summary and trend rows are present
4. Inspect `Recurring Distribution`.
5. Verify:
   - at least one expected subscription is `active`
   - next delivery timestamps look sane
   - recent deliveries have `delivered` posture when email providers are healthy
   - recent artifacts can be exported for forensics
6. Inspect `Governance Coverage`.
7. Verify:
   - `coverage_gap_count` is `0` unless there is an intentional suppression window
   - `followup_open_count` is `0` unless recovery work is actively tracked
   - `followup_overdue_count` is `0`
   - recent governance decisions explain every `delivery_suppressed` or `recipient_domain_blocked` row
   - recent audit events match the latest recipient/template policy changes
   - every queue item has sane `due_at` and `last_notified_at` posture
   - governance snapshot export is downloadable for handoff

## Prometheus Checks

```bash
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_refresh_last_success_age_seconds'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_refresh_consecutive_failures'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=cybervpn_growth_reporting_refresh_worker_last_rows_written'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_delivery_last_success_age_seconds'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_delivery_consecutive_failures'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=cybervpn_growth_reporting_delivery_worker_last_delivered'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_cleanup_last_success_age_seconds'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_cleanup_consecutive_failures'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_governance_gap_subscriptions'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_recipient_domain_blocked_subscriptions'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_governance_followup_last_success_age_seconds'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_governance_followup_consecutive_failures'
curl -s http://localhost:9094/api/v1/query --data-urlencode 'query=customer_growth:reporting_governance_followup_overdue_subscriptions'
```

## Governance Conformance And Gate

1. Run the governance conformance pack:
   - `npm run conformance:customer-growth-reporting-governance`
2. Initialize a governance evidence pack before a rollout or incident review:
   - `npm run evidence:customer-growth-reporting-governance:init -- <date> <environment> <run-id> <ring> "<owner>"`
3. Capture and attach both API artifacts:
   - `GET /api/v1/admin/growth-reporting/governance`
   - `GET /api/v1/admin/growth-reporting/governance/export`
4. Use the GitHub protection handoff when governance wants a protected merge gate:
   - required check `All Customer Growth Reporting Governance Checks Passed`
   - handoff doc `docs/runbooks/CUSTOMER_GROWTH_REPORTING_GOVERNANCE_GITHUB_PROTECTION_HANDOFF.md`

## Failure Triage

If `CustomerGrowthReportingRefreshFailing` fires:

1. Check worker logs for `growth_reporting_refresh_complete` or backend refresh errors.
2. Check internal backend route health:
   - `POST /api/v1/admin/growth-reporting/internal/refresh`
3. Inspect the latest `growth_reporting_refresh_runs` rows.
4. Confirm the worker has valid:
   - `BACKEND_API_URL`
   - `BACKEND_INTERNAL_SECRET`

## Stale Triage

If `CustomerGrowthReportingRefreshStale` fires:

1. Confirm the scheduler is running only once.
2. Check the `refresh_growth_reporting_rollups` task schedule.
3. Verify backend and worker clocks are sane and UTC-based.
4. Run a manual admin refresh and confirm the latest run ledger updates.

## Delivery Triage

If `CustomerGrowthReportingDeliveryFailing` or `CustomerGrowthReportingDeliveryStale` fires:

1. Check worker logs for:
   - `growth_reporting_delivery_complete`
   - `growth_reporting_delivery_failed`
   - `growth_reporting_delivery_provider_unavailable`
2. Confirm worker email provider posture:
   - `EMAIL_DEV_MODE`
   - `RESEND_API_KEY` or `BREVO_API_KEY`
   - `SMTP_*` for dev/test
3. Check internal backend delivery endpoints:
   - `POST /api/v1/admin/growth-reporting/internal/deliveries/claim`
   - `POST /api/v1/admin/growth-reporting/internal/deliveries/{delivery_id}/complete`
4. In admin `Growth -> Overview`, inspect:
   - recurring subscriptions
   - recent reporting deliveries
   - exportable delivery artifacts for failed rows
5. Verify claimed deliveries are not stuck in `processing` without a matching completion callback.
6. If deliveries are being skipped, open the governance overview and confirm whether the reason is `delivery_suppressed` or `recipient_domain_blocked`.

## Cleanup Triage

If `CustomerGrowthReportingCleanupFailing` or `CustomerGrowthReportingCleanupStale` fires:

1. Check worker logs for `growth_reporting_cleanup_complete`.
2. Check internal backend cleanup route:
   - `POST /api/v1/admin/growth-reporting/internal/cleanup`
3. Verify retention configuration:
   - `growth_reporting_rollup_retention_days`
   - `growth_reporting_refresh_run_retention_days`
   - `growth_reporting_delivery_retention_days`
4. Confirm old delivered/failed/skipped artifacts are aging out as expected.

## Governance Gap Triage

If `CustomerGrowthReportingGovernanceCoverageGap` or `CustomerGrowthReportingRecipientDomainBlocked` fires:

1. Open Admin `Growth -> Overview -> Governance Coverage`.
2. Export the governance snapshot and attach it to the incident or rollout evidence.
3. Inspect recent governance decisions:
   - `delivery_suppressed`
   - `recipient_domain_blocked`
4. Inspect recent audit events for:
   - subscription recipient changes
   - template changes
   - suppression windows
   - pause / resume actions
5. If the gap is expected:
   - verify `suppressed_until` and `suppression_reason_code`
   - confirm the alert can clear after the suppression window ends
6. If the gap is not expected:
   - update recipient allowlists or recipient email policy
   - resume or unsuppress the subscription
   - trigger or wait for the next delivery claim cycle
7. Confirm `customer_growth:reporting_governance_gap_subscriptions` returns to `0`.

## Governance Follow-up Triage

If `CustomerGrowthReportingGovernanceFollowupStale`, `CustomerGrowthReportingGovernanceFollowupFailing`, or `CustomerGrowthReportingGovernanceFollowupOverdue` fires:

1. Open Admin `Growth -> Overview -> Governance Coverage`.
2. Inspect:
   - `followup_open_count`
   - `followup_overdue_count`
   - queue rows with `due_at`, `last_notified_at`, and current `health_status`
3. Check the scheduled worker and internal processing route:
   - worker task `process_growth_reporting_governance_followups`
   - `POST /api/v1/admin/growth-reporting/internal/governance/followups/process`
4. Review audit trail entries for the affected subscription:
   - `growth_reporting.subscription.followup.opened`
   - `growth_reporting.subscription.followup.reopened`
   - `growth_reporting.subscription.followup.auto_resolved`
   - `growth_reporting.subscription.followup.reminded`
   - `growth_reporting.subscription.followup.resolved`
   - `growth_reporting.subscription.followup.dismissed`
5. If the issue is recoverable:
   - clear the suppression window or domain policy blocker
   - use admin `Resolve` when recovery is operator-validated
6. If the gap is intentional or non-actionable:
   - use admin `Dismiss` with an explicit reason code
   - ensure the reason appears in audit history and export snapshot
7. Confirm:
   - `customer_growth:reporting_governance_followup_overdue_subscriptions` returns to `0`
   - consecutive worker failures reset to `0`
   - reminder spam does not continue after resolution or dismissal

## Recovery

1. Restore worker-to-backend connectivity or internal secret configuration.
2. Re-run the scheduled task or use the admin refresh action.
3. Confirm:
   - `latest_success_at` advances
   - `rows_written` is non-zero when lifecycle data exists
   - consecutive failures reset to `0`
4. For delivery incidents, confirm:
   - `cybervpn_growth_reporting_delivery_worker_last_delivered` is positive on the next healthy run
   - the latest reporting delivery rows move to `delivered`
5. For cleanup incidents, confirm:
   - `cybervpn_growth_reporting_cleanup_worker_last_deleted` updates when old artifacts exist
   - cleanup consecutive failures reset to `0`
