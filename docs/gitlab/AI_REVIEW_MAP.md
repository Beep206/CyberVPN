# CyberVPN AI Review Map

Status: active advisory map
Updated: 2026-05-30
Applies to: Paperclip AI agents working in `root/CyberVPN`

This document is the operational review map for autonomous Paperclip work in the
CyberVPN repository. `CODEOWNERS` mirrors the GitLab-visible owners, while this
document defines the Paperclip process gates that GitLab CE cannot enforce as
required approvals today. Merge authority and risk decisions are governed by
`docs/gitlab/AUTONOMY_POLICY_V1.md`.

## Current GitLab Constraints

- `main` is protected.
- Direct push to `main` is disabled for agents.
- Merge to `main` is restricted to Maintainers.
- GitLab requires successful pipelines before merge.
- GitLab requires all discussions to be resolved before merge.
- GitLab approval settings/rules APIs return `404` on this instance, so required
  reviewer approvals are handled as Paperclip gates plus maintainer merge.

## Autonomy Policy v1

Autonomy Policy v1 is active as of 2026-05-30.

- Green work can merge without owner approval after CI is green and discussions
  are resolved.
- Amber work can merge without owner approval after CI is green, discussions are
  resolved, and required Paperclip gates are complete.
- Red work still requires explicit owner or Board approval before merge or
  production deploy.
- Production deploys are Red even when the code change itself was Green or
  Amber.
- Staging deploys may become automatic after a staging target and staging-only
  credentials exist.

## Branch And MR Rules

Agents must not push directly to `main` or `master`.

Implementation branches must use one of these shapes:

```text
ai/<issue-key>/<agent-key>/<short-name>
ai/<phase>/<short-name>
```

Every autonomous change must open a GitLab Merge Request. The MR description
must include:

- Summary.
- Risk level: Green, Amber, or Red.
- Touched paths.
- Tests or checks run.
- Screenshots or route traces for UI changes.
- Required Paperclip reviewer gates.
- Known limitations.

## GitLab Identities

| Paperclip role | GitLab user | Access | Primary use |
| --- | --- | --- | --- |
| Human owner | `@root` | Owner | Final override and Red approvals |
| Paperclip maintainer bot | `@project_2_bot_47e02027a044988533d001e0f32068e4` | Maintainer | Merge path and maintainer-owned config |
| Helio Backend API Engineer | `@project_2_bot_636d1e9cec59fb2c62c1a196e9ebbe19` | Developer | Backend implementation |
| Neon Customer Frontend Engineer | `@project_2_bot_0ebf743cab9a2612b1090188a0d202d4` | Developer | Customer frontend implementation |
| Nova Frontend/TMA Engineer | `@project_2_bot_78474156d1e0e66966f321d6b7f5cd99` | Developer | Telegram Mini App and frontend implementation |
| Prism Admin Partner Frontend Engineer | `@project_2_bot_935b03b6d9ae0de290d6013f6305a68a` | Developer | Admin and partner frontend implementation |
| Vector Backend Integrations Engineer | `@project_2_bot_d1b79d24eaa7e4d697a18499471878ce` | Developer | Telegram bot, workers, integrations |
| SecurityEngineer | `@project_2_bot_1bc2e283e4524b692d54cee8bc5038a0` | Developer | Security review and sensitive-area changes |
| Quill QA | `@project_2_bot_c28b4531b213a91cac4be03b85d51e53` | Developer | QA verification, regression checks |
| Scribe Release Docs & Evidence Manager | `@project_2_bot_dddce23b58dd40c3c5049137c898ab16` | Developer | Evidence, release notes, review records |

Roles without a dedicated GitLab bot as of this map:

- Orion CTO: Paperclip architecture gate only.
- Lyra Product Designer: Paperclip UX gate only.
- Atlas Platform and Remnawave NodeOps Engineer: Paperclip infra gate only.
- Ledger Billing and Subscription Risk Analyst: Paperclip billing-risk gate only.
- Orbit Mobile VPN Engineer: Paperclip mobile gate only.

Do not add placeholder usernames to `CODEOWNERS`. If a role needs GitLab-level
ownership, create a real GitLab project access token or group first, then update
both `CODEOWNERS` and this map.

## Risk Levels

### Green

Green changes can proceed autonomously through MR, CI, and a maintainer merge
gate:

- Documentation.
- Tests.
- Non-sensitive copy.
- Isolated UI without auth, payment, permissions, support, admin, or customer
  data exposure changes.

Required gates:

- CI pipeline green.
- Discussions resolved.
- Scribe evidence note if release-facing.

Merge authority:

- Paperclip maintainer bot may merge without owner approval.

### Amber

Amber changes can be implemented autonomously, but require Paperclip reviewer
gates before maintainer merge:

- Support tickets.
- User-generated content.
- Admin workflows.
- Partner workflows.
- Telegram Mini App auth-context usage.
- Customer, partner, or admin data visibility.
- Notification or worker behavior visible to users.

Required gates:

- CI pipeline green.
- Discussions resolved.
- SecurityEngineer review complete for data, auth, permission, admin, TMA,
  Telegram, or worker paths.
- Quill QA verification complete for user-visible behavior.
- Orion CTO Paperclip gate complete for architecture-affecting scope.
- Scribe evidence pack complete for release candidates.

Merge authority:

- Paperclip maintainer bot may merge without owner approval after all required
  Paperclip gates are linked from the MR.

### Red

Red changes need explicit human or Board approval before implementation or
merge:

- Payments.
- Auth core, sessions, cookies, 2FA, or identity core.
- Admin permission core.
- Production secrets.
- Production deploy or canary.
- VPN provisioning.
- Remnawave production config.
- Infrastructure exposure.

Required gates:

- Human owner or Board approval.
- SecurityEngineer review.
- Relevant domain gate: Atlas for infra or Remnawave, Ledger for billing,
  Orion for architecture.
- CI pipeline green.
- Scribe release evidence.

Merge authority:

- Owner or Board approval is required. CI alone is never enough for Red scope.

## Path Review Matrix

| Path | Implementer | Required Paperclip gates |
| --- | --- | --- |
| `backend/` | Helio | SecurityEngineer for auth, permissions, admin, support, billing, user data, partner data |
| `backend/src/**/support/**` | Helio | SecurityEngineer, Quill QA, Orion CTO for API contract |
| `backend/src/**/auth/**` | SecurityEngineer or Helio | SecurityEngineer, Orion CTO, human approval if auth core |
| `backend/src/**/permissions/**` | SecurityEngineer or Helio | SecurityEngineer, Orion CTO, human approval if permission core |
| `backend/src/**/billing/**` | Helio | SecurityEngineer, Ledger, human approval if payment behavior changes |
| `frontend/` | Neon or Nova | Quill QA for user-visible changes, SecurityEngineer for auth/TMA/support/data visibility |
| `frontend/src/**/support/**` | Neon or Nova | SecurityEngineer, Quill QA, Lyra UX gate |
| `frontend/src/**/miniapp/**` | Nova or Neon | SecurityEngineer, Quill QA |
| `admin/` | Prism | SecurityEngineer, Quill QA, Lyra UX gate |
| `partner/` | Prism | Quill QA, SecurityEngineer for workspace/data visibility |
| `services/telegram-bot/` | Vector | SecurityEngineer, Quill QA if user-visible |
| `services/task-worker/` | Vector | SecurityEngineer for data/notification/retry behavior |
| `infra/`, `charts/`, `platform-gitops/` | Atlas or maintainer bot | SecurityEngineer, Atlas, human approval for production exposure |
| `docs/` | Scribe | Quill QA for verification docs, SecurityEngineer for security docs |
| `.gitlab-ci.yml` | Maintainer bot or Scribe | SecurityEngineer if security pipeline changes, Quill QA if verification gates change |

## Support Platform Initial Gate

The support ticket platform is Amber by default.

Minimum required gates before support-platform MRs merge:

- Backend API contract: Orion CTO Paperclip gate.
- Backend access control and data isolation: SecurityEngineer gate.
- Customer/TMA/admin/partner UI flows: Quill QA gate.
- User-generated content and internal notes: SecurityEngineer gate.
- Screenshots and command evidence: Scribe gate.

The implementing agent must not be the only reviewer for its own area. When a
single GitLab bot owns both implementation and review paths in `CODEOWNERS`, the
Paperclip gate must name a separate reviewer agent in the MR description.

## Merge Procedure

1. Implementing agent pushes an `ai/*` branch.
2. Implementing agent opens a GitLab MR.
3. MR pipeline runs.
4. Required Paperclip gates are completed and linked in the MR.
5. All GitLab discussions are resolved.
6. Maintainer bot or human owner merges after GitLab reports a green pipeline.

Never merge Red scope solely because CI is green.

Under Autonomy Policy v1, the maintainer bot is allowed to perform step 6 for
Green and Amber MRs without owner approval when the MR evidence proves the
required gates are complete.

## Maintenance

Update this file when:

- A new agent gets a GitLab token.
- A GitLab username changes.
- GitLab Premium/Ultimate approval features become available.
- A new major product area is added.
- A role is removed or paused in Paperclip.
