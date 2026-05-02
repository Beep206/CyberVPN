#!/usr/bin/env python3
"""Render the platform-gitops repository scaffold and Flux bootstrap helper."""

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


def render_readme(*, repository_name: str, cluster_name: str, flux_version: str) -> str:
    cluster_path = f"clusters/{cluster_name}"
    return f"""# {repository_name}

This repository is the canonical desired-state source for CyberVPN Kubernetes delivery.

Frozen baseline:

- repository name: `{repository_name}`
- bootstrap cluster: `{cluster_name}`
- bootstrap path: `{cluster_path}`
- GitOps engine: `Flux`
- bootstrap transport: `flux bootstrap github --token-auth=false`
- pinned Flux version for the initial bootstrap helper: `{flux_version}`

Source-of-truth boundary:

- this repository is the desired-state source for Kubernetes cluster configuration;
- Flux is the reconciler, not the source of truth;
- application source code, OCI images, and infrastructure code remain outside this repository;
- secret **values** are never committed here.

Repository layout:

- `clusters/<cluster>` contains the cluster-specific Flux entrypoint and cluster-local overlays;
- `infrastructure/<cluster>` is reserved for cluster add-ons, controllers, CRDs, and platform-level services;
- `apps/<cluster>` is reserved for first-party and delegated workload delivery.

Bootstrap stance:

- the initial bootstrap path uses GitHub with SSH deploy-key auth, not PAT-in-cluster auth;
- per the official Flux docs, `--token-auth=false` generates a SSH key and uses the GitHub token only at bootstrap time to configure the deploy key;
- since image automation is not in scope for `P1.6`, the deploy key should remain read-only.

Out of scope for this baseline:

- HelmRelease or Kustomization delivery for real platform services;
- workload onboarding;
- secret values in Git;
- production cluster bootstrap.
"""


def render_gitignore() -> str:
    return """# local secrets and credentials
*.pem
*.key
*.pub
*.agekey
*.gpg
*.kubeconfig
*.talosconfig

# editor and OS noise
.DS_Store
Thumbs.db
*.swp
*.swo

# transient output
artifacts/
tmp/
"""


def render_cluster_readme(*, cluster_name: str) -> str:
    return f"""# {cluster_name}

This directory is the cluster-specific entrypoint for the `{cluster_name}` management cluster.

Rules:

- `flux-system/` is created and updated by Flux bootstrap and later Flux upgrades;
- future cluster-local Kustomization and GitRepository objects should be added here only after `P2.2`;
- this directory must not contain secret values;
- manual cluster mutation with `kubectl apply` is not a source-of-truth replacement for files under this path.
"""


def render_segment_readme(*, segment: str, cluster_name: str) -> str:
    if segment == "infrastructure":
        purpose = "cluster add-ons, platform controllers, CRDs, and other cluster-scoped services"
    else:
        purpose = "first-party platform workloads and delegated application delivery"

    return f"""# {segment}/{cluster_name}

Reserved for `{cluster_name}` {purpose}.

This path is intentionally scaffolded before real manifests land so the repository structure
is frozen during `P1.6` without pretending that delivery resources already exist.

When resources are introduced:

- use stable Flux APIs only;
- keep secret values out of Git;
- prefer explicit `kustomization.yaml` files checked into Git;
- keep infrastructure and apps separated so reconciliation order stays auditable.
"""


def render_bootstrap_script(*, repository_name: str, cluster_name: str, flux_version: str) -> str:
    cluster_path = f"clusters/{cluster_name}"
    return f"""#!/usr/bin/env bash
set -euo pipefail

: "${{GITHUB_TOKEN:?GITHUB_TOKEN must be exported with repo admin access for bootstrap}}"
: "${{GITHUB_OWNER:?GITHUB_OWNER must be set to the GitHub org or user owning the repo}}"

REPOSITORY="${{GITHUB_REPOSITORY:-{repository_name}}}"
BRANCH="${{GITOPS_BRANCH:-main}}"
FLUX_VERSION="${{FLUX_VERSION:-{flux_version}}}"
CLUSTER_PATH="${{CLUSTER_PATH:-{cluster_path}}}"
GITHUB_HOSTNAME="${{GITHUB_HOSTNAME:-github.com}}"

bootstrap_args=(
  github
  --token-auth=false
  --owner="$GITHUB_OWNER"
  --repository="$REPOSITORY"
  --branch="$BRANCH"
  --path="$CLUSTER_PATH"
  --version="$FLUX_VERSION"
)

if [[ "$GITHUB_HOSTNAME" != "github.com" ]]; then
  bootstrap_args+=(
    --hostname="$GITHUB_HOSTNAME"
    --ssh-hostname="$GITHUB_HOSTNAME"
  )
fi

flux bootstrap "${{bootstrap_args[@]}}"
"""


def render_check_script(*, cluster_name: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

flux check
flux get sources git -A
flux get kustomizations -A
kubectl get ns flux-system
kubectl -n flux-system get deploy
kubectl get gitrepositories.source.toolkit.fluxcd.io -A

echo "Flux bootstrap checks completed for {cluster_name}."
"""


def render_versions_env(*, repository_name: str, cluster_name: str, flux_version: str) -> str:
    return (
        f"GITOPS_REPOSITORY_NAME={repository_name}\n"
        f"BOOTSTRAP_CLUSTER_NAME={cluster_name}\n"
        f"BOOTSTRAP_CLUSTER_PATH=clusters/{cluster_name}\n"
        f"FLUX_VERSION={flux_version}\n"
        "FLUX_BOOTSTRAP_MODE=github-ssh-deploy-key\n"
    )


def command_render_repo(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    write_text(
        output_dir / "README.md",
        render_readme(
            repository_name=args.repository_name,
            cluster_name=args.cluster_name,
            flux_version=args.flux_version,
        ),
    )
    write_text(output_dir / ".gitignore", render_gitignore())
    write_text(output_dir / "clusters" / args.cluster_name / "README.md", render_cluster_readme(cluster_name=args.cluster_name))
    write_text(
        output_dir / "infrastructure" / args.cluster_name / "README.md",
        render_segment_readme(segment="infrastructure", cluster_name=args.cluster_name),
    )
    write_text(
        output_dir / "apps" / args.cluster_name / "README.md",
        render_segment_readme(segment="apps", cluster_name=args.cluster_name),
    )
    write_text(
        output_dir / "scripts" / "bootstrap-flux-github.sh",
        render_bootstrap_script(
            repository_name=args.repository_name,
            cluster_name=args.cluster_name,
            flux_version=args.flux_version,
        ),
        mode=0o750,
    )
    write_text(
        output_dir / "scripts" / f"check-{args.cluster_name}.sh",
        render_check_script(cluster_name=args.cluster_name),
        mode=0o750,
    )
    write_text(
        output_dir / "versions.env",
        render_versions_env(
            repository_name=args.repository_name,
            cluster_name=args.cluster_name,
            flux_version=args.flux_version,
        ),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_repo = subparsers.add_parser("render-repo", help="Render the platform-gitops repository scaffold.")
    render_repo.add_argument("--output-dir", required=True)
    render_repo.add_argument("--repository-name", default="platform-gitops")
    render_repo.add_argument("--cluster-name", default="nonprod-mgmt")
    render_repo.add_argument("--flux-version", default="v2.8.6")
    render_repo.set_defaults(func=command_render_repo)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
