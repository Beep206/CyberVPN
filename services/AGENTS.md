# CyberVPN Services Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file and the nearest service-specific `AGENTS.md` before changing
`services/`.

Services include Python and Rust workers, bots, adapters, controllers, and
network processes. Use each service's manifest, lockfile, local instructions,
and existing CI workflow as the source of truth for commands and architecture.

## Durable processing

- Assume brokers and schedulers can deliver a message more than once.
- Every durable handler must define an idempotency key, duplicate behavior,
  transaction boundary, acknowledgment point, retry policy, and terminal
  failure/dead-letter behavior.
- Acknowledge only after intended durable state is committed or the documented
  safe handoff is complete.
- Do not perform irreversible external side effects before the state needed to
  deduplicate or recover them is durable.
- Use an outbox/inbox/event ledger or the established equivalent when database
  state and message publication must remain consistent.
- Test crash/restart at meaningful boundaries, duplicate delivery, reordered
  delivery, partial provider success, and replay.
- Permanent validation, authentication, authorization, or contract failures are
  not retryable. Transient retries must be bounded with backoff/jitter.

## Concurrency, resources, and lifecycle

- Make ownership of locks, leases, schedules, leader election, and worker
  concurrency explicit.
- Use atomic compare-and-set/unique constraints for race-sensitive state.
- Bound queue depth, task concurrency, batch size, payload size, memory, child
  processes, connection pools, retries, and shutdown time.
- Support graceful shutdown: stop accepting work, cancel/finish according to
  policy, release leases, flush safe telemetry, and close clients.
- Use health/readiness checks that reflect real dependencies without causing
  side effects.
- Avoid arbitrary sleeps; use controlled clocks and bounded polling.

## External boundaries

- Reuse long-lived HTTP, database, Redis, NATS/broker, and provider clients.
- Set explicit timeouts and connection limits.
- Validate incoming message/event schemas and versions before side effects.
- Preserve compatibility for event names, payloads, task names, and routing
  keys; version intentional breaks.
- Retry only safe provider operations and preserve provider idempotency keys.
- Redact provider payloads and map errors to stable internal categories.

## Security and observability

- Enforce service identity, audience, tenant/workspace scope, and authorization
  at every callable boundary.
- Never log secrets, message payloads containing PII, cookies, tokens, raw
  Telegram data, payment details, VPN/subscription URLs, private keys, or device
  credentials.
- Structured logs, traces, and metrics should include safe correlation,
  message/task ID, attempt, latency, state transition, and terminal outcome.
- Add metrics for queue lag/depth, retries, duplicates, dead letters, failures,
  external latency, and saturation when relevant.
- Audit security-sensitive, financial, attribution, provisioning, and
  notification state transitions.

## Testing

Add relevant:

- pure handler/domain unit tests;
- broker serialization and routing contract tests;
- database transaction/idempotency/concurrency tests;
- duplicate, retry, crash, timeout, and dead-letter tests;
- provider adapter tests with controlled fakes;
- graceful shutdown and lease-expiry tests;
- integration tests using local containers;
- cross-service/e2e tests for durable workflows.

Assert durable state and emitted/acknowledged messages, not only handler return
values or mock calls.

## Validation

Run the exact format/lint/typecheck/test/build commands from the nearest
manifest and CI workflow after the final change.

For Python services, normally run the service environment's Ruff format/check,
mypy, pytest, and coverage gates. For Rust services, run manifest-scoped fmt,
clippy with warnings denied, tests, and the relevant runtime smoke.

Do not treat `continue-on-error`, missing tools, placeholder scripts, or a
successful image build as proof of service behavior. Run service-specific
broker/database/provider integration tests for changed durable paths.
