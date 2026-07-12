from __future__ import annotations

import hashlib
import json
import runpy
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.remnawave.policy_compiler.compiler import (  # noqa: E402
    GeneratedDriftError,
    build_outputs,
    check_generated,
    generate,
)
from scripts.remnawave.policy_compiler.loader import PolicyLoadError, load_policy  # noqa: E402

POLICY_PATH = REPO_ROOT / "scripts" / "remnawave" / "policies" / "premium_smart_ru.yaml"
CLI_PATH = REPO_ROOT / "scripts" / "remnawave" / "policy_compiler" / "cli.py"

EXPECTED_SOURCE_GROUPS = (
    "private_networks",
    "direct_processes",
    "bittorrent_protocol",
    "torrent_processes",
    "torrent_sources",
    "ads_trackers",
    "tor",
    "quic_doq",
    "eu_exceptions",
    "ru_services",
    "broad_ru",
)
EXPECTED_RULE_STAGES = (
    "private_networks",
    "direct_processes",
    "bittorrent_protocol",
    "torrent_processes",
    "torrent_sources",
    "ads_trackers",
    "tor",
    "quic_doq",
    "eu_exceptions",
    "ru_services",
    "broad_ru",
    "final",
)
EXPECTED_RULE_IDS = (
    "direct_private",
    "direct_approved_processes",
    "block_bittorrent_protocol",
    "block_torrent_processes",
    "block_torrent_sources",
    "block_ads_trackers",
    "block_tor_best_effort",
    "block_quic_doq",
    "route_eu_exceptions",
    "route_ru_services",
    "route_broad_ru",
    "route_final_eu",
)
EXPECTED_RENDERER_COVERAGE = {
    "normalizedPolicy": "rendered",
    "mihomo": "rendered",
    "xrayClient": "rendered",
    "xrayServer": "rendered",
    "legacyHeader": "rendered",
}
EXPECTED_GENERATED_FILES = (
    "legacy-routing-header.json",
    "manifest.json",
    "mihomo.yaml",
    "policy.normalized.json",
    "policy.schema.json",
    "xray-client.json",
    "xray-server.json",
)


def _canonical_data() -> dict[str, Any]:
    data = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write_policy(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "premium_smart_ru.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _run_direct_cli(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, str, str]:
    original_sys_path = list(sys.path)
    monkeypatch.setattr(sys, "argv", [str(CLI_PATH), *argv])
    try:
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(CLI_PATH), run_name="__main__")
    finally:
        sys.path[:] = original_sys_path
    captured = capsys.readouterr()
    assert isinstance(exc_info.value.code, int)
    return exc_info.value.code, captured.out, captured.err


def test_canonical_policy_preserves_smart_ru_semantics() -> None:
    policy = load_policy(POLICY_PATH)

    assert policy.version == 1
    assert policy.product == "premium_smart_ru"
    assert policy.routes.model_dump(mode="python") == {
        "private": "direct",
        "default": "eu",
        "ru_services": "ru",
        "eu_exceptions": "eu",
    }
    assert tuple(policy.source_groups.model_dump(mode="python")) == EXPECTED_SOURCE_GROUPS
    assert [rule.stage for rule in policy.rules] == list(EXPECTED_RULE_STAGES)
    assert [rule.id for rule in policy.rules] == list(EXPECTED_RULE_IDS)
    assert [rule.action for rule in policy.rules] == [
        "direct",
        "direct",
        "block",
        "block",
        "block",
        "block",
        "block",
        "block",
        "eu",
        "ru",
        "ru",
        "eu",
    ]

    groups = policy.source_groups.model_dump(mode="python")
    assert all(groups[group] for group in EXPECTED_SOURCE_GROUPS)
    assert {source_id for source_ids in groups.values() for source_id in source_ids} == set(policy.sources)

    transport_matrix = {
        region: {
            location: tuple(transports)
            for location, transports in getattr(policy.transport_groups, region).members.items()
        }
        for region in ("eu", "ru")
    }
    assert transport_matrix == {
        "eu": {"de": ("raw", "xhttp"), "nl": ("raw", "xhttp")},
        "ru": {"moscow": ("raw", "xhttp"), "spb": ("raw", "xhttp")},
    }
    assert sum(len(transports) for members in transport_matrix.values() for transports in members.values()) == 8

    assert (policy.regions.eu.primary, policy.regions.eu.fallback) == ("de", "nl")
    assert (policy.regions.ru.primary, policy.regions.ru.fallback) == ("spb", "moscow")
    assert policy.transport_groups.eu.health.probe_url == "https://www.gstatic.com/generate_204"
    assert policy.transport_groups.eu.primary_transport == "xhttp"
    assert policy.transport_groups.eu.fallback_transport == "xhttp"
    assert policy.transport_groups.ru.primary_transport == "xhttp"
    assert policy.transport_groups.ru.fallback_transport == "xhttp"
    assert policy.transport_groups.ru.health.probe_url == "https://www.ozon.ru/"
    assert policy.transport_groups.eu.health.probe_url != policy.transport_groups.ru.health.probe_url
    assert policy.transport_groups.eu.health.expected_status == 204
    assert policy.transport_groups.ru.health.expected_status == 307
    assert policy.transport_groups.eu.health.constrain_probe_to_region is True
    assert policy.transport_groups.ru.health.constrain_probe_to_region is True
    assert policy.transport_groups.eu.health.transport_checks == "independent"
    assert policy.transport_groups.ru.health.transport_checks == "independent"

    for region, expected_event, expected_metric in (
        ("eu", "premium_smart_ru.eu.degraded", "premium_smart_ru_eu_degraded"),
        ("ru", "premium_smart_ru.ru.degraded", "premium_smart_ru_ru_degraded"),
    ):
        degraded = getattr(policy.transport_groups, region).degraded
        assert degraded.on_primary_unavailable == "use_fallback"
        assert degraded.on_fallback_unavailable == "use_primary_if_healthy"
        assert degraded.on_all_unavailable == "explicit_degraded"
        assert degraded.cross_region_fallback is False
        assert degraded.event == expected_event
        assert degraded.metric == expected_metric

    tor_rule = next(rule for rule in policy.rules if rule.stage == "tor")
    assert policy.blocks.tor == "best_effort"
    assert tor_rule.assurance == "best_effort"
    assert all(rule.assurance == "enforced" for rule in policy.rules if rule.stage != "tor")


def test_loader_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    policy_path = tmp_path / "duplicate-key.yaml"
    policy_path.write_text("version: 1\nversion: 1\n", encoding="utf-8")

    with pytest.raises(PolicyLoadError, match="duplicate YAML key 'version' at line 2"):
        load_policy(policy_path)


def test_loader_rejects_duplicate_inline_entries(tmp_path: Path) -> None:
    data = _canonical_data()
    data["sources"]["tor-inline"]["entries"].append(" domain-suffix,onion ")

    with pytest.raises(PolicyLoadError, match="source contains duplicate entries: domain-suffix,onion"):
        load_policy(_write_policy(tmp_path, data))


def test_loader_rejects_duplicated_critical_source_membership(tmp_path: Path) -> None:
    data = _canonical_data()
    data["source_groups"]["ru_services"].append("ru-eu-exceptions")

    with pytest.raises(PolicyLoadError, match="critical source lists cannot be duplicated across groups"):
        load_policy(_write_policy(tmp_path, data))


def test_loader_rejects_semantically_duplicate_critical_entries(tmp_path: Path) -> None:
    data = _canonical_data()
    data["sources"]["ru-eu-exceptions"]["entries"].append("DOMAIN-SUFFIX,1337x.to")

    with pytest.raises(PolicyLoadError, match="duplicated across sources torrent-domains-inline and ru-eu-exceptions"):
        load_policy(_write_policy(tmp_path, data))


def test_loader_rejects_invalid_rule_ordering(tmp_path: Path) -> None:
    data = _canonical_data()
    data["rules"][0], data["rules"][1] = data["rules"][1], data["rules"][0]

    with pytest.raises(PolicyLoadError, match="rule stages must preserve canonical first-match order"):
        load_policy(_write_policy(tmp_path, data))


def test_loader_rejects_final_rule_with_source_matcher(tmp_path: Path) -> None:
    data = _canonical_data()
    data["rules"][-1]["source_group"] = "broad_ru"

    with pytest.raises(PolicyLoadError, match="final rule must be an effective tcp,udp matcher"):
        load_policy(_write_policy(tmp_path, data))


def test_generation_is_deterministic_and_second_generation_is_unchanged(tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"

    first = generate(POLICY_PATH, output_dir)
    first_bytes = {path.name: path.read_bytes() for path in first.changed}
    first_mtimes = {path.name: path.stat().st_mtime_ns for path in first.changed}
    second = generate(POLICY_PATH, output_dir)

    assert first.output_dir == output_dir
    assert tuple(sorted(path.name for path in first.changed)) == EXPECTED_GENERATED_FILES
    assert second.output_dir == output_dir
    assert second.changed == ()
    assert second.policy_sha256 == first.policy_sha256
    assert {path.name: path.read_bytes() for path in output_dir.iterdir()} == first_bytes
    assert {path.name: path.stat().st_mtime_ns for path in output_dir.iterdir()} == first_mtimes


def test_check_generated_reports_drift_without_mutating_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    generate(POLICY_PATH, output_dir)
    drifted_path = output_dir / "policy.normalized.json"
    drifted_path.write_text('{"drifted": true}\n', encoding="utf-8")
    before_bytes = {path.name: path.read_bytes() for path in output_dir.iterdir()}
    before_mtimes = {path.name: path.stat().st_mtime_ns for path in output_dir.iterdir()}

    with pytest.raises(GeneratedDriftError) as exc_info:
        check_generated(POLICY_PATH, output_dir)

    assert exc_info.value.paths == (drifted_path,)
    assert {path.name: path.read_bytes() for path in output_dir.iterdir()} == before_bytes
    assert {path.name: path.stat().st_mtime_ns for path in output_dir.iterdir()} == before_mtimes


def test_manifest_records_counts_checksums_source_inventory_and_renderer_gaps() -> None:
    policy, outputs = build_outputs(POLICY_PATH)
    manifest = json.loads(outputs["manifest.json"])

    assert manifest["compiler"] == "cybervpn.remnawave.policy_compiler.v1"
    assert manifest["schemaVersion"] == 1
    assert manifest["product"] == "premium_smart_ru"
    assert manifest["source"] == {
        "path": "scripts/remnawave/policies/premium_smart_ru.yaml",
        "sha256": _sha256(POLICY_PATH.read_bytes()),
    }
    assert manifest["counts"] == {
        "rules": 12,
        "sources": 41,
        "remoteSources": 29,
        "pinnedRemoteSources": 29,
        "mutableRemoteSources": 0,
        "criticalSourceReferences": 41,
        "criticalInlineEntries": 221,
        "transportVariants": 8,
    }
    assert manifest["artifacts"] == {
        artifact_name: {
            "bytes": len(outputs[artifact_name]),
            "sha256": _sha256(outputs[artifact_name]),
        }
        for artifact_name in EXPECTED_GENERATED_FILES
        if artifact_name != "manifest.json"
    }

    inventory = manifest["sourceIntegrity"]["inventory"]
    assert set(inventory) == set(policy.sources)
    assert manifest["sourceIntegrity"]["pinned"] == sorted(
        source_id for source_id, source in policy.sources.items() if source.integrity is not None
    )
    assert manifest["sourceIntegrity"]["mutable"] == []
    for source_id, source in policy.sources.items():
        item = inventory[source_id]
        assert item["entryCount"] == len(source.entries)
        assert len(item["descriptorSha256"]) == 64
        if source.integrity is None:
            assert item["revision"] == "local-policy-v1"
            assert item["pinned"] is True
            assert len(item["contentSha256"]) == 64
        else:
            assert item["revision"] == source.integrity.revision
            assert item["pinned"] is source.integrity.pinned
            assert item["contentSha256"] == source.integrity.sha256

    renderer_coverage = manifest["rendererCoverage"]
    assert {name: item["status"] for name, item in renderer_coverage.items()} == EXPECTED_RENDERER_COVERAGE
    assert renderer_coverage["normalizedPolicy"]["risk"] == "none"
    for renderer in ("mihomo", "xrayClient", "xrayServer", "legacyHeader"):
        assert renderer_coverage[renderer]["status"] == "rendered"
        assert renderer_coverage[renderer]["artifact"] in manifest["artifacts"]
        assert renderer_coverage[renderer]["reason"]
        assert renderer_coverage[renderer]["risk"] == "none"


def test_direct_cli_generate_and_check_exit_behavior(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "generated"

    generate_code, generate_stdout, generate_stderr = _run_direct_cli(
        ["generate", "--policy", str(POLICY_PATH), "--output-dir", str(output_dir)],
        capsys,
        monkeypatch,
    )
    generated = json.loads(generate_stdout)

    assert generate_code == 0
    assert generate_stderr == ""
    assert generated["status"] == "generated"
    assert tuple(sorted(Path(path).name for path in generated["changed"])) == (EXPECTED_GENERATED_FILES)
    assert generated["outputDir"] == str(output_dir)
    assert len(generated["policySha256"]) == 64

    check_code, check_stdout, check_stderr = _run_direct_cli(
        ["check", "--policy", str(POLICY_PATH), "--output-dir", str(output_dir)],
        capsys,
        monkeypatch,
    )
    checked = json.loads(check_stdout)

    assert check_code == 0
    assert check_stderr == ""
    assert checked == {
        "status": "clean",
        "outputDir": str(output_dir),
        "changed": [],
        "policySha256": generated["policySha256"],
    }

    (output_dir / "manifest.json").write_text('{"drifted": true}\n', encoding="utf-8")

    drift_code, drift_stdout, drift_stderr = _run_direct_cli(
        ["check", "--policy", str(POLICY_PATH), "--output-dir", str(output_dir)],
        capsys,
        monkeypatch,
    )

    assert drift_code == 1
    assert drift_stdout == ""
    assert "generated policy artifacts are missing or stale" in drift_stderr
    assert str(output_dir / "manifest.json") in drift_stderr
