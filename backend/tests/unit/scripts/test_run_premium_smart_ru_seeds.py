from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts/remnawave/run-premium-smart-ru-seeds.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_premium_smart_ru_seeds", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage_contract_is_private_complete_and_bound_to_out_of_band_hashes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    root = tmp_path / "private-root"
    root.mkdir(mode=0o700)
    root.chmod(0o700)

    contract = module._stage_artifacts(root)
    try:
        manifest_path = contract.directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        variables = contract.psql_variables()

        assert contract.directory.parent == root.resolve()
        assert manifest["schemaVersion"] == 1
        assert manifest["product"] == "premium_smart_ru"
        assert set(manifest["artifacts"]) == {
            "mihomo.yaml",
            "incy-xray.json",
            "legacy-routing-header.json",
        }
        assert variables["cybervpn_premium_smart_ru_stage_manifest_sha256"] == _sha256(manifest_path)
        for key, name in module.STAGED_NAMES.items():
            artifact = contract.directory / name
            assert variables[f"cybervpn_premium_smart_ru_{key}_sha256"] == _sha256(artifact)
            assert manifest["artifacts"][name]["sha256"] == _sha256(artifact)
            if os.name != "nt":
                assert artifact.stat().st_mode & 0o777 == 0o600
        if os.name != "nt":
            assert contract.directory.stat().st_mode & 0o777 == 0o700
    finally:
        module._remove_stage(contract)

    assert not contract.directory.exists()


def test_adjacent_artifact_and_manifest_tampering_cannot_change_trusted_values(
    tmp_path: Path,
) -> None:
    module = _load_module()
    root = tmp_path / "private-root"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    contract = module._stage_artifacts(root)
    trusted = contract.psql_variables()
    try:
        artifact_path = contract.directory / "mihomo.yaml"
        manifest_path = contract.directory / "manifest.json"
        artifact_path.write_bytes(artifact_path.read_bytes() + b"\n# tampered\n")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["mihomo.yaml"]["sha256"] = _sha256(artifact_path)
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        assert _sha256(artifact_path) != trusted["cybervpn_premium_smart_ru_mihomo_sha256"]
        assert _sha256(manifest_path) != trusted["cybervpn_premium_smart_ru_stage_manifest_sha256"]
    finally:
        module._remove_stage(contract)


def test_stage_regenerates_incy_instead_of_trusting_mutable_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    tampered = json.loads(module.INCY_SOURCE.read_text(encoding="utf-8"))
    tampered["routing"]["rules"][0]["outboundTag"] = "block"
    tampered_path = tmp_path / "tampered-incy.json"
    tampered_path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(module, "INCY_SOURCE", tampered_path)
    root = tmp_path / "private-root"
    root.mkdir(mode=0o700)

    contract = module._stage_artifacts(root)
    try:
        staged = (contract.directory / "incy-xray.json").read_bytes()
        generator = module.runpy.run_path(str(module.INCY_GENERATOR_SOURCE))
        expected = (json.dumps(generator["build_template"](), ensure_ascii=False, indent=2) + "\n").encode()
        assert staged == expected
        assert staged != tampered_path.read_bytes()
    finally:
        module._remove_stage(contract)


def test_psql_command_passes_digests_directly_and_requires_explicit_sql_files(
    tmp_path: Path,
) -> None:
    module = _load_module()
    root = tmp_path / "private-root"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    contract = module._stage_artifacts(root)
    try:
        command = module._psql_command(contract, psql="psql", selection="both")
    finally:
        module._remove_stage(contract)

    assert command[:4] == ["psql", "-X", "-v", "ON_ERROR_STOP=1"]
    for name, value in contract.psql_variables().items():
        assert f"{name}={value}" in command
    assert command[-4:] == [
        "-f",
        str(module.MAIN_SEED),
        "-f",
        str(module.INCY_SEED),
    ]
    assert all("password" not in part.casefold() for part in command)


def test_docker_transport_stages_private_files_runs_psql_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    root = tmp_path / "private-root"
    root.mkdir(mode=0o700)
    contract = module._stage_artifacts(root)
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> None:
        calls.append((list(command), dict(kwargs)))

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    try:
        container_directory = module._copy_stage_to_container(
            contract,
            docker="docker",
            container="remnawave-db",
            container_stage_root="/var/lib/postgresql/cybervpn-seed-stage",
            owner="postgres",
        )
        assert container_directory.startswith("/var/lib/postgresql/cybervpn-seed-stage/premium-smart-ru-")

        module._run_container_psql(
            contract,
            docker="docker",
            container="remnawave-db",
            container_stage_directory=container_directory,
            selection="both",
            database_user="remnawave",
            database_name="remnawave",
        )
        module._remove_container_stage(
            docker="docker",
            container="remnawave-db",
            container_stage_root="/var/lib/postgresql/cybervpn-seed-stage",
            directory=container_directory,
        )
    finally:
        module._remove_stage(contract)

    commands = [command for command, _ in calls]
    assert commands[0][:4] == ["docker", "exec", "remnawave-db", "install"]
    assert sum(command[:2] == ["docker", "cp"] for command in commands) == 4
    psql_calls = [
        (command, kwargs)
        for command, kwargs in calls
        if command[:6] == ["docker", "exec", "-i", "remnawave-db", "psql", "-X"]
    ]
    assert len(psql_calls) == 2
    for command, kwargs in psql_calls:
        assert command[:4] == ["docker", "exec", "-i", "remnawave-db"]
        assert ["-U", "remnawave"] == command[command.index("-U") : command.index("-U") + 2]
        assert ["-d", "remnawave"] == command[command.index("-d") : command.index("-d") + 2]
        assert any(value == f"cybervpn_premium_smart_ru_stage_dir={container_directory}" for value in command)
        assert isinstance(kwargs.get("input"), bytes)
        assert kwargs.get("check") is True
    assert commands[-1] == [
        "docker",
        "exec",
        "remnawave-db",
        "rm",
        "-rf",
        "--",
        container_directory,
    ]


def test_container_stage_root_and_cleanup_are_path_confined() -> None:
    module = _load_module()
    for unsafe in ("relative", "/", "/var/lib/../tmp"):
        with pytest.raises(RuntimeError, match="safe absolute path"):
            module._validate_container_stage_root(unsafe)

    with pytest.raises(RuntimeError, match="outside the trusted root"):
        module._remove_container_stage(
            docker="docker",
            container="remnawave-db",
            container_stage_root="/var/lib/postgresql/cybervpn-seed-stage",
            directory="/var/lib/postgresql/not-owned/premium-smart-ru-forged",
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership and mode contract")
def test_stage_contract_refuses_world_writable_or_symlink_root(tmp_path: Path) -> None:
    module = _load_module()
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o777)
    unsafe.chmod(0o777)
    with pytest.raises(RuntimeError, match="group/world-writable"):
        module._stage_artifacts(unsafe)

    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    symlink = tmp_path / "stage-link"
    symlink.symlink_to(private, target_is_directory=True)
    with pytest.raises(RuntimeError, match="must not be a symlink"):
        module._stage_artifacts(symlink)
