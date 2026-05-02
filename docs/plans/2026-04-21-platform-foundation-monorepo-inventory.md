# CyberVPN Platform Foundation Monorepo Inventory

**Date:** 2026-04-22  
**Status:** Frozen baseline for `T0.6`

This document inventories the current deployment, secrets, telemetry, realtime, fleet-bootstrap, workflow, and documentation surfaces across the monorepo.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](2026-04-21-platform-foundation-phase-0-execution-packet.md)

This inventory exists so later phases use real repository paths, explicit owner lanes, and explicit migration posture rather than category-only statements.

## 1. Inventory Rules

Disposition labels used here:

| Disposition | Meaning |
|---|---|
| `keep` | remains valid in target-state for a clearly limited scope |
| `migrate` | valid today but must be rewired or replaced in later phases |
| `retire` | should stop being normative and must not anchor future implementation |

Owner-lane labels used here:

- `platform-architecture`
- `sre-platform`
- `infra-platform`
- `security`
- `backend-platform`
- `transport-backend`
- `frontend-platform`
- `partner-admin`
- `growth-data`
- `docs-program`
- `desktop-mobile`

## 2. Coverage Summary

This inventory explicitly covers the required monorepo areas:

| Area | Covered surfaces |
|---|---|
| `backend/` | config loading, outbox, websocket and monitoring realtime paths |
| `services/` | task-worker broker/SSE, helix-adapter runtime boundary, local env surfaces |
| `frontend/` | local env surface |
| `partner/` | frontend runtime telemetry route and realtime monitoring clients |
| `admin/` | frontend runtime telemetry route and realtime monitoring clients |
| `infra/` | Docker Compose, Terraform live stacks, Ansible rollout/bootstrap, Prometheus, Alloy |
| `.github/` | CI, release, promotion, and deployment workflows |
| `docs/` | runbooks, plans, prompts, and legacy deployment guidance |

## 3. Deployment Paths Inventory

| Path | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [infra/docker-compose.yml](../../infra/docker-compose.yml) | local dev and shared service topology for Remnawave, DB, Redis, monitoring, worker, Helix lab | `infra-platform` | `keep` | keep for local development only; must not remain the production deployment authority |
| [infra/README.md](../../infra/README.md) | operator entrypoint for local Compose and staged Ansible usage | `infra-platform` | `migrate` | mixes valid local-dev guidance with migration-era rollout guidance |
| [infra/terraform/live/staging/foundation](../../infra/terraform/live/staging/foundation) and [infra/terraform/live/production/foundation](../../infra/terraform/live/production/foundation) | foundational VM/network/cloud resources | `infra-platform` | `keep` | migrate naming and engine to `OpenTofu`, but this resource class remains canonical |
| [infra/terraform/live/staging/dns](../../infra/terraform/live/staging/dns) and [infra/terraform/live/production/dns](../../infra/terraform/live/production/dns) | DNS and Cloudflare record management | `infra-platform` | `keep` | remains valid target-state resource class |
| [infra/terraform/live/staging/edge](../../infra/terraform/live/staging/edge) and [infra/terraform/live/production/edge](../../infra/terraform/live/production/edge) | external edge and fleet VM provisioning | `infra-platform` | `migrate` | ownership remains with infrastructure layer, but execution must move under controller-driven workflows |
| [infra/terraform/live/staging/control-plane](../../infra/terraform/live/staging/control-plane) and [infra/terraform/live/production/control-plane](../../infra/terraform/live/production/control-plane) | legacy VM control-plane substrate | `infra-platform` | `migrate` | legacy slug; target-state replaces this with Kubernetes workload clusters |
| [infra/ansible/playbooks/control-plane-rollout.yml](../../infra/ansible/playbooks/control-plane-rollout.yml) and [rollback-control-plane.yml](../../infra/ansible/playbooks/rollback-control-plane.yml) | legacy VM control-plane rollout | `infra-platform` | `migrate` | remains needed during migration window only |
| [infra/ansible/playbooks/edge-bootstrap.yml](../../infra/ansible/playbooks/edge-bootstrap.yml) and [edge-verify.yml](../../infra/ansible/playbooks/edge-verify.yml) | base bootstrap for external edge hosts | `infra-platform` | `migrate` | target-state replaces manual/bootstrap sequencing with controller-driven provisioning |
| [infra/ansible/playbooks/remnawave-rollout.yml](../../infra/ansible/playbooks/remnawave-rollout.yml) and [helix-rollout.yml](../../infra/ansible/playbooks/helix-rollout.yml) | staged rollout of external node services | `infra-platform` | `migrate` | useful migration scaffolding, not target-state steady-state node orchestration |
| [infra/ansible/playbooks/alloy-rollout.yml](../../infra/ansible/playbooks/alloy-rollout.yml) and [alloy-verify.yml](../../infra/ansible/playbooks/alloy-verify.yml) | current edge collector rollout | `sre-platform` | `migrate` | keep rollout knowledge, migrate execution under fleet lifecycle model |
| [.github/workflows/control-plane-images.yml](../../.github/workflows/control-plane-images.yml) | builds digest-pinned backend, task-worker, helix-adapter images | `backend-platform` | `migrate` | remains useful until GitOps promotion becomes canonical |
| [.github/workflows/control-plane-promote.yml](../../.github/workflows/control-plane-promote.yml) | updates Ansible release manifests on promotion branches | `infra-platform` | `migrate` | target-state promotion must converge on GitOps repo updates, not inventory manifest edits |
| [.github/workflows/deploy-staging.yml](../../.github/workflows/deploy-staging.yml) | staging deployment placeholder | `infra-platform` | `retire` | currently summary-only; should not be treated as a real deployment path |
| [.github/workflows/iac-ci.yml](../../.github/workflows/iac-ci.yml) | validates current Terraform and Ansible stacks | `infra-platform` | `migrate` | keep CI intent, migrate terminology and eventually engine from Terraform to OpenTofu |
| [.github/workflows/backend-ci.yml](../../.github/workflows/backend-ci.yml), [frontend-ci.yml](../../.github/workflows/frontend-ci.yml), [helix-adapter-ci.yml](../../.github/workflows/helix-adapter-ci.yml), [task-worker-ci.yml](../../.github/workflows/task-worker-ci.yml), [api-contract.yml](../../.github/workflows/api-contract.yml) | service CI surfaces | `backend-platform` / `frontend-platform` | `keep` | CI remains valid and independent from platform migration |
| [.github/workflows/release.yml](../../.github/workflows/release.yml), [desktop-release.yml](../../.github/workflows/desktop-release.yml), [mobile-release.yml](../../.github/workflows/mobile-release.yml), [android-tv-release.yml](../../.github/workflows/android-tv-release.yml) | artifact release workflows outside core platform foundation | `desktop-mobile` | `keep` | not blockers for platform foundation, but still deployment/release surfaces in repo |

## 4. Secrets And `.env` Surfaces Inventory

### 4.1 Host-Local Runtime Secrets And Local Dev Files

| Path | Consumer or loader | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [infra/.env](../../infra/.env) and [infra/.env.example](../../infra/.env.example) | root Compose stack via `env_file` in [infra/docker-compose.yml](../../infra/docker-compose.yml) | `infra-platform` | `migrate` | current shared local and operator config surface; target-state must move runtime secrets to `OpenBao` |
| [backend/.env](../../backend/.env) and [backend/.env.example](../../backend/.env.example) | `BaseSettings` in [backend/src/config/settings.py](../../backend/src/config/settings.py) | `backend-platform` | `migrate` | host-local runtime secret/config loading must be replaced for deployed environments |
| [services/task-worker/.env](../../services/task-worker/.env) and [services/task-worker/.env.example](../../services/task-worker/.env.example) | `BaseSettings` in [services/task-worker/src/config.py](../../services/task-worker/src/config.py) and `env_file` in [infra/docker-compose.yml](../../infra/docker-compose.yml) | `transport-backend` | `migrate` | current worker runtime secrets remain host-local |
| [services/telegram-bot/.env](../../services/telegram-bot/.env) and [services/telegram-bot/.env.example](../../services/telegram-bot/.env.example) | bot local runtime env file | `transport-backend` | `migrate` | not yet aligned to secrets-plane model |
| [frontend/.env.local](../../frontend/.env.local) and [frontend/.env.example](../../frontend/.env.example) | Next.js local dev/build-time vars | `frontend-platform` | `keep` | keep for local development only; production config must not depend on workstation-local files |
| [partner/.env.example](../../partner/.env.example) and [admin/.env.example](../../admin/.env.example) | app-local example env surfaces | `partner-admin` | `keep` | keep as example templates; runtime secret material must not live here in deployed environments |
| [infra/subscription/.env](../../infra/subscription/.env) and [infra/subscription/.env.example](../../infra/subscription/.env.example) | subscription local profile env surface | `infra-platform` | `migrate` | local-only today, not target-state deployment source |
| [infra/helix/adapter.env.example](../../infra/helix/adapter.env.example) and [infra/helix/node.env.example](../../infra/helix/node.env.example) | Helix lab templates | `transport-backend` | `keep` | keep as local lab bootstrap templates only |
| [services/helix-adapter/.env.example](../../services/helix-adapter/.env.example) and [services/helix-node/.env.example](../../services/helix-node/.env.example) | service template env surfaces | `transport-backend` | `keep` | keep for local dev examples; deployed runtime must move to `OpenBao`-managed delivery |

### 4.2 Vaulted And Inventory-Based Secret Sprawl

| Path family | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [infra/ansible/inventories/staging/group_vars](../../infra/ansible/inventories/staging/group_vars) and [infra/ansible/inventories/production/group_vars](../../infra/ansible/inventories/production/group_vars) | inventory-scoped rollout vars and vaulted secrets | `infra-platform` | `migrate` | useful migration source material, but not target-state secrets-plane |
| [docs/secret-rotation.md](../../docs/secret-rotation.md) | current manual secret-rotation guidance | `security` / `infra-platform` | `migrate` | must be rewritten against `OpenBao` target model |

### 4.3 Key Secret Consumers Already Visible In Code

| Path | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [backend/src/config/settings.py](../../backend/src/config/settings.py) | central backend env consumer, still defaults `otel_exporter_endpoint` to `http://otel-collector:4317` | `backend-platform` | `migrate` | must move both secrets-plane and collector target to target-state |
| [services/task-worker/src/config.py](../../services/task-worker/src/config.py) | worker env consumer | `transport-backend` | `migrate` | runtime config must move to platform secrets delivery |

## 5. Collector And Telemetry Assumptions Inventory

| Path | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [infra/ansible/roles/alloy_agent](../../infra/ansible/roles/alloy_agent) | current edge Alloy rollout and config rendering | `sre-platform` | `keep` | aligns with target-state collector direction |
| [infra/ansible/playbooks/alloy-rollout.yml](../../infra/ansible/playbooks/alloy-rollout.yml) and [alloy-verify.yml](../../infra/ansible/playbooks/alloy-verify.yml) | rollout and verification for edge Alloy | `sre-platform` | `migrate` | keep knowledge, migrate execution under future fleet/controller flows |
| [infra/prometheus/prometheus.yml](../../infra/prometheus/prometheus.yml) | local monitoring scrape config | `sre-platform` | `migrate` | contains valid `alloy-edge` scrape plus obsolete `otel-collector` scrape assumptions |
| [infra/docker-compose.yml](../../infra/docker-compose.yml) `otel-collector` service | standalone collector for OTLP in local monitoring profile | `sre-platform` | `retire` | target-state collector unifies on `Alloy` |
| [infra/docker-compose.yml](../../infra/docker-compose.yml) `promtail` service | local log shipping tier | `sre-platform` | `retire` | Promtail is obsolete for target-state |
| [backend/src/config/settings.py](../../backend/src/config/settings.py) default `otel_exporter_endpoint` | backend traces target points to `otel-collector` | `backend-platform` | `migrate` | must point at target-state Alloy gateway model |
| [docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md](../../docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md) | current partner runtime observability runbook | `sre-platform` | `keep` | valid operational truth surface; remains separate from PostHog |
| [docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md](../../docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md) | current edge telemetry verification | `sre-platform` | `migrate` | useful migration-era verification, needs rewrite against fleet controller and target-state observability |
| [docs/CYBERVPN_FULL_DESCRIPTION.md](../../docs/CYBERVPN_FULL_DESCRIPTION.md) and [docs/PROJECT_OVERVIEW.md](../../docs/PROJECT_OVERVIEW.md) | broad descriptive docs that still mention `promtail` and `otel-collector` | `docs-program` | `retire` | must not remain normative for platform observability design |
| [docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md](../../docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md) and [docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md](../../docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md) | agent prompts that encode obsolete collector assumptions | `docs-program` | `retire` | explicit cleanup target for `T0.7` |

## 6. Outbox, Eventing, Realtime, And Queueing Inventory

| Path | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [backend/src/application/events/outbox.py](../../backend/src/application/events/outbox.py) | durable outbox boundary for partner-platform subset | `backend-platform` | `migrate` | keep concept and code path, migrate taxonomy and downstream publication to target-state NATS flow |
| [docs/api/platform-foundation-event-taxonomy.md](../api/platform-foundation-event-taxonomy.md) | frozen `T0.2` taxonomy baseline | `platform-architecture` | `keep` | current canonical target-state event model |
| [services/task-worker/src/services/sse_publisher.py](../../services/task-worker/src/services/sse_publisher.py) | Redis pub/sub SSE fan-out on `cybervpn:sse:events` | `transport-backend` | `migrate` | current browser fan-out path; upstream triggers must converge on `outbox -> NATS -> realtime gateway` |
| [services/task-worker/src/broker.py](../../services/task-worker/src/broker.py) | `TaskIQ` with `RedisStreamBroker` and result backend | `transport-backend` | `keep` | keep as async job/queue substrate for now; must not be treated as the platform event backbone |
| [backend/src/presentation/api/v1/ws/monitoring.py](../../backend/src/presentation/api/v1/ws/monitoring.py), [notifications.py](../../backend/src/presentation/api/v1/ws/notifications.py), [tickets.py](../../backend/src/presentation/api/v1/ws/tickets.py), and [backend/src/infrastructure/messaging/websocket_manager.py](../../backend/src/infrastructure/messaging/websocket_manager.py) | current operational websocket channels and ticketed monitoring socket | `backend-platform` | `migrate` | keep operational realtime function, but upstream event source must stop relying on ad hoc direct pushes |
| [partner/src/app/api/analytics/frontend-runtime/route.ts](../../partner/src/app/api/analytics/frontend-runtime/route.ts) and [admin/src/app/api/analytics/frontend-runtime/route.ts](../../admin/src/app/api/analytics/frontend-runtime/route.ts) | frontend runtime telemetry forwarding | `partner-admin` | `keep` | operational telemetry, not product analytics |
| [partner/src/lib/api/integrations.ts](../../partner/src/lib/api/integrations.ts) and [admin/src/lib/api/integrations.ts](../../admin/src/lib/api/integrations.ts) | browser-side realtime monitoring ticket and socket clients | `partner-admin` | `keep` | valid operator/monitoring surface, but not product realtime path |

Current posture summary:

1. `TaskIQ` and Redis Streams are present and valid for background work.
2. Redis pub/sub still powers SSE fan-out for some realtime updates.
3. Operational websocket paths already exist for monitoring topics.
4. Canonical `NATS` event backbone is not implemented yet.

## 7. Edge And Node Bootstrap Inventory

| Path | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [infra/ansible/README.md](../../infra/ansible/README.md) | staged bootstrap and rollout cookbook for edge/control-plane hosts | `infra-platform` | `migrate` | rich operational knowledge, but still operator-sequenced rather than controller-owned |
| [infra/ansible/playbooks/edge-bootstrap.yml](../../infra/ansible/playbooks/edge-bootstrap.yml) | base bootstrap for external hosts | `infra-platform` | `migrate` | target-state replaces direct playbook execution with workflow/controller orchestration |
| [infra/ansible/playbooks/remnawave-rollout.yml](../../infra/ansible/playbooks/remnawave-rollout.yml), [helix-rollout.yml](../../infra/ansible/playbooks/helix-rollout.yml), [alloy-rollout.yml](../../infra/ansible/playbooks/alloy-rollout.yml) | service rollout per host group | `infra-platform` / `sre-platform` | `migrate` | preserve knowledge, remove host-by-host steady-state ownership |
| [infra/ansible/scripts/generate_inventory.py](../../infra/ansible/scripts/generate_inventory.py) | OpenTofu-to-Ansible inventory bridge and `alloy-edge` target snapshot generator | `infra-platform` | `migrate` | useful migration bridge, not target-state source of truth |
| [infra/terraform/live/staging/edge](../../infra/terraform/live/staging/edge) and [infra/terraform/live/production/edge](../../infra/terraform/live/production/edge) | VM/IP/firewall/DNS provisioning for external edge nodes | `infra-platform` | `migrate` | remains infra execution substrate, but future requests must originate in Node Fleet Controller |
| [services/helix-adapter/README.md](../../services/helix-adapter/README.md) | runtime adapter boundary for Helix | `transport-backend` | `keep` | valid adapter boundary, but not full fleet lifecycle plane |
| [docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md](../../docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md), [REMNAWAVE_2_7_4_STAGING_HANDOFF.md](../../docs/runbooks/REMNAWAVE_2_7_4_STAGING_HANDOFF.md), [STAGING_REMNAWAVE_SMOKE_CHECKLIST.md](../../docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md) | migration-era operator runbooks for staged node rollout | `infra-platform` | `migrate` | useful evidence/runbook inputs, but not target-state orchestration |

## 8. GitHub Actions And Promotion Workflow Inventory

### 8.1 Infrastructure And Platform Foundation Workflows

| Workflow | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [iac-ci.yml](../../.github/workflows/iac-ci.yml) | validates current Terraform and Ansible stacks | `infra-platform` | `migrate` | keep validation intent, migrate naming and stack coverage |
| [control-plane-images.yml](../../.github/workflows/control-plane-images.yml) | builds digest-pinned control-plane images | `backend-platform` | `migrate` | intermediate step before GitOps image promotion |
| [control-plane-promote.yml](../../.github/workflows/control-plane-promote.yml) | updates `release.yml` in Ansible inventories | `infra-platform` | `migrate` | inventory-manifest mutation is not the target-state promotion model |
| [deploy-staging.yml](../../.github/workflows/deploy-staging.yml) | staging deployment placeholder | `infra-platform` | `retire` | no canonical deployment action exists here |
| [partner-admin-conformance.yml](../../.github/workflows/partner-admin-conformance.yml) and [partner-observability-conformance.yml](../../.github/workflows/partner-observability-conformance.yml) | conformance checks for app/runtime slices | `partner-admin` / `sre-platform` | `keep` | valid test/conformance surfaces |

### 8.2 Service And Application CI/Release Workflows

| Workflow family | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| `backend-ci`, `backend-security`, `frontend-ci`, `helix-adapter-ci`, `task-worker-ci`, `api-contract`, `ci`, `codeql` | CI and security validation | `backend-platform` / `frontend-platform` / `transport-backend` / `partner-admin` | `keep` | remain valid foundation support |
| `release`, `desktop-release`, `mobile-ci`, `mobile-release`, `android-tv-release`, `verta-udp-*` | product artifact release and verification | `desktop-mobile` | `keep` | not blockers for platform foundation, but still repo-level release paths |

## 9. Docs, Runbooks, And Prompt Surfaces That Encode Runtime Models

| Path | Current role | Owner lane | Disposition | Notes |
|---|---|---|---|---|
| [docs/plans/legacy/vpn-business-deployment-guide.md](legacy/vpn-business-deployment-guide.md) | legacy deployment model | `docs-program` | `retire` | explicitly legacy |
| [docs/plans/legacy/staging-environment.md](legacy/staging-environment.md) | legacy staging environment model | `docs-program` | `retire` | explicitly legacy |
| [docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md](../runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md) | current manual promotion and rollout runbook for VM control plane | `infra-platform` | `migrate` | remains needed during transition only |
| [docs/runbooks/REMNAWAVE_2_7_4_STAGING_HANDOFF.md](../runbooks/REMNAWAVE_2_7_4_STAGING_HANDOFF.md) | detailed operator handoff for staged edge rollout | `infra-platform` | `migrate` | migration-era operational evidence, not target-state orchestration |
| [docs/runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md](../runbooks/STAGING_REMNAWAVE_SMOKE_CHECKLIST.md) | focused edge smoke checklist | `infra-platform` | `migrate` | keep as evidence input, rewrite later against fleet lifecycle and adapter checks |
| [docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md](../runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md) | edge post-deploy verification including Alloy | `sre-platform` | `migrate` | useful now, but tied to legacy rollout mechanics |
| [docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md](../runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md) | operational runtime observability guide | `sre-platform` | `keep` | aligned with operational-truth boundary |
| [docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md](../prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md) and [AGENT_TEAM_PHASE8_PROMPT.md](../prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md) | prompts that still describe `promtail` and standalone `otel-collector` assumptions | `docs-program` | `retire` | explicit target for cleanup |
| [docs/CYBERVPN_FULL_DESCRIPTION.md](../CYBERVPN_FULL_DESCRIPTION.md) and [docs/PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) | broad product/system description with obsolete monitoring composition | `docs-program` | `migrate` | can remain descriptive only after observability references are corrected |

## 10. Inventory Findings By Theme

### 10.1 Current Target-State Alignment Already Present

The repo already contains valid building blocks that should be preserved:

1. durable outbox code exists in [backend/src/application/events/outbox.py](../../backend/src/application/events/outbox.py);
2. edge Alloy rollout already exists in [infra/ansible/roles/alloy_agent](../../infra/ansible/roles/alloy_agent);
3. infrastructure stacks are already split by `foundation`, `dns`, `edge`, and legacy `control-plane`;
4. GitHub Actions already build digest-pinned images for backend, task-worker, and helix-adapter;
5. operational observability and runtime-monitoring surfaces already exist for partner/admin flows.

### 10.2 Current Drift From Target-State

The strongest current drifts are:

1. host-local `.env` files remain live runtime inputs for multiple services;
2. local monitoring still includes `promtail` and standalone `otel-collector`;
3. control-plane promotion still mutates Ansible inventory manifests;
4. edge and node rollout still rely on Ansible and operator-sequenced procedures;
5. Redis pub/sub SSE remains a realtime delivery path outside the target-state `NATS` backbone;
6. legacy docs and prompts still encode obsolete runtime assumptions.

## 11. Explicit Blockers Created For Later Phases

### 11.1 `Phase 1` Blockers

These blockers must be addressed before `Phase 1` can be considered aligned with the target model:

1. `OpenBao` adoption is blocked by host-local runtime secrets in:
   - [infra/.env](../../infra/.env)
   - [backend/.env](../../backend/.env)
   - [services/task-worker/.env](../../services/task-worker/.env)
   - [services/telegram-bot/.env](../../services/telegram-bot/.env)
2. observability unification is blocked by obsolete collector assumptions in:
   - [infra/docker-compose.yml](../../infra/docker-compose.yml)
   - [infra/prometheus/prometheus.yml](../../infra/prometheus/prometheus.yml)
   - [backend/src/config/settings.py](../../backend/src/config/settings.py)
3. GitOps rollout is blocked by legacy promotion/deploy surfaces:
   - [control-plane-promote.yml](../../.github/workflows/control-plane-promote.yml)
   - [deploy-staging.yml](../../.github/workflows/deploy-staging.yml)
   - [docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md](../runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md)
4. fleet automation is blocked by manual or semi-manual rollout sequencing in:
   - [infra/ansible/README.md](../../infra/ansible/README.md)
   - [infra/ansible/playbooks/edge-bootstrap.yml](../../infra/ansible/playbooks/edge-bootstrap.yml)
   - [infra/ansible/playbooks/remnawave-rollout.yml](../../infra/ansible/playbooks/remnawave-rollout.yml)
   - [infra/ansible/playbooks/helix-rollout.yml](../../infra/ansible/playbooks/helix-rollout.yml)

### 11.2 `Phase 2` Blockers

These blockers must be addressed before `Phase 2` can claim eventing and runtime alignment:

1. realtime/event backbone convergence is blocked by Redis pub/sub and ad hoc websocket pushes in:
   - [services/task-worker/src/services/sse_publisher.py](../../services/task-worker/src/services/sse_publisher.py)
   - [backend/src/presentation/api/v1/ws/monitoring.py](../../backend/src/presentation/api/v1/ws/monitoring.py)
   - [backend/src/infrastructure/messaging/websocket_manager.py](../../backend/src/infrastructure/messaging/websocket_manager.py)
2. outbox-to-NATS convergence is blocked because the existing outbox remains partial and partner-scoped:
   - [backend/src/application/events/outbox.py](../../backend/src/application/events/outbox.py)
3. docs and prompts cleanup is blocked by obsolete guidance that would reintroduce deprecated components:
   - [docs/prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md](../prompts/agent-teams/AGENT_TEAM_PHASE3_PROMPT.md)
   - [docs/prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md](../prompts/agent-teams/AGENT_TEAM_PHASE8_PROMPT.md)
   - [docs/CYBERVPN_FULL_DESCRIPTION.md](../CYBERVPN_FULL_DESCRIPTION.md)
4. edge/fleet state convergence is blocked because current rollout data still lives in inventory vars and operator memory:
   - [infra/ansible/inventories/staging/group_vars](../../infra/ansible/inventories/staging/group_vars)
   - [infra/ansible/inventories/production/group_vars](../../infra/ansible/inventories/production/group_vars)

## 12. Frozen Next Use Of This Inventory

This document is now the input for:

1. `T0.7 Temporary Exceptions Register And Removal Deadlines`
2. `T0.8 Phase Gates, Evidence Templates, And Conformance Scoring Model`
3. `Phase 1` work-package scoping for `OpenBao`, `NATS`, `Flux`, `PostHog`, and observability cleanup
4. `Phase 2` work-package scoping for outbox, realtime, and collector convergence
