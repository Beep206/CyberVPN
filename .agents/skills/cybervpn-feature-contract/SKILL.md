---
name: cybervpn-feature-contract
description: Create a strict CyberVPN task contract before implementing any non-trivial feature, bug fix, refactor, API, database, auth, payment, VPN, admin, partner, frontend, mobile, service, protocol, infrastructure, or release change.
---

# Feature Contract

Before editing production code:

1. Read the original request verbatim and applicable specs/ADRs/contracts.
2. Reproduce or trace the current behavior.
3. Split the request into atomic numbered acceptance criteria. Each criterion must name:
   - observable user/system result;
   - production execution path;
   - success behavior;
   - failure/permission/degraded behavior;
   - persisted state, event or artifact proving completion;
   - automated test and any runtime/manual smoke.
4. Record in-scope/out-of-scope and explicit assumptions.
5. Map affected surfaces: backend, frontend, admin, partner, mobile, desktop, services, packages, API/OpenAPI, database, workers, infrastructure, observability and release artifacts.
6. Add negative criteria prohibiting documentation-only, mock-only, build-only, silent fallback, weakened-test and generated-file shortcuts.
7. Include auth/RBAC/tenant, replay/idempotency/concurrency, privacy/logging, localization/a11y, compatibility, migration/rollback and observability criteria when relevant.
8. Enumerate exact required validation commands before implementation.
9. Write `.codex/current-task.json` with status `in_progress`.
10. Run `requirements_auditor`; incorporate missing criteria rather than silently narrowing scope.

A criterion is invalid if it could pass while the requested business behavior remains broken.
