---
name: cybervpn-verify-done
description: Prove that a CyberVPN implementation is genuinely complete and prevent unsupported Done or Complete claims.
---

# Verify Done

1. Re-read the original request independently of the plan.
2. Rebuild the acceptance-criteria list and compare it with `.codex/current-task.json`.
3. Trace every criterion through the real production path and resulting state/artifact.
4. Search changed paths for TODO, FIXME, placeholder, mock, fallback, no-op, hard-coded data, ignored exception, skip, xfail, `continue-on-error`, disabled gate and generated drift.
5. Verify tests fail when the requested production behavior is broken; rendering, invocation, mocks and status codes alone are insufficient.
6. Run targeted tests and all affected-surface lint/typecheck/test/build gates.
7. Re-export/regenerate contracts and require a second generation to produce no diff.
8. Test migration upgrade/downgrade/re-upgrade and concurrency/idempotency when relevant.
9. Reproduce any alleged pre-existing failure on the clean merge base.
10. Spawn `verifier` and `adversarial_reviewer`; record both in the task contract.
11. Resolve findings and rerun affected validation.
12. Mark every AC with implementation and test/runtime evidence.
13. Set `verified` only when all required validations pass with exit code 0 and unresolved is empty. Otherwise set `partial` or `blocked` with exact unresolved items.
