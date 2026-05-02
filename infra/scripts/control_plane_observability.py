#!/usr/bin/env python3
"""Render observability bundles for non-prod external control-plane VMs."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


@dataclass(frozen=True)
class Node:
    name: str
    ipv4_address: str
    component: str
    cluster_id: str
    environment: str


PROJECT = "cybervpn"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_component_nodes(*, path: Path, component: str, cluster_id: str, environment: str) -> list[Node]:
    payload = load_json(path)
    return [
        Node(
            name=name,
            ipv4_address=str(details["ipv4_address"]),
            component=component,
            cluster_id=cluster_id,
            environment=environment,
        )
        for name, details in payload.items()
    ]


def render_loki_write(
    *,
    loki_url: str,
    basic_auth_username: str,
    basic_auth_password: str,
    bearer_token: str,
) -> str:
    auth_lines = ""
    if basic_auth_username:
        auth_lines = (
            "    basic_auth {\n"
            f'      username = "{basic_auth_username}"\n'
            f'      password = "{basic_auth_password}"\n'
            "    }\n"
        )
    elif bearer_token:
        auth_lines = f'    bearer_token = "{bearer_token}"\n'

    return (
        'loki.write "control_plane" {\n'
        "  endpoint {\n"
        f'    url = "{loki_url}"\n'
        f"{auth_lines}"
        "  }\n"
        "}\n"
    )


def render_openbao_alloy(node: Node, *, loki_url: str, basic_auth_username: str, basic_auth_password: str, bearer_token: str) -> str:
    return (
        'logging {\n  level = "info"\n  format = "logfmt"\n}\n\n'
        + render_loki_write(
            loki_url=loki_url,
            basic_auth_username=basic_auth_username,
            basic_auth_password=basic_auth_password,
            bearer_token=bearer_token,
        )
        + '\n'
        + 'loki.source.journal "openbao_service" {\n'
        '  matches = "_SYSTEMD_UNIT=openbao.service"\n'
        '  labels = {\n'
        '    job         = "alloy-control-plane"\n'
        f'    project     = "{PROJECT}"\n'
        f'    environment = "{node.environment}"\n'
        f'    component   = "{node.component}"\n'
        f'    cluster_id  = "{node.cluster_id}"\n'
        f'    instance    = "{node.name}"\n'
        '    log_source  = "journald"\n'
        '  }\n'
        '  forward_to = [loki.write.control_plane.receiver]\n'
        '}\n\n'
        'local.file_match "openbao_audit" {\n'
        '  path_targets = [\n'
        '    {\n'
        '      __address__ = "localhost"\n'
        '      __path__    = "/var/log/openbao/*.log"\n'
        '      job         = "alloy-control-plane"\n'
        f'      project     = "{PROJECT}"\n'
        f'      environment = "{node.environment}"\n'
        f'      component   = "{node.component}"\n'
        f'      cluster_id  = "{node.cluster_id}"\n'
        f'      instance    = "{node.name}"\n'
        '      log_source  = "file"\n'
        '    },\n'
        '  ]\n'
        '}\n\n'
        'loki.source.file "openbao_audit" {\n'
        '  targets    = local.file_match.openbao_audit.targets\n'
        '  forward_to = [loki.write.control_plane.receiver]\n'
        '}\n'
    )


def render_nats_alloy(node: Node, *, loki_url: str, basic_auth_username: str, basic_auth_password: str, bearer_token: str) -> str:
    common = render_loki_write(
        loki_url=loki_url,
        basic_auth_username=basic_auth_username,
        basic_auth_password=basic_auth_password,
        bearer_token=bearer_token,
    )
    return (
        'logging {\n  level = "info"\n  format = "logfmt"\n}\n\n'
        + common
        + '\n'
        + 'loki.source.journal "nats_service" {\n'
        '  matches = "_SYSTEMD_UNIT=nats.service"\n'
        '  labels = {\n'
        '    job         = "alloy-control-plane"\n'
        f'    project     = "{PROJECT}"\n'
        f'    environment = "{node.environment}"\n'
        f'    component   = "{node.component}"\n'
        f'    cluster_id  = "{node.cluster_id}"\n'
        f'    instance    = "{node.name}"\n'
        '    log_source  = "journald"\n'
        '  }\n'
        '  forward_to = [loki.write.control_plane.receiver]\n'
        '}\n\n'
        'loki.source.journal "nats_exporter" {\n'
        '  matches = "_SYSTEMD_UNIT=nats-exporter.service"\n'
        '  labels = {\n'
        '    job         = "alloy-control-plane"\n'
        f'    project     = "{PROJECT}"\n'
        f'    environment = "{node.environment}"\n'
        f'    component   = "{node.component}"\n'
        f'    cluster_id  = "{node.cluster_id}"\n'
        f'    instance    = "{node.name}"\n'
        '    log_source  = "journald"\n'
        '  }\n'
        '  forward_to = [loki.write.control_plane.receiver]\n'
        '}\n'
    )


def render_posthog_alloy(node: Node, *, loki_url: str, basic_auth_username: str, basic_auth_password: str, bearer_token: str) -> str:
    return (
        'logging {\n  level = "info"\n  format = "logfmt"\n}\n\n'
        + render_loki_write(
            loki_url=loki_url,
            basic_auth_username=basic_auth_username,
            basic_auth_password=basic_auth_password,
            bearer_token=bearer_token,
        )
        + '\n'
        + 'local.file_match "docker_logs" {\n'
        '  path_targets = [\n'
        '    {\n'
        '      __address__ = "localhost"\n'
        '      __path__    = "/var/lib/docker/containers/*/*-json.log"\n'
        '      job         = "alloy-control-plane"\n'
        f'      project     = "{PROJECT}"\n'
        f'      environment = "{node.environment}"\n'
        f'      component   = "{node.component}"\n'
        f'      cluster_id  = "{node.cluster_id}"\n'
        f'      instance    = "{node.name}"\n'
        '      log_source  = "docker-json"\n'
        '    },\n'
        '  ]\n'
        '}\n\n'
        'loki.source.file "docker_logs" {\n'
        '  targets    = local.file_match.docker_logs.targets\n'
        '  forward_to = [loki.write.control_plane.receiver]\n'
        '}\n\n'
        'loki.source.journal "nginx_service" {\n'
        '  matches = "_SYSTEMD_UNIT=nginx.service"\n'
        '  labels = {\n'
        '    job         = "alloy-control-plane"\n'
        f'    project     = "{PROJECT}"\n'
        f'    environment = "{node.environment}"\n'
        f'    component   = "{node.component}"\n'
        f'    cluster_id  = "{node.cluster_id}"\n'
        f'    instance    = "{node.name}"\n'
        '    log_source  = "journald"\n'
        '  }\n'
        '  forward_to = [loki.write.control_plane.receiver]\n'
        '}\n'
    )


def render_alloy_service(config_path: str, storage_path: str, listen_addr: str) -> str:
    return (
        "[Unit]\n"
        "Description=CyberVPN Control Plane Grafana Alloy\n"
        "Documentation=https://grafana.com/docs/alloy/latest/\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart=/usr/bin/alloy run --disable-reporting --storage.path={storage_path} --server.http.listen-addr={listen_addr} {config_path}\n"
        "Restart=on-failure\n"
        "RestartSec=5\n"
        "UMask=0077\n"
        "NoNewPrivileges=yes\n"
        "PrivateTmp=yes\n"
        "ProtectHome=yes\n"
        "ProtectSystem=full\n"
        "ReadWritePaths=/var/lib/alloy\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def render_install_script(component: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$(cd "$(dirname "$0")" && pwd)"

apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg
install -d -m 0755 /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/grafana.gpg ]; then
  curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/grafana.gpg
fi
cat >/etc/apt/sources.list.d/grafana.list <<'EOF'
deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main
EOF
apt-get update
apt-get install -y alloy
usermod -a -G adm,systemd-journal alloy || true

install -d -m 0755 /etc/alloy /var/lib/alloy
install -m 0600 "$bundle_dir/config.alloy" /etc/alloy/config.alloy
install -m 0644 "$bundle_dir/cybervpn-alloy.service" /etc/systemd/system/cybervpn-alloy.service

systemctl stop alloy || true
systemctl disable alloy || true
systemctl daemon-reload
systemctl enable --now cybervpn-alloy.service
systemctl status --no-pager cybervpn-alloy.service

echo "Alloy control-plane bundle installed for {component}."
"""


def render_prometheus_targets(nodes: Iterable[Node], *, alloy_http_port: int) -> str:
    targets = [
        {
            "targets": [f"{node.ipv4_address}:{alloy_http_port}"],
            "labels": {
                "job": "alloy-control-plane",
                "project": PROJECT,
                "environment": node.environment,
                "component": node.component,
                "cluster_id": node.cluster_id,
                "instance": node.name,
            },
        }
        for node in nodes
    ]
    return json.dumps(targets, indent=2) + "\n"


def render_openbao_targets(cluster_id: str, environment: str, metrics_addrs: dict[str, str]) -> str:
    targets = []
    for node_name, metrics_addr in metrics_addrs.items():
        parsed = urlparse(metrics_addr)
        targets.append(
            {
                "targets": [parsed.netloc],
                "labels": {
                    "job": "openbao",
                    "project": PROJECT,
                    "environment": environment,
                    "component": "openbao",
                    "cluster_id": cluster_id,
                    "instance": node_name,
                },
            }
        )
    return json.dumps(targets, indent=2) + "\n"


def render_readme(environment: str, alloy_http_port: int, openbao_target_file: str) -> str:
    return f"""# {environment} control-plane observability bundle

This bundle establishes the `P1.7` observability baseline for the external non-prod control planes:

- `openbao-nonprod`
- `nats-nonprod`
- `posthog-nonprod`

What it renders:

- per-host Alloy configs and install scripts under `hosts/`
- Prometheus `file_sd` targets under `prometheus/`
- references for the local monitoring host and Grafana dashboard/rule surfaces in the monorepo

Operator flow:

1. Export real OpenTofu outputs for:
   - `staging/openbao` -> `openbao_nodes`
   - `staging/nats` -> `nats_nodes`
   - `staging/posthog` -> `posthog_nodes`
2. Render this bundle.
3. Copy `prometheus/control-plane-alloy-{environment}.json` into the monitoring host `file_sd` directory.
4. Copy `prometheus/{openbao_target_file}` into the monitoring host `file_sd` directory.
5. Run each `hosts/<name>/install-alloy.sh` on the corresponding VM.

Important boundary:

- this baseline covers **external VM control planes only**
- `nonprod-mgmt` Talos cluster add-on observability remains a later packet and lands through the Kubernetes path, not host-level Alloy package install
- `promtail` and standalone long-lived `otel-collector` are not valid target collectors for any newly introduced systems in this bundle

Default Alloy metrics port:

- `{alloy_http_port}`
"""


def command_render_bundle(args: argparse.Namespace) -> int:
    if bool(args.loki_basic_auth_username) != bool(args.loki_basic_auth_password):
        raise SystemExit("Both --loki-basic-auth-username and --loki-basic-auth-password must be set together.")
    if args.loki_basic_auth_username and args.loki_bearer_token:
        raise SystemExit("Use either basic auth or bearer token for Loki, not both.")

    output_dir = Path(args.output_dir)

    openbao_nodes_payload = load_json(Path(args.openbao_nodes_file))
    nats_nodes_payload = load_json(Path(args.nats_nodes_file))
    posthog_nodes_payload = load_json(Path(args.posthog_nodes_file))

    openbao_cluster_id = args.openbao_cluster_id
    nats_cluster_id = args.nats_cluster_id
    posthog_instance_id = args.posthog_instance_id

    openbao_nodes = load_component_nodes(
        path=Path(args.openbao_nodes_file),
        component="openbao",
        cluster_id=openbao_cluster_id,
        environment=args.environment,
    )
    nats_nodes = load_component_nodes(
        path=Path(args.nats_nodes_file),
        component="nats",
        cluster_id=nats_cluster_id,
        environment=args.environment,
    )
    posthog_nodes = load_component_nodes(
        path=Path(args.posthog_nodes_file),
        component="posthog",
        cluster_id=posthog_instance_id,
        environment=args.environment,
    )
    all_nodes = [*openbao_nodes, *nats_nodes, *posthog_nodes]

    for node in openbao_nodes:
        node_dir = output_dir / "hosts" / node.name
        write_text(
            node_dir / "config.alloy",
            render_openbao_alloy(
                node,
                loki_url=args.loki_url,
                basic_auth_username=args.loki_basic_auth_username,
                basic_auth_password=args.loki_basic_auth_password,
                bearer_token=args.loki_bearer_token,
            ),
            mode=0o600,
        )
        write_text(node_dir / "cybervpn-alloy.service", render_alloy_service("/etc/alloy/config.alloy", "/var/lib/alloy/data", f"0.0.0.0:{args.alloy_http_port}"), mode=0o644)
        write_text(node_dir / "install-alloy.sh", render_install_script("openbao"), mode=0o750)

    for node in nats_nodes:
        node_dir = output_dir / "hosts" / node.name
        write_text(
            node_dir / "config.alloy",
            render_nats_alloy(
                node,
                loki_url=args.loki_url,
                basic_auth_username=args.loki_basic_auth_username,
                basic_auth_password=args.loki_basic_auth_password,
                bearer_token=args.loki_bearer_token,
            ),
            mode=0o600,
        )
        write_text(node_dir / "cybervpn-alloy.service", render_alloy_service("/etc/alloy/config.alloy", "/var/lib/alloy/data", f"0.0.0.0:{args.alloy_http_port}"), mode=0o644)
        write_text(node_dir / "install-alloy.sh", render_install_script("nats"), mode=0o750)

    for node in posthog_nodes:
        node_dir = output_dir / "hosts" / node.name
        write_text(
            node_dir / "config.alloy",
            render_posthog_alloy(
                node,
                loki_url=args.loki_url,
                basic_auth_username=args.loki_basic_auth_username,
                basic_auth_password=args.loki_basic_auth_password,
                bearer_token=args.loki_bearer_token,
            ),
            mode=0o600,
        )
        write_text(node_dir / "cybervpn-alloy.service", render_alloy_service("/etc/alloy/config.alloy", "/var/lib/alloy/data", f"0.0.0.0:{args.alloy_http_port}"), mode=0o644)
        write_text(node_dir / "install-alloy.sh", render_install_script("posthog"), mode=0o750)

    openbao_metrics_addrs = {
        node_name: str(node_payload["metrics_addr"])
        for node_name, node_payload in openbao_nodes_payload.items()
    }
    openbao_targets_file = f"{openbao_cluster_id}-targets.json"
    write_text(
        output_dir / "prometheus" / f"control-plane-alloy-{args.environment}.json",
        render_prometheus_targets(all_nodes, alloy_http_port=args.alloy_http_port),
        mode=0o644,
    )
    write_text(
        output_dir / "prometheus" / openbao_targets_file,
        render_openbao_targets(openbao_cluster_id, args.environment, openbao_metrics_addrs),
        mode=0o644,
    )
    write_text(
        output_dir / "README.md",
        render_readme(args.environment, args.alloy_http_port, openbao_targets_file),
        mode=0o644,
    )
    write_text(
        output_dir / "versions.env",
        (
            f"ENVIRONMENT={args.environment}\n"
            f"ALLOY_HTTP_PORT={args.alloy_http_port}\n"
            f"OPENBAO_CLUSTER_ID={openbao_cluster_id}\n"
            f"NATS_CLUSTER_ID={nats_cluster_id}\n"
            f"POSTHOG_INSTANCE_ID={posthog_instance_id}\n"
        ),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_bundle = subparsers.add_parser("render-bundle", help="Render the non-prod control-plane observability bundle.")
    render_bundle.add_argument("--output-dir", required=True)
    render_bundle.add_argument("--openbao-nodes-file", required=True)
    render_bundle.add_argument("--nats-nodes-file", required=True)
    render_bundle.add_argument("--posthog-nodes-file", required=True)
    render_bundle.add_argument("--environment", default="nonprod")
    render_bundle.add_argument("--openbao-cluster-id", default="openbao-nonprod")
    render_bundle.add_argument("--nats-cluster-id", default="nats-nonprod")
    render_bundle.add_argument("--posthog-instance-id", default="posthog-nonprod")
    render_bundle.add_argument("--loki-url", default="http://loki:3100/loki/api/v1/push")
    render_bundle.add_argument("--loki-basic-auth-username", default="")
    render_bundle.add_argument("--loki-basic-auth-password", default="")
    render_bundle.add_argument("--loki-bearer-token", default="")
    render_bundle.add_argument("--alloy-http-port", type=int, default=9100)
    render_bundle.set_defaults(func=command_render_bundle)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
