---
name: cybervpn-release-gate
description: Assess or prepare CyberVPN release readiness using actual required CI, packaging, migration, security, artifact, staging-smoke, and rollback evidence rather than task status or QA prose.
---

# Release Gate

1. Establish exact release scope, merge base, version/channel and target environments.
2. Require clean reviewed commits and all relevant required CI statuses.
3. Run changed-surface plus complete release gates; no `continue-on-error` for required checks.
4. Verify generated artifacts, dependency locks, migrations, downgrade/rollback and config compatibility.
5. Produce/sign/package required web, backend, mobile, desktop, service and protocol artifacts.
6. Generate SBOM/provenance/checksums where the release process supports them.
7. Run approved staging smoke with sanitized evidence for critical auth, payment, subscription, provisioning, partner and VPN flows.
8. Run security review and confirm no unresolved release-blocking finding.
9. Separate code-ready, artifact-ready, staging-ready and production-deployed states.
10. Never call a release GO from closed tasks or reports whose underlying gates fail. Production deployment occurs only when the current task explicitly requests it.
