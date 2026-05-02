from __future__ import annotations

import uuid

from src.domain.entities import AuditEntryRecord, FleetRequestRecord, OperationRunRecord
from src.infra.database.repositories import FleetRequestRepository


class AuditTrailService:
    def __init__(self, repository: FleetRequestRepository) -> None:
        self._repository = repository

    async def record_request_event(
        self,
        *,
        event_type: str,
        actor: str,
        request: FleetRequestRecord,
        operation_run: OperationRunRecord | None = None,
        payload: dict[str, object] | None = None,
    ) -> AuditEntryRecord:
        entry = AuditEntryRecord(
            audit_entry_id=f"audit_{uuid.uuid4().hex}",
            event_type=event_type,
            actor=actor,
            request_id=request.request_id,
            operation_run_id=operation_run.operation_run_id if operation_run is not None else None,
            payload={
                "request_type": request.request_type.value,
                "request_status": request.status.value,
                **(payload or {}),
            },
        )
        return await self._repository.append_audit_entry(entry)

