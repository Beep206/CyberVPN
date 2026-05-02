#!/usr/bin/env python3
"""Generate an Ansible inventory snapshot from OpenTofu edge outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an Ansible inventory snapshot from OpenTofu edge outputs."
    )
    parser.add_argument(
        "--stack-dir",
        "--terraform-dir",
        dest="stack_dir",
        required=True,
        help="Path to the OpenTofu stack that exposes the edge_nodes output.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the generated inventory snapshot.",
    )
    parser.add_argument(
        "--environment",
        required=True,
        help="Environment suffix used in generated group names, for example staging.",
    )
    parser.add_argument(
        "--tofu-bin",
        "--terraform-bin",
        dest="tofu_bin",
        default="tofu",
        help="OpenTofu binary to execute. Terraform may be passed explicitly for rollback workflows.",
    )
    parser.add_argument(
        "--stack-output-file",
        "--terraform-output-file",
        dest="stack_output_file",
        help="Optional JSON file with the edge_nodes payload, used instead of calling OpenTofu output.",
    )
    parser.add_argument(
        "--ansible-user",
        default="cyberops",
        help="Default ansible_user written into hostvars.",
    )
    parser.add_argument(
        "--prometheus-output",
        help="Optional path for a Prometheus file_sd target snapshot.",
    )
    parser.add_argument(
        "--metrics-port",
        default=9100,
        type=int,
        help="Metrics port written into the Prometheus target snapshot.",
    )
    return parser.parse_args()


def parse_edge_nodes_payload(raw_payload: str) -> dict[str, dict[str, object]]:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenTofu output was not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Expected edge_nodes output to be a JSON object keyed by hostname.")

    return payload


def load_edge_nodes(tofu_bin: str, stack_dir: Path) -> dict[str, dict[str, object]]:
    result = subprocess.run(
        [tofu_bin, "output", "-json", "edge_nodes"],
        cwd=stack_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_edge_nodes_payload(result.stdout)


def build_inventory(
    edge_nodes: dict[str, dict[str, object]],
    environment: str,
    ansible_user: str,
) -> dict[str, object]:
    env_group = f"edge_{environment}"
    inventory: dict[str, object] = {
        "all": {
            "children": {
                env_group: {
                    "hosts": {},
                }
            }
        }
    }

    children = inventory["all"]["children"]  # type: ignore[index]
    env_hosts = children[env_group]["hosts"]  # type: ignore[index]

    for hostname in sorted(edge_nodes):
        node = edge_nodes[hostname]
        role = str(node["role"])
        role_group = f"{role}_edge_{environment}"
        location_group = f"{str(node['location'])}_{environment}"

        hostvars = {
            "ansible_host": node["ip"],
            "ansible_port": node["ssh_port"],
            "ansible_user": ansible_user,
            "node_role": role,
            "node_location": node["location"],
            "node_environment": environment,
            "node_server_type": node["server_type"],
            "node_labels": node["labels"],
        }

        env_hosts[hostname] = hostvars

        for group_name in (role_group, location_group):
            group = children.setdefault(group_name, {"hosts": {}})
            group["hosts"][hostname] = {}

    return inventory


def build_prometheus_targets(
    edge_nodes: dict[str, dict[str, object]],
    environment: str,
    metrics_port: int,
) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []

    for hostname in sorted(edge_nodes):
        node = edge_nodes[hostname]
        targets.append(
            {
                "targets": [f"{node['ip']}:{metrics_port}"],
                "labels": {
                    "job": "alloy-edge",
                    "environment": environment,
                    "hostname": hostname,
                    "node_role": str(node["role"]),
                    "node_location": str(node["location"]),
                    "server_type": str(node["server_type"]),
                },
            }
        )

    return targets


def main() -> int:
    args = parse_args()
    stack_dir = Path(args.stack_dir).resolve()
    output_path = Path(args.output).resolve()
    prometheus_output_path = (
        Path(args.prometheus_output).resolve() if args.prometheus_output else None
    )

    if not stack_dir.exists():
        print(f"OpenTofu stack directory does not exist: {stack_dir}", file=sys.stderr)
        return 1

    try:
        if args.stack_output_file:
            edge_nodes = parse_edge_nodes_payload(Path(args.stack_output_file).read_text())
        else:
            edge_nodes = load_edge_nodes(args.tofu_bin, stack_dir)
        inventory = build_inventory(edge_nodes, args.environment, args.ansible_user)
        prometheus_targets = build_prometheus_targets(
            edge_nodes=edge_nodes,
            environment=args.environment,
            metrics_port=args.metrics_port,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        print(f"Failed to read OpenTofu outputs: {stderr}", file=sys.stderr)
        return exc.returncode or 1
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    print(f"Wrote inventory snapshot to {output_path}")

    if prometheus_output_path:
        prometheus_output_path.parent.mkdir(parents=True, exist_ok=True)
        prometheus_output_path.write_text(
            json.dumps(prometheus_targets, indent=2, sort_keys=True) + "\n"
        )
        print(f"Wrote Prometheus target snapshot to {prometheus_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
