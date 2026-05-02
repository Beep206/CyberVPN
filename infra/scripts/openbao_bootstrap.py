#!/usr/bin/env python3
"""Canonical bootstrap helper for the non-prod OpenBao foundation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_DIR = REPO_ROOT / "infra" / "openbao" / "policies"


@dataclass(frozen=True)
class BaoContext:
    bao_bin: str
    address: str
    ca_cert: Path | None
    token: str | None
    namespace: str | None = None

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["VAULT_ADDR"] = self.address
        env.setdefault("BAO_FORMAT", "json")
        if self.ca_cert is not None:
            env["VAULT_CACERT"] = str(self.ca_cert)
        if self.token:
            env["VAULT_TOKEN"] = self.token
        if self.namespace:
            env["VAULT_NAMESPACE"] = self.namespace
        return env


def run_bao(context: BaoContext, args: Iterable[str], *, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [context.bao_bin, *args],
        check=True,
        capture_output=True,
        text=True,
        input=stdin,
        env=context.env(),
    )


def maybe_json(stdout: str) -> object:
    stdout = stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text_private(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"environment variable {name} must be set")
    return value


def command_render_seal_env(args: argparse.Namespace) -> int:
    lines = [
        f"VAULT_ADDR={args.address}",
        f"VAULT_CACERT={args.ca_cert}",
        "VAULT_SEAL_TYPE=awskms",
        f"VAULT_AWSKMS_SEAL_KEY_ID={args.kms_key_id}",
        f"AWS_REGION={args.aws_region}",
        f"AWS_ACCESS_KEY_ID={required_env('AWS_ACCESS_KEY_ID')}",
        f"AWS_SECRET_ACCESS_KEY={required_env('AWS_SECRET_ACCESS_KEY')}",
    ]
    session_token = os.getenv("AWS_SESSION_TOKEN", "").strip()
    if session_token:
        lines.append(f"AWS_SESSION_TOKEN={session_token}")
    lines.append("")
    write_text_private(Path(args.output), "\n".join(lines))
    return 0


def command_init_cluster(args: argparse.Namespace) -> int:
    context = BaoContext(
        bao_bin=args.bao_bin,
        address=args.address,
        ca_cert=Path(args.ca_cert) if args.ca_cert else None,
        token=None,
    )
    status = maybe_json(run_bao(context, ["status", "-format=json"]).stdout)
    if not isinstance(status, dict):
        raise SystemExit("failed to parse bao status output")
    if status.get("initialized"):
        return 0

    result = run_bao(
        context,
        [
            "operator",
            "init",
            f"-key-shares={args.key_shares}",
            f"-key-threshold={args.key_threshold}",
            f"-recovery-shares={args.recovery_shares}",
            f"-recovery-threshold={args.recovery_threshold}",
            "-format=json",
        ],
    )
    write_text_private(Path(args.output), result.stdout)
    return 0


def ensure_namespace(root_context: BaoContext, namespace: str) -> None:
    payload = maybe_json(run_bao(root_context, ["namespace", "list", "-format=json"]).stdout)
    keys: set[str] = set()
    if isinstance(payload, dict):
        data = payload.get("data", {})
        if isinstance(data, dict):
            for item in data.get("keys", []) or []:
                if isinstance(item, str):
                    keys.add(item.rstrip("/"))
    if namespace not in keys:
        run_bao(root_context, ["namespace", "create", f"{namespace}/"])


def auth_enabled(context: BaoContext, path: str) -> bool:
    payload = maybe_json(run_bao(context, ["auth", "list", "-format=json"]).stdout)
    return isinstance(payload, dict) and f"{path.rstrip('/')}/" in payload


def ensure_auth_mount(context: BaoContext, *, path: str, auth_type: str, description: str) -> None:
    if auth_enabled(context, path):
        return
    run_bao(context, ["auth", "enable", f"-path={path}", f"-description={description}", auth_type])


def secret_enabled(context: BaoContext, path: str) -> bool:
    payload = maybe_json(run_bao(context, ["secrets", "list", "-format=json"]).stdout)
    return isinstance(payload, dict) and f"{path.rstrip('/')}/" in payload


def ensure_secret_mount(
    context: BaoContext,
    *,
    path: str,
    secret_type: str,
    description: str,
    max_lease_ttl: str | None = None,
    version: int | None = None,
) -> None:
    if not secret_enabled(context, path):
        cmd = ["secrets", "enable", f"-path={path}", f"-description={description}"]
        if max_lease_ttl:
            cmd.append(f"-max-lease-ttl={max_lease_ttl}")
        if version is not None:
            cmd.append(f"-version={version}")
        cmd.append(secret_type)
        run_bao(context, cmd)
    elif max_lease_ttl:
        run_bao(context, ["secrets", "tune", f"-max-lease-ttl={max_lease_ttl}", f"{path}/"])


def apply_policies(context: BaoContext, policy_dir: Path) -> None:
    for policy_file in sorted(policy_dir.glob("*.hcl")):
        run_bao(context, ["policy", "write", policy_file.stem, str(policy_file)])


def load_json_file(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_oidc_config(root_context: BaoContext, config_path: Path) -> None:
    spec = load_json_file(config_path)
    if not isinstance(spec, dict):
        raise SystemExit("OIDC config must be a JSON object")
    config = spec.get("config")
    if not isinstance(config, dict):
        raise SystemExit("OIDC config must contain a config object")
    run_bao(root_context, ["write", "auth/oidc-operators/config", "-"], stdin=json.dumps(config))
    roles = spec.get("roles", [])
    if not isinstance(roles, list):
        raise SystemExit("OIDC config roles must be an array")
    for role in roles:
        if not isinstance(role, dict) or "name" not in role or "payload" not in role:
            raise SystemExit("each OIDC role must contain name and payload")
        run_bao(
            root_context,
            ["write", f"auth/oidc-operators/role/{role['name']}", "-"],
            stdin=json.dumps(role["payload"]),
        )


def apply_jwt_mounts(platform_context: BaoContext, spec_path: Path) -> None:
    spec = load_json_file(spec_path)
    if not isinstance(spec, dict):
        raise SystemExit("JWT mount spec must be a JSON object")
    mounts = spec.get("mounts", [])
    if not isinstance(mounts, list):
        raise SystemExit("JWT mount spec field 'mounts' must be an array")

    for mount in mounts:
        if not isinstance(mount, dict):
            raise SystemExit("each JWT mount entry must be an object")
        cluster_id = str(mount.get("cluster_id", "")).strip()
        if not cluster_id:
            raise SystemExit("each JWT mount entry must define cluster_id")
        mount_path = f"jwt-k8s-{cluster_id}"
        ensure_auth_mount(
            platform_context,
            path=mount_path,
            auth_type="jwt",
            description=f"Kubernetes JWT auth for {cluster_id}",
        )

        config = mount.get("config", {})
        if not isinstance(config, dict):
            raise SystemExit("JWT mount config must be an object")
        if config:
            payload = dict(config)
            ca_file = payload.pop("oidc_discovery_ca_pem_file", None)
            if ca_file:
                payload["oidc_discovery_ca_pem"] = Path(str(ca_file)).read_text(encoding="utf-8")
            run_bao(
                platform_context,
                ["write", f"auth/{mount_path}/config", "-"],
                stdin=json.dumps(payload),
            )

        roles = mount.get("roles", [])
        if not isinstance(roles, list):
            raise SystemExit("JWT mount roles must be an array")
        for role in roles:
            if not isinstance(role, dict) or "name" not in role or "payload" not in role:
                raise SystemExit("each JWT role must contain name and payload")
            run_bao(
                platform_context,
                ["write", f"auth/{mount_path}/role/{role['name']}", "-"],
                stdin=json.dumps(role["payload"]),
            )


def maybe_issue_bootstrap_token(root_context: BaoContext, args: argparse.Namespace) -> None:
    if not args.issue_bootstrap_token_output:
        return
    result = run_bao(
        root_context,
        [
            "token",
            "create",
            f"-policy={args.bootstrap_token_policy}",
            f"-ttl={args.bootstrap_token_ttl}",
            "-orphan",
            "-format=json",
        ],
    )
    write_text_private(Path(args.issue_bootstrap_token_output), result.stdout)


def command_apply_baseline(args: argparse.Namespace) -> int:
    root_token = args.token
    if not root_token and args.token_file:
        root_token = Path(args.token_file).read_text(encoding="utf-8").strip()
    if not root_token:
        raise SystemExit("apply-baseline requires --token or --token-file")

    root_context = BaoContext(
        bao_bin=args.bao_bin,
        address=args.address,
        ca_cert=Path(args.ca_cert) if args.ca_cert else None,
        token=root_token,
    )
    ensure_namespace(root_context, args.platform_namespace)
    ensure_auth_mount(root_context, path="oidc-operators", auth_type="oidc", description="Human operator login path")
    apply_policies(root_context, Path(args.policy_dir))

    platform_context = BaoContext(
        bao_bin=root_context.bao_bin,
        address=root_context.address,
        ca_cert=root_context.ca_cert,
        token=root_context.token,
        namespace=args.platform_namespace,
    )
    ensure_auth_mount(platform_context, path="cert-fleet", auth_type="cert", description="Fleet certificate authentication")
    ensure_auth_mount(
        platform_context,
        path="approle-bootstrap",
        auth_type="approle",
        description="Bootstrap-only AppRole path",
    )
    ensure_secret_mount(
        platform_context,
        path="kv-apps",
        secret_type="kv",
        description="Application secrets",
        version=2,
    )
    ensure_secret_mount(
        platform_context,
        path="kv-shared",
        secret_type="kv",
        description="Shared platform secrets",
        version=2,
    )
    ensure_secret_mount(
        platform_context,
        path="pki-k8s",
        secret_type="pki",
        description="Kubernetes internal TLS PKI",
        max_lease_ttl=args.pki_k8s_max_ttl,
    )
    ensure_secret_mount(
        platform_context,
        path="pki-infra",
        secret_type="pki",
        description="Infrastructure TLS PKI",
        max_lease_ttl=args.pki_infra_max_ttl,
    )

    if args.oidc_config:
        apply_oidc_config(root_context, Path(args.oidc_config))
    if args.jwt_mounts:
        apply_jwt_mounts(platform_context, Path(args.jwt_mounts))

    maybe_issue_bootstrap_token(root_context, args)

    if args.run_smoke_secret_check:
        run_bao(platform_context, ["kv", "put", "-mount=kv-shared", "bootstrap/smoke", "value=ok"])
        run_bao(platform_context, ["kv", "get", "-mount=kv-shared", "-field=value", "bootstrap/smoke"])

    if args.revoke_root_token:
        run_bao(root_context, ["token", "revoke", "-self"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_seal = subparsers.add_parser("render-seal-env", help="Render /etc/openbao/openbao.env from local AWS env vars")
    render_seal.add_argument("--output", required=True)
    render_seal.add_argument("--kms-key-id", required=True)
    render_seal.add_argument("--aws-region", required=True)
    render_seal.add_argument("--address", default="https://127.0.0.1:8200")
    render_seal.add_argument("--ca-cert", default="/etc/openbao/tls/ca.pem")
    render_seal.set_defaults(func=command_render_seal_env)

    init_cluster = subparsers.add_parser("init-cluster", help="Initialize an auto-unseal OpenBao cluster and save the init payload")
    init_cluster.add_argument("--bao-bin", default="bao")
    init_cluster.add_argument("--address", default="https://127.0.0.1:8200")
    init_cluster.add_argument("--ca-cert", default="/etc/openbao/tls/ca.pem")
    init_cluster.add_argument("--key-shares", type=int, default=1)
    init_cluster.add_argument("--key-threshold", type=int, default=1)
    init_cluster.add_argument("--recovery-shares", type=int, default=5)
    init_cluster.add_argument("--recovery-threshold", type=int, default=3)
    init_cluster.add_argument("--output", required=True)
    init_cluster.set_defaults(func=command_init_cluster)

    apply_baseline = subparsers.add_parser("apply-baseline", help="Apply canonical namespaces, mounts, and policies")
    apply_baseline.add_argument("--bao-bin", default="bao")
    apply_baseline.add_argument("--address", default="https://127.0.0.1:8200")
    apply_baseline.add_argument("--ca-cert", default="/etc/openbao/tls/ca.pem")
    apply_baseline.add_argument("--token")
    apply_baseline.add_argument("--token-file")
    apply_baseline.add_argument("--platform-namespace", default="platform")
    apply_baseline.add_argument("--policy-dir", default=str(DEFAULT_POLICY_DIR))
    apply_baseline.add_argument("--oidc-config")
    apply_baseline.add_argument("--jwt-mounts")
    apply_baseline.add_argument("--pki-k8s-max-ttl", default="43800h")
    apply_baseline.add_argument("--pki-infra-max-ttl", default="43800h")
    apply_baseline.add_argument("--issue-bootstrap-token-output")
    apply_baseline.add_argument("--bootstrap-token-policy", default="root-human-operators-admin")
    apply_baseline.add_argument("--bootstrap-token-ttl", default="8h")
    apply_baseline.add_argument("--run-smoke-secret-check", action="store_true")
    apply_baseline.add_argument("--revoke-root-token", action="store_true")
    apply_baseline.set_defaults(func=command_apply_baseline)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
