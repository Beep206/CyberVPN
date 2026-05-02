from __future__ import annotations

from src.domain.entities import BootstrapTokenRecord, NodeRecord
from src.domain.enums import BootstrapState, LifecycleState
from src.domain.exceptions import NodeNotFoundError
from src.infra.database.repositories import FleetRequestRepository
from src.infra.secrets.openbao_manager import BootstrapIssuePreview, OpenBaoBootstrapManager


class BootstrapService:
    def __init__(self, repository: FleetRequestRepository, manager: OpenBaoBootstrapManager) -> None:
        self._repository = repository
        self._manager = manager

    async def issue_for_node(self, *, node_id: str, operation_run_id: str) -> tuple[NodeRecord, BootstrapIssuePreview]:
        node = await self._repository.get_node(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {node_id}")
        preview = self._manager.issue_bootstrap_token(node_id=node_id, operation_run_id=operation_run_id)
        await self._repository.create_bootstrap_token(preview.token)
        updated_node = await self._repository.upsert_node(
            NodeRecord(
                node_id=node.node_id,
                environment=node.environment,
                role=node.role,
                country=node.country,
                provider=node.provider,
                region=node.region,
                node_class=node.node_class,
                current_lifecycle_state=LifecycleState.BOOTSTRAP_ISSUED,
                enrollment_status=node.enrollment_status,
                bootstrap_state=BootstrapState.ISSUED,
                certificate_state=node.certificate_state,
                provider_resource_state=node.provider_resource_state,
                request_id=node.request_id,
                operation_run_id=operation_run_id,
                created_at=node.created_at,
            )
        )
        return updated_node, preview

