# CyberVPN AI Merge Request Contract

Status: active
Updated: 2026-05-29
Applies to: autonomous Paperclip AI merge requests in `root/CyberVPN`

This contract defines what every autonomous AI merge request must include before
it is eligible for maintainer merge. It complements `CODEOWNERS` and
`docs/gitlab/AI_REVIEW_MAP.md`.

## Repository Gates

The project is configured so that:

- `main` is protected.
- Developer agents cannot push directly to `main`.
- Merge to `main` is restricted to Maintainers.
- A successful pipeline is required before merge.
- All GitLab discussions must be resolved before merge.
- Source branches are deleted after merge.
- Squash is enabled by default.
- Phase 5 factory dry runs use disposable docs-only merge requests for gate evidence.

GitLab CE does not expose required approval rules on this instance, so reviewer
approvals are represented as Paperclip gates and GitLab discussions.

## Required MR Description Sections

Use `.gitlab/merge_request_templates/Default.md`. Every autonomous MR must keep
these sections filled in:

- Summary.
- Scope Classification.
- Touched Paths.
- What Was Intentionally Not Changed.
- Tests Run.
- Remote CI.
- Screenshots / UI Evidence.
- Security Notes.
- Rollback Notes.
- Reviewer Agents Required.
- Paperclip Links.
- Labels.
- Merge Gate.

If a section is not applicable, write `not applicable` and explain why.

## Label Taxonomy

Apply `lane::autonomous` to every Paperclip-authored autonomous MR.

Risk labels:

| Label | Meaning | Merge requirement |
| --- | --- | --- |
| `risk::green` | Documentation, tests, non-sensitive copy, or isolated UI only | Green CI and resolved discussions |
| `risk::amber` | Support, admin, partner, TMA, user-generated content, user data, notifications, or worker behavior | Green CI, resolved discussions, required Paperclip gates |
| `risk::red` | Payments, auth core, admin permissions core, production secrets, production deploy, VPN provisioning, Remnawave production config, or infrastructure exposure | Human or Board approval plus required Paperclip gates |

Area labels:

| Label | Primary paths |
| --- | --- |
| `area::backend` | `backend/` |
| `area::frontend` | `frontend/` |
| `area::admin` | `admin/` |
| `area::partner` | `partner/` |
| `area::telegram` | `services/telegram-bot/`, `services/task-worker/` |
| `area::docs` | `docs/`, `CODEOWNERS`, `.gitlab/merge_request_templates/` |

Data labels:

| Label | Meaning |
| --- | --- |
| `data::none` | No customer, partner, payment, auth, or production data touched |
| `data::synthetic-only` | Uses fake, fixture, local, or staging-safe data only |
| `data::sensitive` | Touches paths or logic that can expose customer, partner, payment, auth, admin, or production data |

Reviewer labels:

| Label | Meaning |
| --- | --- |
| `needs::security` | SecurityEngineer Paperclip gate required |
| `needs::qa` | Quill QA Paperclip gate required |
| `needs::luma` | Luma localization gate required |

Release labels:

| Label | Meaning |
| --- | --- |
| `sentinel::candidate` | Candidate for release/evidence tracking |

## Required Checks By Scope

Green scope:

- MR template complete.
- `lane::autonomous` and `risk::green` labels applied.
- `data::none` or `data::synthetic-only` label applied.
- CI pipeline green.
- All discussions resolved.

Amber scope:

- All Green requirements.
- `risk::amber` label applied.
- Area label applied.
- `needs::security` for auth, permissions, support, admin, partner, TMA,
  Telegram, worker, or data visibility changes.
- `needs::qa` for user-visible behavior.
- Scribe evidence for release candidates.

Red scope:

- All Amber requirements.
- `risk::red` label applied.
- Human owner or Board approval recorded in Paperclip and linked in the MR.
- No production deploy or production secret movement unless the approval says so
  explicitly.

## CI Contract

The monorepo CI contract is checked by `gitlab:ci-contract`, which runs
`scripts/validate_gitlab_ci_contract.py`.

The validator must ensure:

- MR pipelines are enabled through `workflow.rules` for `merge_request_event`.
- Path-gated jobs exist for frontend, admin, partner, backend, Telegram bot, and
  task worker changes.
- Security jobs remain present.
- Manual deploy and package controls remain present.
- The default MR template exists.
- This MR contract document exists.
- Test and build jobs must not use `allow_failure`.
- `CODEOWNERS` and `docs/gitlab/AI_REVIEW_MAP.md` remain present.

## Failed Pipeline Rule

A failed pipeline blocks merge because project setting
`only_allow_merge_if_pipeline_succeeds` is enabled. Phase 5 must still run a
throwaway dry-run MR that deliberately fails CI and records evidence that GitLab
blocks merge.

## Evidence Requirements

For each autonomous MR, Scribe should record:

- MR URL.
- Pipeline URL and status.
- Merge commit SHA when merged.
- Test commands and outputs summarized in the MR.
- Screenshot paths or route traces for UI changes.
- Residual risks and skipped checks.

## Sources

- GitLab description templates: `.gitlab/merge_request_templates/*.md` on the
  default branch.
- GitLab labels API: project labels are managed through `/projects/:id/labels`.
- CyberVPN ownership process: `docs/gitlab/AI_REVIEW_MAP.md`.
