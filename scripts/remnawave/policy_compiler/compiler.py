from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .loader import load_policy
from .models import PremiumSmartRuPolicy
from .renderers import (
    LEGACY_HEADER_NAME,
    MIHOMO_NAME,
    XRAY_CLIENT_NAME,
    XRAY_SERVER_NAME,
    render_artifacts,
)

NORMALIZED_POLICY_NAME = "policy.normalized.json"
POLICY_SCHEMA_NAME = "policy.schema.json"
MANIFEST_NAME = "manifest.json"


class GeneratedDriftError(RuntimeError):
    def __init__(self, paths: tuple[Path, ...]) -> None:
        self.paths = paths
        super().__init__(
            "generated policy artifacts are missing or stale: "
            + ", ".join(map(str, paths))
        )


@dataclass(frozen=True)
class GenerationResult:
    output_dir: Path
    changed: tuple[Path, ...]
    policy_sha256: str


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _source_label(policy_path: Path) -> str:
    parts = policy_path.resolve().parts
    try:
        index = tuple(part.casefold() for part in parts).index("scripts")
    except ValueError:
        return policy_path.name
    return Path(*parts[index:]).as_posix()


def default_output_dir(policy_path: str | Path) -> Path:
    source = Path(policy_path)
    return source.parent.parent / "generated" / source.stem


def normalize_policy(policy: PremiumSmartRuPolicy) -> dict[str, object]:
    return policy.model_dump(mode="json", exclude_none=True)


def build_outputs(
    policy_path: str | Path,
) -> tuple[PremiumSmartRuPolicy, dict[str, bytes]]:
    source_path = Path(policy_path)
    policy = load_policy(source_path)
    source_bytes = source_path.read_bytes()
    normalized_bytes = _json_bytes(normalize_policy(policy))
    schema_bytes = _json_bytes(PremiumSmartRuPolicy.model_json_schema())
    rendered_artifacts = render_artifacts(policy)

    mutable_sources = sorted(
        source_id
        for source_id, source in policy.sources.items()
        if source.integrity is not None and not source.integrity.pinned
    )
    pinned_sources = sorted(
        source_id
        for source_id, source in policy.sources.items()
        if source.integrity is not None and source.integrity.pinned
    )
    groups = policy.source_groups.model_dump(mode="python")
    source_inventory = {}
    for source_id, source in sorted(policy.sources.items()):
        source_value = source.model_dump(mode="json", exclude_none=True)
        descriptor_bytes = json.dumps(
            source_value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        source_inventory[source_id] = {
            "descriptorSha256": _sha256(descriptor_bytes),
            "entryCount": len(source.entries),
            "revision": source.integrity.revision
            if source.integrity is not None
            else "local-policy-v1",
            "pinned": source.integrity.pinned if source.integrity is not None else True,
            "contentSha256": source.integrity.sha256
            if source.integrity is not None
            else _sha256(_json_bytes(list(source.entries))),
        }
    manifest = {
        "compiler": "cybervpn.remnawave.policy_compiler.v1",
        "schemaVersion": policy.version,
        "product": policy.product,
        "source": {
            "path": _source_label(source_path),
            "sha256": _sha256(source_bytes),
        },
        "artifacts": {
            NORMALIZED_POLICY_NAME: {
                "bytes": len(normalized_bytes),
                "sha256": _sha256(normalized_bytes),
            },
            POLICY_SCHEMA_NAME: {
                "bytes": len(schema_bytes),
                "sha256": _sha256(schema_bytes),
            },
            **{
                name: {"bytes": len(content), "sha256": _sha256(content)}
                for name, content in rendered_artifacts.items()
            },
        },
        "counts": {
            "rules": len(policy.rules),
            "sources": len(policy.sources),
            "remoteSources": len(mutable_sources) + len(pinned_sources),
            "pinnedRemoteSources": len(pinned_sources),
            "mutableRemoteSources": len(mutable_sources),
            "criticalSourceReferences": sum(
                len(source_ids) for source_ids in groups.values()
            ),
            "criticalInlineEntries": sum(
                len(policy.sources[source_id].entries)
                for source_ids in groups.values()
                for source_id in source_ids
            ),
            "transportVariants": sum(
                len(transports)
                for group in (policy.transport_groups.eu, policy.transport_groups.ru)
                for transports in group.members.values()
            ),
        },
        "sourceIntegrity": {
            "pinned": pinned_sources,
            "mutable": mutable_sources,
            "inventory": source_inventory,
        },
        "rendererCoverage": {
            "normalizedPolicy": {
                "status": "rendered",
                "reason": "typed canonical intermediate representation",
                "risk": "none",
            },
            "mihomo": {
                "status": "rendered",
                "artifact": MIHOMO_NAME,
                "reason": "full deterministic Mihomo config rendered from canonical policy",
                "risk": "none",
            },
            "xrayClient": {
                "status": "rendered",
                "artifact": XRAY_CLIENT_NAME,
                "reason": "typed INCY/HAPP routing and regional transport policy",
                "risk": "none",
            },
            "xrayServer": {
                "status": "rendered",
                "artifact": XRAY_SERVER_NAME,
                "reason": "typed server routing rules consumed by the operator",
                "risk": "none",
            },
            "legacyHeader": {
                "status": "rendered",
                "artifact": LEGACY_HEADER_NAME,
                "reason": "canonical compatibility routing header",
                "risk": "none",
            },
        },
    }
    return policy, {
        NORMALIZED_POLICY_NAME: normalized_bytes,
        POLICY_SCHEMA_NAME: schema_bytes,
        **rendered_artifacts,
        MANIFEST_NAME: _json_bytes(manifest),
    }


def _write_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return True


def generate(
    policy_path: str | Path, output_dir: str | Path | None = None
) -> GenerationResult:
    source_path = Path(policy_path)
    destination = (
        Path(output_dir) if output_dir is not None else default_output_dir(source_path)
    )
    _policy, outputs = build_outputs(source_path)
    changed = tuple(
        destination / name
        for name, content in outputs.items()
        if _write_if_changed(destination / name, content)
    )
    return GenerationResult(
        output_dir=destination,
        changed=changed,
        policy_sha256=_sha256(outputs[NORMALIZED_POLICY_NAME]),
    )


def check_generated(
    policy_path: str | Path, output_dir: str | Path | None = None
) -> GenerationResult:
    source_path = Path(policy_path)
    destination = (
        Path(output_dir) if output_dir is not None else default_output_dir(source_path)
    )
    _policy, outputs = build_outputs(source_path)
    drifted = tuple(
        destination / name
        for name, expected in outputs.items()
        if not (destination / name).exists()
        or (destination / name).read_bytes() != expected
    )
    if drifted:
        raise GeneratedDriftError(drifted)
    return GenerationResult(
        output_dir=destination,
        changed=(),
        policy_sha256=_sha256(outputs[NORMALIZED_POLICY_NAME]),
    )
