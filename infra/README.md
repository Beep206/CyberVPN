# Infrastructure

Local Docker Compose stack that mirrors the launch plan in `docs/plans/legacy/vpn-business-deployment-guide.md`.

The directory now also contains the first staging-first IaC scaffold:

- `infra/terraform/` for cloud resources, managed via `OpenTofu` during the migration window;
- `infra/ansible/` for host bootstrap and later workload deployment.
- `infra/openbao/` for canonical OpenBao policy assets and example auth specs.

The Docker Compose files remain the reference for local development and service topology. The new IaC layout is intentionally separate so we can automate staging edge infrastructure without forcing an immediate control-plane migration.

Current Phase `P1` control-plane additions in this repo:

- `infra/terraform/live/staging/openbao` provisions the first canonical `OpenBao` non-prod foundation on a dedicated Hetzner VM with AWS KMS auto-unseal.
- `infra/scripts/openbao_bootstrap.py` is the canonical helper for:
  - rendering `/etc/openbao/openbao.env` from current AWS env
  - initializing the cluster
  - applying the baseline namespace, auth mounts, secrets engines, and policies
- `infra/openbao/policies` and `infra/openbao/examples` are the source-controlled baseline for the frozen `P1.2` mount and policy posture.
- `infra/terraform/live/staging/nats` provisions the first canonical shared `nats-nonprod` JetStream foundation on dedicated Hetzner VMs with local JetStream storage and a restricted route/exporter firewall.
- `infra/scripts/nats_bootstrap.py` is the canonical helper for:
  - rendering per-node TLS and `nats-server.conf` bundles
  - rendering a Prometheus `file_sd` target artifact for `nats-exporter`
  - producing per-node install scripts for the out-of-band config/TLS cut-in
- `infra/nats/examples/accounts.json.example` is the source-controlled baseline for the frozen `P1.3` account and subject-permission posture.
- `infra/terraform/live/staging/posthog` provisions the first canonical `posthog-nonprod` product-intelligence foundation on a dedicated Hetzner VM with Docker, host-level `NGINX`, and a baseline local backup timer.
- `infra/scripts/posthog_bootstrap.py` is the canonical helper for:
  - rendering deployment env and Docker Compose override files;
  - rendering host-level `NGINX` configs for public ingestion paths and protected UI catch-all;
  - rendering install and baseline backup scripts for out-of-band host cut-in.
- `infra/terraform/live/staging/nonprod-mgmt` provisions the first canonical `nonprod-mgmt` Talos management cluster on dedicated Hetzner VMs with a reserved Kubernetes API endpoint IP and Talos provider bootstrap resources.
- `infra/scripts/nonprod_mgmt_bootstrap.py` is the canonical helper for:
  - rendering a pinned `clusterctl` config for Cluster API core plus Talos providers;
  - rendering the guarded CAPH install step that requires an explicit validated `CAPH_COMPONENTS_URL`;
  - freezing the operator bootstrap bundle for the management-cluster control substrate.
- `infra/terraform/live/production/prod-mgmt` provisions the first canonical `prod-mgmt` Talos management cluster on dedicated Hetzner VMs with a provider-native L4 Kubernetes API endpoint and Talos provider bootstrap resources.
- `infra/scripts/prod_mgmt_bootstrap.py` is the canonical helper for:
  - rendering a pinned `clusterctl` config for Cluster API core plus Talos providers;
  - rendering the guarded CAPH install step that requires an explicit validated `CAPH_COMPONENTS_URL`;
  - freezing the production operator bootstrap bundle for the management-cluster control substrate.
- `infra/scripts/platform_gitops_bootstrap.py` is the canonical helper for:
  - rendering the standalone `platform-gitops` repository scaffold;
  - freezing the initial `clusters/nonprod-mgmt` / `infrastructure/nonprod-mgmt` / `apps/nonprod-mgmt` repository layout;
  - rendering the guarded Flux bootstrap helper that uses GitHub SSH deploy-key auth instead of PAT-in-cluster auth.
- `infra/scripts/control_plane_observability.py` is the canonical helper for:
  - rendering per-host Alloy bundles for `openbao-nonprod`, `nats-nonprod`, and `posthog-nonprod`;
  - rendering Prometheus `file_sd` target artifacts for `alloy-control-plane` and `openbao`;
  - freezing the rule that new external control-plane VMs use `Alloy`, not `promtail` or standalone long-lived `otel-collector` paths.
- `infra/scripts/control_plane_recovery.py` is the canonical helper for:
  - rendering the non-prod operator bundle for `OpenBao`, `NATS`, `PostHog`, and `nonprod-mgmt` backup and restore flows;
  - freezing the baseline artifact layout and restore notes before live DR evidence exists;
  - keeping `P1.8` recovery work explicit and separate from later Kubernetes-native backup orchestration.
- `infra/scripts/workload_cluster_bootstrap.py` is the canonical helper for:
  - rendering the first `P2.1` workload-cluster scaffold for `platform-gitops`;
  - freezing the management-cluster-side CAPI contract for `nonprod-hetzner-hel1-core`;
  - freezing the initial network baseline intent for `Cloudflare`, provider-native `LoadBalancer`, `Cilium Gateway API`, `cert-manager`, and `trust-manager`.
- `infra/scripts/platform_services_bootstrap.py` is the canonical helper for:
  - rendering the first `P2.2` base platform-services scaffold for `platform-gitops`;
  - freezing ordered Flux reconciliation for `cert-manager`, `trust-manager`, `External Secrets Operator`, `kube-prometheus-stack`, `Loki`, `Tempo`, and `Alloy`;
  - freezing the current maintained `OpenBao -> operator -> Kubernetes Secret` implementation path without introducing a second ingress controller beyond the already chosen `Cilium Gateway API` substrate.
- `infra/scripts/collector_convergence.py` is the canonical helper for:
  - auditing repo-side `promtail` and standalone `otel-collector` references against the frozen Alloy-only target state;
  - rendering a tracked-legacy vs unexpected-reference report for `P2.3`;
  - failing validation if new collector drift appears outside the explicitly tracked migration surfaces.
- `infra/scripts/cluster_backup_bootstrap.py` is the canonical helper for:
  - rendering the first `P2.4` non-prod workload-cluster data-protection scaffold for `CloudNativePG`, the `Barman Cloud Plugin`, and `Velero`;
  - freezing the split between PostgreSQL durable recovery via object-store plus WAL archive and fast same-provider recovery via CSI volume snapshots;
  - freezing the rule that `Velero` file-system backup stays exception-only while `Velero` CSI snapshot data movement remains the portability path.
- `infra/scripts/workload_delivery_bootstrap.py` is the canonical helper for:
  - rendering the first `P2.5` source-repo and `platform-gitops` scaffold for `backend` and `task-worker`;
  - freezing the `GitHub Actions -> OCI Helm -> GitOps PR -> Flux` delivery contract for first-party workloads;
  - freezing `OCIRepository + HelmRelease` app delivery and the rule that Ansible release-manifest mutation is no longer the target promotion model.
- `infra/scripts/event_backbone_bootstrap.py` is the canonical helper for:
  - rendering the first `P2.6` repo-side dispatcher, stream, consumer, and replay scaffold around the current persisted outbox;
  - validating that the current backend still exposes the frozen default durable consumers `analytics_mart` and `operational_replay`;
  - freezing service-side `notification_delivery` and `realtime_gateway_projection` as reserved-next consumers for `P2.7`, not silently active cut-in paths.
- `infra/scripts/realtime_delivery_bootstrap.py` is the canonical helper for:
  - rendering the first `P2.7` realtime-gateway scaffold and browser-delivery contract downstream of `PARTNER_EVENTS`;
  - freezing `partner.workspace.feed` as the first canonical business/browser channel;
  - freezing `SSE` as the primary browser delivery protocol while keeping monitoring WebSocket paths explicitly operational-only and the legacy notifications socket explicitly temporary.
- `infra/scripts/control_plane_workload_migration.py` is the canonical helper for:
  - rendering the first `P2.8` Kubernetes runtime scaffold for `backend`, `task-worker`, and `task-scheduler`;
  - freezing OpenBao-backed secret delivery and rollout ordering for the initial control-plane workload migration set;
  - freezing `helix-adapter` and `telegram-bot` as explicit exclusions from the first migration wave.
- `infra/scripts/prod_control_plane_cutover.py` is the canonical helper for:
  - rendering the first `P3.8` production cutover scaffold for `prod-hetzner-fsn1-core`;
  - freezing `Flagger + Gateway API` as the production backend progressive-delivery baseline;
  - freezing production `CloudNativePG`, scheduled backup, alerting, and workload rollout ordering before any live production workload evidence exists.
- `infra/scripts/production_conformance_bundle.py` is the canonical helper for:
  - rendering the final `P3.9` production drill and Gate `D` conformance bundle;
  - freezing the run order and evidence domains for `OpenBao`, `NATS`, `CloudNativePG`, `GitOps`, `PostHog`, and `Node Fleet Controller`;
  - freezing the final scorecard snapshot and gate-evidence assembly surface before any live production drill evidence exists.

Current Ansible rollout phases in this repo:

- Phase 2: base host bootstrap (`infra/ansible/playbooks/edge-bootstrap.yml`)
- Phase 3: Remnawave edge rollout (`infra/ansible/playbooks/remnawave-rollout.yml`)
- Phase 4: Helix edge rollout (`infra/ansible/playbooks/helix-rollout.yml`)
- Phase 5: Alloy telemetry rollout and IaC verification gates (`infra/ansible/playbooks/alloy-rollout.yml`)

## Quick start
1. Review and edit `infra/.env` (generated for local use) or copy `infra/.env.example`.
2. Start the core services:

```bash
cd infra
docker compose up -d
```

Optional services are enabled via profiles:

```bash
docker compose --profile proxy --profile subscription --profile bot --profile monitoring up -d
```

Helix lab profiles are opt-in:

```bash
# Adapter only
docker compose --profile helix up -d

# Adapter + two local lab nodes + monitoring + worker audits
docker compose --profile helix-lab --profile monitoring --profile worker up -d
```

### Development mode

For hot-reload, debug ports, and verbose logging:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Adds: DEBUG logging, Python debugger port (5678), Grafana anonymous auth.

## Local endpoints
- Panel: http://localhost:3000 (or http://panel.localhost with the proxy profile)
- Metrics: http://localhost:3001/metrics
- Postgres: localhost:6767
- Subscription page: http://localhost:3010 (subscription profile)
- Prometheus: http://localhost:9094 (monitoring profile)
- Grafana: http://localhost:3002 (monitoring profile)
- Helix adapter: http://localhost:8088/healthz (helix profile)
- Helix lab node: http://localhost:8091/healthz (helix-lab profile)
- Helix lab node 02: http://localhost:8092/healthz (helix-lab profile)

## Remnawave baseline

- validated baseline: panel/backend `2.7.4`, edge node `2.7.4`
- canonical internal contract: `backend/src/infrastructure/remnawave/contracts.py`
- vendored SDK baseline: `SDK/python-sdk-production` on `2.7.4`, reference and contract-test input only
- webhook contract: `X-Remnawave-Signature` + `X-Remnawave-Timestamp` with `REMNAWAVE_WEBHOOK_SECRET`
- upgrade procedure and doc guards: `docs/runbooks/REMNAWAVE_UPGRADE_GUARDRAILS.md`

## Helix Lab

The Helix lab keeps `Remnawave` authoritative while adding an adapter and two lab node
daemons around it, so route failover can be exercised against a real secondary path.

1. Copy `infra/.env.example` to `infra/.env` if you have not already.
2. Fill in:
   - `HELIX_INTERNAL_AUTH_TOKEN`
   - `HELIX_MANIFEST_SIGNING_KEY`
   - `HELIX_REMNAWAVE_TOKEN` once you have a real local API token
3. Review reference templates:
   - `infra/helix/adapter.env.example`
   - `infra/helix/node.env.example`
4. Start the core stack and lab services:

```bash
cd infra
docker compose --profile helix-lab --profile monitoring --profile worker up -d
```

5. Bootstrap the local lab assignment state:

```bash
bash infra/tests/bootstrap_helix_lab.sh
```

6. Verify:
   - adapter health: `curl http://localhost:8088/readyz`
   - node health: `curl http://localhost:8091/readyz`
   - node 02 health: `curl http://localhost:8092/readyz`
   - Prometheus targets: `curl http://localhost:9094/api/v1/targets`
   - Grafana dashboard: `CyberVPN Helix`

### Helix Headless Perf Lab

Once the lab stack is healthy, you can drive Helix perf runs directly from the desktop workspace:

```powershell
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_lab_bench.ps1 -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_recovery_lab.ps1 -Mode failover -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_target_matrix.ps1 -Preset mixed -UseSyntheticLabTarget
```

Artifacts land under `apps/desktop-client/.artifacts/*` and include runtime config, manifest,
sidecar stdout/stderr, health snapshots, telemetry snapshots, and the JSON report for each run.

The adapter applies SQLx migrations on startup. The lab nodes keep their state in the
`helix_node_state` and `helix_node_state_2` Docker volumes so rollback and last-known-good
behavior survive container restarts.

### Helix Rollback And Hardening Drills

Static rollback verification:

```bash
bash infra/tests/verify_helix_rollback.sh
```

Destructive live rollback verification:

```bash
HELIX_REQUIRE_LIVE=true HELIX_RUN_DESTRUCTIVE_DRILL=true bash infra/tests/verify_helix_rollback.sh
```

Reset lab history before a new destructive drill:

```bash
bash infra/tests/reset_helix_lab_history.sh
```

Helix backend live load scenario lives in:

```text
backend/tests/load/test_helix_load.py
```

Deterministic local canary-evidence budget test:

```text
backend/tests/load/test_helix_canary_evidence_budget.py
```

See [docs/testing/helix-load-test-plan.md](C:/project/CyberVPN/docs/testing/helix-load-test-plan.md) for the required environment and the internal-beta acceptance rules.

## PostgreSQL Backups

The `db-backup` service runs daily automated backups using `pg_dump --format=custom`.

- **Storage:** `infra/backups/postgres/` (host-mounted, outside Docker volumes)
- **Schedule:** Daily at midnight UTC (`@daily`)
- **Retention:** 7 days (older backups auto-deleted)
- **Format:** Custom (compressed, supports selective restore via `pg_restore`)

### Manual backup

```bash
docker exec db-backup /backup.sh
```

### List available backups

```bash
ls -lht infra/backups/postgres/
```

### Restore to existing database (full)

```bash
# Stop the app first to avoid active connections
docker compose stop remnawave

# Restore from the most recent backup
docker exec -i remnawave-db pg_restore \
  --clean --if-exists \
  --dbname="${POSTGRES_DB}" \
  -U "${POSTGRES_USER}" \
  < infra/backups/postgres/<db-name>/latest.dump

# Restart
docker compose start remnawave
```

### Restore to a fresh database

```bash
# Drop and recreate the database
docker exec remnawave-db psql -U "${POSTGRES_USER}" -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker exec remnawave-db psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

# Restore
docker exec -i remnawave-db pg_restore \
  --dbname="${POSTGRES_DB}" \
  -U "${POSTGRES_USER}" \
  < infra/backups/postgres/<db-name>/latest.dump
```

### Restore a single table

```bash
docker exec -i remnawave-db pg_restore \
  --dbname="${POSTGRES_DB}" \
  -U "${POSTGRES_USER}" \
  --table=<table_name> \
  --clean --if-exists \
  < infra/backups/postgres/<db-name>/latest.dump
```

### Verify backup integrity

```bash
# List contents without restoring
pg_restore --list infra/backups/postgres/<db-name>/latest.dump
```

## Valkey (Redis) Zero-Persistence

Valkey runs with persistence disabled (`--save "" --appendonly no`). This is intentional:

- **Use case:** Cache and TaskIQ message broker only — no durable data
- **Benefit:** Lower disk I/O, faster writes, simpler operations
- **Trade-off:** All data lost on container restart (cache rebuilds from DB, pending tasks re-enqueue)
- **No backup needed:** There is no state to back up

If you need durable queues in the future, enable AOF: `--appendonly yes --appendfsync everysec`.

## Notes
- If you change `METRICS_PASS` in `infra/.env`, update `infra/prometheus/prometheus.yml`.
- Subscription Page requires a Remnawave API token from the panel.
- Helix alerts live in `infra/prometheus/rules/helix_alerts.yml`.
- Staging Remnawave edge rollout uses `make ansible-phase3-staging` after Terraform inventory generation and vault bootstrap.
- Staging Helix edge rollout uses `make ansible-phase4-staging` once a published `helix-node` image, adapter URL, token, node id, and transport ports are set in Ansible vars.
- Staging Alloy rollout uses `make ansible-phase5-staging` once the Loki push URL and any required auth are set in `infra/ansible/inventories/staging/group_vars/edge_staging/alloy.yml`.
- `make inventory-staging` emits a Prometheus target artifact under `infra/artifacts/prometheus/staging/alloy-edge.json`.
- `make inventory-production` emits the production equivalents without touching the local dev Prometheus target directory.
- `make inventory-production` requires a real initialized `infra/terraform/live/production/edge` backend and state.
- `terraform/live/staging/control-plane` and `terraform/live/production/control-plane` provision Phase 7 host scaffolding for backend, worker, Helix adapter, and backup flows.
- `terraform/live/staging/openbao` provisions the `openbao-nonprod` baseline and must be applied before later secrets-plane dependent packets claim readiness.
- `terraform/live/staging/nats` provisions the `nats-nonprod` baseline and must be applied before later event-backbone dependent packets claim readiness.
- `terraform/live/staging/posthog` provisions the `posthog-nonprod` baseline and must be applied before later product-intelligence dependent packets claim readiness.
- Control-plane rollout is handled by `make ansible-control-plane-rollout-staging` / `make ansible-control-plane-rollout-production` once the corresponding inventory and vault files exist.
- Control-plane backup evidence is handled by `make ansible-control-plane-backup-staging` and documented in `docs/runbooks/CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md`.
- Phase 8 promotes control-plane images through `infra/ansible/inventories/*/group_vars/control_plane_*/release.yml` with digest-pinned refs, not mutable tags.
- Use `.github/workflows/control-plane-images.yml` to publish digests and `.github/workflows/control-plane-promote.yml` to prepare a reviewable promotion branch.
- Use `docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md` for the release and vault bootstrap procedure.
- Use `docs/runbooks/CONTROL_PLANE_DR_DRILL.md` before running a destructive restore drill.
- Run `make monitoring-validate` from `infra/` to verify the dashboard set expected by Phase 5.
- Keep IaC rollout manual; `tofu apply` and Ansible rollout remain operator-approved steps, not auto-apply CI hooks.
- Use `docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md` as the post-deploy evidence checklist.
- Use `docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md` for the Phase 6 production canary procedure.
- Run `bash infra/tests/test_helix_stack.sh` after profile changes to verify the lab wiring.
- Run `bash infra/tests/verify_helix_rollback.sh` to verify rollback-drill prerequisites and, optionally, execute a destructive rollback rehearsal with `HELIX_RUN_DESTRUCTIVE_DRILL=true`.
