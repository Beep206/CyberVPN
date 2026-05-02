# CyberVPN Platform Foundation Temporary Exceptions Register

**Date:** 2026-04-22  
**Status:** Frozen baseline for `T0.7`

This document is the authoritative register of temporary architectural and operational exceptions allowed during the platform foundation program.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [2026-04-21-platform-foundation-monorepo-inventory.md](2026-04-21-platform-foundation-monorepo-inventory.md)

This register exists so no team can keep a temporary deviation alive without:

- an owner;
- an explicit risk statement;
- a removal phase;
- a removal verification rule.

## 1. Register Rules

Every temporary exception must carry:

- `exception_id`
- `scope`
- `current_behavior`
- `target_behavior`
- `why_exception_exists`
- `risk_if_kept`
- `owner_lane`
- `creation_phase`
- `required_removal_phase`
- `allowed_scope`
- `blocking_status`
- `verification_needed_for_removal`

Rules:

1. This register is authoritative for temporary exceptions in the platform foundation program.
2. No undocumented exception may survive after `T0.7`.
3. “Temporary” without a removal phase is prohibited.
4. “Temporary” without removal verification is prohibited.
5. No exception may survive beyond `P3` without explicit architectural supersession approved in canonical documents.
6. Local development convenience is not automatically a platform exception; it becomes an exception only when it can distort non-local or canonical platform work.

## 2. Summary Table

| Exception ID | Scope | Owner lane | Required removal phase | Blocking status |
|---|---|---|---|---|
| `EX-001` | Compose and VM-based control-plane deployment authority | `infra-platform` | `P3` | blocks `P3` production conformance if still present beyond local-only scope |
| `EX-002` | host-local runtime `.env` secrets in deployed services | `backend-platform` / `transport-backend` / `infra-platform` | `P2` | blocks `P2` secrets delivery alignment |
| `EX-003` | Ansible inventory and vaulted group vars as runtime secret source | `infra-platform` / `security` | `P2` | blocks `P2` secrets-plane alignment |
| `EX-004` | Ansible-managed edge and node bootstrap as steady-state procedure | `infra-platform` | `P3` | blocks `P3` fleet automation conformance |
| `EX-005` | Ansible inventory manifest promotion flow | `infra-platform` | `P2` | blocks `P2` GitOps promotion model |
| `EX-006` | missing canonical staging deploy path | `infra-platform` | `P1` | blocks `P1` non-prod deployment readiness |
| `EX-007` | Promtail remains in stack/docs/prompts | `sre-platform` / `docs-program` | `P2` | blocks `P2` collector convergence |
| `EX-008` | standalone `otel-collector` assumptions remain in stack/config/docs | `sre-platform` / `backend-platform` / `docs-program` | `P2` | blocks `P2` collector convergence |
| `EX-009` | Redis pub/sub SSE browser fan-out remains primary realtime bridge | `transport-backend` | `P2` | blocks `P2` realtime backbone convergence |
| `EX-010` | partial outbox coverage and no canonical NATS dispatcher | `backend-platform` | `P2` | blocks `P2` eventing alignment |
| `EX-011` | obsolete prompts and normative docs describe retired runtime models | `docs-program` | `P1` | blocks clean `P1` execution packets |
| `EX-012` | fleet desired/observed state still encoded in inventories and operator memory | `infra-platform` / `platform-architecture` | `P3` | blocks `P3` Node Fleet Controller conformance |
| `EX-013` | missing live OpenTofu backend evidence and operator-provided credentials for `P1.1` closure | `infra-platform` / `sre-platform` | `P1` | blocks `P1.1` complete and `P1` phase closure, but does not block starting `P1.2+` |
| `EX-014` | missing live non-prod OpenBao apply/bootstrap evidence and operator-provided auth inputs for `P1.2` closure | `infra-platform` / `security` | `P1` | blocks `P1.2` complete and `P1` phase closure, but does not block starting `P1.3+` |
| `EX-015` | missing live shared non-prod NATS apply, bundle install, and JetStream smoke evidence for `P1.3` closure | `infra-platform` / `sre-platform` | `P1` | blocks `P1.3` complete and `P1` phase closure, but does not block starting `P1.4+` |
| `EX-016` | missing live non-prod PostHog apply, bundle install, proxy, TLS, and capture smoke evidence for `P1.4` closure | `infra-platform` / `growth-platform` | `P1` | blocks `P1.4` complete and `P1` phase closure, but does not block starting `P1.5+` |
| `EX-017` | missing live non-prod management-cluster apply, Talos bootstrap, and provider-install evidence for `P1.5` closure | `infra-platform` / `platform-architecture` | `P1` | blocks `P1.5` complete and `P1` phase closure, but does not block starting `P1.6+` |
| `EX-018` | missing live platform GitOps repository bootstrap and Flux reconciliation evidence for `P1.6` closure | `infra-platform` / `platform-architecture` | `P1` | blocks `P1.6` complete and `P1` phase closure, but does not block starting `P1.7+` |
| `EX-019` | missing live external control-plane observability rollout and monitoring evidence for `P1.7` closure | `sre-platform` / `infra-platform` | `P1` | blocks `P1.7` complete and `P1` phase closure, but does not block starting `P1.8+` |
| `EX-020` | missing live control-plane backup and restore evidence for `P1.8` closure | `sre-platform` / `infra-platform` | `P1` | blocks `P1.8` complete and `P1` phase closure, but does not block starting later implementation prep |
| `EX-021` | missing live non-prod workload-cluster creation and network-baseline evidence for `P2.1` closure | `infra-platform` / `platform-architecture` / `sre-platform` | `P2` | blocks `P2.1` complete and `P2` phase closure, but does not block starting `P2.2+` repo-slice work |
| `EX-022` | missing live non-prod platform-services Flux reconciliation and controller readiness evidence for `P2.2` closure | `infra-platform` / `sre-platform` / `security` | `P2` | blocks `P2.2` complete and `P2` phase closure, but does not block starting `P2.3+` repo-slice work |
| `EX-023` | missing live Alloy cutover and retirement evidence for remaining tracked legacy collector surfaces after `P2.3` repo convergence work | `sre-platform` / `infra-platform` / `backend-platform` / `docs-program` | `P2` | blocks `P2.3` complete and `P2` phase closure, but does not block starting later `P2` repo-slice work |
| `EX-024` | missing live workload-cluster data-protection reconciliation and recovery evidence for `P2.4` closure | `sre-platform` / `infra-platform` / `data-platform` / `security` | `P2` | blocks `P2.4` complete and `P2` phase closure, but does not block starting later `P2` repo-slice work |
| `EX-025` | missing live OCI chart publication, GitOps promotion PR, and first-workload Flux rollout evidence for `P2.5` closure | `infra-platform` / `backend-platform` / `sre-platform` / `security` | `P2` | blocks `P2.5` complete and `P2` phase closure, but does not block starting later `P2` repo-slice work |
| `EX-026` | missing live NATS stream creation, dispatcher publish, durable consumer, and replay evidence for `P2.6` closure | `backend-platform` / `transport-backend` / `infra-platform` / `sre-platform` | `P2` | blocks `P2.6` complete and `P2` phase closure, but does not block starting later `P2` repo-slice work |
| `EX-027` | missing live realtime gateway deployment, browser delivery endpoint, and polling-replacement flow evidence for `P2.7` closure | `transport-backend` / `backend-platform` / `infra-platform` / `sre-platform` | `P2` | blocks `P2.7` complete and `P2` phase closure, but does not block starting later `P2` repo-slice work |
| `EX-028` | missing live non-prod rollout, OpenBao-backed secret materialization, and migration-job evidence for `P2.8` closure | `backend-platform` / `infra-platform` / `sre-platform` / `security` | `P2` | blocks `P2.8` complete and `P2` phase closure, but does not block starting later work |
| `EX-029` | missing live production management-cluster apply, L4 endpoint, Talos bootstrap, and provider-install evidence for `P2.9` closure | `infra-platform` / `platform-architecture` / `sre-platform` / `security` | `P2` | blocks `P2.9` complete and `P2` phase closure, but does not block starting later `P2` or `P3` repo-slice work |
| `EX-030` | missing live Node Fleet Controller deployment, durable DB persistence, and NATS publication evidence for `P3.1` closure | `fleet-platform` / `backend-platform` / `infra-platform` / `transport-backend` | `P3` | blocks `P3.1` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-031` | missing live OpenTofu runner wiring, OpenBao bootstrap and unwrap, enrollment, and certificate rotation evidence for `P3.2` closure | `fleet-platform` / `infra-platform` / `security` / `transport-backend` | `P3` | blocks `P3.2` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-032` | missing live external-node baseline reporting, synthetic verification, runtime-adapter acknowledgement, and traffic-eligibility evidence for `P3.3` closure | `fleet-platform` / `sre-platform` / `transport-backend` / `infra-platform` | `P3` | blocks `P3.3` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-033` | missing live operator workflow entry, node-pool reconciliation, and replace/drain/quarantine evidence for `P3.4` closure | `fleet-platform` / `infra-platform` / `transport-backend` | `P3` | blocks `P3.4` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-034` | missing live failover signal ingestion, guarded policy evaluation, and failover workflow evidence for `P3.5` closure | `fleet-platform` / `transport-backend` / `infra-platform` / `security` | `P3` | blocks `P3.5` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-035` | missing live PostHog authoritative capture, identified flag evaluation, and governed frontend event evidence for `P3.6` closure | `growth-platform` / `backend-platform` / `partner-platform` / `transport-backend` | `P3` | blocks `P3.6` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-036` | missing live PostHog dashboard population, deployed checkout/onboarding capture proof, and retention follow-up evidence for `P3.7` closure | `growth-platform` / `backend-platform` / `partner-platform` / `transport-backend` | `P3` | blocks `P3.7` complete and `P3` phase closure, but does not block starting later `P3` repo-slice work |
| `EX-037` | missing live production workload-cluster reconciliation, Flagger canary, CNPG and backup, alerting, and deploy or rollback evidence for `P3.8` closure | `infra-platform` / `backend-platform` / `sre-platform` / `security` / `data-platform` | `P3` | blocks `P3.8` complete and `P3` phase closure, but does not block starting `P3.9` repo-slice work |
| `EX-038` | missing live production drill transcripts, final scorecard completion, and Gate D sign-off evidence for `P3.9` closure | `sre-platform` / `infra-platform` / `backend-platform` / `data-platform` / `growth-platform` / `fleet-platform` / `security` | `P3` | blocks `P3.9` complete, `P3` phase closure, and `Gate D` passed claims |

## 3. Exception Entries

### `EX-001` Compose And VM-Based Control-Plane Deployment Authority

- `scope`: current non-local control-plane deployment and rollout path
- `current_behavior`:
  - legacy VM control-plane rollout remains anchored in:
    - [infra/ansible/playbooks/control-plane-rollout.yml](/home/beep/projects/VPNBussiness/infra/ansible/playbooks/control-plane-rollout.yml:1)
    - [infra/ansible/playbooks/rollback-control-plane.yml](/home/beep/projects/VPNBussiness/infra/ansible/playbooks/rollback-control-plane.yml:1)
    - [docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md:1)
  - local topology and shared service composition remain defined in [infra/docker-compose.yml](/home/beep/projects/VPNBussiness/infra/docker-compose.yml:1)
- `target_behavior`: Kubernetes workload clusters plus GitOps own deployed control-plane state; Compose stays local-dev only
- `why_exception_exists`: migration to Talos/CAPI/Flux is not implemented yet
- `risk_if_kept`: legacy VM rollout authority continues to compete with GitOps and prevents production conformance
- `owner_lane`: `infra-platform`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P3`
- `allowed_scope`: local development is allowed; non-local deployment authority is temporary only
- `blocking_status`: tolerated before `P3`, blocking if still used as production authority at `P3`
- `verification_needed_for_removal`:
  - non-prod and prod control-plane rollout no longer depend on Ansible control-plane playbooks
  - Compose is not the authority for deployed control-plane state
  - GitOps and workload-cluster rollout evidence exists

### `EX-002` Host-Local Runtime `.env` Secrets In Deployed Services

- `scope`: deployed runtime services still loading sensitive config from host-local `.env`
- `current_behavior`:
  - [backend/.env](/home/beep/projects/VPNBussiness/backend/.env:1)
  - [services/task-worker/.env](/home/beep/projects/VPNBussiness/services/task-worker/.env:1)
  - [services/telegram-bot/.env](/home/beep/projects/VPNBussiness/services/telegram-bot/.env:1)
  - [infra/.env](/home/beep/projects/VPNBussiness/infra/.env:1)
  - [infra/subscription/.env](/home/beep/projects/VPNBussiness/infra/subscription/.env:1)
- `target_behavior`: deployed runtime secrets arrive through `OpenBao`-managed delivery; local `.env` remains local-dev only
- `why_exception_exists`: OpenBao-backed runtime secret delivery is not implemented yet
- `risk_if_kept`: secret sprawl, poor auditability, environment drift, manual rotation overhead
- `owner_lane`: `backend-platform` / `transport-backend` / `infra-platform`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: local development only after removal; deployed environments are temporary exception scope
- `blocking_status`: tolerated in `P1`, blocking for `P2` application/platform rollout alignment
- `verification_needed_for_removal`:
  - deployed runtime services no longer require host-local `.env` for secrets
  - OpenBao/VSO or equivalent target-state secret delivery is proven in non-prod
  - rotated secret evidence shows removal of host-local runtime dependency

### `EX-003` Ansible Inventory And Vaulted Group Vars As Runtime Secret Source

- `scope`: inventory-bound secrets and vaulted group vars acting as runtime secret authority
- `current_behavior`:
  - [infra/ansible/inventories/staging/group_vars](/home/beep/projects/VPNBussiness/infra/ansible/inventories/staging/group_vars:1)
  - [infra/ansible/inventories/production/group_vars](/home/beep/projects/VPNBussiness/infra/ansible/inventories/production/group_vars:1)
  - [docs/secret-rotation.md](/home/beep/projects/VPNBussiness/docs/secret-rotation.md:1)
- `target_behavior`: OpenBao owns deployed secret and identity material; inventory files stop acting as runtime secrets-plane
- `why_exception_exists`: current rollout bridge still depends on Ansible inventory and vaulted vars
- `risk_if_kept`: secrets remain tied to rollout tooling, not to central secrets-plane governance
- `owner_lane`: `infra-platform` / `security`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: migration bridge only
- `blocking_status`: tolerated in `P1`, blocking for `P2` secrets-plane conformance
- `verification_needed_for_removal`:
  - runtime secret material is removed from inventory vaults except explicitly approved break-glass items
  - OpenBao paths and auth mounts are used for deployed runtime secret access
  - secret rotation runbook no longer depends on inventory-vault authority

### `EX-004` Ansible-Managed Edge And Node Bootstrap As Steady-State Procedure

- `scope`: external edge/VPN nodes still depend on operator-sequenced Ansible bootstrap and rollout
- `current_behavior`:
  - [infra/ansible/README.md](/home/beep/projects/VPNBussiness/infra/ansible/README.md:1)
  - [infra/ansible/playbooks/edge-bootstrap.yml](/home/beep/projects/VPNBussiness/infra/ansible/playbooks/edge-bootstrap.yml:1)
  - [infra/ansible/playbooks/remnawave-rollout.yml](/home/beep/projects/VPNBussiness/infra/ansible/playbooks/remnawave-rollout.yml:1)
  - [infra/ansible/playbooks/helix-rollout.yml](/home/beep/projects/VPNBussiness/infra/ansible/playbooks/helix-rollout.yml:1)
  - [infra/ansible/playbooks/alloy-rollout.yml](/home/beep/projects/VPNBussiness/infra/ansible/playbooks/alloy-rollout.yml:1)
- `target_behavior`: Node Fleet Controller owns provisioning, replacement, drain, quarantine, bootstrap, and traffic-eligibility workflows
- `why_exception_exists`: controller workflows do not exist yet
- `risk_if_kept`: node lifecycle remains manual, hard to audit, slow to scale, and difficult to fail over automatically
- `owner_lane`: `infra-platform`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P3`
- `allowed_scope`: migration bridge and break-glass only
- `blocking_status`: tolerated through `P2`, blocking for `P3` fleet conformance
- `verification_needed_for_removal`:
  - controller-driven `node-add`, `replace`, `drain`, and `quarantine` flows exist
  - Ansible node rollout is documented as break-glass only
  - steady-state node provisioning no longer depends on operator playbook sequencing

### `EX-005` Ansible Inventory Manifest Promotion Flow

- `scope`: image promotion still mutates Ansible inventory release manifests
- `current_behavior`:
  - [.github/workflows/control-plane-promote.yml](/home/beep/projects/VPNBussiness/.github/workflows/control-plane-promote.yml:1)
  - promotion target file under `infra/ansible/inventories/*/group_vars/control_plane_*/release.yml`
- `target_behavior`: promotion changes flow through GitOps repo and deployment-state repos, not inventory manifests
- `why_exception_exists`: platform GitOps promotion path is not implemented yet
- `risk_if_kept`: inventory mutation remains coupled to release flow and competes with GitOps target model
- `owner_lane`: `infra-platform`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: migration-era control-plane only
- `blocking_status`: tolerated in `P1`, blocking for `P2` rollout model convergence
- `verification_needed_for_removal`:
  - promotion PRs modify GitOps deployment state instead of Ansible inventory manifests
  - control-plane-promote workflow is retired or explicitly demoted to legacy-only status
  - rollout evidence references GitOps reconciliation, not inventory edits

### `EX-006` Missing Canonical Staging Deploy Path

- `scope`: no real canonical non-prod deployment workflow exists yet
- `current_behavior`:
  - [.github/workflows/deploy-staging.yml](/home/beep/projects/VPNBussiness/.github/workflows/deploy-staging.yml:1) is a placeholder summary job
- `target_behavior`: non-prod deployment path is canonical, repeatable, and aligned with GitOps/bootstrap model
- `why_exception_exists`: non-prod GitOps and environment bootstrap are not implemented yet
- `risk_if_kept`: teams may invent unofficial staging deploy paths or treat placeholder workflow as sufficient
- `owner_lane`: `infra-platform`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P1`
- `allowed_scope`: temporary only until non-prod platform substrate exists
- `blocking_status`: blocking for `P1` completion
- `verification_needed_for_removal`:
  - canonical non-prod deployment path exists and is documented
  - placeholder workflow is removed or replaced by real deployment validation
  - non-prod deploy evidence references the canonical path

### `EX-007` Promtail Remains In Stack, Docs, Or Prompts

- `scope`: `promtail` is still present in stack definitions and normative guidance
- `current_behavior`:
  - [infra/docker-compose.yml](/home/beep/projects/VPNBussiness/infra/docker-compose.yml:774)
  - [docs/CYBERVPN_FULL_DESCRIPTION.md](/home/beep/projects/VPNBussiness/docs/CYBERVPN_FULL_DESCRIPTION.md:507)
  - [docs/PROJECT_OVERVIEW.md](/home/beep/projects/VPNBussiness/docs/PROJECT_OVERVIEW.md:276)
  - [docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md](/home/beep/projects/VPNBussiness/docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md:616)
  - [docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md](/home/beep/projects/VPNBussiness/docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md:910)
- `target_behavior`: `Alloy` is the only target-state collector described for platform rollout
- `why_exception_exists`: local stack and old documentation were created before collector convergence decision was frozen
- `risk_if_kept`: deprecated log collector keeps re-entering implementation and docs
- `owner_lane`: `sre-platform` / `docs-program`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: none beyond transition cleanup
- `blocking_status`: tolerated in `P1`, blocking for `P2` collector convergence
- `verification_needed_for_removal`:
  - Promtail is removed from normative docs, prompts, and active stack paths
  - inventory marks Promtail as retired with no active production/non-prod dependency
  - evidence pack shows Alloy-only target collector posture

### `EX-008` Standalone `otel-collector` Assumptions Remain In Stack, Config, Or Docs

- `scope`: backend and local monitoring still assume a standalone `otel-collector`
- `current_behavior`:
  - [infra/docker-compose.yml](/home/beep/projects/VPNBussiness/infra/docker-compose.yml:674)
  - [infra/prometheus/prometheus.yml](/home/beep/projects/VPNBussiness/infra/prometheus/prometheus.yml:107)
  - [backend/src/config/settings.py](/home/beep/projects/VPNBussiness/backend/src/config/settings.py:207)
  - [docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md](/home/beep/projects/VPNBussiness/docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md:661)
- `target_behavior`: OTLP and collector flows converge on `Alloy` deployment modes
- `why_exception_exists`: old local monitoring topology predates the collector unification decision
- `risk_if_kept`: applications and docs continue targeting the wrong collector architecture
- `owner_lane`: `sre-platform` / `backend-platform` / `docs-program`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: temporary local migration bridge only
- `blocking_status`: tolerated in `P1`, blocking for `P2` collector convergence
- `verification_needed_for_removal`:
  - application defaults no longer point at standalone `otel-collector`
  - local and non-prod observability docs point at Alloy deployment modes
  - Prometheus scrape and health assumptions no longer refer to standalone OTEL collector as the target posture

### `EX-009` Redis Pub/Sub SSE Browser Fan-Out Remains Primary Realtime Bridge

- `scope`: browser fan-out still depends on Redis pub/sub SSE path outside canonical backbone
- `current_behavior`:
  - [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)
  - Redis channel `cybervpn:sse:events`
- `target_behavior`: upstream trigger path becomes `transactional outbox -> NATS -> realtime gateway`, with SSE/WebSocket only as delivery mechanics
- `why_exception_exists`: canonical NATS backbone and realtime gateway integration are not implemented yet
- `risk_if_kept`: realtime delivery remains partially disconnected from durable event publication and replay model
- `owner_lane`: `transport-backend`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: temporary browser fan-out only
- `blocking_status`: blocking for `P2` eventing/realtime alignment if still primary
- `verification_needed_for_removal`:
  - realtime gateway consumes canonical upstream events from NATS-backed paths
  - Redis pub/sub is removed or explicitly demoted to non-authoritative compatibility glue
  - replay and lag evidence exists for the canonical realtime path

### `EX-010` Partial Outbox Coverage And No Canonical NATS Dispatcher

- `scope`: existing outbox remains partial and partner-scoped; no general canonical dispatcher to NATS exists
- `current_behavior`:
  - [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)
- `target_behavior`: business-critical publication boundary is canonical and service-relevant event families flow through outbox to `NATS`
- `why_exception_exists`: dispatcher and broader event-family coverage belong to later phases
- `risk_if_kept`: services continue mixing direct publish paths, local events, and partial durable publication
- `owner_lane`: `backend-platform`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P2`
- `allowed_scope`: temporary partial coverage only
- `blocking_status`: blocking for `P2` canonical eventing alignment
- `verification_needed_for_removal`:
  - canonical dispatcher exists for business-critical events
  - outbox coverage extends beyond the current partner-scoped subset where required by target-state
  - event consumers and replay evidence reference the canonical dispatcher path

### `EX-011` Obsolete Prompts And Normative Docs Describe Retired Runtime Models

- `scope`: prompts and docs can still reintroduce deprecated components or workflows
- `current_behavior`:
  - [docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md](/home/beep/projects/VPNBussiness/docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md:1)
  - [docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md](/home/beep/projects/VPNBussiness/docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md:1)
  - [docs/CYBERVPN_FULL_DESCRIPTION.md](/home/beep/projects/VPNBussiness/docs/CYBERVPN_FULL_DESCRIPTION.md:1)
  - [docs/PROJECT_OVERVIEW.md](/home/beep/projects/VPNBussiness/docs/PROJECT_OVERVIEW.md:1)
- `target_behavior`: prompts and normative docs reflect frozen target-state decisions and do not steer implementation back to retired models
- `why_exception_exists`: legacy material predates the current platform-foundation target-state
- `risk_if_kept`: implementation packets and contributors continue to recreate deprecated patterns
- `owner_lane`: `docs-program`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P1`
- `allowed_scope`: descriptive historical context only, not normative guidance
- `blocking_status`: blocking for clean `P1` execution and implementation packet authoring
- `verification_needed_for_removal`:
  - prompts no longer prescribe `promtail`, standalone `otel-collector`, or obsolete rollout models
  - descriptive docs are either updated or explicitly marked non-normative historical context
  - new implementation packets reference canonical platform documents instead

### `EX-012` Fleet Desired And Observed State Still Encoded In Inventories And Operator Memory

- `scope`: fleet desired state, node metadata, and rollout memory still live in inventories, runbooks, and operator sequencing instead of a durable controller store
- `current_behavior`:
  - [infra/ansible/inventories/staging/group_vars](/home/beep/projects/VPNBussiness/infra/ansible/inventories/staging/group_vars:1)
  - [infra/ansible/inventories/production/group_vars](/home/beep/projects/VPNBussiness/infra/ansible/inventories/production/group_vars:1)
  - [infra/ansible/README.md](/home/beep/projects/VPNBussiness/infra/ansible/README.md:1)
- `target_behavior`: Node Fleet Controller DB owns desired state, observed state, request lifecycle, and traffic eligibility
- `why_exception_exists`: controller durable model is frozen, but service implementation does not exist yet
- `risk_if_kept`: capacity, failover, bootstrap, and quarantine behavior remain hard to reconcile, audit, and automate
- `owner_lane`: `infra-platform` / `platform-architecture`
- `creation_phase`: `pre-P0`
- `required_removal_phase`: `P3`
- `allowed_scope`: migration bridge and break-glass only
- `blocking_status`: tolerated through `P2`, blocking for `P3` fleet control-plane conformance
- `verification_needed_for_removal`:
  - controller DB exists and owns fleet desired/observed state
  - inventories no longer act as the durable fleet state source
  - operator runbooks reference controller requests and lifecycle state, not implicit inventory truth

### `EX-013` Missing Live OpenTofu Backend Evidence And Operator-Provided Credentials For `P1.1` Closure

- `scope`: `P1.1` cannot be declared complete from the current workspace because real remote-backend evidence depends on operator-provided backend config and cloud credentials that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo migration slice for `P1.1` is implemented and validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-1-opentofu-migration/evidence-pack.md:1) explicitly records that no `backend.hcl` files or relevant env credentials are present in the current workspace
  - [rollback-note.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-1-opentofu-migration/rollback-note.md:1) exists, but owner acknowledgement is still pending
  - [capture_opentofu_cutover_evidence.sh](/home/beep/projects/VPNBussiness/infra/scripts/capture_opentofu_cutover_evidence.sh:1) and `make tofu-capture-cutover-evidence` exist, but have not been run against real remote backends yet
- `target_behavior`: operator-approved real remote-backend evidence exists for the in-scope live stacks, including `tofu init`, `state pull` backup, reviewed `tofu plan`, archived evidence, and rollback-owner acknowledgement
- `why_exception_exists`: secrets and backend config are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P1.1` could be treated as “finished enough” without proving real backend cutover posture; later packets could inherit unverified assumptions about state access and rollback safety
- `owner_lane`: `infra-platform` / `sre-platform`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.2+` foundational build work to begin; does not allow `P1.1 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.1` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided `backend.hcl` and cloud credentials are supplied out of band
  - `make tofu-capture-cutover-evidence` or equivalent approved command is executed against real remote backends
  - evidence bundle records `state pull` backup, `plan` result, and no unexplained migration drift
  - rollback note owner acknowledgement is completed

### `EX-014` Missing Live Non-Prod OpenBao Apply Or Bootstrap Evidence And Operator-Provided Auth Inputs For `P1.2` Closure

- `scope`: `P1.2` cannot be declared complete from the current workspace because real non-prod `OpenBao` bring-up depends on operator-provided backend config, Hetzner and AWS credentials, and issuer-specific auth inputs that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P1.2` is implemented and validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-2-openbao-nonprod-foundation/evidence-pack.md:1) explicitly records that no live `backend.hcl`, cloud credentials, or operator OIDC/JWT inputs are present in the current workspace
  - [2026-04-22-platform-foundation-p1-2-openbao-nonprod-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-2-openbao-nonprod-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/openbao_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/openbao_bootstrap.py:1) and [infra/tests/test_openbao_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_openbao_bootstrap.py:1) exist, but have not been exercised against a real host yet
- `target_behavior`: operator-approved non-prod stack apply exists, `OpenBao` is initialized and baseline-configured on the live host, and evidence exists for KMS-backed service start, baseline namespace/auth/secrets/policy layout, and a `kv` smoke path
- `why_exception_exists`: cloud credentials, backend config, and real operator auth issuer inputs are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P1.2` could be treated as “finished enough” without proving that the non-prod secrets plane actually boots, unseals, initializes, and accepts the frozen baseline; later packets could inherit unverified assumptions about auth and bootstrap posture
- `owner_lane`: `infra-platform` / `security`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.3+` foundational work to proceed in parallel; does not allow `P1.2 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.2` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided `backend.hcl`, `terraform.tfvars`, `TF_VAR_hcloud_token`, and AWS credentials are supplied out of band
  - live `tofu init/plan/apply` evidence exists for `infra/terraform/live/staging/openbao`
  - host bootstrap evidence exists for:
    - `/etc/openbao/openbao.env`
    - `systemctl start openbao`
    - `bao status`
    - `bao operator init`
    - baseline namespace/auth/secrets/policy apply
    - file audit enable
    - `kv` smoke read/write
  - real operator auth issuer inputs are attached for `oidc-operators`, or the residual is explicitly split into a later auth-configuration packet instead of being left implicit

### `EX-015` Missing Live Shared Non-Prod NATS Apply, Bundle Install, And JetStream Smoke Evidence For `P1.3` Closure

- `scope`: `P1.3` cannot be declared complete from the current workspace because real shared non-prod `NATS` bring-up depends on operator-provided backend config, Hetzner credentials, and live node access that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P1.3` is implemented and validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-3-nats-nonprod-foundation/evidence-pack.md:1) explicitly records that no live `backend.hcl`, `TF_VAR_hcloud_token`, or real node outputs are present in the current workspace
  - [2026-04-22-platform-foundation-p1-3-nats-nonprod-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-3-nats-nonprod-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/nats_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/nats_bootstrap.py:1) and [infra/tests/test_nats_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_nats_bootstrap.py:1) exist, but have not been exercised against real hosts yet
- `target_behavior`: operator-approved non-prod stack apply exists, the rendered bundle is installed on all three nodes, the cluster forms successfully, and evidence exists for stream create/publish/consume, replay, and exporter scraping
- `why_exception_exists`: cloud credentials, backend config, and live node access are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P1.3` could be treated as “finished enough” without proving that the non-prod event backbone actually forms a cluster, accepts JetStream traffic, replays correctly, and exposes its metrics safely; later packets could inherit unverified assumptions about cluster reachability and credential posture
- `owner_lane`: `infra-platform` / `sre-platform`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.4+` foundational work to proceed in parallel; does not allow `P1.3 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.3` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided `backend.hcl`, `terraform.tfvars`, and `TF_VAR_hcloud_token` are supplied out of band
  - live `tofu init/plan/apply` evidence exists for `infra/terraform/live/staging/nats`
  - bundle-install evidence exists for all three nodes
  - cluster evidence exists for:
    - `nats server report jetstream`
    - stream create
    - publish and consume
    - replay or consumer redelivery proof
    - Prometheus exporter scrape
  - generated route or account credentials have been rotated, replaced, or otherwise reheated through an explicit operator rehearsal

### `EX-016` Missing Live Non-Prod PostHog Apply, Bundle Install, Proxy, TLS, And Capture Smoke Evidence For `P1.4` Closure

- `scope`: `P1.4` cannot be declared complete from the current workspace because real non-prod `PostHog` bring-up depends on operator-provided backend config, Hetzner credentials, DNS, and live domain inputs that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P1.4` is implemented and validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-4-posthog-nonprod-foundation/evidence-pack.md:1) explicitly records that no live `backend.hcl`, `TF_VAR_hcloud_token`, or real domain inputs are present in the current workspace
  - [2026-04-22-platform-foundation-p1-4-posthog-nonprod-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-4-posthog-nonprod-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/posthog_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/posthog_bootstrap.py:1) and [infra/tests/test_posthog_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_posthog_bootstrap.py:1) exist, but have not been exercised against a real host yet
- `target_behavior`: operator-approved non-prod stack apply exists, the rendered bundle is installed on the live host, the domain serves the `NGINX`-fronted PostHog instance with TLS, and evidence exists for protected-UI access, capture smoke, and baseline backup execution
- `why_exception_exists`: cloud credentials, backend config, and real domain inputs are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P1.4` could be treated as “finished enough” without proving that the non-prod product-intelligence host actually serves traffic, terminates TLS, protects the UI path, and accepts product analytics requests safely; later packets could inherit unverified assumptions about proxy posture and access control
- `owner_lane`: `infra-platform` / `growth-platform`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.5+` foundational work to proceed in parallel; does not allow `P1.4 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.4` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided `backend.hcl`, `terraform.tfvars`, and `TF_VAR_hcloud_token` are supplied out of band
  - live `tofu init/plan/apply` evidence exists for `infra/terraform/live/staging/posthog`
  - bundle-install evidence exists on the live host
  - live evidence exists for:
    - `NGINX` serving the configured domain
    - TLS issuance
    - protected-UI login or access
    - capture or identify smoke
    - baseline local backup execution

### `EX-017` Missing Live Non-Prod Management-Cluster Apply, Talos Bootstrap, And Provider-Install Evidence For `P1.5` Closure

- `scope`: `P1.5` cannot be declared complete from the current workspace because real non-prod management-cluster bring-up depends on operator-provided backend config, Hetzner credentials, validated Talos image inputs, and live provider-install inputs that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P1.5` is implemented and validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-5-nonprod-mgmt-foundation/evidence-pack.md:1) explicitly records that no live `backend.hcl`, `TF_VAR_hcloud_token`, validated Talos image or snapshot id, or real node outputs are present in the current workspace
  - [2026-04-22-platform-foundation-p1-5-nonprod-mgmt-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-5-nonprod-mgmt-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/nonprod_mgmt_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/nonprod_mgmt_bootstrap.py:1) and [infra/tests/test_nonprod_mgmt_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_nonprod_mgmt_bootstrap.py:1) exist, but have not been exercised against a real Talos management cluster yet
- `target_behavior`: operator-approved non-prod management-cluster apply exists, Talos bootstrap succeeds on the live nodes, sensitive client outputs are captured out of band, and evidence exists for Cluster API core plus Talos provider install on the running management cluster
- `why_exception_exists`: cloud credentials, backend config, validated Talos image inputs, and real provider-install inputs are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P1.5` could be treated as “finished enough” without proving that the non-prod management cluster actually boots, exposes the frozen endpoint, returns working `talosconfig` and `kubeconfig`, and accepts the pinned `clusterctl` bootstrap path; later packets could inherit unverified assumptions about the workload-cluster control substrate
- `owner_lane`: `infra-platform` / `platform-architecture`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.6+` foundational work to proceed in parallel; does not allow `P1.5 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.5` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided `backend.hcl`, `terraform.tfvars`, and `TF_VAR_hcloud_token` are supplied out of band
  - a validated Talos Hetzner image or snapshot id is attached to the live change record
  - live `tofu init/plan/apply` evidence exists for `infra/terraform/live/staging/nonprod-mgmt`
  - live Talos evidence exists for:
    - `tofu output -raw talosconfig`
    - `tofu output -raw kubeconfig_raw`
    - successful `talosctl health` or equivalent bootstrap proof against the endpoint
    - successful `kubectl get nodes`
  - management-cluster bootstrap evidence exists for:
    - `bash install-capi-core.sh`
    - a validated `CAPH_COMPONENTS_URL`
    - `bash install-caph.sh`
    - running controller pods for Cluster API core and Talos providers
    - explicit record of the CAPH install source used

### `EX-018` Missing Live Platform GitOps Repository Bootstrap And Flux Reconciliation Evidence For `P1.6` Closure

- `scope`: `P1.6` cannot be declared complete from the current workspace because real GitOps bootstrap depends on operator-provided GitHub repository inputs, GitHub bootstrap credentials, and a live `nonprod-mgmt` kubeconfig that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P1.6` is implemented and validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-6-platform-gitops-and-flux-bootstrap/evidence-pack.md:1) explicitly records that no live GitHub owner or repository inputs, `GITHUB_TOKEN`, or real `nonprod-mgmt` kubeconfig are present in the current workspace
  - [2026-04-22-platform-foundation-p1-6-platform-gitops-and-flux-bootstrap-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-6-platform-gitops-and-flux-bootstrap-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/platform_gitops_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/platform_gitops_bootstrap.py:1) and [infra/tests/test_platform_gitops_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_platform_gitops_bootstrap.py:1) exist, but have not been exercised against a real GitHub repository or running Flux installation yet
- `target_behavior`: operator-approved `platform-gitops` repository exists, Flux is bootstrapped onto `nonprod-mgmt` using the frozen GitHub SSH deploy-key posture, and evidence exists for repository bootstrap, controller installation, and baseline reconciliation checks
- `why_exception_exists`: GitHub bootstrap credentials, repository ownership inputs, and live cluster credentials are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P1.6` could be treated as “finished enough” without proving that the separate desired-state repository actually exists, that Flux can bootstrap from it safely, and that the cluster reconciler is running against the frozen source-of-truth boundary; later packets could inherit unverified assumptions about GitOps availability
- `owner_lane`: `infra-platform` / `platform-architecture`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.7+` foundational work to proceed in parallel; does not allow `P1.6 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.6` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided GitHub owner, repository, and bootstrap credential inputs are supplied out of band
  - the rendered `platform-gitops` scaffold is committed to the real target repository
  - live `flux bootstrap github --token-auth=false` evidence exists against `nonprod-mgmt`
  - live Flux evidence exists for:
    - `flux check`
    - `flux get sources git -A`
    - `flux get kustomizations -A`
    - `kubectl -n flux-system get deploy`
  - explicit record exists for the bootstrap repository URL, branch, and cluster path used

### `EX-019` Missing Live External Control-Plane Observability Rollout And Monitoring Evidence For `P1.7` Closure

- `scope`: `P1.7` cannot be declared complete from the current workspace because real control-plane observability closure depends on live host rollout onto the `OpenBao`, `NATS`, and `PostHog` non-prod VMs plus real monitoring-host handoff and runtime scrape or log evidence
- `current_behavior`:
  - repo slice for `P1.7` is implemented and locally validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-7-control-plane-observability/evidence-pack.md:1) explicitly records that no live bundle rollout, no Prometheus `file_sd` handoff, and no Grafana or Loki runtime evidence are present in the current workspace
  - [2026-04-22-platform-foundation-p1-7-control-plane-observability-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-7-control-plane-observability-execution-packet.md:1) documents the exact live closure requirements
  - [infra/scripts/control_plane_observability.py](/home/beep/projects/VPNBussiness/infra/scripts/control_plane_observability.py:1) and [infra/tests/test_control_plane_observability.py](/home/beep/projects/VPNBussiness/infra/tests/test_control_plane_observability.py:1) exist, but have not been exercised against real non-prod control-plane hosts yet
- `target_behavior`: the real `OpenBao`, `NATS`, and `PostHog` non-prod VMs run the rendered Alloy bundle, Prometheus scrapes the generated `alloy-control-plane` and `openbao` targets successfully, Loki receives logs from the new control-plane VMs, and the dedicated Grafana dashboard shows live non-prod data
- `why_exception_exists`: live Hetzner stacks, real host access, monitoring-host `file_sd` directories, real Loki credentials, and running Grafana/Prometheus evidence are intentionally outside git and absent from the current session
- `risk_if_kept`: the team could treat external control-plane observability as “done enough” without proving that the real non-prod control planes are actually visible through the canonical collector, scrape, log, and dashboard surfaces; later packets could inherit unverified monitoring assumptions
- `owner_lane`: `sre-platform` / `infra-platform`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows `P1.8+` foundational work to proceed in parallel; does not allow `P1.7 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P1` execution, but blocking for `P1.7` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - operator-provided live node outputs are supplied out of band from:
    - `infra/terraform/live/staging/openbao`
    - `infra/terraform/live/staging/nats`
    - `infra/terraform/live/staging/posthog`
  - a live bundle render is produced from those outputs
  - successful Alloy installation evidence exists for the real `OpenBao`, `NATS`, and `PostHog` non-prod VMs
  - live Prometheus evidence exists for:
    - `up{job="alloy-control-plane"}`
    - `up{job="openbao"}`
    - continued `up{job="nats-exporter"}`
  - live Loki or Grafana evidence exists showing control-plane logs from all three VM classes
  - an explicit operator record exists that `nonprod-mgmt` host-level rollout was intentionally excluded from `P1.7`

### `EX-020` Missing Live Control-Plane Backup And Restore Evidence For `P1.8` Closure

- `scope`: `P1.8` cannot be declared complete from the current workspace because real closure depends on live backup captures and at least one restore or rebuild proof for the new non-prod control planes and management-cluster metadata layer
- `current_behavior`:
  - repo slice for `P1.8` is implemented and locally validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p1-8-control-plane-backup-and-restore/evidence-pack.md:1) explicitly records that no live `OpenBao`, `NATS`, `Talos`, or `PostHog` backup or restore evidence exists in the current workspace
  - [2026-04-22-platform-foundation-p1-8-control-plane-backup-and-restore-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p1-8-control-plane-backup-and-restore-execution-packet.md:1) documents the exact live closure requirements
  - [infra/scripts/control_plane_recovery.py](/home/beep/projects/VPNBussiness/infra/scripts/control_plane_recovery.py:1) and [infra/tests/test_control_plane_recovery.py](/home/beep/projects/VPNBussiness/infra/tests/test_control_plane_recovery.py:1) exist, but have not been executed against real non-prod stacks yet
- `target_behavior`: the real non-prod control planes have reproducible backup artifacts, management-cluster metadata backup artifacts, and attached restore or rebuild evidence consistent with the frozen operator bundle and runbook
- `why_exception_exists`: required secrets, API credentials, cluster credentials, and live non-prod infrastructure are intentionally outside git and absent from the current session
- `risk_if_kept`: the team could believe backup and DR are “good enough” without proving that the covered control-plane systems can actually be recovered from captured artifacts; later phase gates could inherit false confidence about recoverability
- `owner_lane`: `sre-platform` / `infra-platform`
- `creation_phase`: `P1`
- `required_removal_phase`: `P1`
- `allowed_scope`: allows later implementation work to proceed in parallel; does not allow `P1.8 complete`, `P1 complete`, or `Gate B passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but blocking for `P1.8` closure and `P1` phase closure
- `verification_needed_for_removal`:
  - real bundle render exists from current non-prod stack outputs
  - live `OpenBao` snapshot capture evidence exists
  - live `NATS` account backup evidence exists
  - live `Talos` `etcd` snapshot and machine-config backup evidence exists
  - live `PostHog` backup retrieval evidence exists
  - at least one restore or rebuild proof exists for:
    - `OpenBao` snapshot install
    - `NATS` restore or rebuild from backup
    - `Talos` recovery using `bootstrap --recover-from`

### `EX-021` Missing Live Non-Prod Workload-Cluster Creation And Network-Baseline Evidence For `P2.1` Closure

- `scope`: `P2.1` cannot be declared complete from the current workspace because real closure depends on a live `nonprod-mgmt` management cluster, an operator-validated `CAPH_TEMPLATE_URL`, provider credentials, and actual workload-cluster or edge-entry evidence that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.1` is implemented and locally validated
  - [evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-1-workload-cluster-bootstrap/evidence-pack.md:1) explicitly records that no live `nonprod-mgmt` kubeconfig, no validated `CAPH_TEMPLATE_URL`, no provider credentials, and no real Cloudflare or L4 evidence are present in the current workspace
  - [2026-04-22-platform-foundation-p2-1-workload-cluster-bootstrap-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-1-workload-cluster-bootstrap-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/workload_cluster_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/workload_cluster_bootstrap.py:1) and [infra/tests/test_workload_cluster_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_workload_cluster_bootstrap.py:1) exist, but have not been exercised against a real management cluster or real `platform-gitops` handoff yet
- `target_behavior`: operator-approved workload-cluster generation and reconciliation evidence exists for `nonprod-hetzner-hel1-core`, and the cluster-facing network baseline is attached through explicit provider-L4 and Cloudflare edge intent records
- `why_exception_exists`: live management-cluster access, provider credentials, validated provider templates, and real edge or load-balancer artifacts are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.1` could be treated as “finished enough” without proving that the first workload-cluster substrate actually reconciles from `nonprod-mgmt`, that the frozen workload-cluster id and path work in practice, or that the edge-entry baseline exists beyond repository intent; later `P2` packets could inherit false assumptions about the workload substrate
- `owner_lane`: `infra-platform` / `platform-architecture` / `sre-platform`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows `P2.2+` repo and validation work to proceed in parallel; does not allow `P2.1 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.1` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - operator-provided access exists to the live `nonprod-mgmt` cluster
  - an operator-validated `CAPH_TEMPLATE_URL` is attached to the live change record
  - real workload-cluster generation evidence exists from:
    - `infrastructure/nonprod-mgmt/workload-clusters/nonprod-hetzner-hel1-core/render-workload-cluster.sh`
    - `clusterctl generate cluster`
  - real reconciliation evidence exists for:
    - `kubectl get clusters.cluster.x-k8s.io -A`
    - `kubectl get machines.cluster.x-k8s.io -A`
    - `kubectl get nodes`
  - cluster-facing edge-entry evidence exists for:
    - provider-native L4 entrypoint creation or reservation
    - recorded Cloudflare mapping intent for the workload-cluster-facing origin
  - explicit operator record exists that cluster-local add-on installation for `Cilium`, `cert-manager`, and `trust-manager` is deferred to `P2.2`, not silently assumed complete inside `P2.1`

### `EX-022` Missing Live Non-Prod Platform-Services Flux Reconciliation And Controller Readiness Evidence For `P2.2` Closure

- `scope`: `P2.2` cannot be declared complete from the current workspace because real closure depends on a live non-prod workload cluster, a real `platform-gitops` repository, Flux reconciliation, and runtime controller readiness evidence that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.2` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-2-platform-services-gitops/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-2-platform-services-gitops/evidence-pack.md:1) explicitly records that no live workload-cluster kubeconfig, no real `platform-gitops` handoff, and no Flux or controller readiness evidence are present in the current workspace
  - [2026-04-22-platform-foundation-p2-2-platform-services-gitops-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-2-platform-services-gitops-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/platform_services_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/platform_services_bootstrap.py:1) and [infra/tests/test_platform_services_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_platform_services_bootstrap.py:1) exist, but have not been exercised against a real Flux-managed workload cluster yet
- `target_behavior`: ordered Flux reconciliation exists for the base non-prod platform-services layer, OpenBao-backed secret delivery controllers are ready, and controller health plus trust or issuer readiness are recorded against the first real workload cluster
- `why_exception_exists`: live cluster access, real GitOps bootstrap handoff, OpenBao CA material, and runtime controller evidence are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.2` could be treated as “finished enough” without proving that the frozen controller ordering actually reconciles, that the chosen maintained operator path works with OpenBao in practice, or that the Alloy/LGTM baseline is live on the first workload cluster; later `P2` packets could inherit false assumptions about secret delivery and observability readiness
- `owner_lane`: `infra-platform` / `sre-platform` / `security`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows `P2.3+` repo and validation work to proceed in parallel; does not allow `P2.2 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.2` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - operator-provided access exists to the live first non-prod workload cluster
  - the `platform-gitops` repository contains the rendered `P2.2` cluster and infrastructure paths
  - Flux reconciliation evidence exists for:
    - `platform-sources`
    - `platform-cert-manager`
    - `platform-external-secrets`
    - `platform-openbao-integration`
    - `platform-trust-manager`
    - `platform-trust-bundles`
    - `platform-kube-prometheus-stack`
    - `platform-observability-backends`
    - `platform-alloy`
  - controller or runtime readiness evidence exists for:
    - `cert-manager`
    - `external-secrets`
    - `kube-prometheus-stack`
    - `loki`
    - `tempo`
    - `alloy-daemonset`
    - `alloy-otlp-gateway`
  - live OpenBao integration evidence exists for:
    - `ClusterSecretStore/openbao-shared`
    - `ClusterSecretStore/openbao-apps`
    - `ExternalSecret/openbao-server-ca`
    - `ClusterIssuer/openbao-k8s-internal`
    - `Bundle/openbao-k8s-internal-ca`
  - explicit operator record exists that `P2.2` did not introduce a standalone ingress controller and continues to rely on the `Cilium Gateway API` substrate frozen in `P2.1`

### `EX-023` Missing Live Alloy Cutover And Retirement Evidence For Remaining Tracked Legacy Collector Surfaces After `P2.3` Repo Convergence Work

- `scope`: `P2.3` cannot be declared complete from the current workspace because real closure depends on removing or replacing the remaining tracked legacy collector surfaces in runtime systems and proving the corresponding live cutovers
- `current_behavior`:
  - repo slice for `P2.3` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-3-collector-convergence/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-3-collector-convergence/evidence-pack.md:1) explicitly records that validation passes only because the remaining legacy collector surfaces are still tracked debt, not because they are already retired
  - [infra/scripts/collector_convergence.py](/home/beep/projects/VPNBussiness/infra/scripts/collector_convergence.py:1) and [infra/tests/test_collector_convergence.py](/home/beep/projects/VPNBussiness/infra/tests/test_collector_convergence.py:1) exist and prove repo-side drift detection, but no live collector cutover evidence exists yet
  - remaining tracked legacy collector surfaces still include:
    - [infra/docker-compose.yml](/home/beep/projects/VPNBussiness/infra/docker-compose.yml:674)
    - [infra/prometheus/prometheus.yml](/home/beep/projects/VPNBussiness/infra/prometheus/prometheus.yml:137)
    - [backend/src/config/settings.py](/home/beep/projects/VPNBussiness/backend/src/config/settings.py:207)
- `target_behavior`: tracked legacy collector surfaces are removed or replaced, repo-side validation still passes with zero unexpected references, and live Alloy-based replacement evidence exists where runtime cutover is required
- `why_exception_exists`: local development topology and current runtime defaults still carry migration-era collector debt, and live replacement proof cannot be produced from the current repository-only session
- `risk_if_kept`: `P2.3` could be treated as finished once the repo-side guardrail exists, even though actual runtime collector convergence has not happened and tracked debt still remains in local stack and runtime defaults
- `owner_lane`: `sre-platform` / `infra-platform` / `backend-platform` / `docs-program`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later `P2` repo and validation work to proceed in parallel; does not allow `P2.3 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.3` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - `infra/scripts/collector_convergence.py validate --repo-root .` still passes after cleanup
  - remaining tracked legacy collector surfaces are removed or formally superseded:
    - `infra/docker-compose.yml`
    - `infra/prometheus/prometheus.yml`
    - `backend/src/config/settings.py`
  - live Alloy-based replacement evidence exists for the affected runtime surfaces where applicable
  - `EX-007` and `EX-008` are retired or narrowed to zero non-local scope

### `EX-024` Missing Live Workload-Cluster Data-Protection Reconciliation And Recovery Evidence For `P2.4` Closure

- `scope`: `P2.4` cannot be declared complete from the current workspace because real closure depends on a live workload cluster, real object-store and snapshot inputs, and successful backup or restore evidence that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.4` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-4-cluster-backup-orchestration/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-4-cluster-backup-orchestration/evidence-pack.md:1) explicitly records that there is no live workload-cluster reconciliation evidence, no object-store credential wiring, no validated CSI `VolumeSnapshotClass`, and no restore proof in the current workspace
  - [2026-04-22-platform-foundation-p2-4-cluster-backup-orchestration-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-4-cluster-backup-orchestration-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/cluster_backup_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/cluster_backup_bootstrap.py:1) and [infra/tests/test_cluster_backup_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_cluster_backup_bootstrap.py:1) exist, but have not been exercised against a real workload cluster or real PostgreSQL recovery flow yet
- `target_behavior`: the first non-prod workload cluster has reconciled `CloudNativePG`, `Barman Cloud Plugin`, and `Velero`; real object-store and snapshot inputs are wired; and live backup plus restore evidence exists for the frozen non-prod data-protection baseline
- `why_exception_exists`: live workload-cluster access, object-store credentials, bucket and KMS ownership, CSI snapshot compatibility, and recovery proof are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.4` could be treated as “done enough” without proving that the frozen split between PostgreSQL durable recovery and generic cluster backup works in practice; later `P2` or `P3` work could inherit false assumptions about database recovery readiness
- `owner_lane`: `sre-platform` / `infra-platform` / `data-platform` / `security`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later `P2` repo and validation work to proceed in parallel; does not allow `P2.4 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.4` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - operator-provided access exists to the live first non-prod workload cluster
  - Flux reconciliation evidence exists for:
    - `platform-cnpg-operator`
    - `platform-barman-plugin`
    - `platform-velero`
    - `platform-backup-policies`
  - live runtime inputs exist and are recorded for:
    - `velero-cloud-credentials`
    - `cnpg-barman-cloud-credentials`
    - object-store bucket, region, and KMS ownership
    - validated CSI `VolumeSnapshotClass`
  - a real `CloudNativePG` workload is wired to:
    - `ObjectStore`
    - WAL archive via `Barman Cloud Plugin`
    - `ScheduledBackup` using `method: plugin`
    - `ScheduledBackup` using `method: volumeSnapshot` where applicable
  - successful live evidence exists for:
    - plugin-based PostgreSQL backup and recovery
    - same-provider volume-snapshot restore
    - `Velero` restore of cluster resources and portable-volume metadata

### `EX-025` Missing Live OCI Chart Publication, GitOps Promotion PR, And First-Workload Flux Rollout Evidence For `P2.5` Closure

- `scope`: `P2.5` cannot be declared complete from the current workspace because real closure depends on live package publication, package access control, GitOps repository mutation, and real workload rollout evidence that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.5` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-5-workload-delivery/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-5-workload-delivery/evidence-pack.md:1) explicitly records that no live `GHCR` chart publication, no live GitOps promotion PR, and no live Flux rollout proof are present in the current workspace
  - [2026-04-22-platform-foundation-p2-5-workload-delivery-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-5-workload-delivery-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/workload_delivery_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/workload_delivery_bootstrap.py:1) and [infra/tests/test_workload_delivery_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_workload_delivery_bootstrap.py:1) exist, but have not been exercised against a real registry, GitOps repository, or workload cluster yet
- `target_behavior`: first-party OCI Helm charts exist in `GHCR`, the GitOps repository is updated by promotion pull request with chart version and image digest pins, and the first workload pair is reconciled by Flux on the first non-prod workload cluster
- `why_exception_exists`: live `GHCR` permissions, package linking, GitOps repository write credentials, Flux cluster access, and rollout evidence are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.5` could be treated as “done enough” while the program still lacks proof that first-party OCI charts can actually be published, promoted, and reconciled; later workload migration packets could inherit false confidence about delivery readiness
- `owner_lane`: `infra-platform` / `backend-platform` / `sre-platform` / `security`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later `P2` repo and validation work to proceed in parallel; does not allow `P2.5 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.5` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - live `GHCR` chart publication exists for the first workload pair
  - package access is configured and recorded for:
    - GitHub Actions publication with `GITHUB_TOKEN`
    - Flux chart pull
    - workload image pull
  - a real `platform-gitops` mutation branch and pull request exist with:
    - changed `OCIRepository` chart version pin
    - changed `HelmRelease` image digest pin
  - Flux reconciliation evidence exists for:
    - `platform-workloads`
    - first `OCIRepository`
    - first `HelmRelease`
  - at least one first workload has deploy and rollback or remediation evidence

### `EX-026` Missing Live NATS Stream Creation, Dispatcher Publish, Durable Consumer, And Replay Evidence For `P2.6` Closure

- `scope`: `P2.6` cannot be declared complete from the current workspace because real closure depends on live JetStream stream state, live dispatcher publishing from the persisted outbox, live durable consumer execution, and replay proof that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.6` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-6-event-backbone/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-6-event-backbone/evidence-pack.md:1) explicitly records that no live stream creation, no live dispatcher publish evidence, no live durable consumer evidence, and no live replay proof are present in the current workspace
  - [2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md:1) documents the required live evidence for packet closure
  - [docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md](/home/beep/projects/VPNBussiness/docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md:1) now freezes the active `PARTNER_EVENTS` stream scope, active consumers, reserved-next consumers, and replay posture
  - [infra/scripts/event_backbone_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/event_backbone_bootstrap.py:1) and [infra/tests/test_event_backbone_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_event_backbone_bootstrap.py:1) exist, but have not been exercised against a real `nats-nonprod` cluster or real outbox dispatcher process yet
- `target_behavior`: the active `PARTNER_EVENTS` stream exists on the real non-prod NATS cluster, the dispatcher publishes current persisted outbox rows into JetStream with durable metadata, at least one active durable consumer processes real events, and replay tooling has non-prod execution proof
- `why_exception_exists`: live NATS credentials, stream-management access, dispatcher deployment targets, workload or service runtime access, and replay approval inputs are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.6` could be treated as “done enough” while the program still lacks proof that the frozen outbox-to-NATS contract actually works in runtime; later realtime, workload, and analytics packets could inherit false confidence about event backbone readiness
- `owner_lane`: `backend-platform` / `transport-backend` / `infra-platform` / `sre-platform`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later `P2` repo and validation work to proceed in parallel; does not allow `P2.6 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.6` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - live `PARTNER_EVENTS` stream creation exists on `nats-nonprod`
  - live dispatcher evidence exists for:
    - claim
    - publish
    - publish metadata persistence in `publication_payload`
  - at least one active durable consumer is running against the real stream:
    - `analytics_mart` or
    - `operational_replay`
  - non-prod replay evidence exists for the frozen replay tooling baseline
  - backlog and lag evidence exists for the first active event path
  - `EX-010` is retired or explicitly narrowed to repo-local legacy remainder only

### `EX-027` Missing Live Realtime Gateway Deployment, Browser Delivery Endpoint, And Polling-Replacement Flow Evidence For `P2.7` Closure

- `scope`: `P2.7` cannot be declared complete from the current workspace because real closure depends on a deployed realtime gateway or equivalent projection-to-browser component, a live browser delivery endpoint, and one real browser flow replacing polling, all of which are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.7` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-7-realtime-delivery/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-7-realtime-delivery/evidence-pack.md:1) explicitly records that no live realtime gateway deployment, no live SSE endpoint, no live `realtime_gateway_projection` proof, and no live browser polling replacement exist in the current workspace
  - [2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md:1) documents the required live evidence for packet closure
  - [docs/api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md](/home/beep/projects/VPNBussiness/docs/api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md:1) now freezes `partner.workspace.feed` as the first canonical browser channel, `SSE` as the primary browser delivery protocol, and current monitoring sockets as operational-only
  - [infra/scripts/realtime_delivery_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/realtime_delivery_bootstrap.py:1) and [infra/tests/test_realtime_delivery_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_realtime_delivery_bootstrap.py:1) exist, but have not been exercised against a live gateway or real browser session yet
- `target_behavior`: a live realtime gateway exists in non-prod, a durable `realtime_gateway_projection` consumer drives browser-facing delivery for `partner.workspace.feed`, an SSE endpoint serves the chosen dashboard flow, and at least one dashboard path uses the canonical browser-delivery route instead of polling
- `why_exception_exists`: live gateway deployment targets, runtime credentials, browser test environment, and chosen-dashboard cutover inputs are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.7` could be treated as “done enough” while the program still lacks proof that the frozen browser-delivery contract works end to end; later workload and product packets could inherit false confidence about realtime UX readiness
- `owner_lane`: `transport-backend` / `backend-platform` / `infra-platform` / `sre-platform`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later `P2` repo and validation work to proceed in parallel; does not allow `P2.7 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel `P2` execution, but blocking for `P2.7` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - a deployed realtime gateway or equivalent projection-to-browser component exists in non-prod
  - a durable `realtime_gateway_projection` consumer runs against `PARTNER_EVENTS`
  - a live browser delivery endpoint exists for the first canonical channel:
    - `/api/v1/realtime/partner/events` or
    - its final approved equivalent
  - at least one chosen dashboard flow uses the canonical path instead of polling
  - the legacy business-path SSE and direct WebSocket surfaces are retired or explicitly narrowed to approved non-authoritative scope
  - `EX-009` is retired or explicitly narrowed to repo-local compatibility remainder only

### `EX-028` Missing Live Non-Prod Rollout, OpenBao-Backed Secret Materialization, And Migration-Job Evidence For `P2.8` Closure

- `scope`: `P2.8` cannot be declared complete from the current workspace because real closure depends on a live non-prod rollout of the first migrated control-plane workload set, OpenBao-backed secret materialization for those releases, backend migration-job execution proof, and deploy or rollback evidence that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.8` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-8-initial-control-plane-workload-migration/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-8-initial-control-plane-workload-migration/evidence-pack.md:1) explicitly records that no live non-prod rollout, no live OpenBao-backed `ExternalSecret` materialization proof, and no live backend migration-job proof exist in the current workspace
  - [2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md:1) documents the required live evidence for packet closure
  - [docs/api/platform-foundation-initial-control-plane-workloads-spec.md](/home/beep/projects/VPNBussiness/docs/api/platform-foundation-initial-control-plane-workloads-spec.md:1) now freezes the first migrated workload set, exclusions, OpenBao-backed secret keys, rollout order, and backend migration-job posture
  - [infra/scripts/control_plane_workload_migration.py](/home/beep/projects/VPNBussiness/infra/scripts/control_plane_workload_migration.py:1) and [infra/tests/test_control_plane_workload_migration.py](/home/beep/projects/VPNBussiness/infra/tests/test_control_plane_workload_migration.py:1) exist, but have not been exercised against a live workload cluster or live OpenBao-backed secret delivery path yet
- `target_behavior`: backend, task-worker, and task-scheduler reconcile on the real non-prod workload cluster through Flux, consume runtime material through the frozen OpenBao-backed `ExternalSecret` contract, execute the backend migration hook successfully, and provide deploy or rollback evidence for the first migrated control-plane workload set
- `why_exception_exists`: live workload-cluster access, live OpenBao data, registry credentials, Flux reconciliation inputs, and rollout approval are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.8` could be treated as “done enough” while the program still lacks proof that the first migrated control-plane workloads actually run under the frozen Kubernetes, GitOps, and secret-delivery contract; later `P2` or `P3` work could inherit false confidence about workload migration readiness
- `owner_lane`: `backend-platform` / `infra-platform` / `sre-platform` / `security`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to proceed in parallel; does not allow `P2.8 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but blocking for `P2.8` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - backend, task-worker, and task-scheduler reconcile on the real non-prod workload cluster
  - OpenBao-backed `ExternalSecret` materialization is proven for all three releases
  - the backend migration job runs successfully during first install or upgrade
  - metrics for all three releases are scraped through the canonical Prometheus baseline
  - at least one non-prod deploy or rollback proof exists for the migrated set
  - `EX-002` is retired or explicitly narrowed for the migrated workload set

### `EX-029` Missing Live Production Management-Cluster Apply, L4 Endpoint, Talos Bootstrap, And Provider-Install Evidence For `P2.9` Closure

- `scope`: `P2.9` cannot be declared complete from the current workspace because real closure depends on a live production management-cluster apply, live Hetzner load-balancer endpoint evidence, live Talos bootstrap evidence, and live provider-install evidence that are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P2.9` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p2-9-prod-mgmt-foundation/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p2-9-prod-mgmt-foundation/evidence-pack.md:1) explicitly records that no live production `backend.hcl`, no live `TF_VAR_hcloud_token`, no validated Talos image or snapshot id, no live load-balancer endpoint evidence, and no live provider-install evidence exist in the current workspace
  - [2026-04-22-platform-foundation-p2-9-prod-mgmt-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p2-9-prod-mgmt-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/terraform/live/production/prod-mgmt/README.md](/home/beep/projects/VPNBussiness/infra/terraform/live/production/prod-mgmt/README.md:1) now freezes the provider-native L4 endpoint posture and the `prod-mgmt` stack operating contract
  - [infra/scripts/prod_mgmt_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/prod_mgmt_bootstrap.py:1) and [infra/tests/test_prod_mgmt_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_prod_mgmt_bootstrap.py:1) exist, but have not been exercised against a live production management cluster yet
- `target_behavior`: a live `prod-mgmt` management cluster exists with the frozen three-control-plane baseline, a provider-native L4 Kubernetes API endpoint is healthy, Talos bootstrap and kubeconfig retrieval are proven against real nodes, and Cluster API plus Talos providers are installed with an explicitly validated CAPH manifest URL
- `why_exception_exists`: live production backend configuration, cloud credentials, validated Talos image inputs, production change approval, and provider-install inputs are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P2.9` could be treated as “done enough” while the program still lacks proof that the frozen production management substrate actually exists and behaves as intended; later `P3` work could inherit false confidence about production substrate readiness
- `owner_lane`: `infra-platform` / `platform-architecture` / `sre-platform` / `security`
- `creation_phase`: `P2`
- `required_removal_phase`: `P2`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to proceed in parallel; does not allow `P2.9 complete`, `P2 complete`, or `Gate C passed` claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but blocking for `P2.9` closure and `P2` phase closure
- `verification_needed_for_removal`:
  - live `tofu init/plan/apply` evidence exists for `infra/terraform/live/production/prod-mgmt`
  - live Hetzner load-balancer evidence exists for:
    - endpoint IP
    - target registration
    - service health on `6443/tcp`
  - live Talos bootstrap evidence exists for the first production control-plane node
  - live `talosconfig` and `kubeconfig` retrieval evidence exists for `prod-mgmt`
  - live `clusterctl init` evidence exists for Cluster API core plus Talos providers
  - live CAPH install evidence exists from an explicitly validated manifest URL

### `EX-030` Missing Live Node Fleet Controller Deployment, Durable DB Persistence, And NATS Publication Evidence For `P3.1` Closure

- `scope`: `P3.1` cannot be declared complete from the current workspace because real
  closure depends on a live `Node Fleet Controller` deployment, real durable DB persistence,
  and real NATS publication evidence that are intentionally absent from the repository and
  current session
- `current_behavior`:
  - repo slice for `P3.1` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p3-1-node-fleet-controller-foundation/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p3-1-node-fleet-controller-foundation/evidence-pack.md:1) explicitly records that no live controller deployment, no live durable DB, and no live JetStream publication proof exist in the current workspace
  - [2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - [services/node-fleet-controller/README.md](/home/beep/projects/VPNBussiness/services/node-fleet-controller/README.md:1) now freezes the first service boundary for API, durable request handling, workflow planning, and NATS adapter posture
  - [services/node-fleet-controller/src/main.py](/home/beep/projects/VPNBussiness/services/node-fleet-controller/src/main.py:1) and the service tests exist, but have not been exercised against a live runtime surface yet
- `target_behavior`: a deployed `Node Fleet Controller` service persists durable request,
  operation-run, and audit state in a real database, publishes canonical `node.command.*.v1`
  events to the non-prod NATS cluster, and serves an operator-visible request flow on the
  chosen runtime surface
- `why_exception_exists`: live deployment targets, database credentials, NATS credentials,
  GitOps release inputs, and operator rollout approval are intentionally kept outside git and
  were not injected into this session
- `risk_if_kept`: `P3.1` could be treated as “done enough” while the program still lacks
  proof that the new controller service actually runs, stores durable request state, and
  publishes canonical fleet commands; later `P3` packets could inherit false confidence about
  controller readiness
- `owner_lane`: `fleet-platform` / `backend-platform` / `infra-platform` / `transport-backend`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.1 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.1` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - the `Node Fleet Controller` is deployed to the chosen non-prod runtime surface
  - durable request, operation-run, and audit entries are proven in a real database
  - canonical `node.command.*.v1` publication is proven against the non-prod NATS cluster
  - at least one operator-visible request flow is exercised end to end
  - deploy or rollback evidence exists for the service runtime

### `EX-031` Missing Live OpenTofu Runner Wiring, OpenBao Bootstrap And Unwrap, Enrollment, And Certificate Rotation Evidence For `P3.2` Closure

- `scope`: `P3.2` cannot be declared complete from the current workspace because real
  closure depends on live OpenTofu runner wiring, live OpenBao bootstrap issuance and unwrap,
  live external node enrollment, and live certificate rotation evidence that are intentionally
  absent from the repository and current session
- `current_behavior`:
  - repo slice for `P3.2` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p3-2-controller-execution-bootstrap-enrollment/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p3-2-controller-execution-bootstrap-enrollment/evidence-pack.md:1) explicitly records that no live runner wiring, no live OpenBao issue or unwrap proof, no live enrollment, and no live rotation proof exist in the current workspace
  - [2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md:1) documents the required live evidence for packet closure
  - `services/node-fleet-controller/` now contains preview-safe execution, bootstrap, enrollment, and rotation layers, but they have not yet been exercised against live OpenTofu or OpenBao surfaces
- `target_behavior`: the deployed controller performs guarded OpenTofu execution through the
  approved runner model, issues and unwraps OpenBao bootstrap material for real nodes, accepts
  live enrollment completion, and exercises renewable certificate rotation end to end
- `why_exception_exists`: live runner infrastructure, state backend credentials, OpenBao auth
  inputs, external node targets, and rollout approvals are intentionally kept outside git and
  were not injected into this session
- `risk_if_kept`: `P3.2` could be treated as “done enough” while the program still lacks
  proof that executor safety, bootstrap delivery, enrollment, and rotation actually work in
  the real platform; later fleet packets could inherit false confidence about node identity
  readiness
- `owner_lane`: `fleet-platform` / `infra-platform` / `security` / `transport-backend`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.2 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.2` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - a live controller runtime performs guarded OpenTofu execution with state locking and
    auditable plan artifacts
  - OpenBao bootstrap issuance and unwrap are proven for a real node flow
  - at least one node completes bootstrap and enrollment through the controller
  - certificate rotation is exercised and audited end to end

### `EX-032` Missing Live External-Node Baseline Reporting, Synthetic Verification, Runtime-Adapter Acknowledgement, And Traffic-Eligibility Evidence For `P3.3` Closure

- `scope`: `P3.3` cannot be declared complete from the current workspace because real
  closure depends on live external-node reporting, live synthetic probe results, live
  runtime-adapter acknowledgement, and live traffic-eligibility promotion that are
  intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P3.3` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p3-3-external-node-service-baseline/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p3-3-external-node-service-baseline/evidence-pack.md:1) explicitly records that no live node reporting, no live synthetic-runner evidence, and no live runtime-adapter acknowledgement exist in the current workspace
  - [2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md:1) documents the required live evidence for packet closure
  - `services/node-fleet-controller/` now contains controller-side baseline, observed-state, synthetic, runtime-readiness, and traffic-eligibility layers, but they have not yet been exercised against live external nodes
- `target_behavior`: the deployed controller receives real baseline and health reports,
  accepts synthetic verification and runtime-adapter readiness, and promotes a node to
  `traffic_eligible` only after all gates pass end to end
- `why_exception_exists`: live external fleet nodes, live Alloy and health-agent bundles,
  runtime-adapter integrations, and rollout approvals are intentionally kept outside git
  and were not injected into this session
- `risk_if_kept`: `P3.3` could be treated as “done enough” while the program still lacks
  proof that controller-side readiness and traffic admission work against real fleet nodes;
  later fleet workflows could inherit false confidence about readiness semantics
- `owner_lane`: `fleet-platform` / `sre-platform` / `transport-backend` / `infra-platform`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.3 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.3` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - at least one real external node reports baseline service state through the controller
  - a real synthetic runner posts successful probe evidence for that node
  - a real runtime adapter acknowledges readiness for that node
  - the controller promotes that node to `traffic_eligible` with durable evidence

### `EX-033` Missing Live Operator Workflow Entry, Node-Pool Reconciliation, And Replace/Drain/Quarantine Evidence For `P3.4` Closure

- `scope`: `P3.4` cannot be declared complete from the current workspace because real
  closure depends on live operator-driven workflow entry, live node-pool reconciliation,
  and live `replace`, `drain`, and `quarantine` evidence that are intentionally absent
  from the repository and current session
- `current_behavior`:
  - repo slice for `P3.4` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p3-4-operator-driven-workflows/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p3-4-operator-driven-workflows/evidence-pack.md:1) explicitly records that no live operator wrapper, no live controller reconciliation, and no live drain or quarantine evidence exist in the current workspace
  - [2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md:1) documents the required live evidence for packet closure
  - `services/node-fleet-controller/` now contains typed operator routes and durable `NodePool` support, but they have not yet been exercised against live fleet workflows
- `target_behavior`: operators enter controller-native typed workflows for add, replace,
  drain, quarantine, and capacity changes; those workflows reconcile against real node pools
  and nodes with durable evidence
- `why_exception_exists`: live controller deployment, live operator wrapper, external fleet
  nodes, and rollout approvals are intentionally kept outside git and were not injected into
  this session
- `risk_if_kept`: `P3.4` could be treated as “done enough” while the program still lacks
  proof that operator workflows really converge on live nodes and pools; later failover logic
  could inherit false confidence about workflow entry and target selection
- `owner_lane`: `fleet-platform` / `infra-platform` / `transport-backend`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.4 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.4` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - at least one live operator command enters the controller through the typed operator surface
  - a live node-pool capacity change reconciles through the controller
  - live `replace`, `drain`, or `quarantine` workflow evidence exists for a real node
  - deploy or rollback evidence exists for the new integration surfaces

### `EX-034` Missing Live Failover Signal Ingestion, Guarded Policy Evaluation, And Failover Workflow Evidence For `P3.5` Closure

- `scope`: `P3.5` cannot be declared complete from the current workspace because real
  closure depends on live impairment signal ingestion, live guarded failover evaluation,
  and live failover workflow evidence that are intentionally absent from the repository and
  current session
- `current_behavior`:
  - repo slice for `P3.5` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p3-5-failover-policy-engine/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p3-5-failover-policy-engine/evidence-pack.md:1) explicitly records that no live DPI/provider impairment feed, no live approval executor, and no live accepted failover workflow evidence exist in the current workspace
  - [2026-04-22-platform-foundation-p3-5-failover-policy-engine-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p3-5-failover-policy-engine-execution-packet.md:1) documents the required live evidence for packet closure
  - `services/node-fleet-controller/` now contains durable failover policy records, typed `node-failover` API flow, and blocked/approval/accepted request semantics, but those surfaces have not yet been exercised against live fleet incidents
- `target_behavior`: live impairment evidence enters the controller, the policy engine
  produces durable blocked or approval-gated requests where appropriate, and at least one
  accepted failover request progresses into real replacement or traffic-shift evidence
- `why_exception_exists`: live external fleet nodes, live impairment simulators, live
  approval flows, and rollout approvals are intentionally kept outside git and were not
  injected into this session
- `risk_if_kept`: `P3.5` could be treated as “done enough” while the program still lacks
  proof that failover automation is actually guarded under live conditions; later fleet
  automation could inherit false confidence about budget, cooldown, and approval semantics
- `owner_lane`: `fleet-platform` / `transport-backend` / `infra-platform` / `security`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.5 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.5` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - live DPI, provider, or health impairment evidence is ingested into the controller
  - at least one failover request is evaluated into `blocked_policy` or `awaiting_approval`
    under real policy records
  - at least one accepted failover request reconciles into real replacement capacity or
    controlled traffic-shift evidence
  - deploy or rollback evidence exists for the new failover-policy integration surfaces

### `EX-035` Missing Live PostHog Authoritative Capture, Identified Flag Evaluation, And Governed Frontend Event Evidence For `P3.6` Closure

- `scope`: `P3.6` cannot be declared complete from the current workspace because real
  closure depends on live `PostHog` capture, live authoritative bridge execution, live
  identified server-side flag evaluation, and live governed frontend event evidence that
  are intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P3.6` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-22/p3-6-posthog-bridge-and-flag-wrapper/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-22/p3-6-posthog-bridge-and-flag-wrapper/evidence-pack.md:1) explicitly records that no live `PostHog` host or token smoke, no live authoritative consumer, and no live identified dashboard flag bootstrap exist in the current workspace
  - [2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-22-platform-foundation-p3-6-posthog-bridge-and-flag-wrapper-execution-packet.md:1) documents the required live evidence for packet closure
  - `backend/` now contains authoritative bridge mappings for the first commercial event families, and `partner/` now contains the governed server-side capture route and typed feature-flag wrapper, but those surfaces have not yet been exercised against a live `PostHog` runtime
- `target_behavior`: live authoritative commercial events and governed frontend UX events
  are captured into `PostHog` through the approved server-side paths, and at least one real
  dashboard request proves identified server-side product-flag evaluation with deterministic
  fallback behavior preserved
- `why_exception_exists`: live `PostHog` project credentials, live partner runtime hosts,
  live authoritative bridge consumers, and rollout approvals are intentionally kept outside
  git and were not injected into this session
- `risk_if_kept`: `P3.6` could be treated as “done enough” while the program still lacks
  proof that product intelligence is authoritative, privacy-safe, and operationally real;
  later dashboards and experiments could inherit false confidence about capture and flag
  semantics
- `owner_lane`: `growth-platform` / `backend-platform` / `partner-platform` / `transport-backend`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.6 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.6` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - a deployed partner runtime proves same-origin governed frontend event capture into a
    live `PostHog` project
  - at least one authoritative commercial event reaches live `PostHog` through the approved
    bridge path
  - at least one real dashboard request proves identified server-side product-flag
    evaluation
  - captured live events show only the approved allowlisted properties
  - deploy or rollback evidence exists for the new product-intelligence integration surfaces

### `EX-036` Missing Live PostHog Dashboard Population, Deployed Checkout/Onboarding Capture Proof, And Retention Follow-Up Evidence For `P3.7` Closure

- `scope`: `P3.7` cannot be declared complete from the current workspace because real
  closure depends on live dashboard population, live checkout and onboarding capture proof,
  and live retention follow-up evidence that are intentionally absent from the repository
  and current session
- `current_behavior`:
  - repo slice for `P3.7` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-23/p3-7-posthog-dashboard-foundation/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-23/p3-7-posthog-dashboard-foundation/evidence-pack.md:1) explicitly records that no live `PostHog` dashboards, no live deployed partner-runtime capture proof, and no live retention follow-up evidence exist in the current workspace
  - [2026-04-23-platform-foundation-p3-7-posthog-dashboard-foundation-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-23-platform-foundation-p3-7-posthog-dashboard-foundation-execution-packet.md:1) documents the required live evidence for packet closure
  - `backend/` and `partner/` now contain dashboard contracts, checkout/onboarding reporters, and the first retention-side bridge expansion, but those surfaces have not yet been exercised against a live `PostHog` deployment
- `target_behavior`: live `PostHog` dashboards are populated from the frozen contract set,
  deployed checkout and onboarding flows emit their governed events into the live product
  intelligence surface, and retention lifecycle dashboards are either fed by their follow-up
  events or explicitly superseded by an approved contract change
- `why_exception_exists`: live `PostHog` project access, live partner storefront and portal
  hosts, live authoritative bridge consumers, and rollout approvals are intentionally kept
  outside git and were not injected into this session
- `risk_if_kept`: `P3.7` could be treated as “done enough” while the program still lacks
  proof that dashboard contracts actually materialize into useful live product intelligence;
  later growth and retention decisions could inherit false confidence about dashboard
  readiness
- `owner_lane`: `growth-platform` / `backend-platform` / `partner-platform` / `transport-backend`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch implementation work to
  proceed in parallel; does not allow `P3.7 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.7` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - a deployed partner runtime proves governed checkout and onboarding event capture into
    live `PostHog`
  - at least one live dashboard or insight view is populated from the frozen `P3.7`
    contract set
  - at least one authoritative commercial event and one governed UX event are visible in
    live dashboard output
  - retention lifecycle follow-up evidence exists or an approved superseding contract
    explicitly narrows the live scope
  - deploy or rollback evidence exists for the new dashboard-foundation integration surfaces

### `EX-037` Missing Live Production Workload-Cluster Reconciliation, Flagger Canary, CNPG And Backup, Alerting, And Deploy Or Rollback Evidence For `P3.8` Closure

- `scope`: `P3.8` cannot be declared complete from the current workspace because real
  closure depends on a live production management cluster, a live production workload
  cluster, live Flux reconciliation, live `Flagger` canary proof, live `CloudNativePG`
  bootstrap and backup evidence, and live production deploy or rollback evidence that are
  intentionally absent from the repository and current session
- `current_behavior`:
  - repo slice for `P3.8` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-23/p3-8-production-control-plane-cutover/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-23/p3-8-production-control-plane-cutover/evidence-pack.md:1) explicitly records that no live production cluster reconciliation, no live `Flagger` canary proof, and no live production deploy or rollback evidence exist in the current workspace
  - [2026-04-23-platform-foundation-p3-8-production-control-plane-cutover-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-23-platform-foundation-p3-8-production-control-plane-cutover-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/prod_control_plane_cutover.py](/home/beep/projects/VPNBussiness/infra/scripts/prod_control_plane_cutover.py:1) and [infra/tests/test_prod_control_plane_cutover.py](/home/beep/projects/VPNBussiness/infra/tests/test_prod_control_plane_cutover.py:1) exist, but have not been exercised against a real production workload cluster or live cutover path yet
- `target_behavior`: the production workload cluster reconciles the frozen production
  progressive-delivery, data, observability, and application cutover surfaces; `Flagger`
  proves a real backend promotion and rollback; `CloudNativePG` bootstrap and scheduled
  backup are live; and deploy or rollback evidence exists for the first production
  control-plane workload set
- `why_exception_exists`: live production clusters, production GitOps credentials,
  production `OpenBao` and backup inputs, real domain or gateway wiring, and rollout
  approvals are intentionally kept outside git and were not injected into this session
- `risk_if_kept`: `P3.8` could be treated as “done enough” while production cutover still
  lacks proof that GitOps, progressive delivery, database runtime, backup, and alerting
  actually work together under real production conditions; later conformance claims could
  inherit false confidence about rollout and rollback safety
- `owner_lane`: `infra-platform` / `backend-platform` / `sre-platform` / `security` / `data-platform`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows later repo, validation, and pre-launch conformance work to
  proceed in parallel; does not allow `P3.8 complete`, `P3 complete`, or `Gate D passed`
  claims
- `blocking_status`: tolerated as a carry-forward exception for parallel execution, but
  blocking for `P3.8` closure and `P3` phase closure
- `verification_needed_for_removal`:
  - operator-provided access exists to the real production management cluster and
    production workload cluster
  - Flux reconciles the frozen production progressive-delivery, data, observability, and
    application cutover surfaces successfully
  - at least one real `Flagger` backend canary promotion and one rollback are recorded
  - production `CloudNativePG` bootstrap, manual `PodMonitor`, and `ScheduledBackup`
    evidence exist
  - deploy or rollback evidence exists for `backend`, `task-worker`, and `task-scheduler`
  - legacy host-based production rollout authority is retired or explicitly demoted to
    break-glass only

### `EX-038` Missing Live Production Drill Transcripts, Final Scorecard Completion, And Gate D Sign-Off Evidence For `P3.9` Closure

- `scope`: `P3.9` cannot be declared complete from the current workspace because real
  closure depends on live production drill transcripts, a fully populated Gate `D`
  scorecard, and final production sign-off evidence that are intentionally absent from the
  repository and current session
- `current_behavior`:
  - repo slice for `P3.9` is implemented and locally validated
  - [docs/evidence/platform-foundation/2026-04-23/p3-9-production-drills-and-conformance/evidence-pack.md](/home/beep/projects/VPNBussiness/docs/evidence/platform-foundation/2026-04-23/p3-9-production-drills-and-conformance/evidence-pack.md:1) explicitly records that no live production drill transcripts, no completed final scorecard snapshot, and no Gate `D` sign-off exist in the current workspace
  - [2026-04-23-platform-foundation-p3-9-production-drills-and-conformance-execution-packet.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-23-platform-foundation-p3-9-production-drills-and-conformance-execution-packet.md:1) documents the required live evidence for packet closure
  - [infra/scripts/production_conformance_bundle.py](/home/beep/projects/VPNBussiness/infra/scripts/production_conformance_bundle.py:1) and [infra/tests/test_production_conformance_bundle.py](/home/beep/projects/VPNBussiness/infra/tests/test_production_conformance_bundle.py:1) exist, but have not been exercised against a real production drill wave
- `target_behavior`: live production drill transcripts exist for `OpenBao`, `NATS`,
  `CloudNativePG`, `GitOps / Flux recovery`, `PostHog`, and `Node Fleet Controller / fleet
  reprovisioning`; the final Gate `D` scorecard snapshot is fully populated with
  evidence-backed scores; and the final Gate `D` evidence pack is assembled and signed off
- `why_exception_exists`: live production clusters, production credentials, operator access,
  live drill windows, and human gate approvers are intentionally kept outside git and were
  not injected into this session
- `risk_if_kept`: the program could mistake repo-side readiness for actual production
  conformance; `Gate D` could be claimed without real drill evidence, without a completed
  scorecard, or without an accountable sign-off chain
- `owner_lane`: `sre-platform` / `infra-platform` / `backend-platform` / `data-platform` / `growth-platform` / `fleet-platform` / `security`
- `creation_phase`: `P3`
- `required_removal_phase`: `P3`
- `allowed_scope`: allows no further gate claim; only permits the repo-side conformance
  scaffold to exist while live production drill execution is pending
- `blocking_status`: blocking for `P3.9` closure, `P3` phase closure, and any `Gate D`
  passed claim
- `verification_needed_for_removal`:
  - live production drill transcripts exist for all mandatory domains
  - the Gate `D` scorecard snapshot is filled with evidence-backed scores
  - the final Gate `D` evidence pack is assembled from the canonical template
  - named human approvers sign off the final gate result

## 4. Frozen Use Of This Register

This register is now the authoritative input for:

1. `T0.8 Phase Gates, Evidence Templates, And Conformance Scoring Model`
2. `T0.9 Phase 0 Closure And Sign-Off Pack`
3. `Phase 1` scoping of `OpenBao`, GitOps bootstrap, observability cleanup, non-prod deployment path, and `P1.1` / `P1.2` carry-forward closure debt
4. `Phase 2` scoping of eventing, collector convergence, secrets delivery cleanup, and `P2.1` / `P2.2` / `P2.3` closure debt
5. `Phase 3` scoping of Node Fleet Controller and final fleet conformance
