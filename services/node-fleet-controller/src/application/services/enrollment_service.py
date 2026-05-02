from __future__ import annotations

from src.domain.entities import EnrollmentCompletion, NodeRecord
from src.domain.enums import BootstrapState, CertificateState, EnrollmentStatus, LifecycleState
from src.domain.exceptions import NodeNotFoundError
from src.infra.database.repositories import FleetRequestRepository
from src.infra.secrets.openbao_manager import CertificateIssuePreview, OpenBaoBootstrapManager


class EnrollmentService:
    def __init__(self, repository: FleetRequestRepository, openbao: OpenBaoBootstrapManager) -> None:
        self._repository = repository
        self._openbao = openbao

    async def complete(
        self,
        *,
        completion: EnrollmentCompletion,
        bootstrap_token_id: str,
    ) -> tuple[NodeRecord, CertificateIssuePreview]:
        node = await self._repository.get_node(completion.node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {completion.node_id}")
        certificate_preview = self._openbao.issue_node_certificate(
            node_id=node.node_id,
            common_name=completion.certificate_common_name,
            ttl_hours=completion.certificate_ttl_hours,
        )
        await self._repository.mark_bootstrap_token_consumed(bootstrap_token_id, consumed_at=certificate_preview.certificate.issued_at)
        await self._repository.create_certificate(certificate_preview.certificate)
        updated_node = await self._repository.upsert_node(
            NodeRecord(
                node_id=node.node_id,
                environment=node.environment,
                role=completion.reported_role,
                country=node.country,
                provider=node.provider,
                region=node.region,
                node_class=node.node_class,
                current_lifecycle_state=LifecycleState.CONFIGURING,
                enrollment_status=EnrollmentStatus.ACCEPTED,
                bootstrap_state=BootstrapState.CONSUMED,
                certificate_state=CertificateState.ACTIVE,
                provider_resource_state=node.provider_resource_state,
                request_id=node.request_id,
                operation_run_id=node.operation_run_id,
                created_at=node.created_at,
            )
        )
        return updated_node, certificate_preview

