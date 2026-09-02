import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.config.settings import settings
from src.presentation.api.v1.remnawave_status import routes
from src.presentation.api.v1.remnawave_status.routes import (
    AdminRemnawaveCapabilities,
    _build_admin_capabilities,
    _numeric_identity_cutover_ready,
    get_admin_remnawave_capabilities_and_streams,
    get_customer_vpn_service_status,
    get_partner_vpn_service_status,
)
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import get_partner_workspace_access

_STREAM_NAMES = ("user_usage", "subscription_requests", "node_connections")


def _stream_health_db(
    *,
    receipt_rows: list[tuple[str, datetime]],
    dead_letter_rows: list[tuple[str, int]] | None = None,
    gap_rows: list[tuple[str, int]] | None = None,
    checkpoint_rows: list[tuple[str, int | None, int, bool, bool, datetime | None]] | None = None,
) -> AsyncMock:
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(all=lambda: receipt_rows),
        SimpleNamespace(all=lambda: dead_letter_rows or []),
        SimpleNamespace(all=lambda: gap_rows or []),
        SimpleNamespace(all=lambda: checkpoint_rows or []),
    ]
    return db


@pytest.mark.unit
def test_admin_capabilities_schema_requires_all_named_fields() -> None:
    required = set(AdminRemnawaveCapabilities.model_json_schema()["required"])

    assert required == {
        "numeric_user_ids",
        "connections",
        "geo_check",
        "node_integrations",
        "shared_lists",
        "node_ssh",
        "tags",
        "host_mapper",
        "root_snippets",
        "redis_stream_export",
    }


@pytest.mark.unit
def test_admin_capabilities_fail_closed_without_exact_target_panel(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    capabilities = _build_admin_capabilities(panel_version=None, node_ssh_available=True)

    assert not any(capabilities.model_dump().values())


@pytest.mark.unit
def test_admin_numeric_and_stream_capabilities_require_observed_readiness(monkeypatch) -> None:
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    unproved = _build_admin_capabilities(panel_version="3.4.3", node_ssh_available=False)
    proved = _build_admin_capabilities(
        panel_version="3.4.3",
        node_ssh_available=False,
        numeric_cutover_ready=True,
        stream_export_observed=True,
    )

    assert unproved.numeric_user_ids is False
    assert unproved.redis_stream_export is False
    assert proved.numeric_user_ids is True
    assert proved.redis_stream_export is True


@pytest.mark.unit
async def test_numeric_cutover_readiness_requires_zero_unresolved_and_full_exact_coverage() -> None:
    ready_db = AsyncMock()
    ready_db.execute.side_effect = [
        SimpleNamespace(scalar_one=lambda: 0),
        SimpleNamespace(scalar_one=lambda: 0),
        SimpleNamespace(scalar_one=lambda: 0),
        SimpleNamespace(scalar_one=lambda: 0),
    ]
    unresolved_db = AsyncMock()
    unresolved_db.execute.return_value = SimpleNamespace(scalar_one=lambda: 1)

    assert await _numeric_identity_cutover_ready(ready_db) is True
    assert await _numeric_identity_cutover_ready(unresolved_db) is False


@pytest.mark.unit
async def test_numeric_cutover_readiness_rejects_normalized_legacy_mismatch() -> None:
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one=lambda: 1)

    assert await _numeric_identity_cutover_ready(db) is False

    invalid_ledger_statement = db.execute.await_args.args[0]
    compiled = str(invalid_ledger_statement).lower()
    assert "lower(trim(remnawave_identity_reconciliations.legacy_uuid))" in compiled
    assert "lower(trim(mobile_users.remnawave_uuid))" in compiled
    assert "lower(trim(service_identities.provider_subject_ref))" in compiled


@pytest.mark.unit
@pytest.mark.parametrize("missing_query_index", [2, 3])
async def test_numeric_cutover_readiness_includes_inactive_and_disabled_rollback_subjects(
    missing_query_index: int,
) -> None:
    db = AsyncMock()
    counts = [0, 0, 0, 0]
    counts[missing_query_index] = 1
    db.execute.side_effect = [SimpleNamespace(scalar_one=lambda value=value: value) for value in counts]

    assert await _numeric_identity_cutover_ready(db) is False

    missing_statement = db.execute.await_args_list[missing_query_index].args[0]
    predicates = " ".join(str(item).lower() for item in missing_statement._where_criteria)
    assert "is_active" not in predicates
    assert "identity_status" not in predicates


@pytest.mark.unit
async def test_numeric_cutover_readiness_rejects_same_owner_inconsistent_provider_pair() -> None:
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one=lambda: 0),
        SimpleNamespace(scalar_one=lambda: 1),
    ]

    assert await _numeric_identity_cutover_ready(db) is False

    alias_statement = db.execute.await_args_list[1].args[0]
    compiled = str(alias_statement).lower()
    assert "customer_account_id" in compiled
    assert "numeric_user_id" in compiled
    assert "legacy_uuid" in compiled
    assert "not (" in compiled


@pytest.mark.unit
async def test_fresh_stream_receipts_are_unknown_when_backlog_is_unobserved(
    monkeypatch,
) -> None:
    frozen_now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(settings, "remnawave_stream_receipt_max_idle_seconds", 300)
    streams = await routes._stream_health(
        _stream_health_db(
            receipt_rows=[(name, frozen_now - timedelta(seconds=299)) for name in _STREAM_NAMES],
        ),
        now=frozen_now,
    )

    assert [item.status for item in streams] == ["unknown"] * 3
    assert [item.degraded_reason for item in streams] == ["backlog_unobserved"] * 3
    assert all(item.lag is None and item.pending is None for item in streams)
    assert routes._stream_export_readiness_observed(streams) is False

    client = AsyncMock()
    client.get.return_value = {"version": "3.4.3"}
    monkeypatch.setattr(routes, "_stream_health", AsyncMock(return_value=streams))
    monkeypatch.setattr(routes, "_numeric_identity_cutover_ready", AsyncMock(return_value=True))
    monkeypatch.setattr(routes, "is_remnawave_node_ssh_available_for", lambda _user: False)

    response = await get_admin_remnawave_capabilities_and_streams(
        current_user=SimpleNamespace(),
        db=AsyncMock(),
        client=client,
    )

    assert response.degraded_reason == "stream_consumer_unobserved"
    assert response.capabilities.redis_stream_export is False


@pytest.mark.unit
async def test_fresh_checkpoint_exposes_real_lag_and_pending(monkeypatch) -> None:
    frozen_now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(settings, "remnawave_stream_receipt_max_idle_seconds", 300)
    checkpoint_rows = [(name, 0, 0, True, True, frozen_now - timedelta(seconds=1)) for name in _STREAM_NAMES]

    healthy = await routes._stream_health(
        _stream_health_db(
            receipt_rows=[(name, frozen_now - timedelta(seconds=1)) for name in _STREAM_NAMES],
            checkpoint_rows=checkpoint_rows,
        ),
        now=frozen_now,
    )

    assert [item.status for item in healthy] == ["healthy"] * 3
    assert all(item.lag == 0 and item.pending == 0 for item in healthy)
    assert routes._stream_export_readiness_observed(healthy) is True

    checkpoint_rows[1] = (
        "subscription_requests",
        2,
        1,
        True,
        True,
        frozen_now - timedelta(seconds=1),
    )
    degraded = await routes._stream_health(
        _stream_health_db(
            receipt_rows=[(name, frozen_now - timedelta(seconds=1)) for name in _STREAM_NAMES],
            checkpoint_rows=checkpoint_rows,
        ),
        now=frozen_now,
    )
    subscription_requests = {item.key: item for item in degraded}["subscription_requests"]

    assert subscription_requests.status == "degraded"
    assert subscription_requests.degraded_reason == "stream_backlog_present"
    assert subscription_requests.lag == 2
    assert subscription_requests.pending == 1
    assert routes._stream_export_readiness_observed(degraded) is False


@pytest.mark.unit
async def test_stream_receipt_at_exact_max_idle_boundary_is_stale(monkeypatch) -> None:
    frozen_now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(settings, "remnawave_stream_receipt_max_idle_seconds", 300)

    streams = await routes._stream_health(
        _stream_health_db(
            receipt_rows=[(name, frozen_now - timedelta(seconds=300)) for name in _STREAM_NAMES],
        ),
        now=frozen_now,
    )

    assert [item.status for item in streams] == ["degraded"] * 3
    assert [item.degraded_reason for item in streams] == ["stream_receipt_stale"] * 3
    assert routes._stream_export_readiness_observed(streams) is False


@pytest.mark.unit
async def test_stream_health_distinguishes_stale_fresh_and_missing_receipts(monkeypatch) -> None:
    frozen_now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(settings, "remnawave_stream_receipt_max_idle_seconds", 300)

    streams = await routes._stream_health(
        _stream_health_db(
            receipt_rows=[
                ("user_usage", frozen_now - timedelta(seconds=301)),
                ("subscription_requests", frozen_now - timedelta(seconds=1)),
            ],
        ),
        now=frozen_now,
    )
    by_name = {item.key: item for item in streams}

    assert by_name["user_usage"].status == "degraded"
    assert by_name["user_usage"].degraded_reason == "stream_receipt_stale"
    assert by_name["subscription_requests"].status == "unknown"
    assert by_name["subscription_requests"].degraded_reason == "backlog_unobserved"
    assert by_name["node_connections"].status == "unknown"
    assert by_name["node_connections"].degraded_reason == "no_committed_receipt"
    assert routes._stream_export_readiness_observed(streams) is False


@pytest.mark.unit
async def test_stream_gap_and_dead_letter_reasons_precede_receipt_staleness(monkeypatch) -> None:
    frozen_now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(settings, "remnawave_stream_receipt_max_idle_seconds", 300)

    streams = await routes._stream_health(
        _stream_health_db(
            receipt_rows=[(name, frozen_now - timedelta(seconds=301)) for name in _STREAM_NAMES],
            dead_letter_rows=[("subscription_requests", 1)],
            gap_rows=[("user_usage", 1)],
        ),
        now=frozen_now,
    )
    by_name = {item.key: item for item in streams}

    assert by_name["user_usage"].degraded_reason == "reconciliation_gap_open"
    assert by_name["subscription_requests"].degraded_reason == "dead_letters_present"
    assert by_name["node_connections"].degraded_reason == "stream_receipt_stale"


@pytest.mark.unit
async def test_admin_status_reports_exact_343_panel_and_341_node_targets(monkeypatch) -> None:
    client = AsyncMock()
    client.get.return_value = {"version": "v3.4.3"}
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(routes, "_stream_health", AsyncMock(return_value=[]))
    monkeypatch.setattr(routes, "_numeric_identity_cutover_ready", AsyncMock(return_value=True))
    monkeypatch.setattr(routes, "is_remnawave_node_ssh_available_for", lambda _user: True)

    response = await get_admin_remnawave_capabilities_and_streams(
        current_user=SimpleNamespace(),
        db=AsyncMock(),
        client=client,
    )

    client.get.assert_awaited_once_with("/system/metadata")
    assert response.panel_version == "3.4.3"
    assert response.target_panel_version == "3.4.3"
    assert response.target_node_version == "3.4.1"
    assert response.contract_version == "3.4.13"
    assert response.degraded_reason is None
    assert response.capabilities.numeric_user_ids is True
    assert response.capabilities.node_ssh is True
    assert response.capabilities.redis_stream_export is False
    assert response.capabilities.connections is True


@pytest.mark.unit
async def test_admin_status_rejects_341_panel_as_version_mismatch(monkeypatch) -> None:
    client = AsyncMock()
    client.get.return_value = {"version": "3.4.1"}
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)
    monkeypatch.setattr(routes, "_stream_health", AsyncMock(return_value=[]))
    monkeypatch.setattr(routes, "_numeric_identity_cutover_ready", AsyncMock(return_value=True))
    monkeypatch.setattr(routes, "is_remnawave_node_ssh_available_for", lambda _user: True)

    response = await get_admin_remnawave_capabilities_and_streams(
        current_user=SimpleNamespace(),
        db=AsyncMock(),
        client=client,
    )

    assert response.panel_version == "3.4.1"
    assert response.degraded_reason == "panel_version_mismatch"
    assert not any(response.capabilities.model_dump().values())


@pytest.mark.unit
async def test_target_panel_readiness_single_flights_simultaneous_status_checks(monkeypatch) -> None:
    refresh_started = asyncio.Event()
    release_refresh = asyncio.Event()

    async def get_metadata(path: str) -> dict[str, str]:
        assert path == "/system/metadata"
        refresh_started.set()
        await release_refresh.wait()
        return {"version": "3.4.3"}

    client = AsyncMock()
    client.get.side_effect = get_metadata
    monkeypatch.setattr(
        routes,
        "_target_panel_readiness_cache",
        routes._TargetPanelReadinessCache(ttl_seconds=5.0),
    )

    checks = [asyncio.create_task(routes._target_panel_ready(client)) for _ in range(8)]
    await asyncio.wait_for(refresh_started.wait(), timeout=1.0)
    release_refresh.set()

    assert await asyncio.gather(*checks) == [True] * 8
    client.get.assert_awaited_once_with("/system/metadata")


@pytest.mark.unit
async def test_target_panel_readiness_single_flights_refresh_after_expiry(monkeypatch) -> None:
    now = [100.0]
    refresh_started = asyncio.Event()
    release_refresh = asyncio.Event()
    call_count = 0

    async def get_metadata(path: str) -> dict[str, str]:
        nonlocal call_count
        assert path == "/system/metadata"
        call_count += 1
        if call_count > 1:
            refresh_started.set()
            await release_refresh.wait()
        return {"version": "3.4.3"}

    client = AsyncMock()
    client.get.side_effect = get_metadata
    monkeypatch.setattr(
        routes,
        "_target_panel_readiness_cache",
        routes._TargetPanelReadinessCache(ttl_seconds=5.0, clock=lambda: now[0]),
    )

    assert await routes._target_panel_ready(client) is True
    now[0] += 5.0
    checks = [asyncio.create_task(routes._target_panel_ready(client)) for _ in range(8)]
    await asyncio.wait_for(refresh_started.wait(), timeout=1.0)
    release_refresh.set()

    assert await asyncio.gather(*checks) == [True] * 8
    assert client.get.await_count == 2


@pytest.mark.unit
async def test_target_panel_readiness_caches_false_until_expiry(monkeypatch) -> None:
    now = [100.0]
    client = AsyncMock()
    client.get.side_effect = [
        {"version": "3.4.1"},
        {"version": "3.4.3"},
    ]
    monkeypatch.setattr(
        routes,
        "_target_panel_readiness_cache",
        routes._TargetPanelReadinessCache(ttl_seconds=5.0, clock=lambda: now[0]),
    )

    assert await routes._target_panel_ready(client) is False
    assert await routes._target_panel_ready(client) is False
    client.get.assert_awaited_once_with("/system/metadata")

    now[0] += 5.0
    assert await routes._target_panel_ready(client) is True
    assert client.get.await_count == 2


@pytest.mark.unit
async def test_target_panel_readiness_never_serves_stale_true_after_refresh_error(monkeypatch) -> None:
    now = [100.0]
    client = AsyncMock()
    client.get.side_effect = [
        {"version": "3.4.3"},
        httpx.ConnectError(
            "panel unavailable",
            request=httpx.Request("GET", "https://remnawave.invalid/system/metadata"),
        ),
        {"version": "3.4.3"},
    ]
    monkeypatch.setattr(
        routes,
        "_target_panel_readiness_cache",
        routes._TargetPanelReadinessCache(ttl_seconds=5.0, clock=lambda: now[0]),
    )

    assert await routes._target_panel_ready(client) is True
    now[0] += 5.0
    assert await routes._target_panel_ready(client) is False
    assert await routes._target_panel_ready(client) is False
    assert client.get.await_count == 2

    now[0] += 5.0
    assert await routes._target_panel_ready(client) is True
    assert client.get.await_count == 3


@pytest.mark.unit
async def test_customer_status_is_scoped_to_authenticated_customer(monkeypatch) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=None,
        is_active=True,
        status="active",
    )
    db.get.return_value = customer
    exact_resolver = AsyncMock(return_value=SimpleNamespace(id=42))
    monkeypatch.setattr(routes, "resolve_exact_mapped_mobile_user_ref", exact_resolver)
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    client = AsyncMock()
    client.get.return_value = {"version": "3.4.3"}
    response = await get_customer_vpn_service_status(customer_account_id=customer_id, db=db, client=client)

    db.get.assert_awaited_once()
    exact_resolver.assert_awaited_once_with(db, customer)
    assert response.connections_available is True
    assert response.usage_available is True
    assert response.devices_available is False
    assert response.degraded is False


@pytest.mark.unit
async def test_customer_status_does_not_advertise_numeric_identity_without_exact_mapping(monkeypatch) -> None:
    customer_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=None,
        is_active=True,
        status="active",
    )
    monkeypatch.setattr(routes, "resolve_exact_mapped_mobile_user_ref", AsyncMock(return_value=None))
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    client = AsyncMock()
    client.get.return_value = {"version": "3.4.3"}
    response = await get_customer_vpn_service_status(customer_account_id=customer_id, db=db, client=client)

    assert response.connections_available is False
    assert response.usage_available is False
    assert response.devices_available is False
    assert response.degraded_reason == "vpn_identity_not_reconciled"


@pytest.mark.unit
async def test_partner_status_counts_only_query_scoped_grants(monkeypatch) -> None:
    workspace_id = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id),
        permission_keys=frozenset({"remnawave_read"}),
    )
    count_result = SimpleNamespace(scalar_one=lambda: 3)
    list_result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(
            all=lambda: [
                SimpleNamespace(resource_type="node", permission_keys=["remnawave_read"]),
                SimpleNamespace(resource_type="tag", permission_keys=["remnawave_write"]),
                SimpleNamespace(
                    resource_type="service_identity",
                    permission_keys=["remnawave_read", "remnawave_execute"],
                ),
            ]
        )
    )
    db = AsyncMock()
    db.execute.side_effect = [count_result, list_result]
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    client = AsyncMock()
    client.get.return_value = {"version": "3.4.3"}
    response = await get_partner_vpn_service_status(workspace_id=workspace_id, access=access, db=db, client=client)

    assert response.workspace_id == workspace_id
    assert response.assigned_resources == 2
    assert response.capabilities.connections is True
    assert response.capabilities.usage is False
    assert response.capabilities.devices is False


@pytest.mark.unit
async def test_partner_status_does_not_advertise_connections_for_unrelated_grants(monkeypatch) -> None:
    workspace_id = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id),
        permission_keys=frozenset({"remnawave_read"}),
    )
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one=lambda: 1),
        SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                all=lambda: [SimpleNamespace(resource_type="tag", permission_keys=["remnawave_read"])]
            )
        ),
    ]
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", True)

    client = AsyncMock()
    client.get.return_value = {"version": "3.4.3"}
    response = await get_partner_vpn_service_status(workspace_id=workspace_id, access=access, db=db, client=client)

    assert response.assigned_resources == 1
    assert response.capabilities.connections is False
    assert response.capabilities.usage is False
    assert response.capabilities.devices is False


@pytest.mark.unit
async def test_partner_and_customer_status_fail_closed_on_panel_mismatch(monkeypatch) -> None:
    workspace_id = uuid4()
    customer_id = uuid4()
    panel = AsyncMock()
    panel.get.return_value = {"version": "3.4.1"}
    monkeypatch.setattr(
        routes,
        "load_readable_partner_remnawave_grants",
        AsyncMock(return_value=[SimpleNamespace(resource_type="node")]),
    )
    partner = await get_partner_vpn_service_status(
        workspace_id=workspace_id,
        access=SimpleNamespace(workspace=SimpleNamespace(id=workspace_id)),
        db=AsyncMock(),
        client=panel,
    )

    customer_db = AsyncMock()
    customer_db.get.return_value = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=42,
        remnawave_uuid=None,
        is_active=True,
        status="active",
    )
    monkeypatch.setattr(
        routes,
        "resolve_exact_mapped_mobile_user_ref",
        AsyncMock(return_value=SimpleNamespace(id=42)),
    )
    customer = await get_customer_vpn_service_status(
        customer_account_id=customer_id,
        db=customer_db,
        client=panel,
    )

    assert partner.capabilities.connections is False
    assert partner.degraded_reason == "panel_unavailable_or_mismatched"
    assert customer.connections_available is False
    assert customer.usage_available is False
    assert customer.degraded_reason == "panel_unavailable_or_mismatched"


@pytest.mark.unit
async def test_partner_status_route_denies_member_without_remnawave_read() -> None:
    workspace_id = uuid4()
    db = AsyncMock()
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def override_access():
        return SimpleNamespace(
            workspace=SimpleNamespace(id=workspace_id, status="active"),
            permission_keys=frozenset(),
            is_internal_admin_override=False,
        )

    async def override_current_user():
        return SimpleNamespace(id=uuid4(), totp_enabled=True)

    async def override_db():
        return db

    app.dependency_overrides[get_partner_workspace_access] = override_access
    app.dependency_overrides[get_current_active_web_user] = override_current_user
    app.dependency_overrides[get_db] = override_db

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        response = await client.get(f"/api/v1/partner-workspaces/{workspace_id}/vpn-service-status")

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing partner workspace permission: remnawave_read"
    db.execute.assert_not_awaited()
