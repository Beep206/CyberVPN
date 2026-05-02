# Open Questions And Decision Log

Status: draft
Owner: platform (proposed)
Last updated: 2026-04-25
Scope: governance and unresolved rollout decisions
Depends on: `00-current-state-and-discovery.md`, `01-target-architecture-and-scope.md`
Related paths: `03-self-hosted-sentry-platform-bootstrap.md`, `12-alerting-ownership-routing-and-severity-policy.md`

## Decided

| Date | Topic | Decision | Source |
| --- | --- | --- | --- |
| 2026-04-24 | Platform model | Treat Sentry as self-hosted for planning and rollout docs | stakeholder direction |
| 2026-04-24 | Scope model | Runtime-first project split, libraries covered indirectly | repository analysis |
| 2026-04-24 | Desktop model | Split desktop into renderer and native projects | rollout recommendation |
| 2026-04-24 | Wave 1 closure model | Close Wave 1 on a verified baseline, not full production-complete ownership/privacy/alerting for every surface | rollout implementation |
| 2026-04-24 | Wave 1 baseline surfaces | Require dedicated smoke proof for `frontend`, `backend`, `services/task-worker`, `cybervpn_mobile`; carry `admin` and `partner` dedicated smoke into the next wave | rollout implementation |
| 2026-04-24 | Wave 2 closure model | Close Wave 2 with `services/telegram-bot`, `services/node-fleet-controller` and `apps/android-tv` at `baseline_complete`, and carry `apps/desktop-client` into the next wave as explicit native/symbol work | rollout implementation |
| 2026-04-24 | Desktop Wave 3 Step 1 model | Close the first desktop step on renderer/native contract alignment and local validation, while carrying artifact upload, native symbols and smoke proof to the next step | rollout implementation |
| 2026-04-24 | Desktop Wave 3 Step 2 model | Close desktop on `baseline_complete` once CI/release artifact wiring and packaged smoke are in place; keep real-project symbolication proof as residual validation, not as a blocker for baseline status | rollout implementation |
| 2026-04-25 | Governance Wave 4 Step 1 model | Freeze logical teams and baseline alert tiers in `governance-registry.json`, validate them in CI, and treat that registry as the pre-Sentry source of truth for later live routing setup | rollout implementation |
| 2026-04-25 | Governance Wave 4 Step 2 model | Freeze repo-local privacy defaults, scrub markers, replay masking and runtime code expectations in `privacy-baseline.json`, validate them in CI and require explicit minimal-PII hooks in web/backend/worker runtimes before calling privacy baseline complete | rollout implementation |
| 2026-04-25 | Governance Wave 4 Step 3 model | Freeze repo-local symbolication and deploy-marker proof expectations in `release-proof-registry.json`, emit release-evidence manifests in CI/release workflows, record deploy markers only where this repo owns the deploy event, and explicitly mark mobile/store and `helix-*` deploy markers as external-deployer responsibility | rollout implementation |
| 2026-04-25 | Governance Wave 4 Step 4 model | Close the repo-owned roadmap on an explicit production-acceptance registry, keeping baseline rollout completion separate from live self-hosted acceptance so no project is marked accepted without real Sentry/external deployer proof | rollout implementation |

## Open questions

| Topic | Current status | Proposed direction | Owner |
| --- | --- | --- | --- |
| Org owner/admin roster | open | at least 2 human admins plus 1 CI service account | platform |
| Team model | resolved for repo baseline | `web`, `core`, `client-apps`, `platform` are now frozen as logical ownership groups in `governance-registry.json`; only real Sentry team slugs remain to be provisioned | engineering leadership |
| Data residency and retention | open | restrictive defaults under self-hosted policy | platform/security |
| Alert connector targets | open | baseline channels are frozen as GitHub + email + one production ops channel; real connector objects still need to be provisioned in self-hosted Sentry | platform/ops |
| Privacy baseline | resolved for repo baseline | `privacy-baseline.json` now freezes SDK-default-PII=`false`, replay masking, scrub headers/markers and approval checkpoints; only live org/project scrub provisioning remains open | platform/security |
| Release proof baseline | resolved for repo baseline | `release-proof-registry.json` now freezes artifact-evidence and deploy-marker expectations; only live symbolication against self-hosted Sentry and external deployer adoption remain open | platform/runtime owners |
| Production acceptance model | resolved for repo baseline | `production-acceptance-registry.json` now tracks final live blockers per project; acceptance can stay pending without blocking the repo-owned rollout from being considered complete | platform/runtime owners |
| Tunnel policy for public web | open | tunnel for public web, direct path for admin first | web/platform |
| Volume budgets | open | set hard quotas before replay/tracing rollout | platform |
| Production status by surface | open | confirm with owners during rollout intake | runtime owners |
| Desktop rollout scope | resolved for baseline | renderer/native split, release workflow wiring and packaged smoke are implemented; only real-project symbolication proof remains as residual validation | client-apps/platform |

## Follow-up tasks

- Confirm real production status of `desktop-client`, `android-tv`, `telegram-bot`, `helix-*`.
- Confirm self-hosted infra ownership boundary and whether platform operations live in another repository.
- Provision real Sentry team slugs and bind them to the logical teams frozen in `governance-registry.json`.
- Apply the repo-local privacy baseline inside the live self-hosted Sentry org/projects and verify it against a smoke event.
- Validate that uploaded mobile/desktop/TV/native artifacts symbolicate a real event in self-hosted Sentry.
- Confirm which external deployment systems must create the live deploy marker for `cybervpn_mobile`, `helix-adapter` and `helix-node`.
- Assign or confirm live deploy-marker ownership for `frontend`, `admin`, `partner`, `backend`, `task-worker`, `telegram-bot` and `node-fleet-controller`.
- Freeze volume, retention and replay policy before turning on all projects.
- Validate desktop symbolication end-to-end once real Sentry credentials and projects are available in CI.

## Decision hygiene

- Every newly approved decision must be copied into the relevant normative document.
- This log is the holding area for unresolved items, not the final place for stable policy.
