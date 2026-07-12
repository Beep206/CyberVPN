from __future__ import annotations

import hashlib
import importlib.util
import ipaddress
import json
import random
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
ANTIFILTER_PARENT = REPO_ROOT / "scripts/remnawave"
FIXTURE_ROOT = REPO_ROOT / "data/antifilter/fixtures/communities"
EXAMPLE_POLICY = REPO_ROOT / "data/antifilter/example-policy.json"
PRODUCTION_POLICY_EXAMPLE = REPO_ROOT / "data/antifilter/production-policy.example.json"
TASK2_OPERATOR = REPO_ROOT / "scripts/remnawave/apply-spb-de-exceptions-server-routing.py"
sys.path.insert(0, str(ANTIFILTER_PARENT))

import antifilter.compiler as compiler_module  # noqa: E402
from antifilter.compiler import _collapse, _network_difference, compile_routes  # noqa: E402
from antifilter.models import (  # noqa: E402
    CATEGORY_COMMUNITIES,
    PolicyValidationError,
    PublishError,
    SafetyGateError,
    SourceValidationError,
    canonical_json_bytes,
    load_policy,
    sha256_bytes,
)
from antifilter.publish import (  # noqa: E402
    approve_candidate,
    promote_active,
    publish_candidate,
    record_failure,
    rollback_to_lkg,
)

NOW = datetime(2026, 7, 11, 0, 0, tzinfo=UTC)


def _load_task2_operator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("task2_spb_de_operator_for_antifilter", TASK2_OPERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _source(tmp_path: Path, name: str = "source") -> Path:
    root = tmp_path / name
    shutil.copytree(FIXTURE_ROOT, root)
    return root / "source.json"


def _policy(tmp_path: Path, name: str = "policy", **changes: object) -> Path:
    value = _json(EXAMPLE_POLICY)
    for key, replacement in changes.items():
        value[key] = replacement
    path = tmp_path / f"{name}.json"
    _write_json(path, value)
    return path


def _replace_route_file(
    source_manifest: Path,
    community: str,
    content: str,
    *,
    family: int = 4,
    source_version: str | None = None,
) -> None:
    source = _json(source_manifest)
    files = source["files"]
    assert isinstance(files, list)
    entry = next(
        (
            item
            for item in files
            if isinstance(item, dict) and item.get("community") == community and item.get("family") == family
        ),
        None,
    )
    if entry is None:
        entry = {
            "community": community,
            "family": family,
            "path": f"{community.replace(':', '_')}.ipv{family}.cidr",
            "sha256": "",
        }
        files.append(entry)
    route_path = source_manifest.parent / str(entry["path"])
    route_path.write_bytes(content.encode("ascii"))
    entry["sha256"] = hashlib.sha256(route_path.read_bytes()).hexdigest()
    if source_version is not None:
        source_data = source["source"]
        assert isinstance(source_data, dict)
        source_data["sourceVersion"] = source_version
    _write_json(source_manifest, source)


def _set_ipv6_policy(source_manifest: Path, policy_path: Path, mode: str, reason: str) -> None:
    source = _json(source_manifest)
    source["ipv6Policy"] = {"mode": mode, "reason": reason}
    _write_json(source_manifest, source)
    policy = _json(policy_path)
    policy["ipv6Policy"] = {"mode": mode, "reason": reason}
    _write_json(policy_path, policy)


def _compile(tmp_path: Path, *, source: Path | None = None, policy: Path | None = None, name: str = "candidate"):
    source = source or _source(tmp_path)
    policy = policy or _policy(tmp_path)
    output = tmp_path / name
    manifest = compile_routes(source, load_policy(policy), output, now=NOW)
    return output, manifest


def _publish(
    candidate: Path,
    store: Path,
    policy_path: Path = EXAMPLE_POLICY,
    *,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    return publish_candidate(
        candidate,
        store,
        policy=load_policy(policy_path),
        approval_path=approval_path,
    )


def test_required_communities_have_exact_explicit_category_mapping() -> None:
    assert CATEGORY_COMMUNITIES == {
        "rkn": ("65444:100",),
        "meta": ("65444:700",),
        "twitter_x": ("65444:710",),
        "netflix": ("65444:720",),
        "amazon_cloudfront": ("65444:730",),
        "microsoft": ("65444:740",),
        "amazon": ("65444:750",),
        "openai": ("65444:760",),
        "youtube": ("65444:770",),
        "google": ("65444:780",),
        "telegram": ("65444:790",),
        "discord": ("65444:800",),
        "custom_networks": ("65444:65444",),
    }
    assert len({community for communities in CATEGORY_COMMUNITIES.values() for community in communities}) == 13


def test_production_policy_example_has_real_endpoints_bootstrap_ranges_and_fail_closed_ipv6() -> None:
    policy = load_policy(PRODUCTION_POLICY_EXAMPLE)
    assert {str(endpoint) for endpoint in policy.self_endpoints} == {
        "45.87.41.146",
        "138.124.115.206",
        "138.16.140.44",
        "178.159.94.225",
        "193.233.91.99",
        "2001:41d0:701:1100::1db1",
    }
    assert policy.max_age_seconds == 7200
    assert policy.ipv6.mode == "fallback_block"
    assert "2a0d:2787:1b:12f5::/64" in {str(network) for network in policy.management_networks}
    assert "45.148.244.55/32" in {str(network) for network in policy.management_networks}
    assert policy.category_thresholds["rkn"].min_prefixes < 21151
    assert policy.category_thresholds["rkn"].max_prefixes > 21151
    assert policy.category_thresholds["telegram"].min_prefixes <= 7
    assert policy.category_thresholds["telegram"].max_prefixes >= 7


def test_fixture_compile_is_byte_deterministic_and_preserves_category_membership(tmp_path: Path) -> None:
    source = _source(tmp_path)
    policy = _policy(tmp_path)
    first, first_manifest = _compile(tmp_path, source=source, policy=policy, name="first")
    second, second_manifest = _compile(tmp_path, source=source, policy=policy, name="second")

    assert first_manifest == second_manifest
    first_files = {path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()}
    second_files = {path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()}
    assert first_files == second_files

    canonical = _json(first / "canonical.json")
    categories = canonical["categories"]
    assert isinstance(categories, dict)
    assert categories["rkn"]["ipv4"] == ["8.8.8.0/24"]
    assert categories["meta"]["ipv4"] == ["1.1.1.0/25"]
    assert categories["twitter_x"]["ipv4"] == ["1.1.1.128/25"]
    assert "1.1.1.0/24" in canonical["union"]["ipv4"]
    assert first_manifest["categories"]["rkn"]["prefixCountRaw"] == 1
    assert first_manifest["categories"]["rkn"]["prefixCountCompiled"] == 1
    assert isinstance(first_manifest["union"]["addressCount"], str)
    assert first_manifest["freshness"] == {
        "status": "fresh",
        "maxAgeSeconds": 604800,
        "maxFutureSkewSeconds": 300,
    }
    assert first_manifest["ipv6Policy"]["mode"] == "disabled"
    xray = _json(first / "xray/de-exceptions.json")
    assert xray["matchedFailurePolicy"] == "fail_closed"
    assert xray["ipv6Policy"]["unmatched"] == "profile_disabled"
    assert all(rule["ip"] for rule in xray["rules"])


def test_property_like_collapse_is_deterministic_idempotent_and_exact() -> None:
    randomizer = random.Random(20260711)  # noqa: S311 - deterministic property-like cases, not security data
    for _ in range(100):
        inputs: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for _ in range(randomizer.randint(1, 80)):
            if randomizer.random() < 0.3:
                prefix = randomizer.randint(112, 128)
                inputs.append(
                    ipaddress.ip_network(
                        f"{ipaddress.IPv6Address(randomizer.getrandbits(112) << 16)}/{prefix}",
                        strict=False,
                    )
                )
            else:
                prefix = randomizer.randint(24, 32)
                inputs.append(
                    ipaddress.ip_network(
                        f"{ipaddress.IPv4Address(randomizer.getrandbits(24) << 8)}/{prefix}",
                        strict=False,
                    )
                )
        first = _collapse(inputs)
        shuffled = list(inputs)
        randomizer.shuffle(shuffled)
        assert _collapse(shuffled) == first
        assert _collapse(first) == first
        assert not _network_difference(inputs, first)
        assert not _network_difference(first, inputs)


@pytest.mark.parametrize(
    ("content", "family", "message"),
    [
        ("not-a-cidr\n", 4, "invalid CIDR"),
        ("8.8.8.0/24 # comment\n", 4, "CIDR-only line"),
        ("8.8.8.0/24,attribute\n", 4, "CIDR-only line"),
        ("2001:4860::/32\n", 4, "address family mismatch"),
        ("", 4, "is empty"),
    ],
)
def test_invalid_empty_and_family_mismatched_route_files_are_rejected(
    tmp_path: Path, content: str, family: int, message: str
) -> None:
    source = _source(tmp_path)
    _replace_route_file(source, "65444:700", content, family=family)
    with pytest.raises(SourceValidationError, match=message):
        compile_routes(source, load_policy(_policy(tmp_path)), tmp_path / "candidate", now=NOW)
    assert not (tmp_path / "candidate").exists()


def test_html_source_type_and_unknown_or_missing_community_fail_closed(tmp_path: Path) -> None:
    source_path = _source(tmp_path)
    source = _json(source_path)
    source_data = source["source"]
    assert isinstance(source_data, dict)
    source_data["type"] = "html"
    _write_json(source_path, source)
    with pytest.raises(SourceValidationError, match="approved canonical CIDR"):
        compile_routes(source_path, load_policy(_policy(tmp_path)), tmp_path / "html", now=NOW)

    source_path = _source(tmp_path, "missing")
    source = _json(source_path)
    files = source["files"]
    assert isinstance(files, list)
    files.pop()
    _write_json(source_path, source)
    with pytest.raises(SourceValidationError, match="required communities are missing"):
        compile_routes(source_path, load_policy(_policy(tmp_path, "missing-policy")), tmp_path / "missing-out", now=NOW)


def test_stale_and_future_sources_are_rejected_with_controlled_clock(tmp_path: Path) -> None:
    for generated_at, message in (
        ("2026-06-01T00:00:00Z", "source is stale"),
        ("2026-07-11T00:06:00Z", "too far in the future"),
    ):
        source_path = _source(tmp_path, generated_at[:10].replace("-", ""))
        source = _json(source_path)
        source_data = source["source"]
        assert isinstance(source_data, dict)
        source_data["generatedAt"] = generated_at
        _write_json(source_path, source)
        with pytest.raises(SourceValidationError, match=message):
            compile_routes(
                source_path,
                load_policy(_policy(tmp_path, f"policy-{generated_at[:10]}")),
                tmp_path / f"out-{generated_at[:10]}",
                now=NOW,
            )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_policy_rejects_non_finite_percentage_thresholds(tmp_path: Path, value: float) -> None:
    policy = _json(EXAMPLE_POLICY)
    policy["thresholds"]["maxIpv4UnionPercent"] = value
    path = tmp_path / "non-finite-policy.json"
    _write_json(path, policy)
    with pytest.raises(PolicyValidationError, match="non-finite JSON number"):
        load_policy(path)


def test_path_traversal_absolute_path_symlink_and_resource_limits_are_rejected(tmp_path: Path) -> None:
    typed_source_path = _source(tmp_path, "bad-path-type")
    typed_source = _json(typed_source_path)
    typed_files = typed_source["files"]
    assert isinstance(typed_files, list) and isinstance(typed_files[0], dict)
    typed_files[0]["path"] = ["not-a-string"]
    _write_json(typed_source_path, typed_source)
    with pytest.raises(SourceValidationError, match="path must be a non-empty string"):
        compile_routes(
            typed_source_path,
            load_policy(_policy(tmp_path, "bad-path-type-policy")),
            tmp_path / "bad-path-type-out",
            now=NOW,
        )

    for unsafe_path in ("../outside.cidr", str((tmp_path / "absolute.cidr").absolute())):
        source_path = _source(tmp_path, hashlib.sha256(unsafe_path.encode()).hexdigest()[:8])
        source_document = _json(source_path)
        files = source_document["files"]
        assert isinstance(files, list)
        assert isinstance(files[0], dict)
        files[0]["path"] = unsafe_path
        _write_json(source_path, source_document)
        with pytest.raises(SourceValidationError, match="path"):
            compile_routes(
                source_path, load_policy(_policy(tmp_path, f"p-{len(unsafe_path)}")), tmp_path / "bad", now=NOW
            )


def test_file_size_line_count_and_compiled_prefix_resource_ceilings_are_enforced(tmp_path: Path) -> None:
    source = _source(tmp_path, "file-size")
    policy_value = _json(EXAMPLE_POLICY)
    limits = policy_value["resourceLimits"]
    assert isinstance(limits, dict)
    limits["maxFileBytes"] = 4
    file_policy = tmp_path / "file-size-policy.json"
    _write_json(file_policy, policy_value)
    with pytest.raises(SourceValidationError, match="exceeds 4 bytes"):
        compile_routes(source, load_policy(file_policy), tmp_path / "file-size-out", now=NOW)

    source = _source(tmp_path, "line-count")
    _replace_route_file(source, "65444:700", "1.1.1.0/25\n1.1.1.128/25\n")
    policy_value = _json(EXAMPLE_POLICY)
    limits = policy_value["resourceLimits"]
    assert isinstance(limits, dict)
    limits["maxLinesPerFile"] = 1
    line_policy = tmp_path / "line-count-policy.json"
    _write_json(line_policy, policy_value)
    with pytest.raises(SourceValidationError, match="exceeds 1 lines"):
        compile_routes(source, load_policy(line_policy), tmp_path / "line-count-out", now=NOW)

    source = _source(tmp_path, "compiled-count")
    policy_value = _json(EXAMPLE_POLICY)
    limits = policy_value["resourceLimits"]
    assert isinstance(limits, dict)
    limits["maxCompiledPrefixes"] = 12
    compiled_policy = tmp_path / "compiled-count-policy.json"
    _write_json(compiled_policy, policy_value)
    with pytest.raises(SafetyGateError, match="compiled output exceeds 12"):
        compile_routes(source, load_policy(compiled_policy), tmp_path / "compiled-count-out", now=NOW)


def test_source_symlink_guard_is_exercised_without_platform_privileges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path = _source(tmp_path, "simulated-symlink")
    source_document = _json(source_path)
    files = source_document["files"]
    assert isinstance(files, list) and isinstance(files[0], dict)
    original = source_path.parent / str(files[0]["path"])
    simulated_link = source_path.parent / "simulated-link.cidr"
    shutil.copyfile(original, simulated_link)
    files[0]["path"] = simulated_link.name
    _write_json(source_path, source_document)

    original_is_symlink = Path.is_symlink

    def simulated_is_symlink(path: Path) -> bool:
        return path == simulated_link or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", simulated_is_symlink)
    with pytest.raises(SourceValidationError, match="symlinks are forbidden"):
        compile_routes(
            source_path,
            load_policy(_policy(tmp_path, "simulated-symlink-policy")),
            tmp_path / "simulated-symlink-out",
            now=NOW,
        )


def test_candidate_directory_switch_is_atomic_and_cleans_partial_temp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path)
    policy = load_policy(_policy(tmp_path))
    output = tmp_path / "candidate"

    def fail_replace(_source: object, _destination: object) -> None:
        raise OSError("injected atomic switch failure")

    monkeypatch.setattr(compiler_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected atomic switch failure"):
        compile_routes(source, policy, output, now=NOW)
    assert not output.exists()
    assert not list(tmp_path.glob(".candidate.tmp-*"))

    source_path = _source(tmp_path, "resource")
    policy_value = _json(EXAMPLE_POLICY)
    limits = policy_value["resourceLimits"]
    assert isinstance(limits, dict)
    limits["maxLineBytes"] = 8
    resource_policy = tmp_path / "resource-policy.json"
    _write_json(resource_policy, policy_value)
    with pytest.raises(SourceValidationError, match="invalid formatting"):
        compile_routes(source_path, load_policy(resource_policy), tmp_path / "resource-out", now=NOW)


def test_private_and_management_ranges_are_subtracted_and_self_endpoints_reject_source(tmp_path: Path) -> None:
    source = _source(tmp_path)
    _replace_route_file(source, "65444:100", "8.8.8.1/24\n10.0.0.0/8\n")
    policy_value = _json(EXAMPLE_POLICY)
    management = policy_value["managementNetworks"]
    assert isinstance(management, list)
    management.append("8.8.8.128/25")
    policy_path = tmp_path / "exclude-policy.json"
    _write_json(policy_path, policy_value)
    output = tmp_path / "excluded"
    manifest = compile_routes(source, load_policy(policy_path), output, now=NOW)
    canonical = _json(output / "canonical.json")
    assert canonical["categories"]["rkn"]["ipv4"] == ["8.8.8.0/25"]
    assert manifest["exclusions"]["private"]["addressCount"] == str(2**24)
    assert manifest["exclusions"]["management"]["addressCount"] == "128"

    source = _source(tmp_path, "self-source")
    policy_value = _json(EXAMPLE_POLICY)
    policy_value["selfEndpoints"] = ["8.8.8.8"]
    self_policy = tmp_path / "self-policy.json"
    _write_json(self_policy, policy_value)
    with pytest.raises(SafetyGateError, match="self endpoint present"):
        compile_routes(source, load_policy(self_policy), tmp_path / "self-out", now=NOW)


def test_publish_accepts_compiled_prefix_splitting_after_management_exclusion(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path, "split-source")
    _replace_route_file(source, "65444:100", "8.0.0.0/8\n")
    policy_value = _json(EXAMPLE_POLICY)
    management = policy_value["managementNetworks"]
    assert isinstance(management, list)
    management.append("8.8.8.128/25")
    policy_path = tmp_path / "split-policy.json"
    _write_json(policy_path, policy_value)

    output = tmp_path / "split-output"
    manifest = compile_routes(source, load_policy(policy_path), output, now=NOW)

    assert manifest["categories"]["rkn"]["prefixCountCompiled"] > manifest["categories"]["rkn"]["prefixCountRaw"]
    pointer = _publish(output, tmp_path / "split-store", policy_path)
    assert pointer["version"] == manifest["version"]


def test_ipv6_enabled_is_separate_and_disabled_state_cannot_silently_accept_routes(tmp_path: Path) -> None:
    reason = "Equivalent IPv6 feed and DE bridge path are enabled for this controlled fixture."
    source = _source(tmp_path, "ipv6-enabled")
    policy = _policy(tmp_path, "ipv6-enabled-policy")
    required_communities = [community for communities in CATEGORY_COMMUNITIES.values() for community in communities]
    for index, community in enumerate(required_communities, start=1):
        _replace_route_file(
            source,
            community,
            f"2001:4860:{index:x}::/48\n",
            family=6,
        )
    _set_ipv6_policy(source, policy, "enabled", reason)
    output = tmp_path / "ipv6-output"
    manifest = compile_routes(source, load_policy(policy), output, now=NOW)
    canonical = _json(output / "canonical.json")
    openai_index = required_communities.index("65444:760") + 1
    assert canonical["categories"]["openai"]["ipv6"] == [f"2001:4860:{openai_index:x}::/48"]
    assert manifest["union"]["families"]["ipv6"] > 0
    assert _json(output / "xray/de-exceptions.json")["ipv6Policy"]["unmatched"] == "normal_profile_policy"

    partial_source = _source(tmp_path, "ipv6-partial")
    partial_policy = _policy(tmp_path, "ipv6-partial-policy")
    _replace_route_file(partial_source, "65444:760", "2001:4860:4860::/48\n", family=6)
    _set_ipv6_policy(partial_source, partial_policy, "enabled", reason)
    with pytest.raises(SafetyGateError, match="communities are missing IPv6 files"):
        compile_routes(
            partial_source,
            load_policy(partial_policy),
            tmp_path / "ipv6-partial-output",
            now=NOW,
        )

    disabled_source = _source(tmp_path, "ipv6-disabled")
    _replace_route_file(disabled_source, "65444:760", "2001:4860:4860::/48\n", family=6)
    with pytest.raises(SafetyGateError, match="IPv6 routes were supplied"):
        compile_routes(
            disabled_source,
            load_policy(_policy(tmp_path, "ipv6-disabled-policy")),
            tmp_path / "ipv6-disabled-output",
            now=NOW,
        )


def test_suspicious_delta_requires_checksum_bound_approval_and_lkg_supports_rollback(tmp_path: Path) -> None:
    thresholds = _json(EXAMPLE_POLICY)["thresholds"]
    assert isinstance(thresholds, dict)
    thresholds["maxAddedPercent"] = 0.1
    thresholds["maxRemovedPercent"] = 0.1
    policy = _policy(tmp_path, thresholds=thresholds)
    first_source = _source(tmp_path, "first-source")
    first = tmp_path / "first"
    first_manifest = compile_routes(first_source, load_policy(policy), first, now=NOW)
    assert first_manifest["safety"]["status"] == "accepted"

    store = tmp_path / "store"
    first_pointer = _publish(first, store, policy)
    assert _json(store / "active.json") == first_pointer
    assert _json(store / "last-known-good.json") == first_pointer

    second_source = _source(tmp_path, "second-source")
    _replace_route_file(
        second_source,
        "65444:65444",
        "76.76.4.0/24\n",
        source_version="offline-fixture-v2",
    )
    second = tmp_path / "second"
    second_manifest = compile_routes(second_source, load_policy(policy), second, now=NOW, previous_dir=first)
    assert (
        second_manifest["previousManifestSha256"] == hashlib.sha256((first / "manifest.json").read_bytes()).hexdigest()
    )
    assert second_manifest["change"]["added"] == 1
    assert second_manifest["change"]["removed"] == 1
    assert second_manifest["safety"]["status"] == "approval_required"

    with pytest.raises(PublishError, match="pending a manual approval"):
        _publish(second, store, policy)
    assert _json(store / "active.json") == first_pointer

    safety_tampered = tmp_path / "second-safety-tampered"
    shutil.copytree(second, safety_tampered)
    safety_manifest = _json(safety_tampered / "manifest.json")
    safety_manifest["safety"] = {"status": "accepted", "reasons": []}
    _write_json(safety_tampered / "manifest.json", safety_manifest)
    with pytest.raises(PublishError, match="safety decision does not match"):
        _publish(safety_tampered, store, policy)

    non_finite_candidate = tmp_path / "second-non-finite"
    shutil.copytree(second, non_finite_candidate)
    non_finite_manifest = _json(non_finite_candidate / "manifest.json")
    non_finite_manifest["change"]["addedPercent"] = float("nan")
    _write_json(non_finite_candidate / "manifest.json", non_finite_manifest)
    with pytest.raises(PublishError, match="non-finite JSON number"):
        _publish(non_finite_candidate, store, policy)

    approval = tmp_path / "approvals" / "second.json"
    record = approve_candidate(
        second,
        approval,
        approved_by="route-reviewer",
        ticket="CHANGE-42",
        approved_at=NOW,
    )
    assert record["manifestSha256"] == hashlib.sha256((second / "manifest.json").read_bytes()).hexdigest()
    invalid_approval = tmp_path / "approvals" / "invalid-time.json"
    invalid_record = dict(record)
    invalid_record["approvedAt"] = "not-a-timestamp"
    _write_json(invalid_approval, invalid_record)
    with pytest.raises(PublishError, match="approval timestamp is invalid"):
        _publish(second, store, policy, approval_path=invalid_approval)
    assert _json(store / "active.json") == first_pointer
    non_finite_approval = tmp_path / "approvals" / "non-finite.json"
    non_finite_record = dict(record)
    non_finite_record["approvedAt"] = float("inf")
    _write_json(non_finite_approval, non_finite_record)
    with pytest.raises(PublishError, match="non-finite JSON number"):
        _publish(second, store, policy, approval_path=non_finite_approval)
    second_pointer = _publish(second, store, policy, approval_path=approval)
    assert _json(store / "active.json") == second_pointer
    assert _json(store / "last-known-good.json") == first_pointer
    assert rollback_to_lkg(store) == first_pointer
    assert _json(store / "active.json") == first_pointer
    _publish(second, store, policy, approval_path=approval)
    assert promote_active(store) == second_pointer
    assert _json(store / "last-known-good.json") == second_pointer


def test_category_attribution_change_is_recorded_and_quarantined_when_union_is_unchanged(tmp_path: Path) -> None:
    thresholds = _json(EXAMPLE_POLICY)["thresholds"]
    assert isinstance(thresholds, dict)
    thresholds["maxAddedPercent"] = 0.1
    thresholds["maxRemovedPercent"] = 0.1
    policy = _policy(tmp_path, "category-delta-policy", thresholds=thresholds)
    first_source = _source(tmp_path, "category-first")
    first = tmp_path / "category-first-out"
    compile_routes(first_source, load_policy(policy), first, now=NOW)

    second_source = _source(tmp_path, "category-second")
    _replace_route_file(second_source, "65444:700", "1.1.1.128/25\n")
    _replace_route_file(
        second_source,
        "65444:710",
        "1.1.1.0/25\n",
        source_version="category-swap-v2",
    )
    second = tmp_path / "category-second-out"
    manifest = compile_routes(
        second_source,
        load_policy(policy),
        second,
        now=NOW,
        previous_dir=first,
    )
    assert manifest["change"]["added"] == 0
    assert manifest["change"]["removed"] == 0
    assert manifest["change"]["categories"]["meta"]["added"] == 1
    assert manifest["change"]["categories"]["twitter_x"]["removed"] == 1
    assert manifest["safety"]["status"] == "approval_required"


def test_malformed_previous_manifest_is_a_typed_rejection(tmp_path: Path) -> None:
    first, _ = _compile(tmp_path, name="previous-valid")
    manifest = _json(first / "manifest.json")
    manifest["artifacts"] = []
    _write_json(first / "manifest.json", manifest)
    with pytest.raises(SourceValidationError, match="artifacts must be an object"):
        compile_routes(
            _source(tmp_path, "previous-next-source"),
            load_policy(_policy(tmp_path, "previous-next-policy")),
            tmp_path / "previous-next-output",
            now=NOW,
            previous_dir=first,
        )


def test_bootstrap_rejects_default_route_and_excessive_public_address_coverage(tmp_path: Path) -> None:
    source = _source(tmp_path)
    _replace_route_file(source, "65444:65444", "0.0.0.0/0\n")
    policy = _policy(tmp_path, selfEndpoints=[])
    with pytest.raises(SafetyGateError, match="IPv4 union address coverage"):
        compile_routes(
            source,
            load_policy(policy),
            tmp_path / "default-route-out",
            now=NOW,
        )


def test_publish_revalidates_forged_default_route_against_trusted_policy(tmp_path: Path) -> None:
    candidate, _ = _compile(tmp_path)
    manifest = _json(candidate / "manifest.json")
    canonical = _json(candidate / "canonical.json")
    canonical["categories"]["custom_networks"]["ipv4"] = ["0.0.0.0/0"]
    canonical["union"] = {"ipv4": ["0.0.0.0/0"], "ipv6": []}
    canonical_raw = canonical_json_bytes(canonical)
    (candidate / "canonical.json").write_bytes(canonical_raw)

    xray = _json(candidate / "xray/de-exceptions.json")
    xray["rules"] = [
        {
            "family": 4,
            "ip": ["0.0.0.0/0"],
            "outboundTag": "DE_EXCEPTIONS_BRIDGE",
        }
    ]
    xray_raw = canonical_json_bytes(xray)
    (candidate / "xray/de-exceptions.json").write_bytes(xray_raw)

    manifest["artifacts"]["canonical.json"] = sha256_bytes(canonical_raw)
    manifest["artifacts"]["xray/de-exceptions.json"] = sha256_bytes(xray_raw)
    manifest["xray"]["rulesSha256"] = sha256_bytes(xray_raw)
    union_payload = {"ipv4": ["0.0.0.0/0"], "ipv6": []}
    manifest["union"] = {
        "prefixCount": 1,
        "addressCount": str(2**32),
        "families": {"ipv4": 1, "ipv6": 0},
        "sha256": sha256_bytes(canonical_json_bytes(union_payload)),
    }
    policy = load_policy(EXAMPLE_POLICY)
    manifest["version"] = sha256_bytes(
        canonical_raw
        + sha256_bytes(policy.canonical_bytes).encode("ascii")
        + manifest["source"]["manifestSha256"].encode("ascii")
    )
    _write_json(candidate / "manifest.json", manifest)

    with pytest.raises(
        PublishError,
        match="category manifest|forbidden or management|address coverage",
    ):
        _publish(candidate, tmp_path / "forged-store")


def test_unpromoted_active_never_replaces_last_known_good_on_later_publish(tmp_path: Path) -> None:
    thresholds = _json(EXAMPLE_POLICY)["thresholds"]
    assert isinstance(thresholds, dict)
    thresholds["maxAddedPercent"] = 1000.0
    thresholds["maxRemovedPercent"] = 1000.0
    policy = _policy(tmp_path, "lkg-policy", thresholds=thresholds)
    store = tmp_path / "lkg-store"

    first_source = _source(tmp_path, "lkg-first-source")
    first = tmp_path / "lkg-first"
    compile_routes(first_source, load_policy(policy), first, now=NOW)
    first_pointer = _publish(first, store, policy)

    second_source = _source(tmp_path, "lkg-second-source")
    _replace_route_file(
        second_source,
        "65444:65444",
        "76.76.4.0/24\n",
        source_version="lkg-v2",
    )
    second = tmp_path / "lkg-second"
    compile_routes(second_source, load_policy(policy), second, now=NOW, previous_dir=first)
    _publish(second, store, policy)
    _publish(second, store, policy)

    third_source = _source(tmp_path, "lkg-third-source")
    _replace_route_file(
        third_source,
        "65444:65444",
        "76.76.6.0/24\n",
        source_version="lkg-v3",
    )
    third = tmp_path / "lkg-third"
    compile_routes(third_source, load_policy(policy), third, now=NOW, previous_dir=second)
    _publish(third, store, policy)

    assert _json(store / "last-known-good.json") == first_pointer
    assert rollback_to_lkg(store) == first_pointer


def test_generated_manifest_is_accepted_by_task2_operator_loader(tmp_path: Path) -> None:
    candidate, manifest = _compile(tmp_path)
    operator = _load_task2_operator()

    artifact = operator._load_antifilter_artifact(candidate / "manifest.json", max_age_hours=0)

    assert manifest["xray"] == {
        "rulesPath": "xray/de-exceptions.json",
        "rulesSha256": hashlib.sha256((candidate / "xray/de-exceptions.json").read_bytes()).hexdigest(),
    }
    assert artifact.rules_path == (candidate / "xray/de-exceptions.json").resolve()
    assert artifact.rules_sha256 == manifest["xray"]["rulesSha256"]
    assert artifact.raw_rules


def test_invalid_candidate_failure_record_and_checksum_tamper_preserve_active_lkg(tmp_path: Path) -> None:
    candidate, _ = _compile(tmp_path)
    store = tmp_path / "store"
    pointer = _publish(candidate, store)
    before_active = (store / "active.json").read_bytes()
    before_lkg = (store / "last-known-good.json").read_bytes()

    source = _source(tmp_path, "invalid-source")
    _replace_route_file(source, "65444:700", "invalid\n")
    with pytest.raises(SourceValidationError) as exc_info:
        compile_routes(
            source,
            load_policy(_policy(tmp_path, "invalid-policy")),
            tmp_path / "invalid-candidate",
            now=NOW,
        )
    failure_path = record_failure(
        store,
        reason=str(exc_info.value),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        failed_at=NOW,
    )
    failure = _json(failure_path)
    assert failure["status"] == "degraded"
    assert "invalid CIDR" in failure["reason"]
    assert (store / "active.json").read_bytes() == before_active
    assert (store / "last-known-good.json").read_bytes() == before_lkg

    incomplete = tmp_path / "incomplete"
    shutil.copytree(candidate, incomplete)
    (incomplete / "xray/de-exceptions.json").unlink()
    incomplete_manifest = _json(incomplete / "manifest.json")
    del incomplete_manifest["artifacts"]["xray/de-exceptions.json"]
    _write_json(incomplete / "manifest.json", incomplete_manifest)
    with pytest.raises(PublishError, match="artifact contract mismatch"):
        _publish(incomplete, store)
    assert _json(store / "active.json") == pointer

    category_tampered = tmp_path / "category-tampered"
    shutil.copytree(candidate, category_tampered)
    category_manifest = _json(category_tampered / "manifest.json")
    category_manifest["categories"]["openai"]["prefixCountCompiled"] = 0
    _write_json(category_tampered / "manifest.json", category_manifest)
    with pytest.raises(PublishError, match="category manifest does not match"):
        _publish(category_tampered, store)

    extra_directory = tmp_path / "extra-directory"
    shutil.copytree(candidate, extra_directory)
    (extra_directory / "unexpected" / "nested").mkdir(parents=True)
    with pytest.raises(PublishError, match="directory contract mismatch"):
        _publish(extra_directory, store)

    tampered = tmp_path / "tampered"
    shutil.copytree(candidate, tampered)
    (tampered / "union/ipv4.cidr").write_text("8.8.4.0/24\n", encoding="ascii")
    with pytest.raises(PublishError, match="checksum mismatch"):
        _publish(tampered, store)
    assert _json(store / "active.json") == pointer
    assert (store / "last-known-good.json").read_bytes() == before_lkg


def test_publish_is_idempotent_for_the_same_immutable_candidate(tmp_path: Path) -> None:
    candidate, _ = _compile(tmp_path)
    store = tmp_path / "store"
    store.mkdir()
    (store / ".state.lock").write_text("locked\n", encoding="ascii")
    with pytest.raises(PublishError, match="state is locked"):
        _publish(candidate, store)
    assert not (store / "active.json").exists()
    (store / ".state.lock").unlink()
    first = _publish(candidate, store)
    second = _publish(candidate, store)
    assert first == second
    assert len([path for path in (store / "versions").iterdir() if path.is_dir()]) == 1
    stored_xray = store / "versions" / first["version"] / "xray/de-exceptions.json"
    stored_xray.unlink()
    with pytest.raises(PublishError, match="escapes or is missing"):
        _publish(candidate, store)


def test_candidate_manifest_and_failure_records_do_not_expose_secret_fields(tmp_path: Path) -> None:
    candidate, _ = _compile(tmp_path)
    combined = b"".join(path.read_bytes() for path in candidate.rglob("*") if path.is_file()).lower()
    for forbidden in (
        b"password",
        b"token",
        b"privatekey",
        b"subscriptionurl",
        b"vlessuuid",
        b"sessionidhash",
    ):
        assert forbidden not in combined
