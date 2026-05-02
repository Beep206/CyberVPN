from __future__ import annotations

import os
import tempfile
import unittest

from src.application.services.bootstrap_service import BootstrapService
from src.application.services.enrollment_service import EnrollmentService
from src.application.services.identity_service import IdentityService
from src.application.services.request_service import FleetRequestService
from src.config import Settings
from src.domain.entities import EnrollmentCompletion, FleetRequestSubmission, NodeRecord
from src.domain.enums import (
    BootstrapState,
    CertificateState,
    EnrollmentStatus,
    LifecycleState,
    ProviderResourceState,
    RequestType,
)
from src.infra.database.repositories import FleetRequestRepository
from src.infra.database.session import dispose_database, get_session_factory, initialize_database
from src.infra.messaging.nats_adapter import NatsJetStreamAdapter
from src.infra.secrets.openbao_manager import OpenBaoBootstrapManager
from src.application.services.audit_service import AuditTrailService


class P32ServicesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tempdir.cleanup)
        database_path = os.path.join(self._tempdir.name, "fleet-controller-p32.sqlite3")
        self.settings = Settings(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            nats_publish_enabled=False,
            openbao_enabled=False,
            environment="test",
        )
        await initialize_database(self.settings)

    async def asyncTearDown(self) -> None:
        await dispose_database(self.settings)

    async def test_bootstrap_enrollment_and_rotation_flow(self) -> None:
        session_factory = get_session_factory(self.settings)
        async with session_factory() as session:
            repository = FleetRequestRepository(session)
            audit_service = AuditTrailService(repository)
            request_service = FleetRequestService(repository, audit_service, NatsJetStreamAdapter(self.settings))

            request, operation = await request_service.submit(
                FleetRequestSubmission(
                    request_type=RequestType.PROVISIONING,
                    requested_by="operator@example.com",
                    idempotency_key="provision-node-fr-001",
                    environment="nonprod",
                    country="fr",
                    provider_selector="auto",
                    node_class="standard",
                )
            )
            await repository.upsert_node(
                NodeRecord(
                    node_id="node_fr_01",
                    environment="nonprod",
                    role="vpn",
                    country="fr",
                    provider="hetzner",
                    region="hel1",
                    node_class="standard",
                    current_lifecycle_state=LifecycleState.VM_CREATED,
                    enrollment_status=EnrollmentStatus.PENDING,
                    bootstrap_state=BootstrapState.NOT_ISSUED,
                    certificate_state=CertificateState.NOT_ISSUED,
                    provider_resource_state=ProviderResourceState.ACTIVE,
                    request_id=request.request_id,
                    operation_run_id=operation.operation_run_id,
                )
            )
            openbao = OpenBaoBootstrapManager(self.settings)
            bootstrap_service = BootstrapService(repository, openbao)
            enrollment_service = EnrollmentService(repository, openbao)
            identity_service = IdentityService(repository, openbao)

            node_after_bootstrap, bootstrap_preview = await bootstrap_service.issue_for_node(
                node_id="node_fr_01",
                operation_run_id=operation.operation_run_id,
            )
            node_after_enrollment, certificate_preview = await enrollment_service.complete(
                completion=EnrollmentCompletion(
                    node_id="node_fr_01",
                    reported_role="vpn",
                    certificate_common_name="node-fr-01.fleet.nonprod.internal.cybervpn",
                ),
                bootstrap_token_id=bootstrap_preview.token.token_id,
            )
            node_after_rotation, rotated_certificate = await identity_service.rotate_certificate(
                node_id="node_fr_01",
                common_name="node-fr-01-rotated.fleet.nonprod.internal.cybervpn",
                ttl_hours=12,
            )
            await session.commit()

        self.assertEqual(node_after_bootstrap.bootstrap_state, BootstrapState.ISSUED)
        self.assertEqual(node_after_enrollment.certificate_state, CertificateState.ACTIVE)
        self.assertEqual(node_after_rotation.current_lifecycle_state, LifecycleState.ROTATING)
        self.assertEqual(certificate_preview.auth_mount, self.settings.openbao_fleet_cert_auth_mount)
        self.assertEqual(rotated_certificate.certificate.common_name, "node-fr-01-rotated.fleet.nonprod.internal.cybervpn")
