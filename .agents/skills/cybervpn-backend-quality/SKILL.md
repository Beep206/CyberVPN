---
name: cybervpn-backend-quality
description: Implement and validate production-grade CyberVPN FastAPI/DDD backend changes with async correctness, authorization, persistence, migrations, observability, and full quality gates.
---

# Backend Quality

1. Map route -> dependency/auth -> application use case -> domain -> repository/external adapter -> transaction/state.
2. Keep routes thin and domain framework-free.
3. Use async I/O, typed DTOs/errors and explicit timeouts/retries.
4. Enforce realm/tenant/object authorization and add negative tests.
5. Define transaction, idempotency and concurrency semantics before mutation code.
6. Add migrations/backfills through `$cybervpn-migration-safety` when schema changes.
7. Add safe structured logs/metrics/traces/audit events without secrets.
8. Add focused unit tests plus database/Redis/external-adapter integration and route/e2e tests.
9. Run Ruff check, Ruff format check, mypy, targeted pytest and full pytest with coverage.
10. Invoke `$cybervpn-contract-sync` for route/schema changes.
