# CyberVPN Autonomy Policy v1

Status: active
Effective date: 2026-05-30
Applies to: Paperclip AI work in `root/CyberVPN`

This policy converts the CyberVPN Paperclip team from ad hoc approvals to a
standing autonomy model. The goal is to let agents take normal Green and Amber
work from Paperclip issue to GitLab merge without the owner being asked at every
step, while keeping Red production and security risks behind explicit human or
Board approval.

## Source Of Truth

The active gates are:

- GitLab project settings and protected branch rules.
- `CODEOWNERS` as the GitLab-visible ownership map.
- `docs/gitlab/AI_REVIEW_MAP.md` for Paperclip reviewer gates.
- `docs/gitlab/AI_MR_CONTRACT.md` and the default MR template for MR evidence.
- Paperclip comments, approvals, and evidence documents linked from the MR.

GitLab CE on this server does not expose required approval rules for this
project, so Paperclip gates are the required approval record until GitLab
approval rules become available.

## Non-Negotiable GitLab Gates

These gates apply to all autonomous work:

- Agents must not push directly to `main` or `master`.
- Implementation branches must start with `ai/`.
- Every code or config change must use a GitLab Merge Request.
- `main` must stay protected with direct push disabled for agents.
- Merge requires a successful GitLab pipeline.
- All GitLab discussions must be resolved before merge.
- Source branches should be deleted after merge.
- Squash is enabled by default.
- No production secrets may be pasted into issues, MR descriptions, comments, or
  logs.

## Risk Classes

### Green

Green work is approved for autonomous merge after CI.

Allowed scope:

- Documentation.
- Tests and fixtures using fake data only.
- Non-sensitive copy and localization.
- Isolated UI that does not touch auth, payments, admin permissions, support,
  customer data, partner data, production deploys, VPN provisioning, Remnawave,
  infrastructure exposure, or secrets.

Required gates:

- MR template is complete.
- Labels include `lane::autonomous`, `risk::green`, and the relevant area/data
  labels.
- GitLab pipeline is green.
- Discussions are resolved.

Merge authority:

- The Paperclip maintainer bot may merge Green MRs without owner approval.

### Amber

Amber work is approved for autonomous merge after reviewer-agent gates.

Allowed scope:

- Support platform work.
- User-generated content.
- Customer, partner, admin, or TMA workflows.
- Data visibility changes that remain inside existing permission boundaries.
- Telegram bot or worker behavior visible to users.
- Non-core notification behavior.

Required gates:

- All Green gates.
- `SecurityEngineer` gate for auth context, permissions, support, admin,
  partner, TMA, Telegram, worker, user-generated content, or data visibility.
- `Quill QA` gate for user-visible behavior.
- `Scribe Release Docs & Evidence Manager` evidence for release candidates and
  merged work.
- `Orion CTO` gate for architecture/API contracts or cross-module contracts.
- The implementing agent must not be the only reviewer for its own MR.

Merge authority:

- The Paperclip maintainer bot may merge Amber MRs without owner approval after
  all required Paperclip gates are linked in the MR and CI is green.

### Red

Red work is not covered by standing autonomy.

Red scope:

- Payments, refunds, billing risk, or subscription charging behavior.
- Auth core, sessions, cookies, 2FA, identity core, or admin permission core.
- Production secrets or secret movement.
- Production deploy, rollback, canary, or release promotion.
- VPN provisioning.
- Remnawave production config.
- Infrastructure exposure, firewalling, public endpoint exposure, or runtime
  topology changes.

Required gates:

- Explicit owner or Board approval in Paperclip.
- SecurityEngineer gate.
- Domain gate: Atlas for infra/Remnawave, Ledger for billing, Orion for
  architecture.
- Green GitLab pipeline unless the approval explicitly authorizes an override.
- Scribe release evidence.

Merge and deploy authority:

- Red MRs must not merge solely because CI is green.
- Red deploys require either a one-time owner override or a pre-signed release
  window that names the scope, commit range, environment, rollback point, and
  expiry.

## Deploy Policy

### Staging

Staging deploys are approved to run automatically after merge to `main` when a
staging target exists and the deploy job uses staging-only credentials.

Requirements before enabling a staging deploy job:

- `STAGING_*` variables exist in GitLab, are masked/protected where applicable,
  and do not grant production access.
- The staging job has `environment: staging`.
- The staging job does not reuse production SSH keys, production database URLs,
  production Telegram tokens, production payment tokens, or production
  Remnawave credentials.
- The staging job writes smoke evidence to the MR, Paperclip issue, or release
  evidence path.

Until those variables and target are present, CI/build/smoke on `main` is the
staging substitute and production remains manual.

### Production

Production deploys are Red.

Allowed production paths:

- One-time owner override, recorded in Paperclip before the deploy.
- Pre-signed release window, recorded in Paperclip before the deploy.

A production approval must include:

- Commit SHA or branch range.
- Environment name.
- Allowed deploy job names.
- Required preflight checks.
- Rollback point.
- Expiry time or release window end.

If preflight fails, the owner or Board must explicitly approve an override before
deploy continues.

## Maintainer Bot Rules

The Paperclip maintainer bot may:

- Create branches and MRs for policy-approved work.
- Merge Green MRs after CI.
- Merge Amber MRs after CI and required Paperclip gates.
- Retarget support branches when needed.
- Delete merged source branches.

The Paperclip maintainer bot must not:

- Approve or merge Red work without owner or Board approval.
- Move production secrets.
- Trigger production deploys without one-time override or pre-signed release
  window.
- Bypass a failed pipeline unless the applicable Red approval explicitly allows
  the override.

## Paperclip Task Routing

Default routing for autonomous work:

- Green: implementer plus CI. Scribe evidence only when release-facing.
- Amber: implementer, SecurityEngineer when sensitive, Quill QA when
  user-visible, Scribe evidence, Orion for architecture/API contracts.
- Red: Board or owner approval first, then SecurityEngineer and domain gate.

Paperclip issues should include:

- Risk class.
- Allowed paths.
- Required gates.
- Branch pattern.
- MR evidence requirements.
- Explicit statement that direct push to `main` is forbidden.

## Upgrade Conditions

Update this policy when:

- GitLab required approval rules become available.
- New agent GitLab tokens are created.
- Staging deploy variables and target are added.
- A new Red domain is introduced.
- The owner changes production deploy approval rules.
