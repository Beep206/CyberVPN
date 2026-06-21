---
name: cybervpn-plugin-release-readiness
description: Evaluate and prepare a CyberVPN branch for release using code, migration, generated-contract, packaging, security, and runtime evidence.
---

1. Determine the merge base, target environment, release surfaces, and explicit deployment scope.
2. Reject task-manager closure, documentation, screenshots, or partial builds as release proof.
3. Run `release_engineer`, `security_reviewer`, and `verifier` against the branch.
4. Require all affected lint, typecheck, unit, integration, e2e/conformance, build, migration, generated-client, packaging, and smoke gates.
5. Verify upgrade, rollback, configuration, secrets, observability, alerting, artifacts, SBOM/provenance, and release notes where applicable.
6. Reproduce alleged pre-existing failures on the clean merge base before excluding them.
7. Do not deploy to production unless the current task explicitly authorizes deployment and provides the required environment and credentials.
8. Return `VERIFIED` only for a genuinely green release candidate; otherwise return `PARTIAL` or `BLOCKED` with exact failing gates and owners.
