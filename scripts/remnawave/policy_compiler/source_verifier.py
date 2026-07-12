from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import httpx

from .loader import load_policy
from .models import PremiumSmartRuPolicy

DEFAULT_MAX_SOURCE_BYTES = 64 * 1024 * 1024


class SourceVerificationError(RuntimeError):
    """Raised when an immutable remote policy source cannot be reproduced."""


@dataclass(frozen=True)
class VerifiedSource:
    source_id: str
    bytes: int
    sha256: str


def _read_bounded(response: httpx.Response, max_source_bytes: int) -> bytes:
    content = bytearray()
    for chunk in response.iter_bytes():
        content.extend(chunk)
        if len(content) > max_source_bytes:
            raise SourceVerificationError(
                f"remote policy source exceeds {max_source_bytes} bytes"
            )
    return bytes(content)


def verify_policy_sources(
    policy: PremiumSmartRuPolicy,
    client: httpx.Client,
    *,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> tuple[VerifiedSource, ...]:
    if max_source_bytes <= 0:
        raise ValueError("max_source_bytes must be positive")

    verified: list[VerifiedSource] = []
    for source_id, source in sorted(policy.sources.items()):
        if source.kind != "http":
            continue
        integrity = source.integrity
        if integrity is None or not integrity.pinned or integrity.sha256 is None:
            raise SourceVerificationError(
                f"remote policy source {source_id!r} is not immutable"
            )
        if source.url is None:
            raise SourceVerificationError(
                f"remote policy source {source_id!r} has no URL"
            )

        try:
            with client.stream("GET", source.url) as response:
                response.raise_for_status()
                content = _read_bounded(response, max_source_bytes)
        except SourceVerificationError:
            raise
        except httpx.HTTPError as exc:
            raise SourceVerificationError(
                f"cannot fetch remote policy source {source_id!r}: {type(exc).__name__}"
            ) from exc

        actual_sha256 = hashlib.sha256(content).hexdigest()
        if actual_sha256 != integrity.sha256:
            raise SourceVerificationError(
                f"remote policy source {source_id!r} checksum mismatch: "
                f"expected {integrity.sha256}, got {actual_sha256}"
            )
        verified.append(
            VerifiedSource(
                source_id=source_id,
                bytes=len(content),
                sha256=actual_sha256,
            )
        )
    return tuple(verified)


def verify_remote_sources(
    policy_path: str | Path,
    *,
    timeout_seconds: float = 30.0,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> tuple[VerifiedSource, ...]:
    policy = load_policy(policy_path)
    timeout = httpx.Timeout(timeout_seconds)
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
        headers={"User-Agent": "CyberVPN-Policy-Compiler/1"},
    ) as client:
        return verify_policy_sources(
            policy,
            client,
            max_source_bytes=max_source_bytes,
        )
