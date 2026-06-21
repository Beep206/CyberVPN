---
name: cybervpn-contract-sync
description: Keep CyberVPN FastAPI OpenAPI schemas and generated frontend, admin, partner, SDK, BFF, and service consumers synchronized after API contract changes.
---

# API Contract Sync

Use whenever routes, dependencies, status codes, auth requirements, Pydantic schemas, enums, error models or OpenAPI generation change.

1. Identify all consumers of the changed operation/schema.
2. Run the repository OpenAPI export with safe local environment values.
3. Inspect the semantic OpenAPI diff: required/optional, nullability, enums, formats, auth, response codes and error bodies.
4. Regenerate `frontend`, `admin` and `partner` clients through their scripts; include SDK/service consumers when affected.
5. Never hand-edit generated clients.
6. Update source adapters/hooks/components for intentional contract changes.
7. Add backend contract tests and consumer type/interaction tests.
8. Run typecheck/tests/build for every affected consumer.
9. Run generation again and require zero generated diff.
10. Record export/generation commands and artifacts in `.codex/current-task.json`.
