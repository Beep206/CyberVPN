> CyberVPN Stage 1 Evidence
> ID: S1-REL-005
> Date: 2026-05-05
> Scope: reusable release notes template and sample only.

# S1-REL-005 Release Notes Template Evidence

## Result

`S1-REL-005` is completed locally.

The repository now contains a reusable release notes template for every `stage1-beta-rc.N` and `stage1-beta-live.N` candidate, plus a sample RC note showing how to use it without turning the sample into an approval.

## Implemented documents

| Document | Purpose |
|---|---|
| `templates/STAGE1_RELEASE_NOTES_TEMPLATE.md` | Canonical template for RC/live release notes |
| `templates/STAGE1_RELEASE_NOTES_SAMPLE_STAGE1_BETA_RC.md` | Non-authoritative sample for a future `stage1-beta-rc.N` |

## Rules captured by the template

- Deploy only by immutable tag or commit SHA.
- Use `release/stage1-controlled-public-beta` as the source branch.
- Use `stage1-beta-rc.N` for staging/beta candidates.
- Use `stage1-beta-live.N` for production live candidates.
- Every runtime change must reference an approved `S1-*` backlog ID.
- Explicitly list disabled/out-of-scope surfaces: partner payouts, public growth mechanics, native releases, Helix/Verta/Beep production, auto-prolongation and full GitOps/Talos/Kubernetes migration.
- Require evidence links for dirty worktree/scope map, secrets scan, DB migrations, first admin bootstrap, DNS/TLS, CORS/cookies/CSRF, payment provider proof, Remnawave proof, backup/restore, rollback, observability and legal/support.
- Include feature flags and kill switches before release.
- Include component rollback notes and rollback success criteria.
- Include known issues/risk acceptance with no P0 blocker accepted without explicit owner sign-off.
- Include post-release checks for trial/pay -> VPN ready, paid-but-no-access, support queue, audit, alerts and Sentry/log privacy.
- Include owner/support/finance/technical approval table.

## Why this matters

Release notes are not cosmetic for S1. They are the compact go/no-go artifact tying together:

- what exact commit/tag is being deployed;
- what user-facing and operational changes are included;
- what is explicitly disabled;
- which backlog IDs justify runtime changes;
- which evidence proves readiness;
- how rollback works if the candidate fails.

Without this template, the project can pass isolated local tests while still lacking release-level accountability.

## Verification performed

| Check | Result |
|---|---|
| Template exists | Passed |
| Sample exists | Passed |
| Backlog/update docs reference `S1-REL-005` as completed locally | Passed |
| `git diff --check` for touched docs | Passed |
| Secret placeholder scan for touched release docs | Passed |
| Static dangerous-pattern scan for touched release docs | Passed |
| Root `npm audit --audit-level=high` | Passed; only existing moderate Next/PostCSS advisory remains |

## Remaining requirements before first RC

| Requirement | Reason |
|---|---|
| Fill a real release note from the template | Template is not release approval |
| Re-run `S1-REL-002` dirty worktree/scope map | Worktree is actively changing |
| Attach fresh evidence links | RC/live notes must point to actual current evidence |
| Owner signs go/no-go | No release without explicit owner decision |
| Prove rollback via `S1-REL-006` | Release notes reference rollback, but rollback dry-run is a separate blocker |

## Next ID

Next ID to execute: `S1-FE-010` - Frontend bundle/env scan. Legal/text work is closed by `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
