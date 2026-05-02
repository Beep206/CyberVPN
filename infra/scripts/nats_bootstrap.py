#!/usr/bin/env python3
"""Render bootstrap bundles for the non-prod NATS JetStream foundation."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ACCOUNTS_FILE = REPO_ROOT / "infra" / "nats" / "examples" / "accounts.json.example"


@dataclass(frozen=True)
class Node:
    name: str
    ipv4_address: str
    client_port: int
    cluster_port: int
    monitor_port: int
    exporter_port: int
    labels: dict[str, str]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_nodes(
    path: Path,
    default_client_port: int,
    default_cluster_port: int,
    default_monitor_port: int,
    default_exporter_port: int,
) -> list[Node]:
    payload = load_json_file(path)
    nodes: list[Node] = []

    if isinstance(payload, dict):
        items = payload.items()
    else:
        raise SystemExit("nodes file must be a JSON object keyed by node name")

    for name, item in sorted(items):
        if not isinstance(item, dict):
            raise SystemExit(f"node entry {name!r} must be an object")
        ipv4_address = str(item.get("ipv4_address", "")).strip()
        if not ipv4_address:
            raise SystemExit(f"node entry {name!r} must define ipv4_address")
        nodes.append(
            Node(
                name=str(name),
                ipv4_address=ipv4_address,
                client_port=int(item.get("client_port", default_client_port)),
                cluster_port=int(item.get("cluster_port", default_cluster_port)),
                monitor_port=int(item.get("monitor_port", default_monitor_port)),
                exporter_port=int(item.get("exporter_port", default_exporter_port)),
                labels={k: str(v) for k, v in (item.get("labels") or {}).items()},
            )
        )

    if len(nodes) < 3:
        raise SystemExit("non-prod JetStream baseline requires at least 3 nodes")
    return nodes


def ensure_account_spec(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SystemExit("accounts spec must be a JSON object")
    accounts = payload.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise SystemExit("accounts spec must contain a non-empty accounts array")
    system_account = str(payload.get("system_account", "")).strip()
    if not system_account:
        raise SystemExit("accounts spec must define system_account")
    return payload


def ensure_password(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return secrets.token_urlsafe(24)


def quoted_list(values: Iterable[str]) -> str:
    rendered = ", ".join(json.dumps(value) for value in values)
    return f"[{rendered}]"


def render_permissions(permissions: dict[str, Any] | None) -> str:
    if not permissions:
        return ""
    publish = permissions.get("publish", [])
    subscribe = permissions.get("subscribe", [])
    if not isinstance(publish, list) or not isinstance(subscribe, list):
        raise SystemExit("permissions publish/subscribe must be arrays")
    parts = [
        "permissions: {",
        f"  publish: {quoted_list([str(v) for v in publish])}",
        f"  subscribe: {quoted_list([str(v) for v in subscribe])}",
        "}",
    ]
    return "\n".join(parts)


def render_accounts_block(accounts_spec: dict[str, Any], credential_manifest: dict[str, dict[str, str]]) -> str:
    rendered_accounts: list[str] = []
    for account in accounts_spec["accounts"]:
        if not isinstance(account, dict):
            raise SystemExit("account entries must be objects")
        account_name = str(account.get("name", "")).strip()
        if not account_name:
            raise SystemExit("account entries must define name")
        users = account.get("users")
        if not isinstance(users, list) or not users:
            raise SystemExit(f"account {account_name!r} must define a non-empty users array")

        rendered_users: list[str] = []
        for user in users:
            if not isinstance(user, dict):
                raise SystemExit(f"account {account_name!r} users must be objects")
            user_name = str(user.get("username", user.get("name", ""))).strip()
            if not user_name:
                raise SystemExit(f"account {account_name!r} contains a user without username")
            password = ensure_password(user.get("password"))
            credential_manifest.setdefault(account_name, {})[user_name] = password
            permissions = render_permissions(user.get("permissions"))
            if permissions:
                rendered_users.append(
                    "{\n"
                    f"  user: {json.dumps(user_name)}\n"
                    f"  password: {json.dumps(password)}\n"
                    f"  {permissions.replace(chr(10), chr(10) + '  ')}\n"
                    "}"
                )
            else:
                rendered_users.append(
                    "{\n"
                    f"  user: {json.dumps(user_name)}\n"
                    f"  password: {json.dumps(password)}\n"
                    "}"
                )

        rendered_accounts.append(
            f"{account_name} {{\n"
            "  users: [\n"
            + ",\n".join("    " + entry.replace("\n", "\n    ") for entry in rendered_users)
            + "\n  ]\n"
            "}"
        )
    return "accounts {\n" + "\n".join("  " + account.replace("\n", "\n  ") for account in rendered_accounts) + "\n}\n"


def render_routes(self_node: Node, nodes: list[Node], route_user: str, route_password: str) -> str:
    routes = [
        f"nats-route://{route_user}:{route_password}@{node.ipv4_address}:{node.cluster_port}"
        for node in nodes
        if node.name != self_node.name
    ]
    return quoted_list(routes)


def render_server_config(
    *,
    cluster_name: str,
    system_account: str,
    node: Node,
    nodes: list[Node],
    route_user: str,
    route_password: str,
    jetstream_store_dir: str,
    jetstream_max_file_store: int,
    jetstream_max_memory_store: int,
    accounts_block: str,
) -> str:
    return (
        f"server_name: {json.dumps(node.name)}\n"
        f"listen: 0.0.0.0:{node.client_port}\n"
        f"http: 127.0.0.1:{node.monitor_port}\n"
        f"system_account: {json.dumps(system_account)}\n"
        "jetstream {\n"
        f"  store_dir: {json.dumps(jetstream_store_dir)}\n"
        f"  max_file_store: {jetstream_max_file_store}\n"
        f"  max_memory_store: {jetstream_max_memory_store}\n"
        "}\n"
        "tls {\n"
        '  cert_file: "/etc/nats/tls/server.crt"\n'
        '  key_file: "/etc/nats/tls/server.key"\n'
        '  ca_file: "/etc/nats/tls/ca.crt"\n'
        '  min_version: "1.2"\n'
        "  timeout: 2\n"
        "}\n"
        f"{accounts_block}"
        "cluster {\n"
        f"  name: {json.dumps(cluster_name)}\n"
        f"  listen: 0.0.0.0:{node.cluster_port}\n"
        f"  advertise: {json.dumps(f'{node.ipv4_address}:{node.cluster_port}')}\n"
        "  authorization {\n"
        f"    user: {json.dumps(route_user)}\n"
        f"    password: {json.dumps(route_password)}\n"
        "    timeout: 2\n"
        "  }\n"
        "  tls {\n"
        '    cert_file: "/etc/nats/tls/server.crt"\n'
        '    key_file: "/etc/nats/tls/server.key"\n'
        '    ca_file: "/etc/nats/tls/ca.crt"\n'
        "    timeout: 2\n"
        "  }\n"
        f"  routes: {render_routes(self_node=node, nodes=nodes, route_user=route_user, route_password=route_password)}\n"
        "}\n"
    )


def render_exporter_env(node: Node) -> str:
    flags = [
        "-addr 0.0.0.0",
        f"-port {node.exporter_port}",
        "-varz",
        "-routez",
        "-healthz",
        "-healthz_js_enabled_only",
        "-jsz streams,consumers",
        "-use_internal_server_name",
        f"http://127.0.0.1:{node.monitor_port}",
    ]
    return f'NATS_EXPORTER_FLAGS="{ " ".join(flags) }"\n'


def render_install_script(node: Node) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

bundle_dir="$$(cd "$$(dirname "$0")" && pwd)"

install -d -m 0750 -o nats -g nats /etc/nats
install -d -m 0750 -o nats -g nats /etc/nats/tls
install -m 0640 -o nats -g nats "$$bundle_dir/nats-server.conf" /etc/nats/nats-server.conf
install -m 0640 -o nats -g nats "$$bundle_dir/nats-exporter.env" /etc/nats/exporter.env
install -m 0640 -o nats -g nats "$$bundle_dir/tls/ca.crt" /etc/nats/tls/ca.crt
install -m 0640 -o nats -g nats "$$bundle_dir/tls/server.crt" /etc/nats/tls/server.crt
install -m 0640 -o nats -g nats "$$bundle_dir/tls/server.key" /etc/nats/tls/server.key
systemctl restart nats.service
systemctl restart nats-exporter.service
systemctl status --no-pager nats.service
systemctl status --no-pager nats-exporter.service
"""


def render_prometheus_targets(cluster_name: str, nodes: list[Node]) -> str:
    payload = [
        {
            "targets": [f"{node.ipv4_address}:{node.exporter_port}"],
            "labels": {
                "job": "nats-exporter",
                "environment": "nonprod",
                "nats_cluster": cluster_name,
                "nats_node": node.name,
            },
        }
        for node in nodes
    ]
    return json.dumps(payload, indent=2) + "\n"


def run_openssl(args: list[str]) -> None:
    subprocess.run(["openssl", *args], check=True, capture_output=True, text=True)


def build_ca_bundle(output_dir: Path, cluster_name: str) -> tuple[Path, Path]:
    ca_dir = output_dir / "ca"
    ca_key = ca_dir / "ca.key"
    ca_crt = ca_dir / "ca.crt"
    ca_conf = ca_dir / "ca.cnf"
    write_text(
        ca_conf,
        (
            "[req]\n"
            "distinguished_name = dn\n"
            "x509_extensions = v3_ca\n"
            "prompt = no\n"
            "[dn]\n"
            f"CN = {cluster_name} CA\n"
            "[v3_ca]\n"
            "basicConstraints = critical, CA:TRUE\n"
            "keyUsage = critical, keyCertSign, cRLSign\n"
            "subjectKeyIdentifier = hash\n"
            "authorityKeyIdentifier = keyid:always,issuer\n"
        ),
    )
    run_openssl(["genrsa", "-out", str(ca_key), "4096"])
    run_openssl(["req", "-x509", "-new", "-nodes", "-key", str(ca_key), "-sha256", "-days", "3650", "-out", str(ca_crt), "-config", str(ca_conf)])
    os.chmod(ca_key, 0o600)
    os.chmod(ca_crt, 0o644)
    return ca_key, ca_crt


def build_node_cert(node_dir: Path, node: Node, ca_key: Path, ca_crt: Path) -> None:
    tls_dir = node_dir / "tls"
    key_path = tls_dir / "server.key"
    csr_path = tls_dir / "server.csr"
    crt_path = tls_dir / "server.crt"
    conf_path = tls_dir / "server.cnf"
    serial_path = tls_dir / "ca.srl"

    write_text(
        conf_path,
        (
            "[req]\n"
            "distinguished_name = dn\n"
            "req_extensions = req_ext\n"
            "prompt = no\n"
            "[dn]\n"
            f"CN = {node.name}\n"
            "[req_ext]\n"
            "subjectAltName = @alt_names\n"
            "extendedKeyUsage = serverAuth, clientAuth\n"
            "keyUsage = critical, digitalSignature, keyEncipherment\n"
            "[alt_names]\n"
            f"DNS.1 = {node.name}\n"
            f"IP.1 = {node.ipv4_address}\n"
        ),
    )

    run_openssl(["genrsa", "-out", str(key_path), "4096"])
    run_openssl(["req", "-new", "-key", str(key_path), "-out", str(csr_path), "-config", str(conf_path)])
    run_openssl(
        [
            "x509",
            "-req",
            "-in",
            str(csr_path),
            "-CA",
            str(ca_crt),
            "-CAkey",
            str(ca_key),
            "-CAcreateserial",
            "-CAserial",
            str(serial_path),
            "-out",
            str(crt_path),
            "-days",
            "825",
            "-sha256",
            "-extensions",
            "req_ext",
            "-extfile",
            str(conf_path),
        ]
    )
    write_text(tls_dir / "ca.crt", ca_crt.read_text(encoding="utf-8"), mode=0o644)
    os.chmod(key_path, 0o600)
    os.chmod(crt_path, 0o644)


def command_render_bundle(args: argparse.Namespace) -> int:
    accounts_spec = ensure_account_spec(load_json_file(Path(args.accounts_file)))
    nodes = load_nodes(
        Path(args.nodes_file),
        default_client_port=args.client_port,
        default_cluster_port=args.cluster_port,
        default_monitor_port=args.monitor_port,
        default_exporter_port=args.exporter_port,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    credentials: dict[str, dict[str, str]] = {}
    route_user = "route-sync"
    route_password = secrets.token_urlsafe(24)
    accounts_block = render_accounts_block(accounts_spec, credentials)

    ca_key, ca_crt = build_ca_bundle(output_dir, args.cluster_name)

    manifest = {
      "cluster_name": args.cluster_name,
      "system_account": accounts_spec["system_account"],
      "route_credentials": {
        "username": route_user,
        "password": route_password,
      },
      "accounts": credentials,
      "nodes": {
        node.name: {
          "ipv4_address": node.ipv4_address,
          "client_port": node.client_port,
          "cluster_port": node.cluster_port,
          "monitor_port": node.monitor_port,
          "exporter_port": node.exporter_port,
        }
        for node in nodes
      },
    }

    write_text(output_dir / "credentials.json", json.dumps(manifest, indent=2) + "\n", mode=0o600)
    write_text(output_dir / "prometheus" / f"{args.cluster_name}-targets.json", render_prometheus_targets(args.cluster_name, nodes), mode=0o644)

    for node in nodes:
        node_dir = output_dir / node.name
        node_dir.mkdir(parents=True, exist_ok=True)
        build_node_cert(node_dir, node, ca_key, ca_crt)
        write_text(
            node_dir / "nats-server.conf",
            render_server_config(
                cluster_name=args.cluster_name,
                system_account=accounts_spec["system_account"],
                node=node,
                nodes=nodes,
                route_user=route_user,
                route_password=route_password,
                jetstream_store_dir=args.jetstream_store_dir,
                jetstream_max_file_store=args.jetstream_max_file_store,
                jetstream_max_memory_store=args.jetstream_max_memory_store,
                accounts_block=accounts_block,
            ),
        )
        write_text(node_dir / "nats-exporter.env", render_exporter_env(node))
        write_text(node_dir / "install-node.sh", render_install_script(node), mode=0o750)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render bootstrap bundles for the non-prod NATS JetStream foundation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_bundle = subparsers.add_parser("render-bundle", help="Render TLS, config, credentials, and install scripts for a NATS JetStream cluster")
    render_bundle.add_argument("--cluster-name", required=True)
    render_bundle.add_argument("--nodes-file", required=True)
    render_bundle.add_argument("--accounts-file", default=str(DEFAULT_ACCOUNTS_FILE))
    render_bundle.add_argument("--output-dir", required=True)
    render_bundle.add_argument("--client-port", type=int, default=4222)
    render_bundle.add_argument("--cluster-port", type=int, default=6222)
    render_bundle.add_argument("--monitor-port", type=int, default=8222)
    render_bundle.add_argument("--exporter-port", type=int, default=7777)
    render_bundle.add_argument("--jetstream-store-dir", default="/var/lib/nats/jetstream")
    render_bundle.add_argument("--jetstream-max-file-store", type=int, default=21474836480)
    render_bundle.add_argument("--jetstream-max-memory-store", type=int, default=268435456)
    render_bundle.set_defaults(func=command_render_bundle)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
