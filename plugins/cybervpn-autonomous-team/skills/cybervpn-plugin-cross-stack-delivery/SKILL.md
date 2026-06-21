---
name: cybervpn-plugin-cross-stack-delivery
description: Deliver a CyberVPN feature across backend, web, admin, partner, mobile, desktop, services, contracts, migrations, and CI with specialist agents and independent verification.
---

1. Read the original task and applicable AGENTS.md files.
2. Create or refresh `.codex/current-task.json` with atomic acceptance criteria.
3. Spawn `repo_mapper` and `requirements_auditor` in parallel.
4. Select only affected implementation specialists and give each explicit file ownership.
5. Keep one writer per shared file set unless separate worktrees isolate writes.
6. Implement the full production path, including failure and authorization behavior.
7. Regenerate OpenAPI clients and generated assets whenever their source contracts change.
8. Run targeted tests, then every affected surface gate through `scripts/codex/verify-changed.sh`.
9. Spawn `verifier` and `adversarial_reviewer`, fix all actionable findings, and rerun affected checks.
10. Finish with `TASK_STATUS: VERIFIED` only when the task contract contains direct evidence for every criterion and required validation.
