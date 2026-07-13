from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.services.vpn_product_readiness import VpnProductReadinessError
from src.application.vpn_testing.suite_loader import load_default_route_registries
from src.application.vpn_testing.task2_probe_plan import (
    TASK2_ANTIFILTER_CATEGORIES,
    TASK2_ARTIFACT_CATEGORY_NAMES,
    build_task2_route_probe_specs,
)
from src.config.settings import settings


def _route_entries() -> list[SimpleNamespace]:
    registry = next(
        item for item in load_default_route_registries() if item["registry_key"] == "premium_spb_de_exceptions_v1"
    )
    return [
        SimpleNamespace(route_key=item["route_key"], metadata_json=dict(item["metadata"]))
        for item in registry["routes"]
    ]


def _write_store(
    root: Path,
    *,
    include_unmatched: bool = False,
    shared_category_network: bool = False,
) -> tuple[str, str]:
    version = "0" * 64
    version_dir = root / "versions" / version
    category_dir = version_dir / "categories"
    union_dir = version_dir / "union"
    category_dir.mkdir(parents=True)
    union_dir.mkdir()

    artifacts: dict[str, str] = {}
    union_lines: list[str] = []
    for index, category in enumerate(TASK2_ANTIFILTER_CATEGORIES):
        line = "8.8.8.0/24" if shared_category_network else f"8.8.{index}.0/24"
        raw = f"{line}\n".encode("ascii")
        artifact_category = TASK2_ARTIFACT_CATEGORY_NAMES.get(category, category)
        relative = f"categories/{artifact_category}.ipv4.cidr"
        (version_dir / relative).write_bytes(raw)
        artifacts[relative] = hashlib.sha256(raw).hexdigest()
        union_lines.append(line)
    if include_unmatched:
        union_lines.append("1.1.1.1/32")
    union_raw = ("\n".join(union_lines) + "\n").encode("ascii")
    (union_dir / "ipv4.cidr").write_bytes(union_raw)
    artifacts["union/ipv4.cidr"] = hashlib.sha256(union_raw).hexdigest()

    manifest = {
        "schemaVersion": 1,
        "product": "premium_spb_de_exceptions",
        "version": version,
        "artifacts": artifacts,
    }
    manifest_raw = json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    (version_dir / "manifest.json").write_bytes(manifest_raw)
    return version, hashlib.sha256(manifest_raw).hexdigest()


def _configure_store(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    include_unmatched: bool = False,
    shared_category_network: bool = False,
) -> None:
    version, manifest_sha256 = _write_store(
        root,
        include_unmatched=include_unmatched,
        shared_category_network=shared_category_network,
    )
    pointer = json.dumps(
        {"version": version, "manifestSha256": manifest_sha256},
        separators=(",", ":"),
        sort_keys=True,
    )
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", pointer)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", pointer)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_manifest", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_store_path", str(root))


def test_build_task2_route_probe_specs_covers_categories_and_transport_network_matrix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_store(monkeypatch, tmp_path / "readiness")

    specs = build_task2_route_probe_specs(_route_entries())

    assert len(specs) == 21
    assert len({item.route_key for item in specs}) == 21
    category_specs = [item for item in specs if item.category and item.route_key.startswith("antifilter-")]
    assert len(category_specs) == 13
    assert all(item.transport == "raw" and item.probe_network == "tcp" for item in category_specs)
    assert all(item.membership == "member" for item in category_specs)
    assert len({(item.probe_network, item.target_ip, item.target_port) for item in specs}) == len(specs)
    matrix = {
        (item.traffic_class, item.transport, item.probe_network, item.expected_outbound)
        for item in specs
        if item.route_key.startswith(("matched-", "default-"))
    }
    assert matrix == {
        ("matched_exception", transport, network, "DE_EXCEPTIONS_BRIDGE")
        for transport in ("raw", "xhttp")
        for network in ("tcp", "udp")
    } | {
        ("unmatched_default", transport, network, "DIRECT")
        for transport in ("raw", "xhttp")
        for network in ("tcp", "udp")
    }


def test_build_task2_route_probe_specs_keeps_correlation_unique_for_overlapping_categories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_store(monkeypatch, tmp_path / "readiness", shared_category_network=True)

    specs = build_task2_route_probe_specs(_route_entries())

    assert len({(item.probe_network, item.target_ip, item.target_port) for item in specs}) == len(specs)


def test_build_task2_route_probe_specs_rejects_unmatched_control_inside_union(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_store(monkeypatch, tmp_path / "readiness", include_unmatched=True)

    with pytest.raises(VpnProductReadinessError, match="unmatched control address"):
        build_task2_route_probe_specs(_route_entries())


def test_build_task2_route_probe_specs_rejects_artifact_checksum_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "readiness"
    _configure_store(monkeypatch, root)
    (root / "versions" / ("0" * 64) / "categories" / "rkn.ipv4.cidr").write_text(
        "8.8.200.0/24\n",
        encoding="ascii",
    )

    with pytest.raises(VpnProductReadinessError, match="checksum"):
        build_task2_route_probe_specs(_route_entries())


def test_build_task2_route_probe_specs_rejects_missing_registry_route(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_store(monkeypatch, tmp_path / "readiness")
    routes = [item for item in _route_entries() if item.route_key != "antifilter-rkn-tcp"]

    with pytest.raises(VpnProductReadinessError, match="route registry"):
        build_task2_route_probe_specs(routes)
