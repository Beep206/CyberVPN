# Issue Triage And Incident Playbook

Status: draft
Owner: platform + runtime owners
Last updated: 2026-04-25
Scope: all Sentry projects
Depends on: `../12-alerting-ownership-routing-and-severity-policy.md`
Related paths: `../04-sentry-project-registry.md`, `../08-tags-context-correlation-and-fingerprinting-contract.md`, `../governance-registry.json`

## Triage flow

1. Confirm project, environment and release.
2. Classify severity: incident-grade or non-incident.
3. Check ownership in `governance-registry.json` and route to the correct logical team.
4. Correlate with `request_id`, `trace_id`, `task_name`, `handler` or `workflow_stage`.
5. Link to Loki, Tempo, PostHog or deployment evidence as needed.

## Incident criteria

- production auth, payment, provisioning or subscription regressions
- crash spikes on packaged clients
- repeated control-plane panics
- release-health degradation tied to a fresh rollout

## Escalation

- page only on approved incident-grade signals
- use staging alerts for release-blocking checks only
- attach deployment and rollback context to every escalated incident
