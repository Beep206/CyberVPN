from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.application.services.vpn_product_readiness import (
    SPB_DE_EXCEPTIONS_PRODUCT_CODE,
    SPB_DE_EXCEPTIONS_READINESS_JWT_ALGORITHM,
    SPB_DE_EXCEPTIONS_READINESS_SCHEMA,
    SPB_DE_EXCEPTIONS_READINESS_SCHEMA_VERSION,
)
from src.config.settings import settings


@dataclass(frozen=True)
class SpbDeReadinessTestArtifact:
    token: str
    public_key: str
    private_key: str
    payload: dict[str, Any]


def make_spb_de_readiness_attestation(
    *,
    payload_overrides: Mapping[str, Any] | None = None,
    private_key: Ed25519PrivateKey | None = None,
) -> SpbDeReadinessTestArtifact:
    signing_key = private_key or Ed25519PrivateKey.generate()
    private_pem = signing_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        signing_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    payload: dict[str, Any] = {
        "schema": SPB_DE_EXCEPTIONS_READINESS_SCHEMA,
        "version": SPB_DE_EXCEPTIONS_READINESS_SCHEMA_VERSION,
        "product_key": SPB_DE_EXCEPTIONS_PRODUCT_CODE,
        "policy_version": "premium_spb_de_exceptions.v1",
        "issued_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "expires_at": datetime(2099, 1, 1, tzinfo=UTC).isoformat(),
        "policy_hash": "sha256:policy-ready",
        "manifest_hash": "sha256:manifest-ready",
        "runtime_evidence_id": "task2-runtime-evidence-20260711",
        "attestation_id": "task2-attestation-20260711",
        "approval_status": "approved",
        "approved_at": datetime(2026, 1, 1, 1, tzinfo=UTC).isoformat(),
        "approved_by": "ops-readiness",
        "revoked": False,
    }
    if payload_overrides is not None:
        for key, value in payload_overrides.items():
            if value is None:
                payload.pop(key, None)
            else:
                payload[key] = value
    token = jwt.encode(payload, private_pem, algorithm=SPB_DE_EXCEPTIONS_READINESS_JWT_ALGORITHM)
    return SpbDeReadinessTestArtifact(
        token=token,
        public_key=public_pem,
        private_key=private_pem,
        payload=payload,
    )


def enable_spb_de_readiness(monkeypatch: pytest.MonkeyPatch) -> SpbDeReadinessTestArtifact:
    artifact = make_spb_de_readiness_attestation()
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", artifact.token)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", artifact.public_key)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_revoked_attestation_ids", "")
    return artifact
