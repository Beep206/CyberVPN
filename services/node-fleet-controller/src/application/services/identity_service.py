from __future__ import annotations

from src.domain.entities import NodeRecord
from src.domain.enums import CertificateState, LifecycleState
from src.domain.exceptions import NodeNotFoundError
from src.infra.database.repositories import FleetRequestRepository
from src.infra.secrets.openbao_manager import CertificateIssuePreview, OpenBaoBootstrapManager


class IdentityService:
    def __init__(self, repository: FleetRequestRepository, openbao: OpenBaoBootstrapManager) -> None:
        self._repository = repository
        self._openbao = openbao

    async def rotate_certificate(
        self,
        *,
        node_id: str,
        common_name: str,
        ttl_hours: int,
    ) -> tuple[NodeRecord, CertificateIssuePreview]:
        node = await self._repository.get_node(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {node_id}")
        existing_certificates = await self._repository.list_certificates(node_id)
        for certificate in existing_certificates:
            if certificate.revoked_at is None and certificate.state is CertificateState.ACTIVE:
                await self._repository.revoke_certificate(certificate.certificate_id, revoked_at=certificate.issued_at)
        preview = self._openbao.issue_node_certificate(
            node_id=node_id,
            common_name=common_name,
            ttl_hours=ttl_hours,
        )
        await self._repository.create_certificate(preview.certificate)
        updated_node = await self._repository.upsert_node(
            NodeRecord(
                node_id=node.node_id,
                environment=node.environment,
                role=node.role,
                country=node.country,
                provider=node.provider,
                region=node.region,
                node_class=node.node_class,
                current_lifecycle_state=LifecycleState.ROTATING,
                enrollment_status=node.enrollment_status,
                bootstrap_state=node.bootstrap_state,
                certificate_state=CertificateState.ROTATING,
                provider_resource_state=node.provider_resource_state,
                request_id=node.request_id,
                operation_run_id=node.operation_run_id,
                created_at=node.created_at,
            )
        )
        return updated_node, preview
