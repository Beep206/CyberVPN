# CyberVPN Backend Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file explicitly before changing `backend/`.

## Architecture and ownership

- Preserve the dependency direction:
  `presentation -> application -> domain`, with `infrastructure` implementing
  domain/application ports.
- Domain code must remain framework-independent: no FastAPI, SQLAlchemy,
  Redis, HTTP-client, or environment-setting imports.
- Keep routes and dependencies thin. They validate transport input, resolve the
  authenticated context, call a use case, and map typed results/errors.
- Put business invariants and state transitions in domain/application code, not
  in routes, ORM models, migrations, response schemas, or frontend code.
- Application code may depend on domain ports, not concrete infrastructure
  implementations.
- Reuse the existing repository/unit-of-work and dependency-injection patterns.
  Do not introduce a second transaction or DI style.

## API and trust boundaries

For every route or externally callable use case, identify and test:

- auth realm and audience;
- principal and session state;
- tenant/workspace/storefront scope;
- role and permission;
- resource ownership;
- allowed source state and target transition;
- idempotency/replay requirements;
- rate-limit and audit requirements.

Never rely on route visibility, client-supplied ownership fields, proxy checks,
or frontend state for authorization. Prevent mass assignment by constructing
commands explicitly from allowlisted fields.

Use Pydantic v2 schemas and explicit response models. Do not expose ORM models,
domain internals, provider payloads, stack traces, or secret-bearing fields.
Keep public error codes stable and map domain errors centrally.

When a request/response schema, enum, route, or status contract changes, update
the canonical OpenAPI output and regenerate every affected client. Do not edit
generated clients manually.

## Async, external I/O, and resources

- Use asynchronous database, Redis, broker, and HTTP operations throughout an
  async request path. Do not call blocking file, subprocess, sleep, SDK, or
  network APIs directly from the event loop.
- Reuse managed clients/pools created through the application lifespan. Do not
  create an `httpx.AsyncClient`, database engine, or Redis connection per
  request.
- Set explicit connect/read/write/pool timeouts and bounded connection limits.
- Retry only transient and idempotent operations. Respect provider rate limits
  and do not retry validation, authorization, or permanent 4xx failures.
- Bound list sizes, pagination, exports, bulk operations, query fan-out, and
  parallel work.
- Use eager loading or explicit projections to prevent implicit async lazy loads
  and N+1 queries.

## Transactions, time, money, and concurrency

- Make transaction ownership explicit. Do not commit inside a repository method
  when the use case owns a multi-step transaction.
- Validate invariants before external side effects. For workflows spanning the
  database and a broker/provider, use the established outbox/event pattern or a
  documented compensating strategy.
- Enforce uniqueness and idempotency in the database, not only with an
  application pre-check.
- Lock or use an atomic conditional update for race-sensitive state changes.
  Test two concurrent attempts and deterministic winner/loser behavior.
- Financial values use the established exact representation (`Decimal` or
  integer minor units), never binary floating point.
- Use timezone-aware UTC datetimes and controlled clocks in tests. Do not use
  naive datetimes or compare application and database clocks implicitly.
- Normalize identifiers, emails, codes, locale, and external references once at
  the boundary and preserve the typed normalized form.

## SQLAlchemy and migrations

- Use SQLAlchemy 2 typed mappings and explicit query construction.
- Never interpolate untrusted values into SQL strings. Parameterize raw SQL and
  use raw SQL only when ORM/Core cannot express the required operation clearly.
- Add database constraints, partial/functional indexes, and foreign-key actions
  that match the business invariant.
- Review query plans for new high-volume filters, joins, ordering, and
  pagination paths.
- Alembic migrations must not import current ORM models.
- Data migrations must be deterministic, restart-safe where practical, bounded,
  and safe for existing rows.
- Test PostgreSQL behavior as authoritative. Preserve SQLite test compatibility
  only when the repository intentionally supports it.
- Test clean upgrade, populated upgrade/backfill, downgrade, and re-upgrade.
  Explicitly document irreversible or long-locking operations.

## Errors, logging, and observability

- Raise typed domain/application exceptions; avoid `except Exception` except at
  a boundary that logs and re-raises/maps deliberately.
- Never swallow cancellation.
- Log safe correlation IDs, operation names, state transitions, latency, and
  terminal outcome. Never log raw request bodies for sensitive endpoints.
- Never log passwords, OTP/TOTP values, cookies, JWTs, refresh tokens, raw
  Telegram initData, payment secrets, provider tokens, VPN configuration,
  subscription URLs, private keys, or customer PII.
- Add metrics/audit events for security-sensitive, financial, attribution,
  provisioning, and durable background operations when operators need them.

## Testing

Add the narrowest tests that prove the behavior, then integration coverage for
the boundary:

- domain/application unit tests for invariants and state transitions;
- repository tests for queries, constraints, transactions, and concurrency;
- API tests for validation, auth, RBAC, tenant isolation, response contracts,
  and error mapping;
- provider-adapter tests using `respx` or an equivalent boundary fake;
- e2e/conformance tests for cross-surface business flows;
- migration tests for schema, data, downgrade, and re-upgrade.

Assertions must inspect persisted state and side effects, not only HTTP status or
mock invocation. Avoid arbitrary sleeps and shared mutable fixtures. Use an
isolated database/transaction strategy and deterministic clocks/IDs.

## Required validation

Use Python 3.13 and the project virtual environment. From the repository root:

```bash
backend/.venv/bin/python -m ruff check backend
backend/.venv/bin/python -m ruff format --check backend
backend/.venv/bin/python -m mypy backend/src --ignore-missing-imports --no-strict-optional
backend/.venv/bin/python -m pytest backend/tests -v --tb=short
```

Run focused tests first. Add relevant conformance, OpenAPI generation, migration,
security, and provider smoke commands for the changed behavior. A mypy, Ruff,
pytest, coverage, migration, or generated-drift failure is a failure, never an
advisory result.
