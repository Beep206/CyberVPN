from __future__ import annotations

import uuid

from src.domain.entities import FleetRequestRecord, FleetRequestSubmission, OperationRunRecord
from src.domain.enums import OperationStatus, RequestStatus
from src.domain.exceptions import RequestNotFoundError
from src.infra.database.repositories import FleetRequestRepository
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter

from .audit_service import AuditTrailService


class FleetRequestService:
    def __init__(
        self,
        repository: FleetRequestRepository,
        audit_service: AuditTrailService,
        nats_adapter: NatsJetStreamAdapter,
    ) -> None:
        self._repository = repository
        self._audit_service = audit_service
        self._nats_adapter = nats_adapter

    async def submit(
        self,
        command: FleetRequestSubmission,
        *,
        initial_status: RequestStatus = RequestStatus.ACCEPTED,
    ) -> tuple[FleetRequestRecord, OperationRunRecord]:
        existing = await self._repository.get_request_by_idempotency_key(command.idempotency_key)
        if existing is not None:
            operation_runs = await self._repository.get_operation_runs_for_request(existing.request_id)
            operation_run = operation_runs[-1]
            return existing, operation_run

        request = FleetRequestRecord(
            request_id=f"req_{uuid.uuid4().hex}",
            request_type=command.request_type,
            requested_by=command.requested_by,
            idempotency_key=command.idempotency_key,
            status=initial_status,
            environment=command.environment,
            country=command.country,
            provider_selector=command.provider_selector,
            region_selector=command.region_selector,
            node_class=command.node_class,
            node_pool_id=command.node_pool_id,
            target_node_id=command.target_node_id,
            reason_code=command.reason_code,
            approval_mode=command.approval_mode,
            requested_capacity_delta=command.requested_capacity_delta,
            correlation_id=command.correlation_id or f"corr_{uuid.uuid4().hex}",
            signal_group_id=command.signal_group_id,
            confidence_score=command.confidence_score,
        )
        operation_run = OperationRunRecord(
            operation_run_id=f"opr_{uuid.uuid4().hex}",
            request_id=request.request_id,
            operation_name=f"{command.request_type.value}_workflow",
            status=OperationStatus.PENDING,
            current_step=self._initial_step_for_status(initial_status),
        )
        request, operation_run = await self._repository.create_request(request, operation_run)
        event_type = self._event_type_for_status(initial_status)
        await self._audit_service.record_request_event(
            event_type=event_type,
            actor=command.requested_by,
            request=request,
            operation_run=operation_run,
            payload={
                "country": command.country,
                "provider_selector": command.provider_selector,
                "target_node_id": command.target_node_id,
                "requested_capacity_delta": command.requested_capacity_delta,
                "signal_group_id": command.signal_group_id,
                "confidence_score": command.confidence_score,
            },
        )
        if initial_status is RequestStatus.ACCEPTED:
            preview = await self._nats_adapter.publish_request_accepted(request=request, operation_run=operation_run)
            await self._audit_service.record_request_event(
                event_type="fleet.request.command_published",
                actor=command.requested_by,
                request=request,
                operation_run=operation_run,
                payload={"subject": preview.subject, "published": preview.published},
            )
        return request, operation_run

    async def get_request(self, request_id: str) -> FleetRequestRecord:
        request = await self._repository.get_request(request_id)
        if request is None:
            raise RequestNotFoundError(f"Request not found: {request_id}")
        return request

    async def list_request_audit(self, request_id: str):
        return await self._repository.list_audit_entries(request_id=request_id)

    @staticmethod
    def _initial_step_for_status(status: RequestStatus) -> str:
        if status is RequestStatus.BLOCKED_POLICY:
            return "request_blocked_policy"
        if status is RequestStatus.AWAITING_APPROVAL:
            return "request_awaiting_approval"
        return "request_accepted"

    @staticmethod
    def _event_type_for_status(status: RequestStatus) -> str:
        if status is RequestStatus.BLOCKED_POLICY:
            return "fleet.request.blocked_policy"
        if status is RequestStatus.AWAITING_APPROVAL:
            return "fleet.request.awaiting_approval"
        return "fleet.request.accepted"
