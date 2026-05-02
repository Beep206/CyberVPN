from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_app_settings,
    get_bootstrap_service,
    get_enrollment_service,
    get_executor_service,
    get_external_node_baseline_service,
    get_failover_policy_service,
    get_identity_service,
    get_operator_command_service,
    get_reconciler_service,
    get_request_service,
    get_session,
)
from src.api.schemas import (
    AuditEntryResponse,
    BaselineProfileResponse,
    BootstrapTokenResponse,
    CapacityAdjustmentRequest,
    CreateFleetRequestRequest,
    CreateFleetRequestResponse,
    CreateNodeRequest,
    EnrollmentCompleteRequest,
    EnrollmentCompleteResponse,
    ExecutorPreviewRequest,
    ExecutorPreviewResponse,
    FailoverPolicyBundleResponse,
    FailoverPolicyBundleUpsertRequest,
    FleetRequestResponse,
    HealthResponse,
    HealthSignalIngestionResponse,
    HealthSignalRequest,
    HealthSignalResponse,
    IssueBootstrapTokenRequest,
    NodeAddCommandRequest,
    NodeCertificateResponse,
    NodeDrainCommandRequest,
    NodeFailoverCommandRequest,
    NodeObservedStateResponse,
    NodePoolResponse,
    NodePoolUpsertRequest,
    NodeQuarantineCommandRequest,
    NodeReplaceCommandRequest,
    NodeResponse,
    OperationRunResponse,
    OperatorCommandResponse,
    ReconcilePreviewItemResponse,
    ReconcilePreviewResponse,
    ReconcileRunOnceResponse,
    ReconcileRunResultResponse,
    ReportObservedStateRequest,
    RotateCertificateRequest,
    RotateCertificateResponse,
    RuntimeReadinessIngestionResponse,
    RuntimeReadinessRequest,
    RuntimeReadinessResponse,
    SentryContractResponse,
    SyntheticCheckIngestionResponse,
    SyntheticCheckRequest,
    SyntheticCheckResponse,
    TrafficEligibilityEvaluationResponse,
    TrafficEligibilityResponse,
)
from src.application.services.bootstrap_service import BootstrapService
from src.application.services.enrollment_service import EnrollmentService
from src.application.services.executor_service import ExecutorService
from src.application.services.external_node_baseline_service import ExternalNodeBaselineService
from src.application.services.failover_policy_service import FailoverPolicyService
from src.application.services.identity_service import IdentityService
from src.application.services.operator_command_service import OperatorCommandService
from src.application.services.reconciler import ReconcilerService
from src.application.services.request_service import FleetRequestService
from src.config import Settings
from src.domain.entities import EnrollmentCompletion, FleetRequestSubmission, NodePoolRecord, NodeRecord
from src.domain.enums import BootstrapState, CertificateState, EnrollmentStatus, LifecycleState, ProviderResourceState
from src.domain.exceptions import (
    FailoverPolicyNotFoundError,
    NodeNotFoundError,
    NodePoolNotFoundError,
    RequestNotFoundError,
)
from src.infra.database.repositories import FleetRequestRepository
from src.observability import is_observability_authorized

router = APIRouter(prefix="/api/v1", tags=["node-fleet-controller"])


@router.get("/health/live", response_model=HealthResponse, tags=["health"])
async def live_health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, environment=settings.environment)


@router.get("/observability/sentry-contract", response_model=SentryContractResponse, tags=["observability"])
async def sentry_contract(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> SentryContractResponse:
    provided_secret = request.headers.get("x-observability-secret")
    if not is_observability_authorized(settings.observability_internal_secret, provided_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return SentryContractResponse(
        runtime_surface="node-fleet-controller",
        service=settings.service_name,
        environment=settings.environment,
        release=settings.sentry_release,
        dsn_configured=bool(settings.sentry_dsn.strip()),
    )


@router.post("/requests", response_model=CreateFleetRequestResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_request(
    body: CreateFleetRequestRequest,
    service: FleetRequestService = Depends(get_request_service),
) -> CreateFleetRequestResponse:
    request, operation_run = await service.submit(
        FleetRequestSubmission(
            request_type=body.request_type,
            requested_by=body.requested_by,
            idempotency_key=body.idempotency_key,
            environment=body.environment,
            country=body.country,
            provider_selector=body.provider_selector,
            region_selector=body.region_selector,
            node_class=body.node_class,
            node_pool_id=body.node_pool_id,
            target_node_id=body.target_node_id,
            reason_code=body.reason_code,
            approval_mode=body.approval_mode,
            requested_capacity_delta=body.requested_capacity_delta,
            correlation_id=body.correlation_id,
            signal_group_id=body.signal_group_id,
            confidence_score=body.confidence_score,
        )
    )
    return CreateFleetRequestResponse(
        request=FleetRequestResponse.from_entity(request),
        operation_run=OperationRunResponse.from_entity(operation_run),
    )


@router.get("/requests/{request_id}", response_model=FleetRequestResponse)
async def get_request(
    request_id: str,
    service: FleetRequestService = Depends(get_request_service),
) -> FleetRequestResponse:
    try:
        request = await service.get_request(request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FleetRequestResponse.from_entity(request)


@router.get("/requests/{request_id}/audit", response_model=list[AuditEntryResponse])
async def get_request_audit(
    request_id: str,
    service: FleetRequestService = Depends(get_request_service),
) -> list[AuditEntryResponse]:
    return [AuditEntryResponse.from_entity(entry) for entry in await service.list_request_audit(request_id)]


@router.get("/reconcile/preview", response_model=ReconcilePreviewResponse)
async def preview_reconcile(
    limit: int = 25,
    service: ReconcilerService = Depends(get_reconciler_service),
) -> ReconcilePreviewResponse:
    items = await service.preview(limit=limit)
    return ReconcilePreviewResponse(items=[ReconcilePreviewItemResponse.from_entity(item) for item in items])


@router.post("/reconcile/run-once", response_model=ReconcileRunOnceResponse)
async def run_reconcile_once(
    limit: int = 25,
    service: ReconcilerService = Depends(get_reconciler_service),
) -> ReconcileRunOnceResponse:
    items = await service.run_once(limit=limit)
    return ReconcileRunOnceResponse(items=[ReconcileRunResultResponse.from_entity(item) for item in items])


@router.post("/nodes", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    body: CreateNodeRequest,
    session: AsyncSession = Depends(get_session),
) -> NodeResponse:
    repository = FleetRequestRepository(session)
    node = await repository.upsert_node(
        NodeRecord(
            node_id=body.node_id,
            environment=body.environment,
            role=body.role,
            country=body.country,
            provider=body.provider,
            region=body.region,
            node_class=body.node_class,
            current_lifecycle_state=LifecycleState.REQUESTED,
            enrollment_status=EnrollmentStatus.PENDING,
            bootstrap_state=BootstrapState.NOT_ISSUED,
            certificate_state=CertificateState.NOT_ISSUED,
            provider_resource_state=ProviderResourceState.PLANNED,
            request_id=body.request_id,
            operation_run_id=body.operation_run_id,
        )
    )
    return NodeResponse.from_entity(node)


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    session: AsyncSession = Depends(get_session),
) -> NodeResponse:
    repository = FleetRequestRepository(session)
    node = await repository.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node not found: {node_id}")
    return NodeResponse.from_entity(node)


@router.put("/node-pools/{node_pool_id}", response_model=NodePoolResponse)
async def upsert_node_pool(
    node_pool_id: str,
    body: NodePoolUpsertRequest,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> NodePoolResponse:
    pool = await service.upsert_node_pool(
        NodePoolRecord(
            node_pool_id=node_pool_id,
            environment=body.environment,
            country=body.country,
            role=body.role,
            node_class=body.node_class,
            provider_selector=body.provider_selector,
            region_selector=body.region_selector,
            desired_capacity=body.desired_capacity,
            current_capacity=body.current_capacity,
        )
    )
    return NodePoolResponse.from_entity(pool)


@router.get("/node-pools/{node_pool_id}", response_model=NodePoolResponse)
async def get_node_pool(
    node_pool_id: str,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> NodePoolResponse:
    try:
        pool = await service.get_node_pool(node_pool_id)
    except NodePoolNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NodePoolResponse.from_entity(pool)


@router.post("/requests/{request_id}/executor/preview", response_model=ExecutorPreviewResponse)
async def preview_request_executor(
    request_id: str,
    body: ExecutorPreviewRequest,
    request_service: FleetRequestService = Depends(get_request_service),
    executor_service: ExecutorService = Depends(get_executor_service),
    session: AsyncSession = Depends(get_session),
) -> ExecutorPreviewResponse:
    request = await request_service.get_request(request_id)
    repository = FleetRequestRepository(session)
    operation_runs = await repository.get_operation_runs_for_request(request_id)
    operation_run = operation_runs[-1]
    preview, _step = await executor_service.preview_plan(
        request=request,
        operation_run=operation_run,
        stack_slug=body.stack_slug,
        workspace_key=body.workspace_key,
        variables=body.variables,
    )
    return ExecutorPreviewResponse.from_entity(preview)


@router.post("/operator/node-add", response_model=OperatorCommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def operator_node_add(
    body: NodeAddCommandRequest,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> OperatorCommandResponse:
    result = await service.submit_node_add(
        requested_by=body.requested_by,
        idempotency_key=body.idempotency_key,
        environment=body.environment,
        country=body.country,
        role=body.role,
        node_class=body.node_class,
        provider_selector=body.provider_selector,
        region_selector=body.region_selector,
        requested_capacity_delta=body.requested_capacity_delta,
        approval_mode=body.approval_mode,
        node_pool_id=body.node_pool_id,
    )
    return OperatorCommandResponse.from_entity(result)


@router.post("/operator/node-replace", response_model=OperatorCommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def operator_node_replace(
    body: NodeReplaceCommandRequest,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> OperatorCommandResponse:
    try:
        result = await service.submit_node_replace(
            requested_by=body.requested_by,
            idempotency_key=body.idempotency_key,
            target_node_id=body.target_node_id,
            reason_code=body.reason_code,
            approval_mode=body.approval_mode,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OperatorCommandResponse.from_entity(result)


@router.post("/operator/node-drain", response_model=OperatorCommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def operator_node_drain(
    body: NodeDrainCommandRequest,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> OperatorCommandResponse:
    try:
        result = await service.submit_node_drain(
            requested_by=body.requested_by,
            idempotency_key=body.idempotency_key,
            target_node_id=body.target_node_id,
            reason_code=body.reason_code,
            approval_mode=body.approval_mode,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OperatorCommandResponse.from_entity(result)


@router.post("/operator/node-quarantine", response_model=OperatorCommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def operator_node_quarantine(
    body: NodeQuarantineCommandRequest,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> OperatorCommandResponse:
    try:
        result = await service.submit_node_quarantine(
            requested_by=body.requested_by,
            idempotency_key=body.idempotency_key,
            target_node_id=body.target_node_id,
            reason_code=body.reason_code,
            approval_mode=body.approval_mode,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OperatorCommandResponse.from_entity(result)


@router.put("/failover-policies/{scope_id}", response_model=FailoverPolicyBundleResponse)
async def upsert_failover_policy_bundle(
    scope_id: str,
    body: FailoverPolicyBundleUpsertRequest,
    service: FailoverPolicyService = Depends(get_failover_policy_service),
) -> FailoverPolicyBundleResponse:
    bundle = await service.upsert_policy_bundle(
        scope_id=scope_id,
        environment=body.environment,
        country=body.country,
        provider_selector=body.provider_selector,
        monthly_limit=body.budget_policy.monthly_limit,
        burst_limit=body.budget_policy.burst_limit,
        current_month_spend=body.budget_policy.current_month_spend,
        max_actions_per_window=body.rate_limit_policy.max_actions_per_window,
        window_seconds=body.rate_limit_policy.window_seconds,
        cooldown_seconds=body.rate_limit_policy.cooldown_seconds,
        max_parallel_failovers=body.rate_limit_policy.max_parallel_failovers,
        risk_threshold=body.approval_policy.risk_threshold,
        budget_approval_threshold=body.approval_policy.budget_approval_threshold,
        approval_mode=body.approval_policy.approval_mode,
        require_human_above_threshold=body.approval_policy.require_human_above_threshold,
        confidence_score_threshold=body.guardrail_policy.confidence_score_threshold,
        minimum_independent_signal_sources=body.guardrail_policy.minimum_independent_signal_sources,
        country_emergency_stop=body.guardrail_policy.country_emergency_stop,
        node_class_allowlist=tuple(body.guardrail_policy.node_class_allowlist),
        provider_exclusion_window_seconds=body.guardrail_policy.provider_exclusion_window_seconds,
        traffic_canary_required=body.guardrail_policy.traffic_canary_required,
        rollback_and_drain_policy=body.guardrail_policy.rollback_and_drain_policy,
    )
    return FailoverPolicyBundleResponse.from_entity(bundle)


@router.get("/failover-policies/{scope_id}", response_model=FailoverPolicyBundleResponse)
async def get_failover_policy_bundle(
    scope_id: str,
    service: FailoverPolicyService = Depends(get_failover_policy_service),
) -> FailoverPolicyBundleResponse:
    try:
        bundle = await service.get_policy_bundle(scope_id)
    except FailoverPolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FailoverPolicyBundleResponse.from_entity(bundle)


@router.post("/operator/node-failover", response_model=OperatorCommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def operator_node_failover(
    body: NodeFailoverCommandRequest,
    service: FailoverPolicyService = Depends(get_failover_policy_service),
) -> OperatorCommandResponse:
    try:
        result = await service.submit_failover(
            requested_by=body.requested_by,
            idempotency_key=body.idempotency_key,
            environment=body.environment,
            country=body.country,
            node_class=body.node_class,
            provider_selector=body.provider_selector,
            region_selector=body.region_selector,
            requested_capacity_delta=body.requested_capacity_delta,
            approval_mode=body.approval_mode,
            signal_group_id=body.signal_group_id,
            confidence_score=body.confidence_score,
            independent_signal_sources=body.independent_signal_sources,
            budget_impact=body.budget_impact,
            risk_score=body.risk_score,
            reason_code=body.reason_code,
            node_pool_id=body.node_pool_id,
            target_node_id=body.target_node_id,
        )
    except (FailoverPolicyNotFoundError, NodePoolNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OperatorCommandResponse.from_entity(result)


@router.post(
    "/node-pools/{node_pool_id}/capacity",
    response_model=OperatorCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def adjust_node_pool_capacity(
    node_pool_id: str,
    body: CapacityAdjustmentRequest,
    service: OperatorCommandService = Depends(get_operator_command_service),
) -> OperatorCommandResponse:
    try:
        result = await service.adjust_pool_capacity(
            node_pool_id=node_pool_id,
            requested_by=body.requested_by,
            idempotency_key=body.idempotency_key,
            target_desired_capacity=body.target_desired_capacity,
            reason_code=body.reason_code,
            approval_mode=body.approval_mode,
        )
    except NodePoolNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OperatorCommandResponse.from_entity(result)


@router.post(
    "/nodes/{node_id}/bootstrap-tokens",
    response_model=BootstrapTokenResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def issue_bootstrap_token(
    node_id: str,
    body: IssueBootstrapTokenRequest,
    service: BootstrapService = Depends(get_bootstrap_service),
) -> BootstrapTokenResponse:
    try:
        _node, preview = await service.issue_for_node(node_id=node_id, operation_run_id=body.operation_run_id)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BootstrapTokenResponse.from_entity(preview.token)


@router.post("/nodes/{node_id}/enrollment/complete", response_model=EnrollmentCompleteResponse)
async def complete_enrollment(
    node_id: str,
    body: EnrollmentCompleteRequest,
    service: EnrollmentService = Depends(get_enrollment_service),
) -> EnrollmentCompleteResponse:
    try:
        node, certificate_preview = await service.complete(
            completion=EnrollmentCompletion(
                node_id=node_id,
                reported_role=body.reported_role,
                certificate_common_name=body.certificate_common_name,
                certificate_ttl_hours=body.certificate_ttl_hours,
            ),
            bootstrap_token_id=body.bootstrap_token_id,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EnrollmentCompleteResponse(
        node=NodeResponse.from_entity(node),
        certificate=NodeCertificateResponse.from_entity(certificate_preview.certificate),
    )


@router.post("/nodes/{node_id}/identity/rotate", response_model=RotateCertificateResponse)
async def rotate_node_identity(
    node_id: str,
    body: RotateCertificateRequest,
    service: IdentityService = Depends(get_identity_service),
) -> RotateCertificateResponse:
    try:
        node, preview = await service.rotate_certificate(
            node_id=node_id,
            common_name=body.common_name,
            ttl_hours=body.ttl_hours,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RotateCertificateResponse(
        node=NodeResponse.from_entity(node),
        certificate=NodeCertificateResponse.from_entity(preview.certificate),
    )


@router.get("/nodes/{node_id}/baseline", response_model=BaselineProfileResponse)
async def get_node_baseline(
    node_id: str,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> BaselineProfileResponse:
    try:
        profile = await service.get_baseline_profile(node_id=node_id)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BaselineProfileResponse.from_entity(profile)


@router.post("/nodes/{node_id}/observed-state", response_model=NodeObservedStateResponse)
async def report_node_observed_state(
    node_id: str,
    body: ReportObservedStateRequest,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> NodeObservedStateResponse:
    try:
        observed = await service.report_observed_state(
            node_id=node_id,
            services_status={key: value.value for key, value in body.services_status.items()},
            alloy_telemetry_flowing=body.alloy_telemetry_flowing,
            enrollment_hook_completed=body.enrollment_hook_completed,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NodeObservedStateResponse.from_entity(observed)


@router.post("/nodes/{node_id}/health-signals", response_model=HealthSignalIngestionResponse)
async def ingest_node_health_signal(
    node_id: str,
    body: HealthSignalRequest,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> HealthSignalIngestionResponse:
    try:
        signal, observed = await service.ingest_health_signal(
            node_id=node_id,
            signal_type=body.signal_type,
            severity=body.severity,
            source=body.source,
            component=body.component,
            details=body.details,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return HealthSignalIngestionResponse(
        signal=HealthSignalResponse.from_entity(signal),
        observed_state=NodeObservedStateResponse.from_entity(observed),
    )


@router.post("/nodes/{node_id}/synthetic-checks", response_model=SyntheticCheckIngestionResponse)
async def record_synthetic_check(
    node_id: str,
    body: SyntheticCheckRequest,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> SyntheticCheckIngestionResponse:
    try:
        check, observed = await service.record_synthetic_check(
            node_id=node_id,
            probe=body.probe,
            status=body.status,
            source=body.source,
            details=body.details,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SyntheticCheckIngestionResponse(
        check=SyntheticCheckResponse.from_entity(check),
        observed_state=NodeObservedStateResponse.from_entity(observed),
    )


@router.post("/nodes/{node_id}/runtime-readiness", response_model=RuntimeReadinessIngestionResponse)
async def record_runtime_readiness(
    node_id: str,
    body: RuntimeReadinessRequest,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> RuntimeReadinessIngestionResponse:
    try:
        readiness, observed = await service.record_runtime_readiness(
            node_id=node_id,
            adapter_slug=body.adapter_slug,
            ack_state=body.ack_state,
            details=body.details,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RuntimeReadinessIngestionResponse(
        readiness=RuntimeReadinessResponse.from_entity(readiness),
        observed_state=NodeObservedStateResponse.from_entity(observed),
    )


@router.get("/nodes/{node_id}/traffic-eligibility", response_model=TrafficEligibilityResponse)
async def get_node_traffic_eligibility(
    node_id: str,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> TrafficEligibilityResponse:
    try:
        eligibility = await service.get_traffic_eligibility(node_id=node_id)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if eligibility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Traffic eligibility not found: {node_id}")
    return TrafficEligibilityResponse.from_entity(eligibility)


@router.post("/nodes/{node_id}/traffic-eligibility/evaluate", response_model=TrafficEligibilityEvaluationResponse)
async def evaluate_node_traffic_eligibility(
    node_id: str,
    service: ExternalNodeBaselineService = Depends(get_external_node_baseline_service),
) -> TrafficEligibilityEvaluationResponse:
    try:
        evaluation = await service.evaluate_traffic_eligibility(node_id=node_id)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TrafficEligibilityEvaluationResponse.from_entity(evaluation)
