---
name: cybervpn-autonomous-delivery
description: Orchestrate a non-trivial CyberVPN feature, bug fix, refactor, migration, cross-surface change, or release task autonomously from discovery through independent verification.
---

# CyberVPN Autonomous Delivery

Use this skill as the default entry point for substantive work.

1. Inspect branch, status, merge base and applicable AGENTS.md/spec files.
2. Invoke `$cybervpn-feature-contract` and create `.codex/current-task.json`.
3. Spawn `repo_mapper` and `requirements_auditor` in parallel for broad or cross-surface work.
4. Wait for both and build an AC-to-production-path/test matrix.
5. Present a concise plan and continue implementation immediately.
6. Spawn the narrowest implementation specialists. Use one writer per shared file set; use worktrees for genuinely parallel writers.
7. Install missing dependencies and local services automatically. Use `sudo -n` for WSL packages and Docker/Redis/PostgreSQL as required.
8. Implement the full vertical path, including contracts, persistence, errors, UI states, observability, migrations and generated artifacts.
9. Add behavior-focused unit, integration, interaction, e2e/conformance, security-negative and migration tests as required.
10. Run targeted checks, then `scripts/codex/verify-changed.sh` and all task-specific runtime smokes.
11. Invoke `$cybervpn-verify-done`.
12. Spawn `verifier` and `adversarial_reviewer` in parallel, wait, fix every concrete finding, and rerun affected checks.
13. Update task evidence and finish only as VERIFIED, PARTIAL or BLOCKED.

Never stop after planning. Never use build output, mocks, screenshots, QA reports or child-agent claims as substitute for observable production behavior.
