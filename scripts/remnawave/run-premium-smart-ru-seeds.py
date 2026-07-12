#!/usr/bin/env python3
"""Stage trusted Premium Smart RU artifacts and optionally run both SQL seeds.

Run this on the PostgreSQL host/container so the server can read the private
stage directory. Database credentials remain in the standard libpq environment
or .pgpass; trusted artifact digests are passed directly to psql variables.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import runpy
import shutil
import stat
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = REPO_ROOT / "scripts/remnawave/generated/premium_smart_ru"
MIHOMO_SOURCE = GENERATED_DIR / "mihomo.yaml"
INCY_SOURCE = (
    REPO_ROOT / "scripts/remnawave/templates/cybervpn-premium-smart-ru-incy-xray.json"
)
INCY_CANARY_SOURCE = REPO_ROOT / (
    "scripts/remnawave/templates/"
    "cybervpn-premium-smart-ru-incy-xray-failover-canary.json"
)
LEGACY_HEADER_SOURCE = GENERATED_DIR / "legacy-routing-header.json"
COMPILER_MANIFEST_SOURCE = GENERATED_DIR / "manifest.json"
INCY_GENERATOR_SOURCE = (
    REPO_ROOT / "scripts/remnawave/generate-premium-smart-ru-incy-xray.py"
)
MAIN_SEED = REPO_ROOT / "scripts/remnawave/seed-cybervpn-premium-smart-ru.sql"
INCY_SEED = REPO_ROOT / "scripts/remnawave/seed-cybervpn-premium-smart-ru-incy-xray.sql"
STAGED_NAMES = {
    "mihomo": "mihomo.yaml",
    "incy": "incy-xray.json",
    "incy_canary": "incy-xray-failover-canary.json",
    "legacy_header": "legacy-routing-header.json",
}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def _load_json(content: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _validate_mihomo(content: bytes) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Mihomo artifact must be valid UTF-8") from exc
    required = (
        "MATCH,World / EU",
        "name: Torrents",
        "name: RU Sites",
        "name: World / EU",
        "RULE-SET,smtp-abuse,REJECT",
    )
    if any(marker not in text for marker in required) or "MATCH,DIRECT" in text:
        raise RuntimeError("Mihomo artifact semantics are invalid")


def _validate_incy(content: bytes, *, automatic_failover: bool = False) -> None:
    artifact = _load_json(content, "INCY artifact")
    remnawave = artifact.get("remnawave")
    routing = artifact.get("routing")
    if not isinstance(remnawave, dict) or not isinstance(routing, dict):
        raise RuntimeError("INCY artifact lacks Remnawave routing metadata")
    route_policy = remnawave.get("routePolicy")
    inject_hosts = remnawave.get("injectHosts")
    if (
        not isinstance(route_policy, dict)
        or route_policy.get("schemaVersion") != 1
        or route_policy.get("product") != "premium_smart_ru"
        or not isinstance(inject_hosts, list)
        or len(inject_hosts) != 4
    ):
        raise RuntimeError("INCY artifact has an invalid product contract")
    if not isinstance(artifact.get("inbounds"), list) or len(artifact["inbounds"]) != 2:
        raise RuntimeError("INCY artifact must define exactly two local inbounds")
    if not isinstance(routing.get("rules"), list) or not routing["rules"]:
        raise RuntimeError("INCY artifact contains no routing rules")
    if not automatic_failover and (
        "balancers" in routing
        or "observatory" in artifact
        or "burstObservatory" in artifact
    ):
        raise RuntimeError(
            "INCY artifact must not enable unstable Xray observatory failover"
        )
    if automatic_failover:
        balancers = routing.get("balancers")
        expected_balancers = [
            {
                "tag": "eu-primary",
                "selector": ["eu-de-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "eu-fallback-loop",
            },
            {
                "tag": "eu-fallback",
                "selector": ["eu-nl-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "block",
            },
            {
                "tag": "ru-primary",
                "selector": ["ru-spb-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "ru-fallback-loop",
            },
            {
                "tag": "ru-fallback",
                "selector": ["ru-msk-2"],
                "strategy": {"type": "leastPing"},
                "fallbackTag": "block",
            },
        ]
        regional_health = route_policy.get("regionalHealth")
        ru_health = (
            regional_health.get("ru") if isinstance(regional_health, dict) else None
        )
        ru_probe = ru_health.get("probe") if isinstance(ru_health, dict) else None
        expected_probe_url = ru_probe.get("url") if isinstance(ru_probe, dict) else None
        expected_observatory = {
            "subjectSelector": ["eu-de-2", "eu-nl-2", "ru-spb-2", "ru-msk-2"],
            "probeUrl": expected_probe_url,
            "probeInterval": "10s",
            "enableConcurrency": True,
        }
        if (
            route_policy.get("rendererMode") != "automatic-failover-canary"
            or balancers != expected_balancers
            or not isinstance(expected_probe_url, str)
            or artifact.get("observatory") != expected_observatory
            or artifact.get("burstObservatory") is not None
        ):
            raise RuntimeError(
                "INCY canary artifact lacks regional failover health checks"
            )
    routes_by_tag = {
        rule.get("ruleTag"): rule
        for rule in routing["rules"]
        if isinstance(rule, dict) and isinstance(rule.get("ruleTag"), str)
    }
    route_key = "balancerTag" if automatic_failover else "outboundTag"
    expected_eu = "eu-primary" if automatic_failover else "eu-de-2"
    expected_ru = "ru-primary" if automatic_failover else "ru-spb-2"
    if routes_by_tag.get("route_final_eu", {}).get(route_key) != expected_eu:
        raise RuntimeError(
            "INCY artifact must route default traffic to the DE-first path"
        )
    if routes_by_tag.get("route_ru_services", {}).get(route_key) != expected_ru:
        raise RuntimeError("INCY artifact must route RU services to the SPB-first path")
    if automatic_failover:
        expected_loop_rules = [
            {
                "type": "field",
                "ruleTag": "route_eu_failover_loop",
                "inboundTag": ["eu-fallback-in"],
                "network": "tcp,udp",
                "balancerTag": "eu-fallback",
            },
            {
                "type": "field",
                "ruleTag": "route_ru_failover_loop",
                "inboundTag": ["ru-fallback-in"],
                "network": "tcp,udp",
                "balancerTag": "ru-fallback",
            },
        ]
        if (
            routing["rules"][:2] != expected_loop_rules
            or routes_by_tag.get("route_eu_failover_loop") != expected_loop_rules[0]
            or routes_by_tag.get("route_ru_failover_loop") != expected_loop_rules[1]
        ):
            raise RuntimeError(
                "INCY canary failover must remain regional and fail closed"
            )
    smtp_rule = routes_by_tag.get("block_smtp_abuse", {})
    if smtp_rule != {
        "type": "field",
        "ruleTag": "block_smtp_abuse",
        "network": "tcp",
        "port": "25,465,587",
        "outboundTag": "block",
    }:
        raise RuntimeError("INCY artifact must block SMTP abuse ports")


def _validate_legacy_header(content: bytes) -> None:
    artifact = _load_json(content, "legacy routing header")
    value = artifact.get("value")
    decoded = artifact.get("decoded")
    if (
        artifact.get("schemaVersion") != 1
        or artifact.get("product") != "premium_smart_ru"
        or artifact.get("consumer") != "remnawave-legacy-routing-header"
        or artifact.get("encoding") != "base64-json"
        or not isinstance(value, str)
        or not isinstance(decoded, dict)
    ):
        raise RuntimeError("Legacy routing header contract is invalid")
    try:
        encoded_payload = json.loads(base64.b64decode(value, validate=True))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Legacy routing header value is not base64 JSON") from exc
    if encoded_payload != decoded:
        raise RuntimeError("Legacy routing header decoded payload does not match value")
    required_values = {
        "Name": "CyberVPN Premium Smart RU",
        "GlobalProxy": "true",
        "DomainStrategy": "AsIs",
        "FakeDNS": "false",
        "RemoteDNSType": "DoH",
        "RemoteDNSDomain": "https://cloudflare-dns.com/dns-query",
        "RemoteDNSIP": "1.1.1.1",
    }
    if any(decoded.get(key) != expected for key, expected in required_values.items()):
        raise RuntimeError("Legacy routing header semantics are invalid")
    block_sites = decoded.get("BlockSites")
    direct_ip = decoded.get("DirectIp")
    if (
        not isinstance(block_sites, list)
        or "domain:rutracker.org" not in block_sites
        or "geosite:category-ads-all" not in block_sites
        or not isinstance(direct_ip, list)
        or "10.0.0.0/8" not in direct_ip
    ):
        raise RuntimeError("Legacy routing header lists are invalid")


def _load_and_validate_sources() -> dict[str, bytes]:
    try:
        artifacts = {
            "mihomo": MIHOMO_SOURCE.read_bytes(),
            "legacy_header": LEGACY_HEADER_SOURCE.read_bytes(),
        }
        compiler_manifest_content = COMPILER_MANIFEST_SOURCE.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"Cannot read Premium Smart RU artifact: {exc}") from exc

    try:
        generator = runpy.run_path(str(INCY_GENERATOR_SOURCE))
        expected_incy = generator["build_template"]()
        expected_incy_canary = generator["build_template"](automatic_failover=True)
    except (KeyError, OSError, RuntimeError) as exc:
        raise RuntimeError(
            "Cannot regenerate INCY artifact from the canonical compiler output"
        ) from exc
    expected_incy_content = (
        json.dumps(expected_incy, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    artifacts["incy"] = expected_incy_content
    artifacts["incy_canary"] = (
        json.dumps(expected_incy_canary, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    _validate_mihomo(artifacts["mihomo"])
    _validate_incy(artifacts["incy"])
    _validate_incy(artifacts["incy_canary"], automatic_failover=True)
    _validate_legacy_header(artifacts["legacy_header"])
    compiler_manifest = _load_json(compiler_manifest_content, "compiler manifest")
    if (
        compiler_manifest.get("schemaVersion") != 1
        or compiler_manifest.get("product") != "premium_smart_ru"
    ):
        raise RuntimeError("Compiler manifest contract is invalid")
    declared = compiler_manifest.get("artifacts")
    if not isinstance(declared, dict):
        raise RuntimeError("Compiler manifest artifacts are invalid")
    for key in ("mihomo", "legacy_header"):
        name = STAGED_NAMES[key]
        metadata = declared.get(name)
        content = artifacts[key]
        if not isinstance(metadata, dict) or metadata != {
            "bytes": len(content),
            "sha256": _sha256(content),
        }:
            raise RuntimeError(f"Compiler manifest does not authenticate {name}")
    artifacts["compiler_manifest"] = compiler_manifest_content
    return artifacts


def _validate_private_stage_root(path: Path) -> Path:
    if path.is_symlink():
        raise RuntimeError("Stage root must not be a symlink")
    try:
        resolved = path.expanduser().resolve(strict=True)
        root_stat = resolved.lstat()
    except OSError as exc:
        raise RuntimeError(f"Cannot access stage root: {exc}") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise RuntimeError("Stage root must be a directory")
    if os.name != "nt":
        if root_stat.st_uid != os.geteuid():
            raise RuntimeError("Stage root must be owned by the operator")
        if root_stat.st_mode & 0o022:
            raise RuntimeError("Stage root must not be group/world-writable")
    return resolved


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


@dataclass(frozen=True)
class StageContract:
    root: Path
    directory: Path
    manifest_sha256: str
    artifact_sha256: dict[str, str]

    def psql_variables(self, *, stage_directory: str | None = None) -> dict[str, str]:
        return {
            "cybervpn_premium_smart_ru_stage_dir": stage_directory
            or self.directory.as_posix(),
            "cybervpn_premium_smart_ru_stage_manifest_sha256": self.manifest_sha256,
            "cybervpn_premium_smart_ru_mihomo_sha256": self.artifact_sha256["mihomo"],
            "cybervpn_premium_smart_ru_incy_sha256": self.artifact_sha256["incy"],
            "cybervpn_premium_smart_ru_incy_canary_sha256": self.artifact_sha256[
                "incy_canary"
            ],
            "cybervpn_premium_smart_ru_legacy_header_sha256": self.artifact_sha256[
                "legacy_header"
            ],
        }


def _stage_artifacts(stage_root: Path) -> StageContract:
    root = _validate_private_stage_root(stage_root)
    artifacts = _load_and_validate_sources()
    directory = Path(tempfile.mkdtemp(prefix="premium-smart-ru-", dir=root)).resolve(
        strict=True
    )
    os.chmod(directory, 0o700)
    try:
        artifact_sha256 = {key: _sha256(artifacts[key]) for key in STAGED_NAMES}
        for key, name in STAGED_NAMES.items():
            _atomic_write(directory / name, artifacts[key])
        manifest = {
            "schemaVersion": 1,
            "product": "premium_smart_ru",
            "sourceCompilerManifestSha256": _sha256(artifacts["compiler_manifest"]),
            "artifacts": {
                STAGED_NAMES[key]: {
                    "bytes": len(artifacts[key]),
                    "sha256": artifact_sha256[key],
                }
                for key in STAGED_NAMES
            },
        }
        manifest_content = _canonical_json(manifest)
        _atomic_write(directory / "manifest.json", manifest_content)
        _fsync_directory(directory)
        _fsync_directory(root)
        return StageContract(
            root=root,
            directory=directory,
            manifest_sha256=_sha256(manifest_content),
            artifact_sha256=artifact_sha256,
        )
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def _remove_stage(contract: StageContract) -> None:
    if contract.directory.parent != contract.root:
        raise RuntimeError("Refusing to remove stage outside the trusted root")
    shutil.rmtree(contract.directory)
    _fsync_directory(contract.root)


def _seed_paths(selection: str) -> list[Path]:
    if selection == "main":
        return [MAIN_SEED]
    if selection == "incy":
        return [INCY_SEED]
    return [MAIN_SEED, INCY_SEED]


def _psql_command(contract: StageContract, *, psql: str, selection: str) -> list[str]:
    command = [psql, "-X", "-v", "ON_ERROR_STOP=1"]
    for name, value in contract.psql_variables().items():
        command.extend(["-v", f"{name}={value}"])
    for seed in _seed_paths(selection):
        command.extend(["-f", str(seed)])
    return command


def _validate_container_stage_root(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or path == PurePosixPath("/"):
        raise RuntimeError("Container stage root must be a safe absolute path")
    return path


def _docker_command(docker: str, container: str, *command: str) -> list[str]:
    return [docker, "exec", container, *command]


def _copy_stage_to_container(
    contract: StageContract,
    *,
    docker: str,
    container: str,
    container_stage_root: str,
    owner: str,
) -> str:
    root = _validate_container_stage_root(container_stage_root)
    directory = root / f"premium-smart-ru-{uuid.uuid4().hex}"
    if not owner or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in owner
    ):
        raise RuntimeError("Container stage owner is invalid")

    subprocess.run(
        _docker_command(
            docker,
            container,
            "install",
            "-d",
            "-m",
            "0700",
            "-o",
            owner,
            "-g",
            owner,
            str(root),
            str(directory),
        ),
        check=True,
    )
    try:
        for source in sorted(contract.directory.iterdir(), key=lambda item: item.name):
            if not source.is_file() or source.is_symlink():
                raise RuntimeError(f"Unexpected staged artifact: {source.name}")
            destination = f"{container}:{directory}/{source.name}"
            subprocess.run([docker, "cp", str(source), destination], check=True)
            subprocess.run(
                _docker_command(
                    docker,
                    container,
                    "chown",
                    f"{owner}:{owner}",
                    f"{directory}/{source.name}",
                ),
                check=True,
            )
            subprocess.run(
                _docker_command(
                    docker,
                    container,
                    "chmod",
                    "0600",
                    f"{directory}/{source.name}",
                ),
                check=True,
            )
        return str(directory)
    except BaseException:
        subprocess.run(
            _docker_command(docker, container, "rm", "-rf", "--", str(directory)),
            check=False,
        )
        raise


def _remove_container_stage(
    *,
    docker: str,
    container: str,
    container_stage_root: str,
    directory: str,
) -> None:
    root = _validate_container_stage_root(container_stage_root)
    target = PurePosixPath(directory)
    if target.parent != root or not target.name.startswith("premium-smart-ru-"):
        raise RuntimeError(
            "Refusing to remove container stage outside the trusted root"
        )
    subprocess.run(
        _docker_command(docker, container, "rm", "-rf", "--", str(target)),
        check=True,
    )


def _run_container_psql(
    contract: StageContract,
    *,
    docker: str,
    container: str,
    container_stage_directory: str,
    selection: str,
    database_user: str | None,
    database_name: str | None,
) -> None:
    variables = contract.psql_variables(stage_directory=container_stage_directory)
    # docker exec does not attach stdin unless -i is set. Without it psql sees
    # EOF, returns success, and none of the validated SQL is actually applied.
    base = [docker, "exec", "-i", container, "psql", "-X", "-v", "ON_ERROR_STOP=1"]
    if database_user:
        base.extend(["-U", database_user])
    if database_name:
        base.extend(["-d", database_name])
    for name, value in variables.items():
        base.extend(["-v", f"{name}={value}"])
    for seed in _seed_paths(selection):
        subprocess.run(base, input=seed.read_bytes(), check=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage-root",
        required=True,
        type=Path,
        help="Existing operator-owned directory without group/world write access",
    )
    parser.add_argument("--seed", choices=("main", "incy", "both"), default="both")
    parser.add_argument("--psql", default="psql")
    parser.add_argument(
        "--docker-container",
        help="Execute psql inside this PostgreSQL container and stage artifacts there",
    )
    parser.add_argument("--docker-binary", default="docker")
    parser.add_argument(
        "--container-stage-root",
        default="/var/lib/postgresql/cybervpn-seed-stage",
    )
    parser.add_argument("--container-stage-owner", default="postgres")
    parser.add_argument("--database-user")
    parser.add_argument("--database-name")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run psql; without this flag only stage and validate artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    contract = _stage_artifacts(args.stage_root)
    try:
        report = {
            "mode": "execute" if args.execute else "dry-run",
            "product": "premium_smart_ru",
            "seed": args.seed,
            "manifestSha256": contract.manifest_sha256,
            "artifactSha256": contract.artifact_sha256,
        }
        print(json.dumps(report, sort_keys=True))
        if args.execute:
            if args.docker_container:
                container_directory = _copy_stage_to_container(
                    contract,
                    docker=args.docker_binary,
                    container=args.docker_container,
                    container_stage_root=args.container_stage_root,
                    owner=args.container_stage_owner,
                )
                try:
                    _run_container_psql(
                        contract,
                        docker=args.docker_binary,
                        container=args.docker_container,
                        container_stage_directory=container_directory,
                        selection=args.seed,
                        database_user=args.database_user,
                        database_name=args.database_name,
                    )
                finally:
                    _remove_container_stage(
                        docker=args.docker_binary,
                        container=args.docker_container,
                        container_stage_root=args.container_stage_root,
                        directory=container_directory,
                    )
            else:
                subprocess.run(
                    _psql_command(contract, psql=args.psql, selection=args.seed),
                    check=True,
                )
    finally:
        _remove_stage(contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
