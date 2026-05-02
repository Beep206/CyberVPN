from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import AuditTrailService
from src.application.services.bootstrap_service import BootstrapService
from src.application.services.enrollment_service import EnrollmentService
from src.application.services.executor_service import ExecutorService
from src.application.services.external_node_baseline_service import ExternalNodeBaselineService
from src.application.services.failover_policy_service import FailoverPolicyService
from src.application.services.identity_service import IdentityService
from src.application.services.operator_command_service import OperatorCommandService
from src.application.services.reconciler import ReconcilerService
from src.application.services.request_service import FleetRequestService
from src.application.services.workflow_engine import WorkflowEngine
from src.config import Settings
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import get_db_session
from src.infra.execution.opentofu_executor import OpenTofuExecutor
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter
from src.infra.secrets.openbao_manager import OpenBaoBootstrapManager


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_session(settings: Settings = Depends(get_app_settings)) -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session(settings):
        yield session


def get_nats_adapter(request: Request) -> NatsJetStreamAdapter:
    return request.app.state.nats_adapter


def get_workflow_engine(request: Request) -> WorkflowEngine:
    return request.app.state.workflow_engine


def get_opentofu_executor(request: Request) -> OpenTofuExecutor:
    return request.app.state.opentofu_executor


def get_openbao_manager(request: Request) -> OpenBaoBootstrapManager:
    return request.app.state.openbao_manager


def get_request_service(
    session: AsyncSession = Depends(get_session),
    nats_adapter: NatsJetStreamAdapter = Depends(get_nats_adapter),
) -> FleetRequestService:
    repository = FleetRequestRepository(session)
    audit_service = AuditTrailService(repository)
    return FleetRequestService(repository, audit_service, nats_adapter)


def get_reconciler_service(
    session: AsyncSession = Depends(get_session),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
) -> ReconcilerService:
    repository = FleetRequestRepository(session)
    return ReconcilerService(repository, workflow_engine)


def get_executor_service(
    session: AsyncSession = Depends(get_session),
    executor: OpenTofuExecutor = Depends(get_opentofu_executor),
) -> ExecutorService:
    return ExecutorService(FleetRequestRepository(session), executor)


def get_bootstrap_service(
    session: AsyncSession = Depends(get_session),
    openbao_manager: OpenBaoBootstrapManager = Depends(get_openbao_manager),
) -> BootstrapService:
    return BootstrapService(FleetRequestRepository(session), openbao_manager)


def get_enrollment_service(
    session: AsyncSession = Depends(get_session),
    openbao_manager: OpenBaoBootstrapManager = Depends(get_openbao_manager),
) -> EnrollmentService:
    return EnrollmentService(FleetRequestRepository(session), openbao_manager)


def get_identity_service(
    session: AsyncSession = Depends(get_session),
    openbao_manager: OpenBaoBootstrapManager = Depends(get_openbao_manager),
) -> IdentityService:
    return IdentityService(FleetRequestRepository(session), openbao_manager)


def get_external_node_baseline_service(
    session: AsyncSession = Depends(get_session),
) -> ExternalNodeBaselineService:
    return ExternalNodeBaselineService(FleetRequestRepository(session))


def get_operator_command_service(
    session: AsyncSession = Depends(get_session),
    nats_adapter: NatsJetStreamAdapter = Depends(get_nats_adapter),
) -> OperatorCommandService:
    repository = FleetRequestRepository(session)
    audit_service = AuditTrailService(repository)
    request_service = FleetRequestService(repository, audit_service, nats_adapter)
    return OperatorCommandService(repository, request_service)


def get_failover_policy_service(
    session: AsyncSession = Depends(get_session),
    nats_adapter: NatsJetStreamAdapter = Depends(get_nats_adapter),
) -> FailoverPolicyService:
    repository = FleetRequestRepository(session)
    audit_service = AuditTrailService(repository)
    request_service = FleetRequestService(repository, audit_service, nats_adapter)
    return FailoverPolicyService(repository, request_service, audit_service)
