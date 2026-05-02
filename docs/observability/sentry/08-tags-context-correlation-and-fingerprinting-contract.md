# Tags, Context, Correlation And Fingerprinting Contract

Status: draft
Owner: platform + runtime owners
Last updated: 2026-04-24
Scope: shared tag dictionary and correlation rules
Depends on: `07-privacy-pii-scrubbing-and-replay-policy.md`
Related paths: `surfaces/`, `12-alerting-ownership-routing-and-severity-policy.md`

## Global required tags

- `runtime_surface`
- `service.name`
- `environment`
- `release`

## Correlation tags by surface type

### Web and backend

- `request_id`
- `trace_id`
- `route_group` or `endpoint_template`

### Worker

- `task_name`
- `task_group`
- `queue`
- `retry_count`
- `trigger_source`

### Bot

- `handler`
- `bot_mode`
- `flow_step`
- `payment_provider`

### Control-plane

- `workflow_stage`
- `operation_type`
- `node_id`
- `correlation_id`

### Mobile, desktop and TV

- `platform`
- `app_version`
- `build_number`
- `runtime_layer` when needed

## Safe user context

- primary application user: internal `user.id`
- Telegram user: hashed ID only
- tenant or realm identifiers only where operationally needed and privacy-safe

## Fingerprinting guidance

- Keep default grouping unless a surface has proven noisy domain exceptions.
- Introduce custom fingerprinting only for well-understood, repeated patterns such as expected transport noise or domain-specific exception families.
- Never fingerprint on raw secrets or high-cardinality PII.
