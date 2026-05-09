# Scope Map Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Scope-map rules | `../../../18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` |
| Dirty worktree inventory | `../../../22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md` |

## Required Before First RC Tag

- Re-run dirty worktree inventory.
- Confirm launch-critical runtime files are tied to `S1-*` backlog IDs.
- Confirm experimental partner/native/Helix/GitOps scope is not enabled in S1 runtime.
- Record excluded/deferred files and owner approval.
- Tag only immutable `stage1-beta-rc.N`, never floating `main`.

Current status: current snapshot exists; pre-RC scope map must be repeated before tagging.
