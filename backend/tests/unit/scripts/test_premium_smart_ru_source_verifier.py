from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.remnawave.policy_compiler.loader import load_policy  # noqa: E402
from scripts.remnawave.policy_compiler.source_verifier import (  # noqa: E402
    SourceVerificationError,
    verify_policy_sources,
)

POLICY_PATH = REPO_ROOT / "scripts" / "remnawave" / "policies" / "premium_smart_ru.yaml"


def test_verifier_accepts_exact_bytes_for_every_remote_source() -> None:
    policy = load_policy(POLICY_PATH)
    content_by_url: dict[str, bytes] = {}
    raw = policy.model_dump(mode="python")
    for source_id, source in policy.sources.items():
        if source.kind != "http":
            continue
        content = f"verified:{source_id}".encode()
        content_by_url[source.url] = content
        raw["sources"][source_id]["integrity"]["sha256"] = hashlib.sha256(content).hexdigest()
    policy = type(policy).model_validate(raw)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content_by_url[str(request.url)])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        verified = verify_policy_sources(policy, client)

    assert len(verified) == 29
    assert [item.source_id for item in verified] == sorted(
        source_id for source_id, source in policy.sources.items() if source.kind == "http"
    )


def test_verifier_rejects_checksum_mismatch_without_exposing_content() -> None:
    policy = load_policy(POLICY_PATH)
    first_source_id = sorted(source_id for source_id, source in policy.sources.items() if source.kind == "http")[0]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"wrong bytes")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SourceVerificationError, match=first_source_id) as exc_info:
            verify_policy_sources(policy, client)

    assert "wrong bytes" not in str(exc_info.value)


def test_verifier_rejects_oversized_source() -> None:
    policy = load_policy(POLICY_PATH)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"too-large")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(SourceVerificationError, match="exceeds 4 bytes"):
            verify_policy_sources(policy, client, max_source_bytes=4)
