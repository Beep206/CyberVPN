from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import Settings
from src.domain.entities import BootstrapTokenRecord, NodeCertificateRecord
from src.domain.enums import CertificateState


@dataclass(frozen=True)
class BootstrapIssuePreview:
    token: BootstrapTokenRecord
    auth_mount: str
    role_name: str
    response_wrap_ttl: str
    preview_only: bool


@dataclass(frozen=True)
class CertificateIssuePreview:
    certificate: NodeCertificateRecord
    auth_mount: str
    role_name: str
    preview_only: bool


class OpenBaoBootstrapManager:
    """Builds preview-safe bootstrap and certificate issuance records."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue_bootstrap_token(
        self,
        *,
        node_id: str,
        operation_run_id: str,
        wrap_ttl: str | None = None,
        ttl_minutes: int = 15,
    ) -> BootstrapIssuePreview:
        token = BootstrapTokenRecord(
            token_id=f"btk_{uuid.uuid4().hex}",
            node_id=node_id,
            operation_run_id=operation_run_id,
            wrapped_ref=f"wrapping/{uuid.uuid4().hex}",
            role_name=self._settings.openbao_bootstrap_role,
            wrap_ttl=wrap_ttl or self._settings.openbao_response_wrap_ttl,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        return BootstrapIssuePreview(
            token=token,
            auth_mount=self._settings.openbao_bootstrap_auth_mount,
            role_name=self._settings.openbao_bootstrap_role,
            response_wrap_ttl=token.wrap_ttl,
            preview_only=not self._settings.openbao_enabled,
        )

    def issue_node_certificate(
        self,
        *,
        node_id: str,
        common_name: str,
        ttl_hours: int,
    ) -> CertificateIssuePreview:
        issued_at = datetime.now(UTC)
        certificate = NodeCertificateRecord(
            certificate_id=f"crt_{uuid.uuid4().hex}",
            node_id=node_id,
            role_name=self._settings.openbao_fleet_cert_role,
            serial=uuid.uuid4().hex,
            common_name=common_name,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(hours=ttl_hours),
            state=CertificateState.ACTIVE,
        )
        return CertificateIssuePreview(
            certificate=certificate,
            auth_mount=self._settings.openbao_fleet_cert_auth_mount,
            role_name=self._settings.openbao_fleet_cert_role,
            preview_only=not self._settings.openbao_enabled,
        )
