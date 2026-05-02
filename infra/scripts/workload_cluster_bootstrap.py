#!/usr/bin/env python3
"""Render the non-prod workload-cluster bootstrap scaffold for P2.1."""

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


def render_root_readme(*, workload_cluster_name: str, management_cluster_name: str) -> str:
    return f"""# P2.1 workload-cluster scaffold

This scaffold freezes the first non-prod workload-cluster baseline for CyberVPN.

Cluster ids:

- management cluster: `{management_cluster_name}`
- workload cluster: `{workload_cluster_name}`

What this scaffold covers:

- the management-cluster-side contract for generating and reviewing the workload-cluster manifest through Cluster API;
- the cluster-local reserved paths for future Flux-managed workloads;
- the initial network baseline intent for:
  - `Cilium`
  - `Gateway API`
  - `cert-manager`
  - `trust-manager`
  - Cloudflare public edge plus provider-native `LoadBalancer`

Important boundaries:

- this scaffold does not claim a live workload cluster already exists;
- it does not bypass the `platform-gitops` boundary frozen in `P1.6`;
- it does not install platform services yet; that remains the follow-up `P2.2` packet;
- it keeps `ClusterClass` and `MachinePool` out of scope for day-1, following the frozen architecture baseline.
"""


def render_management_cluster_readme(*, workload_cluster_name: str, management_cluster_name: str) -> str:
    return f"""# {management_cluster_name} workload-cluster contract

This path contains the management-cluster-side contract for the `{workload_cluster_name}` workload cluster.

Rules:

- these files are reconciled onto `{management_cluster_name}`, not onto the workload cluster itself;
- the actual provider template URL must be operator-validated before manifest generation;
- generated cluster manifests are artifacts, not the long-term source of truth, until a real GitOps path and live provider validation exist;
- `MachineDeployment` is the default worker model;
- `ClusterClass` and `MachinePool` stay out of this baseline.
"""


def render_cluster_inputs_env(
    *,
    workload_cluster_name: str,
    kubernetes_version: str,
    region: str,
    control_plane_replicas: int,
    worker_replicas: int,
    control_plane_machine_type: str,
    worker_machine_type: str,
    talos_version: str,
) -> str:
    return (
        f"WORKLOAD_CLUSTER_ID={workload_cluster_name}\n"
        f"KUBERNETES_VERSION={kubernetes_version}\n"
        f"HCLOUD_REGION={region}\n"
        f"CONTROL_PLANE_MACHINE_COUNT={control_plane_replicas}\n"
        f"WORKER_MACHINE_COUNT={worker_replicas}\n"
        f"HCLOUD_CONTROL_PLANE_MACHINE_TYPE={control_plane_machine_type}\n"
        f"HCLOUD_WORKER_MACHINE_TYPE={worker_machine_type}\n"
        f"TALOS_VERSION={talos_version}\n"
        "HCLOUD_SSH_KEY_NAME=REQUIRED\n"
        "HCLOUD_NETWORK_NAME=REQUIRED\n"
        "HCLOUD_CONTROL_PLANE_LOAD_BALANCER_NAME=REQUIRED\n"
        "CAPH_TEMPLATE_URL=REQUIRED\n"
    )


def render_generate_cluster_script(*, workload_cluster_name: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
source "$bundle_dir/workload-cluster-inputs.env"

: "${{CAPH_TEMPLATE_URL:?CAPH_TEMPLATE_URL must point to an operator-validated CAPH workload-cluster template}}"

output_dir="${{OUTPUT_DIR:-$bundle_dir/generated}}"
mkdir -p "$output_dir"

clusterctl generate cluster "${{WORKLOAD_CLUSTER_ID:-{workload_cluster_name}}}" \\
  --kubernetes-version "${{KUBERNETES_VERSION}}" \\
  --control-plane-machine-count "${{CONTROL_PLANE_MACHINE_COUNT}}" \\
  --worker-machine-count "${{WORKER_MACHINE_COUNT}}" \\
  --from "${{CAPH_TEMPLATE_URL}}" \\
  > "$output_dir/${{WORKLOAD_CLUSTER_ID}}.yaml"

echo "Generated workload-cluster manifest at $output_dir/${{WORKLOAD_CLUSTER_ID}}.yaml"
"""


def render_workload_cluster_readme(*, workload_cluster_name: str) -> str:
    return f"""# {workload_cluster_name}

This directory is reserved for the workload-cluster-local GitOps entrypoint once the cluster exists.

During `P2.1` this path is intentionally light:

- it freezes the workload cluster id and reserved repo surface;
- it avoids pretending that cluster-local reconciliation already exists;
- it keeps real platform add-ons and workloads for `P2.2+`.
"""


def render_apps_readme(*, workload_cluster_name: str) -> str:
    return f"""# apps/{workload_cluster_name}

Reserved for first-party workloads targeting `{workload_cluster_name}`.

No application manifests should land here before:

- the workload cluster exists;
- Flux is attached to the cluster;
- the `P2.2` base platform services are in place.
"""


def render_network_readme(*, workload_cluster_name: str, gateway_class_name: str) -> str:
    return f"""# {workload_cluster_name} network baseline

This path freezes the day-1 network substrate intent for `{workload_cluster_name}`.

Baseline decisions:

- public web and control-plane HTTP(S) traffic stays behind `Cloudflare`;
- the cluster exposes its gateway entrypoint through a provider-native `LoadBalancer`;
- in-cluster ingress is `Cilium Gateway API`;
- certificate automation is `cert-manager`;
- trust distribution is `trust-manager`;
- `Cilium` `L2 announcements` and `BGP` are fallback paths only, not the default entry design.

Gateway class:

- `{gateway_class_name}`

This directory currently contains only baseline values and intent files. Real `HelmRelease`,
`GatewayClass`, `Gateway`, and issuer objects belong to later packets once the cluster exists.
"""


def render_edge_baseline_env(*, gateway_class_name: str) -> str:
    return (
        "PUBLIC_EDGE_PROVIDER=cloudflare\n"
        "ORIGIN_EXPOSURE=provider-loadbalancer\n"
        "LOADBALANCER_STRATEGY=provider-native-l4\n"
        f"GATEWAY_CLASS_NAME={gateway_class_name}\n"
        "VPN_DATA_PLANE_ON_CLOUDFLARE=false\n"
        "CILIUM_FALLBACK_L2_OR_BGP=non-default\n"
    )


def render_cilium_values() -> str:
    return """# P2.1 network baseline values for Cilium
# Source basis:
# - Gateway API support enabled through gatewayAPI.enabled=true
# - kube-proxy replacement required for the frozen day-1 network posture
gatewayAPI:
  enabled: true
kubeProxyReplacement: true
"""


def render_cert_manager_values() -> str:
    return """# P2.1 network baseline values for cert-manager
# Source basis:
# - install cert-manager exactly once per cluster
# - use the OCI chart and install CRDs explicitly
crds:
  enabled: true
"""


def render_trust_manager_values() -> str:
    return """# P2.1 network baseline values for trust-manager
# Source basis:
# - install after cert-manager
# - keep Secret targets disabled until explicit authorization design exists
{}
"""


def render_versions_env(
    *,
    management_cluster_name: str,
    workload_cluster_name: str,
    gateway_class_name: str,
    kubernetes_version: str,
    region: str,
    control_plane_replicas: int,
    worker_replicas: int,
    talos_version: str,
) -> str:
    return (
        f"MANAGEMENT_CLUSTER_ID={management_cluster_name}\n"
        f"WORKLOAD_CLUSTER_ID={workload_cluster_name}\n"
        f"KUBERNETES_VERSION={kubernetes_version}\n"
        f"REGION={region}\n"
        f"CONTROL_PLANE_MACHINE_COUNT={control_plane_replicas}\n"
        f"WORKER_MACHINE_COUNT={worker_replicas}\n"
        f"TALOS_VERSION={talos_version}\n"
        f"GATEWAY_CLASS_NAME={gateway_class_name}\n"
        "NETWORK_BASELINE=CLOUDFLARE_PROVIDER_L4_CILIUM_GATEWAY_API\n"
    )


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)

    management_dir = output_dir / "infrastructure" / args.management_cluster_name / "workload-clusters" / args.workload_cluster_name
    cluster_dir = output_dir / "clusters" / args.workload_cluster_name
    infrastructure_dir = output_dir / "infrastructure" / args.workload_cluster_name / "network"
    apps_dir = output_dir / "apps" / args.workload_cluster_name

    write_text(
        output_dir / "README.md",
        render_root_readme(
            workload_cluster_name=args.workload_cluster_name,
            management_cluster_name=args.management_cluster_name,
        ),
        mode=0o644,
    )
    write_text(
        management_dir / "README.md",
        render_management_cluster_readme(
            workload_cluster_name=args.workload_cluster_name,
            management_cluster_name=args.management_cluster_name,
        ),
        mode=0o644,
    )
    write_text(
        management_dir / "workload-cluster-inputs.env",
        render_cluster_inputs_env(
            workload_cluster_name=args.workload_cluster_name,
            kubernetes_version=args.kubernetes_version,
            region=args.region,
            control_plane_replicas=args.control_plane_replicas,
            worker_replicas=args.worker_replicas,
            control_plane_machine_type=args.control_plane_machine_type,
            worker_machine_type=args.worker_machine_type,
            talos_version=args.talos_version,
        ),
        mode=0o640,
    )
    write_text(
        management_dir / "render-workload-cluster.sh",
        render_generate_cluster_script(workload_cluster_name=args.workload_cluster_name),
        mode=0o750,
    )
    write_text(cluster_dir / "README.md", render_workload_cluster_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(apps_dir / "README.md", render_apps_readme(workload_cluster_name=args.workload_cluster_name), mode=0o644)
    write_text(
        infrastructure_dir / "README.md",
        render_network_readme(
            workload_cluster_name=args.workload_cluster_name,
            gateway_class_name=args.gateway_class_name,
        ),
        mode=0o644,
    )
    write_text(infrastructure_dir / "edge-baseline.env", render_edge_baseline_env(gateway_class_name=args.gateway_class_name), mode=0o644)
    write_text(infrastructure_dir / "cilium-values.yaml", render_cilium_values(), mode=0o644)
    write_text(infrastructure_dir / "cert-manager-values.yaml", render_cert_manager_values(), mode=0o644)
    write_text(infrastructure_dir / "trust-manager-values.yaml", render_trust_manager_values(), mode=0o644)
    write_text(
        output_dir / "versions.env",
        render_versions_env(
            management_cluster_name=args.management_cluster_name,
            workload_cluster_name=args.workload_cluster_name,
            gateway_class_name=args.gateway_class_name,
            kubernetes_version=args.kubernetes_version,
            region=args.region,
            control_plane_replicas=args.control_plane_replicas,
            worker_replicas=args.worker_replicas,
            talos_version=args.talos_version,
        ),
        mode=0o644,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the P2.1 workload-cluster scaffold.")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.add_argument("--management-cluster-name", default="nonprod-mgmt")
    render_scaffold.add_argument("--workload-cluster-name", default="nonprod-hetzner-hel1-core")
    render_scaffold.add_argument("--region", default="hel1")
    render_scaffold.add_argument("--kubernetes-version", default="v1.35.0")
    render_scaffold.add_argument("--talos-version", default="v1.11.4")
    render_scaffold.add_argument("--control-plane-replicas", type=int, default=3)
    render_scaffold.add_argument("--worker-replicas", type=int, default=2)
    render_scaffold.add_argument("--control-plane-machine-type", default="cpx31")
    render_scaffold.add_argument("--worker-machine-type", default="cpx21")
    render_scaffold.add_argument("--gateway-class-name", default="cilium")
    render_scaffold.set_defaults(func=command_render_scaffold)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
