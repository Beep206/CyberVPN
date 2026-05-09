# Release Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Approved decision log | `../../../17_STAGE1_APPROVED_DECISION_LOG.md` |
| Operational inputs/evidence rules | `../../../18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` |
| Dirty worktree scope map | `../../../22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md` |
| Release notes template | `../../../78_STAGE1_REL_005_RELEASE_NOTES_TEMPLATE_EVIDENCE.md` |
| Local rollback dry-run | `../../../90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md` |
| Evidence pack index | `../../../91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md` |
| RC tag eligibility | `../../../129_STAGE1_STEP_31_RC_TAG_EVIDENCE.md` |
| Owner go/no-go | `../../../130_STAGE1_STEP_32_OWNER_GO_NO_GO_EVIDENCE.md` |

## Required Before Go-Live

- Re-run dirty worktree scope map immediately before first RC tag.
- Create immutable `stage1-beta-rc.N` from `release/stage1-controlled-public-beta`.
- Fill real release notes for the candidate.
- Re-run final RC test/audit/scan gates.
- Repeat rollback against final staging/prod RC artifacts.
- Record owner go/no-go and known accepted issues.

Current status: local release governance evidence exists; `stage1-beta-rc.1` was checked but not created because the release branch is missing and the worktree is dirty. Owner go/no-go is prepared with a recommended `NO-GO_FOR_CONTROLLED_BETA_LAUNCH`.
