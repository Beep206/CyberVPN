#!/usr/bin/env python3
"""Render and validate the P3.8 production control-plane cutover scaffold."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


MANAGEMENT_CLUSTER_NAME = "prod-mgmt"
WORKLOAD_CLUSTER_NAME = "prod-hetzner-fsn1-core"
APP_NAMESPACE = "platform-apps"
DATA_NAMESPACE = "platform-data"
FLAGGER_NAMESPACE = "flagger-system"
GATEWAY_NAMESPACE = "networking"
GATEWAY_NAME = "platform-public-gateway"
BACKEND_SECRET_KEY = "kv-apps/data/prod/platform/backend"
TASK_WORKER_SECRET_KEY = "kv-apps/data/prod/platform/task-worker"
POSTGRES_SECRET_KEY = "kv-apps/data/prod/platform/postgres"
SOURCE_REPOSITORY_SLUG = "beep/vpnbussiness"

REQUIRED_ANCHORS: dict[str, tuple[str, ...]] = {
    "docs/api/platform-foundation-initial-control-plane-workloads-spec.md": (
        "`backend`",
        "`task-worker`",
        "`task-scheduler`",
    ),
    "infra/scripts/control_plane_workload_migration.py": (
        "WORKLOAD_CLUSTER_NAME = \"nonprod-hetzner-hel1-core\"",
        "BACKEND_SECRET_KEY = \"kv-apps/data/nonprod/platform/backend\"",
    ),
    "infra/scripts/platform_services_bootstrap.py": (
        "External Secrets Operator",
        "kube-prometheus-stack",
        "Alloy",
    ),
    "infra/scripts/cluster_backup_bootstrap.py": (
        "CloudNativePG",
        "ScheduledBackup",
        "Velero",
    ),
    "infra/scripts/prod_mgmt_bootstrap.py": (
        "prod-mgmt",
        "clusterctl",
        "CAPH_COMPONENTS_URL",
    ),
    "backend/src/config/settings.py": (
        "metrics_port: int = 9091",
        "database_url:",
    ),
    "services/task-worker/src/config.py": (
        "metrics_port: int = 9091",
        "worker_concurrency:",
    ),
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def render_root_readme() -> str:
    return f"""# P3.8 production control-plane cutover scaffold

This scaffold freezes the first production control-plane workload cutover contract for
CyberVPN.

Frozen target:

- management cluster: `{MANAGEMENT_CLUSTER_NAME}`
- production workload cluster: `{WORKLOAD_CLUSTER_NAME}`
- first production runtime set:
  - `backend`
  - `task-worker`
  - `task-scheduler`

Canonical decisions frozen here:

- production cutover authority is `platform-gitops`, not legacy Ansible inventory mutation
  or Compose-era rollout memory;
- the backend is the only first-wave workload that receives progressive delivery in this
  packet, via `Flagger + Gateway API`;
- worker and scheduler reconcile only after the backend release and its progressive-delivery
  prerequisites exist;
- production data authority for the first cutover wave is `CloudNativePG`, with manual
  `PodMonitor` ownership and `ScheduledBackup` resources frozen in Git;
- runtime secret delivery stays `OpenBao -> External Secrets Operator -> Kubernetes Secret`
  with production paths under `kv-apps/data/prod/platform/*`;
- `Alloy` remains the only collector baseline; no `promtail` or standalone long-lived
  `otel-collector` paths are reintroduced;
- this scaffold freezes rollback order and alert boundaries before any live production
  workload exists.

Important boundaries:

- this scaffold does not claim live `prod-mgmt`, live workload-cluster reconciliation, or
  live Cloudflare/provider-L4 cutover already exists;
- it does not place secret values in git;
- it does not claim `helix-adapter` or the external fleet are part of the first production
  workload cutover wave;
- it does not claim `Gate D` or `P3.8 complete`.
"""


def render_platform_gitops_readme() -> str:
    return f"""# platform-gitops

This directory models the production desired-state additions frozen by `P3.8`.

Cluster:

- `{WORKLOAD_CLUSTER_NAME}`

Frozen production cutover surfaces:

- `infrastructure/{WORKLOAD_CLUSTER_NAME}/progressive-delivery`
- `infrastructure/{WORKLOAD_CLUSTER_NAME}/data`
- `infrastructure/{WORKLOAD_CLUSTER_NAME}/observability`
- `apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads`

Source-of-truth boundary:

- `platform-gitops` owns production release pins and rollout ordering;
- `Flux` remains the reconciler, not the source of truth;
- `Flagger` controls backend progressive delivery after `Flux` applies the release;
- `CloudNativePG` is the production PostgreSQL runtime authority for the first cutover wave;
- `OpenBao` remains the secret authority and is referenced only through `ExternalSecret`
  contracts.
"""


def render_cluster_readme() -> str:
    return f"""# {WORKLOAD_CLUSTER_NAME}

This directory is the cluster-local Flux entrypoint for the `P3.8` production cutover
layer on `{WORKLOAD_CLUSTER_NAME}`.

Rules:

- cluster-local `Flux` ordering remains explicit and is not delegated to operator memory;
- the production control-plane cutover layer depends on the earlier platform-services,
  observability, and data-protection baselines rather than silently recreating them;
- the backend production rollout is progressive;
- worker and scheduler are sequenced after the backend release instead of racing the first
  production API cutover.
"""


def render_versions_env() -> str:
    return f"""MANAGEMENT_CLUSTER_NAME={MANAGEMENT_CLUSTER_NAME}
WORKLOAD_CLUSTER_NAME={WORKLOAD_CLUSTER_NAME}
APP_NAMESPACE={APP_NAMESPACE}
DATA_NAMESPACE={DATA_NAMESPACE}
FLAGGER_NAMESPACE={FLAGGER_NAMESPACE}
GATEWAY_NAMESPACE={GATEWAY_NAMESPACE}
GATEWAY_NAME={GATEWAY_NAME}
BACKEND_SECRET_KEY={BACKEND_SECRET_KEY}
TASK_WORKER_SECRET_KEY={TASK_WORKER_SECRET_KEY}
POSTGRES_SECRET_KEY={POSTGRES_SECRET_KEY}
FIRST_PROGRESSIVE_RELEASE=backend
FIRST_PRODUCTION_RUNTIME_SET=backend,task-worker,task-scheduler
"""


def render_spec_manifest() -> str:
    return f"""packet: P3.8
managementCluster: {MANAGEMENT_CLUSTER_NAME}
workloadCluster: {WORKLOAD_CLUSTER_NAME}
appNamespace: {APP_NAMESPACE}
dataNamespace: {DATA_NAMESPACE}
flaggerNamespace: {FLAGGER_NAMESPACE}
gateway:
  namespace: {GATEWAY_NAMESPACE}
  name: {GATEWAY_NAME}
firstProductionRuntimeSet:
  - backend
  - task-worker
  - task-scheduler
progressiveDelivery:
  firstWaveRelease: backend
  provider: gatewayapi:v1
dataAuthority:
  engine: cloudnative-pg
  clusterName: cybervpn-control-plane-db
  scheduledBackup: cybervpn-control-plane-db-daily
secretContracts:
  backend: {BACKEND_SECRET_KEY}
  task-worker: {TASK_WORKER_SECRET_KEY}
  task-scheduler: {TASK_WORKER_SECRET_KEY}
  postgres: {POSTGRES_SECRET_KEY}
"""


def render_check_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-REPLACE_ME_REPO_ROOT}"

python "${REPO_ROOT}/infra/scripts/prod_control_plane_cutover.py" validate --repo-root "${REPO_ROOT}"
echo "Scaffold root: ${OUTPUT_DIR}"
"""


def render_cluster_flux_kustomization(*, name: str, path: str, depends_on: list[str]) -> str:
    depends_block = "\n".join(f"    - name: {item}" for item in depends_on)
    return (
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\n"
        "kind: Kustomization\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 10m\n"
        "  prune: true\n"
        "  wait: true\n"
        "  timeout: 10m\n"
        "  dependsOn:\n"
        f"{depends_block}\n"
        "  sourceRef:\n"
        "    kind: GitRepository\n"
        "    name: flux-system\n"
        f"  path: {path}\n"
    )


def render_simple_kustomization(*, resources: list[str]) -> str:
    rendered = "\n".join(f"  - {item}" for item in resources)
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
{rendered}
"""


def render_progressive_delivery_readme() -> str:
    return f"""# progressive-delivery

This path freezes the first production progressive-delivery substrate for
`{WORKLOAD_CLUSTER_NAME}`.

Frozen decisions:

- `Flagger` is installed in `{FLAGGER_NAMESPACE}`;
- `meshProvider=gatewayapi:v1` is mandatory for the first production canary path;
- the first progressive workload is `cybervpn-backend`;
- the generated `HTTPRoute` must attach to:
  - gateway namespace `{GATEWAY_NAMESPACE}`
  - gateway name `{GATEWAY_NAME}`
- production backend cutover is not treated as successful until canary analysis, rollback,
  and alert evidence exist.
"""


def render_flagger_namespace() -> str:
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {FLAGGER_NAMESPACE}
  labels:
    cybervpn.io/platform-service: flagger
"""


def render_flagger_repository() -> str:
    return """apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: flagger-repository
  namespace: flux-system
spec:
  interval: 30m
  url: https://flagger.app
"""


def render_flagger_helmrelease() -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: flagger
  namespace: {FLAGGER_NAMESPACE}
spec:
  interval: 30m
  chart:
    spec:
      chart: flagger
      version: "1.38.0"
      sourceRef:
        kind: HelmRepository
        name: flagger-repository
        namespace: flux-system
      interval: 30m
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    prometheus:
      install: false
      url: http://prometheus-operated.monitoring:9090
    meshProvider: gatewayapi:v1
"""


def render_data_readme() -> str:
    return f"""# data

This path freezes the first production data-runtime contract for `{WORKLOAD_CLUSTER_NAME}`.

Frozen decisions:

- the first production control-plane PostgreSQL runtime is `CloudNativePG`;
- the first production cluster name is `cybervpn-control-plane-db`;
- `ScheduledBackup` is declared in Git and remains mandatory for the first wave;
- `CloudNativePG` monitoring uses manually managed `PodMonitor` resources because upstream
  deprecates `.spec.monitoring.enablePodMonitor`;
- application and superuser credentials arrive through `ExternalSecret`, not static git
  manifests.
"""


def render_data_namespace() -> str:
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {DATA_NAMESPACE}
  labels:
    cybervpn.io/runtime-surface: platform-data
    cybervpn.io/openbao-secret-delivery: "required"
"""


def render_postgres_app_secret() -> str:
    return f"""apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: cybervpn-control-plane-db-app
  namespace: {DATA_NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: openbao-apps
  target:
    name: cybervpn-control-plane-db-app
    creationPolicy: Owner
  dataFrom:
    - extract:
        key: {POSTGRES_SECRET_KEY}
"""


def render_postgres_superuser_secret() -> str:
    return f"""apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: cybervpn-control-plane-db-superuser
  namespace: {DATA_NAMESPACE}
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: openbao-apps
  target:
    name: cybervpn-control-plane-db-superuser
    creationPolicy: Owner
  dataFrom:
    - extract:
        key: {POSTGRES_SECRET_KEY}
"""


def render_cnpg_cluster() -> str:
    return f"""apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: cybervpn-control-plane-db
  namespace: {DATA_NAMESPACE}
spec:
  instances: 3
  imageName: ghcr.io/cloudnative-pg/postgresql:17.6
  primaryUpdateStrategy: unsupervised
  superuserSecret:
    name: cybervpn-control-plane-db-superuser
  bootstrap:
    initdb:
      database: cybervpn
      owner: cybervpn
      secret:
        name: cybervpn-control-plane-db-app
  storage:
    size: 100Gi
  monitoring:
    enablePodMonitor: false
  resources:
    requests:
      cpu: "1"
      memory: 2Gi
    limits:
      cpu: "2"
      memory: 4Gi
"""


def render_cnpg_podmonitor() -> str:
    return f"""apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: cybervpn-control-plane-db
  namespace: monitoring
spec:
  namespaceSelector:
    matchNames:
      - {DATA_NAMESPACE}
  selector:
    matchLabels:
      cnpg.io/cluster: cybervpn-control-plane-db
  podMetricsEndpoints:
    - port: metrics
"""


def render_cnpg_scheduledbackup() -> str:
    return f"""apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: cybervpn-control-plane-db-daily
  namespace: {DATA_NAMESPACE}
spec:
  schedule: "0 0 1 * * *"
  backupOwnerReference: cluster
  cluster:
    name: cybervpn-control-plane-db
"""


def render_observability_readme() -> str:
    return """# observability

This path freezes the production alerting contract for the first workload cutover wave.

Frozen rules:

- control-plane workload alerts are declared in Git alongside the cutover contract;
- production alerting watches backend availability, Flagger canary state, and the first
  production PostgreSQL cluster;
- `Alloy` remains the only collector assumption; no cutover artifact may reintroduce
  `promtail` or standalone `otel-collector` assumptions.
"""


def render_prometheus_rule() -> str:
    return f"""apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cybervpn-production-control-plane
  namespace: monitoring
spec:
  groups:
    - name: cybervpn.production.control-plane
      rules:
        - alert: CyberVPNBackendUnavailable
          expr: up{{namespace="{APP_NAMESPACE}", service="cybervpn-backend"}} == 0
          for: 5m
          labels:
            severity: critical
            environment: prod
          annotations:
            summary: Backend service is unavailable on the production workload cluster
        - alert: CyberVPNBackendCanaryFailed
          expr: flagger_canary_status{{name="cybervpn-backend", namespace="{APP_NAMESPACE}"}} == 0
          for: 5m
          labels:
            severity: critical
            environment: prod
          annotations:
            summary: Flagger reports the production backend canary as failed
        - alert: CyberVPNControlPlaneDatabasePodsMissing
          expr: count(up{{namespace="{DATA_NAMESPACE}", pod=~"cybervpn-control-plane-db-.*"}}) < 3
          for: 10m
          labels:
            severity: warning
            environment: prod
          annotations:
            summary: Fewer than three CloudNativePG pods are reporting for the production database cluster
"""


def render_workloads_readme() -> str:
    return f"""# platform-workloads

This path freezes the first production application cutover set for `{WORKLOAD_CLUSTER_NAME}`.

Frozen production workload set:

- `backend`
- `task-worker`
- `task-scheduler`

Rules:

- namespace creation is explicit and ordered before all releases;
- the backend is the first release and the only canary-managed workload in this packet;
- worker and scheduler use the already frozen `cybervpn-task-worker` chart family and wait
  for backend cutover prerequisites;
- all runtime secret values are referenced through production OpenBao paths.
"""


def render_app_namespace() -> str:
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {APP_NAMESPACE}
  labels:
    cybervpn.io/runtime-surface: platform-control-plane
    cybervpn.io/environment: prod
"""


def render_ocirepository(*, name: str, chart_name: str) -> str:
    return f"""apiVersion: source.toolkit.fluxcd.io/v1
kind: OCIRepository
metadata:
  name: {name}
  namespace: flux-system
spec:
  interval: 30m
  layerSelector:
    mediaType: application/vnd.cncf.helm.chart.content.v1.tar+gzip
    operation: copy
  secretRef:
    name: ghcr-platform-workloads
  url: oci://ghcr.io/{SOURCE_REPOSITORY_SLUG}/charts/{chart_name}
  ref:
    tag: REPLACE_ME_PRODUCTION_CHART_VERSION
"""


def render_backend_helmrelease() -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cybervpn-backend
  namespace: {APP_NAMESPACE}
spec:
  interval: 10m
  chartRef:
    kind: OCIRepository
    name: cybervpn-backend-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
      strategy: rollback
  values:
    replicaCount: 3
    image:
      repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/backend
      digest: sha256:REPLACE_ME_BACKEND_IMAGE_DIGEST
    externalSecret:
      targetName: backend-runtime
      extractKey: {BACKEND_SECRET_KEY}
    service:
      enabled: true
      type: ClusterIP
      port: 8000
      targetPort: 8000
    metrics:
      enabled: true
      servicePort: 9091
      containerPort: 9091
      serviceMonitor:
        enabled: true
        interval: 30s
    pdb:
      enabled: true
      minAvailable: 2
    migrationJob:
      enabled: true
      command:
        - alembic
        - upgrade
        - head
"""


def render_backend_canary() -> str:
    return f"""apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: cybervpn-backend
  namespace: {APP_NAMESPACE}
spec:
  provider: gatewayapi:v1
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cybervpn-backend
  progressDeadlineSeconds: 600
  service:
    port: 8000
    targetPort: 8000
    hosts:
      - api.REPLACE_ME_PRODUCTION_DOMAIN
    gatewayRefs:
      - name: {GATEWAY_NAME}
        namespace: {GATEWAY_NAMESPACE}
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
      - name: request-duration
        thresholdRange:
          max: 500
        interval: 1m
"""


def render_task_worker_helmrelease(
    *,
    release_name: str,
    digest_placeholder: str,
    target_name: str,
    mode: str,
    command: list[str],
    args: list[str],
    multiproc_enabled: bool,
    replica_count: int,
    pdb_enabled: bool,
) -> str:
    command_block = "\n".join(f"        - {item}" for item in command)
    args_block = "\n".join(f"        - {item}" for item in args) if args else "        []"
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: {release_name}
  namespace: {APP_NAMESPACE}
spec:
  interval: 10m
  chartRef:
    kind: OCIRepository
    name: cybervpn-task-worker-chart
    namespace: flux-system
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
      strategy: rollback
  values:
    replicaCount: {replica_count}
    image:
      repository: ghcr.io/REPLACE_ME_IMAGE_REPOSITORY/task-worker
      digest: {digest_placeholder}
    externalSecret:
      targetName: {target_name}
      extractKey: {TASK_WORKER_SECRET_KEY}
    workload:
      mode: {mode}
      command:
{command_block}
      args:
{args_block}
    metrics:
      enabled: true
      servicePort: 9091
      containerPort: 9091
      serviceMonitor:
        enabled: true
        interval: 30s
    prometheusMultiproc:
      enabled: {"true" if multiproc_enabled else "false"}
      dir: /tmp/prometheus-multiproc
    pdb:
      enabled: {"true" if pdb_enabled else "false"}
      minAvailable: 1
"""


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()

    platform_gitops_dir = output_dir / "platform-gitops"
    cluster_dir = platform_gitops_dir / "clusters" / WORKLOAD_CLUSTER_NAME
    prod_infra_dir = platform_gitops_dir / "infrastructure" / WORKLOAD_CLUSTER_NAME
    prod_apps_dir = platform_gitops_dir / "apps" / WORKLOAD_CLUSTER_NAME / "platform-workloads"

    write_text(output_dir / "README.md", render_root_readme())
    write_text(output_dir / "versions.env", render_versions_env())
    write_text(output_dir / "spec-manifest.yaml", render_spec_manifest())
    write_text(output_dir / "scripts" / "check-prod-control-plane-cutover.sh", render_check_script(), mode=0o750)

    write_text(platform_gitops_dir / "README.md", render_platform_gitops_readme())
    write_text(cluster_dir / "README.md", render_cluster_readme())
    write_text(
        cluster_dir / "kustomization.yaml",
        render_simple_kustomization(
            resources=[
                "platform-production-progressive-delivery.yaml",
                "platform-production-data.yaml",
                "platform-production-observability.yaml",
                "platform-production-workloads-namespace.yaml",
                "platform-production-backend.yaml",
                "platform-production-task-worker.yaml",
                "platform-production-task-scheduler.yaml",
            ]
        ),
    )
    write_text(
        cluster_dir / "platform-production-progressive-delivery.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-progressive-delivery",
            path=f"./infrastructure/{WORKLOAD_CLUSTER_NAME}/progressive-delivery",
            depends_on=["platform-kube-prometheus-stack"],
        ),
    )
    write_text(
        cluster_dir / "platform-production-data.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-data",
            path=f"./infrastructure/{WORKLOAD_CLUSTER_NAME}/data",
            depends_on=["platform-openbao-integration", "platform-kube-prometheus-stack"],
        ),
    )
    write_text(
        cluster_dir / "platform-production-observability.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-observability",
            path=f"./infrastructure/{WORKLOAD_CLUSTER_NAME}/observability",
            depends_on=["platform-kube-prometheus-stack", "platform-alloy"],
        ),
    )
    write_text(
        cluster_dir / "platform-production-workloads-namespace.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-workloads-namespace",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/namespace",
            depends_on=["platform-openbao-integration"],
        ),
    )
    write_text(
        cluster_dir / "platform-production-backend.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-backend",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/backend",
            depends_on=[
                "platform-production-progressive-delivery",
                "platform-production-data",
                "platform-production-observability",
                "platform-production-workloads-namespace",
            ],
        ),
    )
    write_text(
        cluster_dir / "platform-production-task-worker.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-task-worker",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/task-worker",
            depends_on=["platform-production-backend"],
        ),
    )
    write_text(
        cluster_dir / "platform-production-task-scheduler.yaml",
        render_cluster_flux_kustomization(
            name="platform-production-task-scheduler",
            path=f"./apps/{WORKLOAD_CLUSTER_NAME}/platform-workloads/task-scheduler",
            depends_on=["platform-production-task-worker"],
        ),
    )

    progressive_dir = prod_infra_dir / "progressive-delivery"
    write_text(progressive_dir / "README.md", render_progressive_delivery_readme())
    write_text(
        progressive_dir / "kustomization.yaml",
        render_simple_kustomization(resources=["flagger/namespace.yaml", "flagger/repository.yaml", "flagger/helmrelease.yaml"]),
    )
    write_text(progressive_dir / "flagger" / "namespace.yaml", render_flagger_namespace())
    write_text(progressive_dir / "flagger" / "repository.yaml", render_flagger_repository())
    write_text(progressive_dir / "flagger" / "helmrelease.yaml", render_flagger_helmrelease())

    data_dir = prod_infra_dir / "data"
    write_text(data_dir / "README.md", render_data_readme())
    write_text(
        data_dir / "kustomization.yaml",
        render_simple_kustomization(
            resources=[
                "namespace.yaml",
                "cnpg/postgres-app-secret.yaml",
                "cnpg/postgres-superuser-secret.yaml",
                "cnpg/cluster.yaml",
                "cnpg/podmonitor.yaml",
                "cnpg/scheduledbackup.yaml",
            ]
        ),
    )
    write_text(data_dir / "namespace.yaml", render_data_namespace())
    write_text(data_dir / "cnpg" / "postgres-app-secret.yaml", render_postgres_app_secret())
    write_text(data_dir / "cnpg" / "postgres-superuser-secret.yaml", render_postgres_superuser_secret())
    write_text(data_dir / "cnpg" / "cluster.yaml", render_cnpg_cluster())
    write_text(data_dir / "cnpg" / "podmonitor.yaml", render_cnpg_podmonitor())
    write_text(data_dir / "cnpg" / "scheduledbackup.yaml", render_cnpg_scheduledbackup())

    observability_dir = prod_infra_dir / "observability"
    write_text(observability_dir / "README.md", render_observability_readme())
    write_text(observability_dir / "kustomization.yaml", render_simple_kustomization(resources=["control-plane/prometheusrule.yaml"]))
    write_text(observability_dir / "control-plane" / "prometheusrule.yaml", render_prometheus_rule())

    write_text(prod_apps_dir / "README.md", render_workloads_readme())
    write_text(
        prod_apps_dir / "namespace" / "kustomization.yaml",
        render_simple_kustomization(resources=["namespace.yaml"]),
    )
    write_text(prod_apps_dir / "namespace" / "namespace.yaml", render_app_namespace())

    write_text(
        prod_apps_dir / "backend" / "kustomization.yaml",
        render_simple_kustomization(resources=["ocirepository.yaml", "helmrelease.yaml", "canary.yaml"]),
    )
    write_text(
        prod_apps_dir / "backend" / "ocirepository.yaml",
        render_ocirepository(name="cybervpn-backend-chart", chart_name="cybervpn-backend"),
    )
    write_text(prod_apps_dir / "backend" / "helmrelease.yaml", render_backend_helmrelease())
    write_text(prod_apps_dir / "backend" / "canary.yaml", render_backend_canary())

    write_text(
        prod_apps_dir / "task-worker" / "kustomization.yaml",
        render_simple_kustomization(resources=["ocirepository.yaml", "helmrelease.yaml"]),
    )
    write_text(
        prod_apps_dir / "task-worker" / "ocirepository.yaml",
        render_ocirepository(name="cybervpn-task-worker-chart", chart_name="cybervpn-task-worker"),
    )
    write_text(
        prod_apps_dir / "task-worker" / "helmrelease.yaml",
        render_task_worker_helmrelease(
            release_name="cybervpn-task-worker",
            digest_placeholder="sha256:REPLACE_ME_TASK_WORKER_IMAGE_DIGEST",
            target_name="task-worker-runtime",
            mode="worker",
            command=["sh", "-c"],
            args=[
                'mkdir -p "$PROMETHEUS_MULTIPROC_DIR" && rm -f "$PROMETHEUS_MULTIPROC_DIR"/* && exec taskiq worker src.broker:broker --workers "${WORKER_CONCURRENCY:-2}" --fs-discover'
            ],
            multiproc_enabled=True,
            replica_count=3,
            pdb_enabled=True,
        ),
    )

    write_text(
        prod_apps_dir / "task-scheduler" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
    )
    write_text(
        prod_apps_dir / "task-scheduler" / "helmrelease.yaml",
        render_task_worker_helmrelease(
            release_name="cybervpn-task-scheduler",
            digest_placeholder="sha256:REPLACE_ME_TASK_SCHEDULER_IMAGE_DIGEST",
            target_name="task-scheduler-runtime",
            mode="scheduler",
            command=["taskiq", "scheduler", "src.broker:scheduler"],
            args=[],
            multiproc_enabled=False,
            replica_count=1,
            pdb_enabled=False,
        ),
    )

    return 0


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    failures: list[str] = []

    for relative_path, anchors in REQUIRED_ANCHORS.items():
        path = repo_root / relative_path
        if not path.exists():
            failures.append(f"missing required file: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor not in content:
                failures.append(f"missing anchor in {relative_path}: {anchor}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(
        "validated production cutover prerequisites: "
        f"cluster={WORKLOAD_CLUSTER_NAME} management={MANAGEMENT_CLUSTER_NAME} "
        "progressive_delivery=flagger-gatewayapi cnpg=manual-podmonitor"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the P3.8 scaffold")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.set_defaults(func=command_render_scaffold)

    validate = subparsers.add_parser("validate", help="Validate repo-side prerequisites for the P3.8 scaffold")
    validate.add_argument("--repo-root", default=".")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
