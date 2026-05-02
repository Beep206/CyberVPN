from __future__ import annotations

import re

from src.application.services.request_service import FleetRequestService
from src.domain.entities import FleetRequestSubmission, NodePoolRecord, OperatorCommandResult
from src.domain.enums import RequestType
from src.domain.exceptions import NodeNotFoundError, NodePoolNotFoundError
from src.infra.database.repositories import FleetRequestRepository


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "default"


class OperatorCommandService:
    def __init__(self, repository: FleetRequestRepository, request_service: FleetRequestService) -> None:
        self._repository = repository
        self._request_service = request_service

    async def upsert_node_pool(self, pool: NodePoolRecord) -> NodePoolRecord:
        return await self._repository.upsert_node_pool(pool)

    async def get_node_pool(self, node_pool_id: str) -> NodePoolRecord:
        pool = await self._repository.get_node_pool(node_pool_id)
        if pool is None:
            raise NodePoolNotFoundError(f"Node pool not found: {node_pool_id}")
        return pool

    async def submit_node_add(
        self,
        *,
        requested_by: str,
        idempotency_key: str,
        environment: str,
        country: str,
        role: str,
        node_class: str,
        provider_selector: str | None,
        region_selector: str | None,
        requested_capacity_delta: int,
        approval_mode: str,
        node_pool_id: str | None = None,
    ) -> OperatorCommandResult:
        pool_id = node_pool_id or self._derive_pool_id(
            environment=environment,
            country=country,
            role=role,
            node_class=node_class,
        )
        existing_pool = await self._repository.get_node_pool(pool_id)
        desired_capacity = (existing_pool.desired_capacity if existing_pool is not None else 0) + requested_capacity_delta
        pool_kwargs = {
            "node_pool_id": pool_id,
            "environment": environment,
            "country": country,
            "role": role,
            "node_class": node_class,
            "provider_selector": provider_selector,
            "region_selector": region_selector,
            "desired_capacity": max(desired_capacity, 0),
            "current_capacity": existing_pool.current_capacity if existing_pool is not None else 0,
        }
        if existing_pool is not None:
            pool_kwargs["created_at"] = existing_pool.created_at
        pool = await self._repository.upsert_node_pool(NodePoolRecord(**pool_kwargs))
        request, operation_run = await self._request_service.submit(
            FleetRequestSubmission(
                request_type=RequestType.PROVISIONING,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                environment=environment,
                country=country,
                provider_selector=provider_selector,
                region_selector=region_selector,
                node_class=node_class,
                node_pool_id=pool.node_pool_id,
                approval_mode=approval_mode,
                requested_capacity_delta=requested_capacity_delta,
            )
        )
        return OperatorCommandResult(
            command_name="node-add",
            request=request,
            operation_run=operation_run,
            node_pool=pool,
        )

    async def submit_node_replace(
        self,
        *,
        requested_by: str,
        idempotency_key: str,
        target_node_id: str,
        reason_code: str,
        approval_mode: str,
    ) -> OperatorCommandResult:
        node = await self._repository.get_node(target_node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {target_node_id}")
        request, operation_run = await self._request_service.submit(
            FleetRequestSubmission(
                request_type=RequestType.REPLACEMENT,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                environment=node.environment,
                country=node.country,
                provider_selector=node.provider,
                region_selector=node.region,
                node_class=node.node_class,
                target_node_id=target_node_id,
                reason_code=reason_code,
                approval_mode=approval_mode,
            )
        )
        return OperatorCommandResult(command_name="node-replace", request=request, operation_run=operation_run)

    async def submit_node_drain(
        self,
        *,
        requested_by: str,
        idempotency_key: str,
        target_node_id: str,
        reason_code: str,
        approval_mode: str,
    ) -> OperatorCommandResult:
        node = await self._repository.get_node(target_node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {target_node_id}")
        request, operation_run = await self._request_service.submit(
            FleetRequestSubmission(
                request_type=RequestType.DRAIN,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                environment=node.environment,
                country=node.country,
                provider_selector=node.provider,
                region_selector=node.region,
                node_class=node.node_class,
                target_node_id=target_node_id,
                reason_code=reason_code,
                approval_mode=approval_mode,
            )
        )
        return OperatorCommandResult(command_name="node-drain", request=request, operation_run=operation_run)

    async def submit_node_quarantine(
        self,
        *,
        requested_by: str,
        idempotency_key: str,
        target_node_id: str,
        reason_code: str,
        approval_mode: str,
    ) -> OperatorCommandResult:
        node = await self._repository.get_node(target_node_id)
        if node is None:
            raise NodeNotFoundError(f"Node not found: {target_node_id}")
        request, operation_run = await self._request_service.submit(
            FleetRequestSubmission(
                request_type=RequestType.QUARANTINE,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                environment=node.environment,
                country=node.country,
                provider_selector=node.provider,
                region_selector=node.region,
                node_class=node.node_class,
                target_node_id=target_node_id,
                reason_code=reason_code,
                approval_mode=approval_mode,
            )
        )
        return OperatorCommandResult(command_name="node-quarantine", request=request, operation_run=operation_run)

    async def adjust_pool_capacity(
        self,
        *,
        node_pool_id: str,
        requested_by: str,
        idempotency_key: str,
        target_desired_capacity: int,
        reason_code: str,
        approval_mode: str,
    ) -> OperatorCommandResult:
        pool = await self._repository.get_node_pool(node_pool_id)
        if pool is None:
            raise NodePoolNotFoundError(f"Node pool not found: {node_pool_id}")
        delta = target_desired_capacity - pool.desired_capacity
        updated_pool = await self._repository.upsert_node_pool(
            NodePoolRecord(
                node_pool_id=pool.node_pool_id,
                environment=pool.environment,
                country=pool.country,
                role=pool.role,
                node_class=pool.node_class,
                provider_selector=pool.provider_selector,
                region_selector=pool.region_selector,
                desired_capacity=target_desired_capacity,
                current_capacity=pool.current_capacity,
                created_at=pool.created_at,
            )
        )
        if delta == 0:
            return OperatorCommandResult(
                command_name="capacity-adjust",
                request=None,
                operation_run=None,
                node_pool=updated_pool,
                no_op_reason="desired_capacity_already_matches_target",
            )
        request_type = RequestType.PROVISIONING if delta > 0 else RequestType.DRAIN
        request, operation_run = await self._request_service.submit(
            FleetRequestSubmission(
                request_type=request_type,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                environment=pool.environment,
                country=pool.country,
                provider_selector=pool.provider_selector,
                region_selector=pool.region_selector,
                node_class=pool.node_class,
                node_pool_id=pool.node_pool_id,
                reason_code=reason_code,
                approval_mode=approval_mode,
                requested_capacity_delta=delta,
            )
        )
        return OperatorCommandResult(
            command_name="capacity-adjust",
            request=request,
            operation_run=operation_run,
            node_pool=updated_pool,
        )

    @staticmethod
    def _derive_pool_id(*, environment: str, country: str, role: str, node_class: str) -> str:
        return "-".join(
            (
                _slugify(environment),
                _slugify(country),
                _slugify(role),
                _slugify(node_class),
            )
        )
