#!/usr/bin/env python3
"""Render the P2.4 non-prod data-protection scaffold for the first workload cluster."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def render_root_readme(*, workload_cluster_name: str) -> str:
    return f"""# P2.4 data-protection scaffold

This scaffold freezes the first non-prod Kubernetes backup and restore baseline for CyberVPN.

Cluster id:

- workload cluster: `{workload_cluster_name}`

Control-surface decisions frozen here:

- `CloudNativePG` is the canonical PostgreSQL operator for Kubernetes workloads;
- PostgreSQL durable backup and PITR source of truth is `CloudNativePG + Barman Cloud Plugin + WAL archive`;
- same-provider fast restore uses CSI-backed volume snapshots;
- cross-provider or cross-cluster volume portability uses `Velero` CSI snapshot data movement to object storage;
- `Velero` is the canonical Kubernetes API object and portable-volume backup orchestrator;
- `Velero` file-system backup remains exception-only, not the default path;
- `Barman Cloud Plugin` is installed in the same namespace as the `CloudNativePG` operator;
- this scaffold does not claim any live object-store credentials, bucket ownership, or snapshot class compatibility already exists.

Important boundaries:

- this scaffold does not commit secret values;
- this scaffold does not claim a real PostgreSQL cluster already exists on the workload cluster;
- `templates/` under backup policies are contracts for later database workloads and are intentionally not part of the applied `kustomization.yaml`;
- live closure requires real object-store credentials, a validated CSI `VolumeSnapshotClass`, and restore evidence.
"""


def render_cluster_readme(*, workload_cluster_name: str) -> str:
    return f"""# {workload_cluster_name}

This directory is the cluster-local Flux entrypoint for the `P2.4` data-protection layer on `{workload_cluster_name}`.

Rules:

- `kustomization.yaml` registers only Flux `Kustomization` objects for ordered reconciliation;
- `P2.4` does not create a PostgreSQL application workload by itself;
- data-protection controllers and policies are reconciled before application-level database clusters consume them;
- the `Barman Cloud Plugin` path is manifest-based because upstream currently documents manifest or Kustomize install, not a Helm chart install.
"""


def render_data_protection_readme(*, workload_cluster_name: str) -> str:
    return f"""# data-protection/{workload_cluster_name}

This path contains the frozen `P2.4` base data-protection scaffold for `{workload_cluster_name}`.

Directory purpose:

- `sources/`
  - chart repositories for `CloudNativePG` and `Velero`
- `namespaces/`
  - required namespaces and labels
- `cnpg-operator/`
  - `CloudNativePG` operator `HelmRelease`
- `barman-plugin/`
  - vendored-manifest contract for the `Barman Cloud Plugin`
- `velero/`
  - `Velero` `HelmRelease`
- `backup-policies/`
  - `Velero` storage locations and schedules
  - non-applied `templates/` for `CloudNativePG` `ObjectStore` and `ScheduledBackup` resources

Implementation notes:

- `Velero` is configured snapshot-first with `defaultSnapshotMoveData=true`;
- `Velero` `defaultVolumesToFsBackup` is set to `false` in the scheduled backup contract;
- `File System Backup` stays available only as an explicit exception path;
- the `Barman Cloud Plugin` manifest placeholder must be replaced by the official release manifest before live reconciliation.
"""


def render_cluster_kustomization() -> str:
    return """apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - platform-data-protection-sources.yaml
  - platform-data-protection-namespaces.yaml
  - platform-cnpg-operator.yaml
  - platform-barman-plugin.yaml
  - platform-velero.yaml
  - platform-backup-policies.yaml
"""


def render_flux_kustomization(*, name: str, path: str, depends_on: list[str] | None = None) -> str:
    depends_block = ""
    if depends_on:
        items = "\n".join(f"    - name: {dependency}" for dependency in depends_on)
        depends_block = f"  dependsOn:\n{items}\n"

    return (
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\n"
        "kind: Kustomization\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 10m\n"
        "  prune: true\n"
        "  wait: true\n"
        "  timeout: 10m\n"
        f"{depends_block}"
        "  sourceRef:\n"
        "    kind: GitRepository\n"
        "    name: flux-system\n"
        f"  path: {path}\n"
    )


def render_simple_kustomization(*, resources: list[str]) -> str:
    rendered_resources = "\n".join(f"  - {resource}" for resource in resources)
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
{rendered_resources}
"""


def render_helmrepository(*, name: str, url: str) -> str:
    return (
        "apiVersion: source.toolkit.fluxcd.io/v1\n"
        "kind: HelmRepository\n"
        f"metadata:\n  name: {name}\n  namespace: flux-system\n"
        "spec:\n"
        "  interval: 30m\n"
        f"  url: {url}\n"
    )


def render_namespace_objects() -> str:
    return """apiVersion: v1
kind: Namespace
metadata:
  name: cnpg-system
  labels:
    cybervpn.io/platform-service: cnpg
    cybervpn.io/trust-bundle: "enabled"
---
apiVersion: v1
kind: Namespace
metadata:
  name: velero
  labels:
    cybervpn.io/platform-service: velero
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/warn: privileged
---
apiVersion: v1
kind: Namespace
metadata:
  name: platform-data
  labels:
    cybervpn.io/platform-service: platform-data
    cybervpn.io/trust-bundle: "enabled"
"""


def render_cnpg_operator_helmrelease(*, cnpg_chart_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: cnpg
  namespace: cnpg-system
spec:
  interval: 30m
  chart:
    spec:
      chart: cloudnative-pg
      version: "{cnpg_chart_version}"
      sourceRef:
        kind: HelmRepository
        name: cnpg-repository
        namespace: flux-system
      interval: 30m
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    crds:
      create: true
# upstream chart version pinned from CloudNativePG charts release metadata
# version: {cnpg_chart_version}
"""


def render_barman_plugin_readme(*, barman_plugin_version: str) -> str:
    return f"""# Barman Cloud Plugin vendor contract

The `Barman Cloud Plugin` is installed via the official release manifest, not via Helm.

Current pinned release:

- `{barman_plugin_version}`

Rules:

- the plugin must be installed in the same namespace as the `CloudNativePG` operator, typically `cnpg-system`;
- the vendored `manifest.yaml` must be replaced by the official release manifest before live reconciliation;
- the placeholder `manifest.yaml` exists only so the scaffold remains structurally complete during repo-side work.
"""


def render_barman_upstream_env(*, barman_plugin_version: str) -> str:
    return (
        f"BARMAN_PLUGIN_VERSION={barman_plugin_version}\n"
        f"BARMAN_PLUGIN_MANIFEST_URL=https://github.com/cloudnative-pg/plugin-barman-cloud/releases/download/{barman_plugin_version}/manifest.yaml\n"
        "BARMAN_PLUGIN_NAMESPACE=cnpg-system\n"
    )


def render_barman_placeholder_manifest() -> str:
    return """# Replace this placeholder with the official Barman Cloud Plugin release manifest before live reconciliation.
apiVersion: v1
kind: List
items: []
"""


def render_barman_sync_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/upstream.env"

curl -fsSL "${BARMAN_PLUGIN_MANIFEST_URL}" -o "${SCRIPT_DIR}/manifest.yaml"
"""


def render_velero_helmrelease(*, velero_chart_version: str) -> str:
    return f"""apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: velero
  namespace: velero
spec:
  interval: 30m
  chart:
    spec:
      chart: velero
      version: "{velero_chart_version}"
      sourceRef:
        kind: HelmRepository
        name: velero-repository
        namespace: flux-system
      interval: 30m
  install:
    remediation:
      retries: 3
  upgrade:
    remediation:
      retries: 3
  values:
    credentials:
      useSecret: true
      existingSecret: velero-cloud-credentials
    initContainers:
      - name: velero-plugin-for-aws
        image: REPLACE_ME_VELERO_PROVIDER_PLUGIN_IMAGE
        imagePullPolicy: IfNotPresent
        volumeMounts:
          - mountPath: /target
            name: plugins
    backupsEnabled: false
    snapshotsEnabled: false
    deployNodeAgent: true
    configuration:
      uploaderType: kopia
      features: EnableCSI
      defaultSnapshotMoveData: true
      defaultBackupTTL: 720h0m0s
    metrics:
      enabled: true
      serviceMonitor:
        enabled: true
      nodeAgentPodMonitor:
        enabled: true
# upstream chart version pinned from vmware-tanzu/helm-charts release metadata
# version: {velero_chart_version}
"""


def render_backup_policies_readme(*, workload_cluster_name: str) -> str:
    return f"""# Backup policies

This directory freezes the first non-prod backup policy scaffold for `{workload_cluster_name}`.

Applied resources:

- `BackupStorageLocation/default`
- `VolumeSnapshotLocation/default`
- `Schedule/platform-cluster-backup-daily`

Template-only resources under `templates/`:

- `ObjectStore/platform-core-postgres-store`
- `ScheduledBackup/platform-core-postgres-plugin`
- `ScheduledBackup/platform-core-postgres-volume-snapshot`
- `Cluster` backup snippet showing how to combine WAL archiving with snapshot backup

Important policy:

- object-store backup plus WAL archive is the PostgreSQL durable recovery source of truth;
- volume snapshots are the fast same-provider restore path;
- `Velero` file-system backup is exception-only, not default;
- live reconciliation also requires runtime-owned inputs that are intentionally not committed here:
  - `velero/velero-cloud-credentials`
  - `cnpg-barman-cloud-credentials` in the target database namespace
  - a validated CSI `VolumeSnapshotClass`
  - object-store bucket, region, and KMS ownership
"""


def render_backup_storage_location(*, workload_cluster_name: str) -> str:
    return f"""apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: default
  namespace: velero
spec:
  backupSyncPeriod: 1m0s
  provider: aws
  default: true
  objectStorage:
    bucket: REPLACE_ME_NONPROD_BACKUP_BUCKET
    prefix: nonprod/{workload_cluster_name}
  credential:
    name: velero-cloud-credentials
    key: cloud
  config:
    region: REPLACE_ME_NONPROD_BACKUP_REGION
    kmsKeyId: REPLACE_ME_AWS_KMS_KEY_ID
"""


def render_volume_snapshot_location() -> str:
    return """apiVersion: velero.io/v1
kind: VolumeSnapshotLocation
metadata:
  name: default
  namespace: velero
spec:
  provider: aws
  credential:
    name: velero-cloud-credentials
    key: cloud
  config:
    region: REPLACE_ME_NONPROD_BACKUP_REGION
"""


def render_velero_schedule(*, data_namespace: str) -> str:
    return f"""apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: platform-cluster-backup-daily
  namespace: velero
spec:
  paused: false
  skipImmediately: true
  schedule: "0 0 3 * * *"
  useOwnerReferencesInBackup: false
  template:
    ttl: 720h0m0s
    includedNamespaces:
      - {data_namespace}
      - velero
      - cnpg-system
      - cert-manager
      - monitoring
      - observability
      - external-secrets
    includeClusterResources: true
    snapshotVolumes: true
    storageLocation: default
    volumeSnapshotLocations:
      - default
    defaultVolumesToFsBackup: false
    snapshotMoveData: true
    datamover: velero
"""


def render_template_readme(*, database_namespace: str, database_cluster_name: str) -> str:
    return f"""# CloudNativePG backup templates

These files are templates only and are intentionally not part of the applied `kustomization.yaml`.

They assume:

- namespace: `{database_namespace}`
- cluster name: `{database_cluster_name}`

Use them once the first real PostgreSQL workload exists on the workload cluster.
"""


def render_cnpg_objectstore_template(*, database_namespace: str, objectstore_name: str) -> str:
    return f"""apiVersion: barmancloud.cnpg.io/v1
kind: ObjectStore
metadata:
  name: {objectstore_name}
  namespace: {database_namespace}
spec:
  configuration:
    destinationPath: s3://REPLACE_ME_NONPROD_POSTGRES_BACKUP_BUCKET/{database_namespace}/
    s3Credentials:
      accessKeyId:
        name: cnpg-barman-cloud-credentials
        key: ACCESS_KEY_ID
      secretAccessKey:
        name: cnpg-barman-cloud-credentials
        key: ACCESS_SECRET_KEY
    wal:
      compression: gzip
"""


def render_cnpg_scheduledbackup_plugin_template(*, database_namespace: str, database_cluster_name: str) -> str:
    return f"""apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: {database_cluster_name}-plugin
  namespace: {database_namespace}
spec:
  schedule: "0 0 2 * * 0"
  backupOwnerReference: self
  immediate: true
  cluster:
    name: {database_cluster_name}
  method: plugin
  pluginConfiguration:
    name: barman-cloud.cloudnative-pg.io
"""


def render_cnpg_scheduledbackup_snapshot_template(*, database_namespace: str, database_cluster_name: str) -> str:
    return f"""apiVersion: postgresql.cnpg.io/v1
kind: ScheduledBackup
metadata:
  name: {database_cluster_name}-volume-snapshot
  namespace: {database_namespace}
spec:
  schedule: "0 0 1 * * *"
  backupOwnerReference: self
  cluster:
    name: {database_cluster_name}
  method: volumeSnapshot
"""


def render_cnpg_cluster_backup_snippet(
    *,
    database_namespace: str,
    database_cluster_name: str,
    objectstore_name: str,
    storage_class: str,
    snapshot_class: str,
) -> str:
    return f"""# Apply this snippet only after the first real PostgreSQL cluster exists.
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: {database_cluster_name}
  namespace: {database_namespace}
spec:
  instances: 3
  storage:
    storageClass: {storage_class}
    size: 100Gi
  walStorage:
    storageClass: {storage_class}
    size: 50Gi
  plugins:
    - name: barman-cloud.cloudnative-pg.io
      isWALArchiver: true
      parameters:
        barmanObjectName: {objectstore_name}
  backup:
    volumeSnapshot:
      className: {snapshot_class}
"""


def render_versions_env(
    *,
    workload_cluster_name: str,
    cnpg_chart_version: str,
    barman_plugin_version: str,
    velero_chart_version: str,
    database_namespace: str,
    database_cluster_name: str,
    objectstore_name: str,
) -> str:
    return (
        f"WORKLOAD_CLUSTER_ID={workload_cluster_name}\n"
        f"CNPG_CHART_VERSION={cnpg_chart_version}\n"
        f"BARMAN_PLUGIN_VERSION={barman_plugin_version}\n"
        f"VELERO_CHART_VERSION={velero_chart_version}\n"
        "VELERO_PROVIDER_PLUGIN_IMAGE=REQUIRED_OPERATOR_PIN\n"
        "VELERO_BACKUP_BUCKET=REPLACE_ME_NONPROD_BACKUP_BUCKET\n"
        "VELERO_BACKUP_REGION=REPLACE_ME_NONPROD_BACKUP_REGION\n"
        "VELERO_BACKUP_KMS_KEY_ID=REPLACE_ME_AWS_KMS_KEY_ID\n"
        "VELERO_SNAPSHOT_CLASS=REPLACE_ME_VOLUME_SNAPSHOT_CLASS\n"
        f"CNPG_DATABASE_NAMESPACE={database_namespace}\n"
        f"CNPG_CLUSTER_NAME={database_cluster_name}\n"
        f"CNPG_OBJECTSTORE_NAME={objectstore_name}\n"
        "CNPG_STORAGE_CLASS=REPLACE_ME_STORAGE_CLASS\n"
        "CNPG_VOLUME_SNAPSHOT_CLASS=REPLACE_ME_VOLUME_SNAPSHOT_CLASS\n"
    )


def render_check_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

flux get kustomizations -A
kubectl get helmreleases.helm.toolkit.fluxcd.io -A
kubectl get deployments -n cnpg-system
kubectl get deployments -n velero
kubectl get secret -n velero velero-cloud-credentials
kubectl get backupstoragelocations.velero.io -n velero
kubectl get volumesnapshotlocations.velero.io -n velero
kubectl get schedules.velero.io -n velero
kubectl get objectstores.barmancloud.cnpg.io -A
kubectl get scheduledbackups.postgresql.cnpg.io -A

echo "P2.4 data-protection checks completed."
"""


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    cluster_dir = output_dir / "clusters" / args.workload_cluster_name
    data_protection_dir = output_dir / "infrastructure" / args.workload_cluster_name / "data-protection"
    templates_dir = data_protection_dir / "backup-policies" / "templates"

    write_text(output_dir / "README.md", render_root_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(cluster_dir / "README.md", render_cluster_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(cluster_dir / "kustomization.yaml", render_cluster_kustomization(), mode=0o644)

    cluster_kustomizations = {
        "platform-data-protection-sources.yaml": render_flux_kustomization(
            name="platform-data-protection-sources",
            path=f"./infrastructure/{args.workload_cluster_name}/data-protection/sources",
        ),
        "platform-data-protection-namespaces.yaml": render_flux_kustomization(
            name="platform-data-protection-namespaces",
            path=f"./infrastructure/{args.workload_cluster_name}/data-protection/namespaces",
        ),
        "platform-cnpg-operator.yaml": render_flux_kustomization(
            name="platform-cnpg-operator",
            path=f"./infrastructure/{args.workload_cluster_name}/data-protection/cnpg-operator",
            depends_on=["platform-data-protection-sources", "platform-data-protection-namespaces"],
        ),
        "platform-barman-plugin.yaml": render_flux_kustomization(
            name="platform-barman-plugin",
            path=f"./infrastructure/{args.workload_cluster_name}/data-protection/barman-plugin",
            depends_on=["platform-cnpg-operator"],
        ),
        "platform-velero.yaml": render_flux_kustomization(
            name="platform-velero",
            path=f"./infrastructure/{args.workload_cluster_name}/data-protection/velero",
            depends_on=["platform-data-protection-sources", "platform-data-protection-namespaces"],
        ),
        "platform-backup-policies.yaml": render_flux_kustomization(
            name="platform-backup-policies",
            path=f"./infrastructure/{args.workload_cluster_name}/data-protection/backup-policies",
            depends_on=["platform-cnpg-operator", "platform-barman-plugin", "platform-velero"],
        ),
    }

    for file_name, content in cluster_kustomizations.items():
        write_text(cluster_dir / file_name, content, mode=0o644)

    write_text(
        data_protection_dir / "README.md",
        render_data_protection_readme(workload_cluster_name=args.workload_cluster_name),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "versions.env",
        render_versions_env(
            workload_cluster_name=args.workload_cluster_name,
            cnpg_chart_version=args.cnpg_chart_version,
            barman_plugin_version=args.barman_plugin_version,
            velero_chart_version=args.velero_chart_version,
            database_namespace=args.database_namespace,
            database_cluster_name=args.database_cluster_name,
            objectstore_name=args.objectstore_name,
        ),
        mode=0o644,
    )
    write_text(output_dir / "scripts" / "check-data-protection.sh", render_check_script(), mode=0o750)

    write_text(
        data_protection_dir / "sources" / "kustomization.yaml",
        render_simple_kustomization(resources=["cnpg-repository.yaml", "velero-repository.yaml"]),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "sources" / "cnpg-repository.yaml",
        render_helmrepository(name="cnpg-repository", url="https://cloudnative-pg.github.io/charts"),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "sources" / "velero-repository.yaml",
        render_helmrepository(name="velero-repository", url="https://vmware-tanzu.github.io/helm-charts"),
        mode=0o644,
    )

    write_text(
        data_protection_dir / "namespaces" / "kustomization.yaml",
        render_simple_kustomization(resources=["namespaces.yaml"]),
        mode=0o644,
    )
    write_text(data_protection_dir / "namespaces" / "namespaces.yaml", render_namespace_objects(), mode=0o644)

    write_text(
        data_protection_dir / "cnpg-operator" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "cnpg-operator" / "helmrelease.yaml",
        render_cnpg_operator_helmrelease(cnpg_chart_version=args.cnpg_chart_version),
        mode=0o644,
    )

    write_text(
        data_protection_dir / "barman-plugin" / "kustomization.yaml",
        render_simple_kustomization(resources=["manifest.yaml"]),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "barman-plugin" / "README.md",
        render_barman_plugin_readme(barman_plugin_version=args.barman_plugin_version),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "barman-plugin" / "upstream.env",
        render_barman_upstream_env(barman_plugin_version=args.barman_plugin_version),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "barman-plugin" / "manifest.yaml",
        render_barman_placeholder_manifest(),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "barman-plugin" / "sync-official-manifest.sh",
        render_barman_sync_script(),
        mode=0o750,
    )

    write_text(
        data_protection_dir / "velero" / "kustomization.yaml",
        render_simple_kustomization(resources=["helmrelease.yaml"]),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "velero" / "helmrelease.yaml",
        render_velero_helmrelease(velero_chart_version=args.velero_chart_version),
        mode=0o644,
    )

    write_text(
        data_protection_dir / "backup-policies" / "kustomization.yaml",
        render_simple_kustomization(
            resources=[
                "backup-storage-location.yaml",
                "volume-snapshot-location.yaml",
                "velero-schedule-platform-cluster-backup.yaml",
            ]
        ),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "backup-policies" / "README.md",
        render_backup_policies_readme(workload_cluster_name=args.workload_cluster_name),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "backup-policies" / "backup-storage-location.yaml",
        render_backup_storage_location(workload_cluster_name=args.workload_cluster_name),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "backup-policies" / "volume-snapshot-location.yaml",
        render_volume_snapshot_location(),
        mode=0o644,
    )
    write_text(
        data_protection_dir / "backup-policies" / "velero-schedule-platform-cluster-backup.yaml",
        render_velero_schedule(data_namespace=args.database_namespace),
        mode=0o644,
    )
    write_text(
        templates_dir / "README.md",
        render_template_readme(
            database_namespace=args.database_namespace,
            database_cluster_name=args.database_cluster_name,
        ),
        mode=0o644,
    )
    write_text(
        templates_dir / "cnpg-objectstore.yaml",
        render_cnpg_objectstore_template(
            database_namespace=args.database_namespace,
            objectstore_name=args.objectstore_name,
        ),
        mode=0o644,
    )
    write_text(
        templates_dir / "cnpg-scheduledbackup-plugin.yaml",
        render_cnpg_scheduledbackup_plugin_template(
            database_namespace=args.database_namespace,
            database_cluster_name=args.database_cluster_name,
        ),
        mode=0o644,
    )
    write_text(
        templates_dir / "cnpg-scheduledbackup-volume-snapshot.yaml",
        render_cnpg_scheduledbackup_snapshot_template(
            database_namespace=args.database_namespace,
            database_cluster_name=args.database_cluster_name,
        ),
        mode=0o644,
    )
    write_text(
        templates_dir / "cnpg-cluster-backup-snippet.yaml",
        render_cnpg_cluster_backup_snippet(
            database_namespace=args.database_namespace,
            database_cluster_name=args.database_cluster_name,
            objectstore_name=args.objectstore_name,
            storage_class=args.storage_class_placeholder,
            snapshot_class=args.volume_snapshot_class_placeholder,
        ),
        mode=0o644,
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the P2.4 data-protection scaffold.")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.add_argument("--workload-cluster-name", default="nonprod-hetzner-hel1-core")
    render_scaffold.add_argument("--cnpg-chart-version", default="0.27.0")
    render_scaffold.add_argument("--barman-plugin-version", default="v0.12.0")
    render_scaffold.add_argument("--velero-chart-version", default="11.3.2")
    render_scaffold.add_argument("--database-namespace", default="platform-data")
    render_scaffold.add_argument("--database-cluster-name", default="platform-core-postgres")
    render_scaffold.add_argument("--objectstore-name", default="platform-core-postgres-store")
    render_scaffold.add_argument("--storage-class-placeholder", default="REPLACE_ME_STORAGE_CLASS")
    render_scaffold.add_argument("--volume-snapshot-class-placeholder", default="REPLACE_ME_VOLUME_SNAPSHOT_CLASS")
    render_scaffold.set_defaults(func=command_render_scaffold)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
