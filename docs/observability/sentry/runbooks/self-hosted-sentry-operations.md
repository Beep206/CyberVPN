# Self-Hosted Sentry Operations

Status: draft
Owner: platform
Last updated: 2026-04-24
Scope: operation of the self-hosted Sentry platform
Depends on: `../03-self-hosted-sentry-platform-bootstrap.md`
Related paths: `../02-open-questions-and-decision-log.md`

## Operational responsibilities

- service availability and health
- storage pressure and retention enforcement
- backups and restore validation
- controlled upgrades
- admin and service-account access review

## Minimum operating checklist

- health checks monitored
- backup and restore exercised
- retention reviewed regularly
- storage and ingest growth tracked
- upgrade path tested before production rollout

## Incident flow

1. Confirm whether the issue is platform-wide or project-specific.
2. Protect ingest and storage before broadening access.
3. Communicate impact to runtime owners.
4. Recover platform health.
5. Re-validate artifact upload, deploy markers and alerting after recovery.
