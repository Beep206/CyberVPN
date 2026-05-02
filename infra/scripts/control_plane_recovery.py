#!/usr/bin/env python3
"""Render the non-prod control-plane backup and recovery bundle."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_mapping(path: Path) -> dict[str, dict[str, object]]:
    payload = load_json_file(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must be a JSON object keyed by node name")
    normalized: dict[str, dict[str, object]] = {}
    for name, item in sorted(payload.items()):
        if not isinstance(item, dict):
            raise SystemExit(f"entry {name!r} in {path} must be an object")
        normalized[str(name)] = item
    return normalized


def load_endpoints(path: Path) -> list[str]:
    payload = load_json_file(path)
    if isinstance(payload, dict):
        endpoints = payload.get("endpoints")
        if not isinstance(endpoints, list):
            raise SystemExit("management endpoints file must contain an endpoints array")
        values = [str(item).strip() for item in endpoints if str(item).strip()]
    elif isinstance(payload, list):
        values = [str(item).strip() for item in payload if str(item).strip()]
    else:
        raise SystemExit("management endpoints file must be either an array or an object with an endpoints array")
    if not values:
        raise SystemExit("management endpoints file must define at least one endpoint")
    return values


def derive_openbao_addr(nodes: dict[str, dict[str, object]]) -> str:
    name = next(iter(nodes))
    entry = nodes[name]
    api_addr = str(entry.get("api_addr", "")).strip()
    if api_addr:
        return api_addr
    ipv4 = str(entry.get("ipv4_address", "")).strip()
    if not ipv4:
        raise SystemExit(f"openbao entry {name!r} must define api_addr or ipv4_address")
    return f"https://{ipv4}:8200"


def derive_nats_url(nodes: dict[str, dict[str, object]]) -> str:
    name = next(iter(nodes))
    entry = nodes[name]
    client_addr = str(entry.get("client_addr", "")).strip()
    if client_addr:
        if client_addr.startswith("tls://") or client_addr.startswith("nats://"):
            return client_addr
        return f"tls://{client_addr}"
    ipv4 = str(entry.get("ipv4_address", "")).strip()
    port = int(entry.get("client_port", 4222))
    if not ipv4:
        raise SystemExit(f"nats entry {name!r} must define client_addr or ipv4_address")
    return f"tls://{ipv4}:{port}"


def derive_posthog_host(nodes: dict[str, dict[str, object]]) -> str:
    name = next(iter(nodes))
    entry = nodes[name]
    domain_name = str(entry.get("domain_name", "")).strip()
    if domain_name:
        return domain_name
    ipv4 = str(entry.get("ipv4_address", "")).strip()
    if not ipv4:
        raise SystemExit(f"posthog entry {name!r} must define domain_name or ipv4_address")
    return ipv4


def render_sync_to_s3() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

source_dir="${1:?source directory is required}"
component_prefix="${2:?component prefix is required}"

if [[ -z "${S3_URI:-}" ]]; then
  echo "S3_URI is not set; skipping object-store upload."
  exit 0
fi

aws_args=(s3 cp --recursive --only-show-errors "$source_dir" "${S3_URI%/}/${component_prefix#/}/")
if [[ -n "${AWS_S3_SSE:-}" ]]; then
  aws_args+=(--sse "$AWS_S3_SSE")
fi
if [[ -n "${AWS_S3_SSE_KMS_KEY_ID:-}" ]]; then
  aws_args+=(--sse-kms-key-id "$AWS_S3_SSE_KMS_KEY_ID")
fi

aws "${aws_args[@]}"
"""


def render_openbao_backup_script(*, cluster_id: str, default_addr: str, artifact_root: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${{ARTIFACT_ROOT:-{artifact_root}}}"
target_dir="$artifact_root/openbao/$timestamp"

mkdir -p "$target_dir"

export VAULT_ADDR="${{VAULT_ADDR:-{default_addr}}}"
export VAULT_CLIENT_TIMEOUT="${{VAULT_CLIENT_TIMEOUT:-10m}}"
if [[ -n "${{OPENBAO_CA_CERT:-}}" ]]; then
  export VAULT_CACERT="$OPENBAO_CA_CERT"
fi

"${{BAO_BIN:-bao}}" operator raft snapshot save "$target_dir/{cluster_id}.snap"
"${{BAO_BIN:-bao}}" operator raft list-peers -format=json > "$target_dir/raft-peers.json"

if [[ -n "${{OPENBAO_SSH_TARGET:-}}" ]]; then
  ssh "${{OPENBAO_SSH_TARGET}}" 'sudo tar -czf - /etc/openbao /etc/systemd/system/openbao.service' > "$target_dir/openbao-config.tgz"
fi

cat > "$target_dir/metadata.json" <<EOF
{{
  "component": "openbao",
  "cluster_id": "{cluster_id}",
  "captured_at": "$timestamp",
  "vault_addr": "$VAULT_ADDR"
}}
EOF

"$bundle_dir/../common/sync-to-s3.sh" "$target_dir" "openbao/$timestamp"
echo "OpenBao snapshot saved under $target_dir"
"""


def render_openbao_restore_notes(cluster_id: str) -> str:
    return f"""# OpenBao restore notes for {cluster_id}

1. Ensure the failed cluster cannot be recovered through normal Raft quorum repair.
2. Select the snapshot file captured with `bao operator raft snapshot save`.
3. Set `VAULT_CLIENT_TIMEOUT` high enough for large snapshot operations.
4. Restore with:

```bash
bao operator raft snapshot restore <snapshot_file>
```

5. If restoring through the API instead of the CLI, the equivalent endpoint is:

```text
POST /v1/sys/storage/raft/snapshot
```

6. After restore, rejoin or rebuild additional nodes from clean data directories and verify `bao operator raft list-peers`.

Source basis:

- OpenBao `operator raft snapshot save`
- OpenBao `operator raft snapshot restore`
- OpenBao `/sys/storage/raft/snapshot`
"""


def render_nats_backup_script(*, cluster_id: str, default_url: str, artifact_root: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${{ARTIFACT_ROOT:-{artifact_root}}}"
target_dir="$artifact_root/nats/$timestamp"
backup_dir="$target_dir/account-backup"

mkdir -p "$backup_dir"

nats_args=()
if [[ -n "${{NATS_CONTEXT:-}}" ]]; then
  nats_args+=(--context "$NATS_CONTEXT")
fi
if [[ -n "${{NATS_CREDS_FILE:-}}" ]]; then
  nats_args+=(--creds "$NATS_CREDS_FILE")
fi
if [[ -n "${{NATS_NKEY_FILE:-}}" ]]; then
  nats_args+=(--nkey "$NATS_NKEY_FILE")
fi
nats_args+=(--server "${{NATS_URL:-{default_url}}}")

"${{NATS_BIN:-nats}}" "${{nats_args[@]}}" account backup --consumers --check --force "$backup_dir"

cat > "$target_dir/metadata.json" <<EOF
{{
  "component": "nats",
  "cluster_id": "{cluster_id}",
  "captured_at": "$timestamp",
  "server": "${{NATS_URL:-{default_url}}}"
}}
EOF

"$bundle_dir/../common/sync-to-s3.sh" "$target_dir" "nats/$timestamp"
echo "NATS account backup saved under $target_dir"
"""


def render_nats_restore_notes(cluster_id: str) -> str:
    return f"""# NATS restore notes for {cluster_id}

1. Prefer automatic JetStream recovery from intact quorum nodes when quorum still exists.
2. Use manual restore only when snapshot-based recovery is required.
3. Restore all streams in the backed-up account with:

```bash
nats account restore <backup_directory>
```

4. `nats account restore` fails if a stream with the same name already exists; remove or rename the existing stream first.
5. The backup path in this packet assumes file-backed JetStream streams. Memory-storage streams cannot be snapshotted with `nats account backup`.

Source basis:

- NATS JetStream disaster recovery
- `nats account backup`
- `nats account restore`
"""


def render_posthog_backup_script(*, instance_id: str, default_host: str, artifact_root: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${{ARTIFACT_ROOT:-{artifact_root}}}"
target_dir="$artifact_root/posthog/$timestamp"
remote_host="${{POSTHOG_SSH_TARGET:?set POSTHOG_SSH_TARGET, for example ops@{default_host}}}"
ssh_opts=()
if [[ -n "${{POSTHOG_SSH_KEY:-}}" ]]; then
  ssh_opts+=(-i "$POSTHOG_SSH_KEY")
fi

mkdir -p "$target_dir"

remote_backup_dir="$(ssh "${{ssh_opts[@]}}" "$remote_host" 'sudo /usr/local/sbin/posthog-local-backup.sh >/dev/null && sudo ls -1dt /var/backups/posthog/* | head -n1')"
ssh "${{ssh_opts[@]}}" "$remote_host" "sudo tar -czf - -C \"$remote_backup_dir\" ." > "$target_dir/posthog-backup.tgz"
ssh "${{ssh_opts[@]}}" "$remote_host" 'sudo tar -czf - /opt/posthog/self-host/.env /opt/posthog/self-host/docker-compose.yml /opt/posthog/self-host/docker-compose.override.yml /etc/nginx/sites-available/posthog.conf' > "$target_dir/posthog-config.tgz"

cat > "$target_dir/metadata.json" <<EOF
{{
  "component": "posthog",
  "instance_id": "{instance_id}",
  "captured_at": "$timestamp",
  "remote_host": "$remote_host",
  "remote_backup_dir": "$remote_backup_dir"
}}
EOF

"$bundle_dir/../common/sync-to-s3.sh" "$target_dir" "posthog/$timestamp"
echo "PostHog backup retrieved under $target_dir"
"""


def render_posthog_restore_notes(instance_id: str) -> str:
    return f"""# PostHog restore notes for {instance_id}

1. This packet treats the non-prod PostHog host as a dedicated external VM with a Docker self-host stack.
2. The baseline backup flow for `P1.8` is:
   - trigger the host-local `posthog-local-backup.sh`
   - retrieve the newest backup artifact over SSH
   - retrieve `.env`, compose files, and `NGINX` config as the configuration baseline
3. Restore must be performed on an isolated host or after explicit service downtime approval.
4. The restore sequence is:
   - recover the configuration files
   - recover the captured PostHog backup artifact set
   - bring the Docker stack back in the documented order for the chosen self-host reference
   - verify login, ingest, and protected UI access through the reverse proxy

Source basis:

- PostHog self-host placement remains outside Kubernetes
- the repo-local `posthog-local-backup.sh` is the canonical baseline backup producer for non-prod
"""


def render_talos_etcd_backup_script(*, cluster_id: str, default_endpoint: str, artifact_root: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${{ARTIFACT_ROOT:-{artifact_root}}}"
target_dir="$artifact_root/nonprod-mgmt/$timestamp"
endpoint="${{TALOS_SNAPSHOT_NODE:-{default_endpoint}}}"

mkdir -p "$target_dir"

"${{TALOSCTL_BIN:-talosctl}}" --talosconfig "${{TALOSCONFIG:?set TALOSCONFIG}}" -n "$endpoint" etcd snapshot "$target_dir/etcd.snapshot"
"${{TALOSCTL_BIN:-talosctl}}" --talosconfig "${{TALOSCONFIG:?set TALOSCONFIG}}" -n "$endpoint" etcd status > "$target_dir/etcd-status.txt"

cat > "$target_dir/metadata.json" <<EOF
{{
  "component": "talos-etcd",
  "cluster_id": "{cluster_id}",
  "captured_at": "$timestamp",
  "snapshot_node": "$endpoint"
}}
EOF

"$bundle_dir/../common/sync-to-s3.sh" "$target_dir" "nonprod-mgmt/$timestamp"
echo "Talos etcd snapshot saved under $target_dir"
"""


def render_talos_machine_config_backup_script(*, endpoints: list[str], artifact_root: str) -> str:
    endpoint_lines = "\n".join(f'endpoints+=("{endpoint}")' for endpoint in endpoints)
    return f"""#!/usr/bin/env bash
set -euo pipefail

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact_root="${{ARTIFACT_ROOT:-{artifact_root}}}"
target_dir="$artifact_root/nonprod-mgmt/$timestamp/machineconfig"

mkdir -p "$target_dir"

endpoints=()
{endpoint_lines}
if [[ -n "${{TALOS_ENDPOINTS:-}}" ]]; then
  IFS=',' read -r -a endpoints <<<"${{TALOS_ENDPOINTS}}"
fi

for endpoint in "${{endpoints[@]}}"; do
  "${{TALOSCTL_BIN:-talosctl}}" --talosconfig "${{TALOSCONFIG:?set TALOSCONFIG}}" -n "$endpoint" get mc v1alpha1 -o yaml > "$target_dir/$endpoint.machineconfig.yaml"
done

echo "Talos machine configs saved under $target_dir"
"""


def render_talos_restore_notes(cluster_id: str) -> str:
    return f"""# Talos restore notes for {cluster_id}

1. Before disaster recovery, check whether quorum can be restored normally:

```bash
talosctl -n <control-plane-ip> etcd members
talosctl -n <control-plane-ip> service etcd
```

2. If full recovery is required, bootstrap from a known-good snapshot:

```bash
talosctl --talosconfig <talosconfig> -n <bootstrap-node> bootstrap --recover-from=./etcd.snapshot
```

3. If the snapshot was copied directly from the data directory instead of created with `talosctl etcd snapshot`, use `--recover-skip-hash-check`.
4. After recovery, verify Talos and Kubernetes health, then allow the remaining control-plane nodes to rejoin.

Source basis:

- Talos disaster recovery
- `talosctl etcd snapshot`
- `talosctl bootstrap --recover-from`
"""


def render_readme(
    *,
    environment: str,
    openbao_cluster_id: str,
    nats_cluster_id: str,
    posthog_instance_id: str,
    management_cluster_id: str,
) -> str:
    return f"""# {environment} control-plane backup and recovery bundle

This bundle establishes the `P1.8` baseline backup and restore posture for the non-prod control planes:

- `{openbao_cluster_id}`
- `{nats_cluster_id}`
- `{posthog_instance_id}`
- `{management_cluster_id}` `etcd` metadata

What it renders:

- operator-facing backup scripts under:
  - `openbao/`
  - `nats/`
  - `posthog/`
  - `nonprod-mgmt/`
- component-specific restore notes
- an optional common `S3` sync helper
- version and scope metadata

Required operator tools:

- `bao`
- `nats`
- `talosctl`
- `ssh`
- `aws` CLI if object-store sync is enabled

Important boundaries:

- this packet does not claim live closure by itself; it only freezes the bundle and restore contract
- `PostHog` backup remains a dedicated product-intelligence path and is not merged into platform observability
- `VPN` and edge fleet DR stays reprovision-first and is intentionally outside this bundle
"""


def render_versions_env(
    *,
    environment: str,
    openbao_cluster_id: str,
    nats_cluster_id: str,
    posthog_instance_id: str,
    management_cluster_id: str,
) -> str:
    return (
        f"ENVIRONMENT={environment}\n"
        f"OPENBAO_CLUSTER_ID={openbao_cluster_id}\n"
        f"NATS_CLUSTER_ID={nats_cluster_id}\n"
        f"POSTHOG_INSTANCE_ID={posthog_instance_id}\n"
        f"MANAGEMENT_CLUSTER_ID={management_cluster_id}\n"
    )


def command_render_bundle(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)

    openbao_nodes = load_mapping(Path(args.openbao_nodes_file))
    nats_nodes = load_mapping(Path(args.nats_nodes_file))
    posthog_nodes = load_mapping(Path(args.posthog_nodes_file))
    talos_endpoints = load_endpoints(Path(args.talos_endpoints_file))

    artifact_root = args.artifact_root.rstrip("/")

    write_text(output_dir / "common" / "sync-to-s3.sh", render_sync_to_s3(), mode=0o750)
    write_text(
        output_dir / "openbao" / "snapshot-openbao.sh",
        render_openbao_backup_script(
            cluster_id=args.openbao_cluster_id,
            default_addr=derive_openbao_addr(openbao_nodes),
            artifact_root=artifact_root,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "openbao" / "restore-openbao.md",
        render_openbao_restore_notes(args.openbao_cluster_id),
        mode=0o644,
    )
    write_text(
        output_dir / "nats" / "backup-nats-account.sh",
        render_nats_backup_script(
            cluster_id=args.nats_cluster_id,
            default_url=derive_nats_url(nats_nodes),
            artifact_root=artifact_root,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "nats" / "restore-nats.md",
        render_nats_restore_notes(args.nats_cluster_id),
        mode=0o644,
    )
    write_text(
        output_dir / "posthog" / "backup-posthog-over-ssh.sh",
        render_posthog_backup_script(
            instance_id=args.posthog_instance_id,
            default_host=derive_posthog_host(posthog_nodes),
            artifact_root=artifact_root,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "posthog" / "restore-posthog.md",
        render_posthog_restore_notes(args.posthog_instance_id),
        mode=0o644,
    )
    write_text(
        output_dir / "nonprod-mgmt" / "backup-etcd.sh",
        render_talos_etcd_backup_script(
            cluster_id=args.management_cluster_id,
            default_endpoint=talos_endpoints[0],
            artifact_root=artifact_root,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "nonprod-mgmt" / "backup-machine-configs.sh",
        render_talos_machine_config_backup_script(endpoints=talos_endpoints, artifact_root=artifact_root),
        mode=0o750,
    )
    write_text(
        output_dir / "nonprod-mgmt" / "restore-nonprod-mgmt.md",
        render_talos_restore_notes(args.management_cluster_id),
        mode=0o644,
    )
    write_text(
        output_dir / "README.md",
        render_readme(
            environment=args.environment,
            openbao_cluster_id=args.openbao_cluster_id,
            nats_cluster_id=args.nats_cluster_id,
            posthog_instance_id=args.posthog_instance_id,
            management_cluster_id=args.management_cluster_id,
        ),
        mode=0o644,
    )
    write_text(
        output_dir / "versions.env",
        render_versions_env(
            environment=args.environment,
            openbao_cluster_id=args.openbao_cluster_id,
            nats_cluster_id=args.nats_cluster_id,
            posthog_instance_id=args.posthog_instance_id,
            management_cluster_id=args.management_cluster_id,
        ),
        mode=0o644,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_bundle = subparsers.add_parser("render-bundle", help="Render the non-prod control-plane backup and recovery bundle.")
    render_bundle.add_argument("--output-dir", required=True)
    render_bundle.add_argument("--openbao-nodes-file", required=True)
    render_bundle.add_argument("--nats-nodes-file", required=True)
    render_bundle.add_argument("--posthog-nodes-file", required=True)
    render_bundle.add_argument("--talos-endpoints-file", required=True)
    render_bundle.add_argument("--environment", default="nonprod")
    render_bundle.add_argument("--artifact-root", default="/var/backups/cybervpn-platform/nonprod")
    render_bundle.add_argument("--openbao-cluster-id", default="openbao-nonprod")
    render_bundle.add_argument("--nats-cluster-id", default="nats-nonprod")
    render_bundle.add_argument("--posthog-instance-id", default="posthog-nonprod")
    render_bundle.add_argument("--management-cluster-id", default="nonprod-mgmt")
    render_bundle.set_defaults(func=command_render_bundle)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
