# CyberVPN Backend Rules

Apply the root completion contract plus these backend rules.

- Preserve Clean Architecture boundaries: presentation -> application ->
  domain, with infrastructure implementing domain ports. Domain code has no
  FastAPI, SQLAlchemy, Redis or HTTP-client imports.
- Keep FastAPI routes thin. Business policy, authorization decisions and
  transaction orchestration belong in use cases/domain services.
- Use async I/O end to end. Never call blocking database, HTTP, Redis, sleep or
  filesystem operations directly from an async request path.
- Use Pydantic v2 models and explicit response contracts. Do not leak ORM
  models or internal exception details.
- Use SQLAlchemy 2 typed mappings and explicit loading. Avoid implicit async
  lazy loads and N+1 queries.
- Make transaction ownership explicit. Financial, attribution, subscription,
  session and provisioning operations require idempotency, deterministic
  retries and concurrency-safe uniqueness.
- Every public/authenticated route requires explicit realm, tenant/workspace,
  principal and permission analysis. Add negative cross-tenant/RBAC tests.
- Never log secrets, raw tokens, cookies, initData, provider payload secrets,
  subscription URLs or VPN credentials.
- Alembic migrations must be reversible unless an approved ADR documents an
  irreversible change. Test clean upgrade, populated upgrade, downgrade and
  re-upgrade.
- API schema changes require OpenAPI export and regeneration of all affected
  TypeScript clients.
- Add unit tests for domain/application behavior and integration/e2e tests for
  database, route, auth and external-boundary behavior.
- Before VERIFIED run Ruff check, Ruff format check, mypy and the affected plus
  full pytest suites. A mypy failure is a failure, never advisory.
