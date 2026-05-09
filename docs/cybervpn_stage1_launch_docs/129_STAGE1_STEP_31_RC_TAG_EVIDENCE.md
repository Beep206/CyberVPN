> CyberVPN Launch Program
> Date: 2026-05-09
> Ordered step: `31. stage1-beta-rc.N`
> Status: `BLOCKED_FOR_REAL_TAG`; local RC eligibility check completed; no tag was created.

# Step 31 - Stage 1 Beta RC Tag Evidence

## Purpose

This document records the release-candidate gate for the ordered launch sequence item:

```text
31. stage1-beta-rc.N
```

The expected output of this step is an immutable release-candidate tag, for example `stage1-beta-rc.1`, created only after the release branch, dirty worktree scope map, evidence pack and security checks are acceptable.

## Result

`stage1-beta-rc.1` was **not created**.

This is intentional. Creating the tag from the current repository state would be misleading because the current `HEAD` does not contain the broad local S1 implementation/evidence worktree.

## RC Candidate Selection

| Item | Value |
|---|---|
| Candidate tag | `stage1-beta-rc.1` |
| Reason | No existing `stage1-beta-rc.*` tags were found |
| Current branch | `main` |
| Current HEAD | `b31728dc2921b5739fc5bb606166cec0d1e843ae` |
| Required release branch | `release/stage1-controlled-public-beta` |
| Release branch exists | No |
| Candidate tag exists | No |
| Worktree clean | No |
| Dirty porcelain entries | `965` |
| Untracked actual files | `534` |

## Commands Executed

| Command | Result |
|---|---|
| `git rev-parse --abbrev-ref HEAD` | `main` |
| `git rev-parse HEAD` | `b31728dc2921b5739fc5bb606166cec0d1e843ae` |
| `git tag --list 'stage1-beta-rc.*' --sort=version:refname` | No existing RC tags |
| `git show-ref --verify --quiet refs/heads/release/stage1-controlled-public-beta` | Branch missing |
| `git status --short \| wc -l` | `965` |
| `git ls-files --others --exclude-standard \| wc -l` | `534` |
| `git diff --quiet && git diff --cached --quiet` plus untracked check | Worktree is not clean |
| Explicit excluded-runtime scan for partner/mobile/desktop/TV/browser-extension/Helix/Verta/Beep/GitOps paths | PASS: no matches |
| Evidence pack README count | PASS: root plus 10 category READMEs |

## Why The Tag Is Blocked

| Blocker | Why it blocks real RC tag creation |
|---|---|
| Release branch missing | `DEC-S1-017` requires `release/stage1-controlled-public-beta` as the launch-candidate branch |
| Dirty worktree | A tag points to a commit, not to uncommitted changes; tagging `HEAD` would exclude current S1 evidence and implementation changes |
| Untracked docs/evidence | The Stage 1 evidence pack is not fully represented by the immutable commit |
| Broad runtime changes | `612` tracked modified entries and `534` actual untracked files require owner-approved inclusion/exclusion before RC |
| External evidence still open | Staging/prod/live evidence remains required before go-live even after a future RC tag |

## What Is Acceptable Now

The ordered local evidence chain through item `30. S1-REL-007` is usable for review and planning.

It is **not** yet an immutable release candidate.

## Required To Create A Real `stage1-beta-rc.N`

1. Owner approves the launch-critical/excluded scope map for the current dirty worktree.
2. Create or switch to `release/stage1-controlled-public-beta`.
3. Stage only approved S1 files and generated artifacts.
4. Commit the approved S1 scope.
5. Re-run final RC checks from the committed tree:
   - dirty worktree scope map;
   - current-tree Gitleaks;
   - dependency audit;
   - frontend bundle/env scan;
   - evidence pack link check;
   - rollback dry-run record.
6. Create an annotated immutable tag such as `stage1-beta-rc.1`.
7. Record the tag SHA in this evidence pack.

## Acceptance Result

Step `31. stage1-beta-rc.N` is **completed as an eligibility check** and **blocked as a real tag operation**.

Next ordered step: `32. Owner go/no-go`.
