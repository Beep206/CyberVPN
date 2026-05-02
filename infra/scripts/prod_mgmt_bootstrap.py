#!/usr/bin/env python3
"""Render the prod management-cluster bootstrap bundle."""

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


def render_clusterctl_yaml(*, cabpt_version: str, cacppt_version: str) -> str:
    return (
        "providers:\n"
        '  - name: "talos"\n'
        f'    url: "https://github.com/siderolabs/cluster-api-bootstrap-provider-talos/releases/download/{cabpt_version}/bootstrap-components.yaml"\n'
        '    type: "BootstrapProvider"\n'
        '  - name: "talos"\n'
        f'    url: "https://github.com/siderolabs/cluster-api-control-plane-provider-talos/releases/download/{cacppt_version}/control-plane-components.yaml"\n'
        '    type: "ControlPlaneProvider"\n'
    )


def render_install_capi_core(*, kubeconfig_path: str, capi_version: str, cabpt_version: str, cacppt_version: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
export KUBECONFIG="${{KUBECONFIG:-{kubeconfig_path}}}"
export CLUSTERCTL_CONFIG="${{CLUSTERCTL_CONFIG:-$bundle_dir/clusterctl/clusterctl.yaml}}"

clusterctl init \\
  --core cluster-api:{capi_version} \\
  --bootstrap talos:{cabpt_version} \\
  --control-plane talos:{cacppt_version} \\
  --infrastructure "-"

kubectl -n capi-system wait deploy/capi-controller-manager --for=condition=Available=True --timeout=10m
kubectl -n cabpt-system wait deploy/cabpt-controller-manager --for=condition=Available=True --timeout=10m
kubectl -n cacppt-system wait deploy/cacppt-controller-manager --for=condition=Available=True --timeout=10m
kubectl get providers --all-namespaces
"""


def render_install_caph(*, kubeconfig_path: str, caph_branch: str, caph_components_url: str | None) -> str:
    embedded_url = caph_components_url.strip() if caph_components_url else ""
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"
export KUBECONFIG="${{KUBECONFIG:-{kubeconfig_path}}}"

components_url="${{CAPH_COMPONENTS_URL:-{embedded_url}}}"
if [[ -z "$components_url" ]]; then
  cat >&2 <<'EOF'
CAPH_COMPONENTS_URL must point to a validated infrastructure-components.yaml
compatible with CAPI v1.13.x. The default latest stable CAPH release line is not
used automatically here because upstream currently documents v1.0.x as incompatible
with CAPI v1.11+ while the v1.1.x-compatible line is still being validated for this
program. Expected source track: syself/cluster-api-provider-hetzner {caph_branch}.
EOF
  exit 1
fi

kubectl apply -f "$components_url"
kubectl -n caph-system wait deploy/caph-controller-manager --for=condition=Available=True --timeout=10m
kubectl get providers --all-namespaces
"""


def render_readme(
    *,
    cluster_name: str,
    kubeconfig_path: str,
    capi_version: str,
    cabpt_version: str,
    cacppt_version: str,
    caph_branch: str,
) -> str:
    return f"""# {cluster_name} bootstrap bundle

This bundle installs Cluster API components into the already-bootstrapped `{cluster_name}`
management cluster.

The bundle assumes the production stack has already established:

- a provider-native L4 load balancer for the stable Kubernetes API endpoint;
- a three-node-or-greater Talos control plane;
- a production change window for first provider installation.

Files:

- `clusterctl/clusterctl.yaml`: provider overrides for Talos bootstrap and control-plane providers
- `install-capi-core.sh`: installs `cluster-api`, `CABPT`, and `CACPPT`
- `install-caph.sh`: installs the Hetzner infrastructure provider from an explicitly pinned manifest URL
- `versions.env`: records the pinned upstream versions used when the bundle was rendered

Usage:

1. Ensure `KUBECONFIG` points at `{kubeconfig_path}` or export an override.
2. Run `bash install-capi-core.sh`.
3. Export `CAPH_COMPONENTS_URL=<validated infrastructure-components.yaml URL>`.
4. Run `bash install-caph.sh`.

Pinned upstream versions:

- `CAPI`: `{capi_version}`
- `CABPT`: `{cabpt_version}`
- `CACPPT`: `{cacppt_version}`
- `CAPH track`: `{caph_branch}`

Compatibility note:

- Upstream `CAPI v1.13.x` is the current supported core line.
- Upstream CAPH documentation states that `v1.0.x` is not compatible with `CAPI v1.11+`.
- This bundle therefore refuses to auto-install Hetzner through the default `clusterctl` provider repository and requires an explicit operator pin for the validated CAPH manifest.
"""


def render_versions_env(
    *,
    cluster_name: str,
    capi_version: str,
    cabpt_version: str,
    cacppt_version: str,
    caph_branch: str,
) -> str:
    return (
        f"MANAGEMENT_CLUSTER_ID={cluster_name}\n"
        f"CAPI_VERSION={capi_version}\n"
        f"CABPT_VERSION={cabpt_version}\n"
        f"CACPPT_VERSION={cacppt_version}\n"
        f"CAPH_TRACK={caph_branch}\n"
    )


def command_render_bundle(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    write_text(
        output_dir / "clusterctl" / "clusterctl.yaml",
        render_clusterctl_yaml(cabpt_version=args.cabpt_version, cacppt_version=args.cacppt_version),
    )
    write_text(
        output_dir / "install-capi-core.sh",
        render_install_capi_core(
            kubeconfig_path=args.kubeconfig_path,
            capi_version=args.capi_version,
            cabpt_version=args.cabpt_version,
            cacppt_version=args.cacppt_version,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "install-caph.sh",
        render_install_caph(
            kubeconfig_path=args.kubeconfig_path,
            caph_branch=args.caph_branch,
            caph_components_url=args.caph_components_url,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "versions.env",
        render_versions_env(
            cluster_name=args.cluster_name,
            capi_version=args.capi_version,
            cabpt_version=args.cabpt_version,
            cacppt_version=args.cacppt_version,
            caph_branch=args.caph_branch,
        ),
    )
    write_text(
        output_dir / "README.md",
        render_readme(
            cluster_name=args.cluster_name,
            kubeconfig_path=args.kubeconfig_path,
            capi_version=args.capi_version,
            cabpt_version=args.cabpt_version,
            cacppt_version=args.cacppt_version,
            caph_branch=args.caph_branch,
        ),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_bundle = subparsers.add_parser("render-bundle", help="Render the management-cluster bootstrap bundle.")
    render_bundle.add_argument("--cluster-name", default="prod-mgmt")
    render_bundle.add_argument("--kubeconfig-path", required=True)
    render_bundle.add_argument("--output-dir", required=True)
    render_bundle.add_argument("--capi-version", default="v1.13.0")
    render_bundle.add_argument("--cabpt-version", default="v0.6.11")
    render_bundle.add_argument("--cacppt-version", default="v0.5.12")
    render_bundle.add_argument("--caph-branch", default="v1.1.x")
    render_bundle.add_argument("--caph-components-url", default=None)
    render_bundle.set_defaults(func=command_render_bundle)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
