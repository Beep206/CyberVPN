"""Backend-owned VPN Tester orchestration and contract checks."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from time import perf_counter
from typing import Any
from uuid import UUID

from httpx import HTTPError

from src.application.vpn_testing.analyzers import analyze_mihomo_template
from src.application.vpn_testing.balancer import recommendation_key, stable_recommendation_hash
from src.application.vpn_testing.generated_subscription_checker import (
    expected_remnawave_assignment,
    generated_mihomo_artifact_summary,
    generated_subscription_checks,
)
from src.application.vpn_testing.redaction import safe_artifact_preview
from src.application.vpn_testing.runtime_agent_client import call_runtime_agent, runtime_agent_configured
from src.application.vpn_testing.suite_loader import load_default_route_registries, load_default_suites
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.models.vpn_tester_model import VpnTestRunModel
from src.infrastructure.database.repositories.vpn_tester_repo import VpnTesterRepository
from src.infrastructure.monitoring.metrics import (
    vpn_tester_balancer_recommendations_total,
    vpn_tester_evidence_cleanup_total,
    vpn_tester_release_gate_blocking,
    vpn_tester_run_duration_seconds,
    vpn_tester_runs_total,
    vpn_tester_runtime_agent_unavailable_total,
    vpn_tester_schedule_runs_total,
)
from src.infrastructure.remnawave.client import RemnawaveClient

DEFAULT_SCHEDULES = (
    {
        "schedule_key": "vpn-tester:lightweight",
        "suite_key": "default_subscription_smoke_v1",
        "mode": "contract",
        "cron": "*/15 * * * *",
        "enabled": False,
        "settings": {"profile": "lightweight"},
    },
    {
        "schedule_key": "vpn-tester:all-tariffs",
        "suite_key": "all_tariffs_contract_v1",
        "mode": "all_tariffs",
        "cron": "5 * * * *",
        "enabled": False,
        "settings": {"profile": "all_tariffs"},
    },
    {
        "schedule_key": "vpn-tester:deep",
        "suite_key": "premium_smart_ru_v1",
        "mode": "contract",
        "cron": "20 2 * * *",
        "enabled": False,
        "settings": {"profile": "deep"},
    },
    {
        "schedule_key": "vpn-tester:runtime",
        "suite_key": "premium_smart_ru_v1",
        "mode": "runtime",
        "cron": "35 2 * * *",
        "enabled": False,
        "settings": {"profile": "runtime_proxy_only", "tun_sandbox": False},
    },
    {
        "schedule_key": "vpn-tester:balancer-preview",
        "suite_key": "premium_smart_ru_v1",
        "mode": "balancer_preview",
        "cron": "*/10 * * * *",
        "enabled": False,
        "settings": {"profile": "recommendations_only"},
    },
    {
        "schedule_key": "vpn-tester:cleanup",
        "suite_key": "default_subscription_smoke_v1",
        "mode": "contract",
        "cron": "45 2 * * *",
        "enabled": False,
        "settings": {"profile": "cleanup"},
    },
)

PREMIUM_SMART_RU_NODE_HOSTS = {
    "de-3.cyber-vpn.org": "🇩🇪 DE Frankfurt 01 25G",
    "nl-4.cyber-vpn.org": "🇳🇱 NL Amsterdam 01 10G",
    "ru-msk-3.cyber-vpn.org": "🇷🇺 RU Moscow 01 25G",
    "ru-spb-3.cyber-vpn.org": "🇷🇺 RU SPB 01 25G",
}
PREMIUM_SMART_RU_INBOUND_TAGS = {
    "VLESS_REALITY_443",
    "VLESS_XHTTP_REALITY_8443",
}
PREMIUM_SMART_RU_INTERNAL_SQUAD = "CYBERVPN_PREMIUM_SMART_RU_NODES"
PREMIUM_SMART_RU_RELEASE_GATE_SUITE = "premium_smart_ru_v1"
PREMIUM_SMART_RU_RELEASE_GATE_VERSION = "v1"
PREMIUM_SMART_RU_RELEASE_GATE_MODE = "runtime"
PREMIUM_SMART_RU_RELEASE_GATE_MAX_AGE = timedelta(hours=24)
PREMIUM_SMART_RU_RELEASE_GATE_CONTRACT_CHECKS = frozenset(
    {
        "generated_subscription.vless_reality_raw_tcp",
        "generated_subscription.xhttp_transport",
        "remnawave.inbounds.vless_reality_raw_tcp",
        "remnawave.inbounds.vless_reality_xhttp",
        "remnawave.hosts.transport_matrix",
    }
)
PREMIUM_SMART_RU_RELEASE_GATE_RAW_COUNT = 4
PREMIUM_SMART_RU_RELEASE_GATE_XHTTP_COUNT = 4
PERSISTED_RUN_CONTEXT_KEYS = frozenset(
    {
        "source",
        "admin_surface",
        "trigger",
        "schedule_key",
        "execute_immediately",
        "idempotency_window",
        "lock_policy",
    }
)


def _csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, tuple | set):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip().lower()]
    return []


def _visibility(plan: SubscriptionPlanModel) -> str:
    return str(plan.catalog_access_class or plan.catalog_visibility or "unknown")


def _plan_code(plan: SubscriptionPlanModel) -> str:
    return str(plan.plan_code or plan.name or plan.id)


def _plan_target(plan: SubscriptionPlanModel) -> str:
    plan_code = _plan_code(plan)
    plan_name = str(plan.name or "").strip()
    return plan_name or plan_code


def _safe_plan_payload(plan: SubscriptionPlanModel) -> dict[str, Any]:
    return {
        "plan_code": _plan_code(plan),
        "display_name": plan.display_name or plan.name,
        "visibility": _visibility(plan),
        "duration_days": plan.duration_days,
        "traffic_limit_bytes": plan.traffic_limit_bytes,
        "connection_modes": _str_list(plan.connection_modes),
        "server_pool": _str_list(plan.server_pool),
        "traffic_policy_keys": sorted((plan.traffic_policy or {}).keys()),
    }


def _result(
    *,
    check_key: str,
    check_name: str,
    category: str,
    status: str,
    target: str = "global",
    severity: str = "error",
    safe_summary: str,
    details: Mapping[str, Any] | None = None,
    started: float | None = None,
) -> dict[str, Any]:
    return {
        "check_key": check_key,
        "check_name": check_name,
        "category": category,
        "status": status,
        "severity": severity,
        "target": target,
        "safe_summary": safe_summary,
        "details": dict(details or {}),
        "duration_ms": _elapsed_ms(started) if started is not None else 0,
    }


def _run_status(results: list[dict[str, Any]]) -> str:
    if any(item["status"] == "fail" for item in results):
        return "fail"
    if any(item["status"] == "degraded" for item in results):
        return "degraded"
    if results and all(item["status"] == "skipped" for item in results):
        return "skipped"
    return "pass"


def _release_gate_result_value(result: Any, field: str) -> Any:
    if isinstance(result, Mapping):
        return result.get(field)
    return getattr(result, field, None)


def _premium_smart_ru_release_evidence_complete(run: Any) -> bool:
    if run is None or str(getattr(run, "status", "")) != "pass":
        return False
    if str(getattr(run, "suite_key", "")) != PREMIUM_SMART_RU_RELEASE_GATE_SUITE:
        return False
    if str(getattr(run, "suite_version", "")) != PREMIUM_SMART_RU_RELEASE_GATE_VERSION:
        return False
    if str(getattr(run, "mode", "")) != PREMIUM_SMART_RU_RELEASE_GATE_MODE:
        return False
    finished_at = getattr(run, "finished_at", None)
    if not isinstance(finished_at, datetime) or finished_at.tzinfo is None:
        return False
    age = _utc_now() - finished_at.astimezone(UTC)
    if age < timedelta(0) or age > PREMIUM_SMART_RU_RELEASE_GATE_MAX_AGE:
        return False

    results = list(getattr(run, "results", None) or [])
    if not results:
        return False
    status_by_key = {
        str(_release_gate_result_value(result, "check_key") or ""): str(
            _release_gate_result_value(result, "status") or ""
        )
        for result in results
    }
    if any(status_by_key.get(check_key) != "pass" for check_key in PREMIUM_SMART_RU_RELEASE_GATE_CONTRACT_CHECKS):
        return False

    raw_keys = {
        check_key
        for check_key, check_status in status_by_key.items()
        if "runtime.transport.raw." in check_key and check_status == "pass"
    }
    xhttp_keys = {
        check_key
        for check_key, check_status in status_by_key.items()
        if "runtime.transport.xhttp." in check_key and check_status == "pass"
    }
    matrix_results = [
        result
        for result in results
        if "runtime.transport_profile_matrix.required" in str(_release_gate_result_value(result, "check_key") or "")
    ]
    matrix_evidence_valid = bool(matrix_results) and all(
        str(_release_gate_result_value(result, "status") or "") == "pass"
        and isinstance(_release_gate_result_value(result, "details"), Mapping)
        and _release_gate_result_value(result, "details").get("server_matrix_valid") is True
        and _release_gate_result_value(result, "details").get("raw_server_matrix_valid") is True
        and _release_gate_result_value(result, "details").get("xhttp_server_matrix_valid") is True
        for result in matrix_results
    )
    return (
        len(raw_keys) == PREMIUM_SMART_RU_RELEASE_GATE_RAW_COUNT
        and len(xhttp_keys) == PREMIUM_SMART_RU_RELEASE_GATE_XHTTP_COUNT
        and matrix_evidence_valid
    )


def _summary(results: list[dict[str, Any]], *, suite_key: str, mode: str) -> dict[str, Any]:
    pass_count = sum(1 for item in results if item["status"] == "pass")
    fail_count = sum(1 for item in results if item["status"] == "fail")
    degraded_count = sum(1 for item in results if item["status"] == "degraded")
    skipped_count = sum(1 for item in results if item["status"] == "skipped")
    return {
        "suite_key": suite_key,
        "mode": mode,
        "status": _run_status(results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "degraded_count": degraded_count,
        "skipped_count": skipped_count,
        "generated_at": _utc_now().isoformat(),
    }


def _idempotency_bucket(now: datetime, window: str) -> str:
    normalized = (window or "minute").strip().lower()
    if normalized in {"none", "disabled", "off"}:
        return f"{now:%Y%m%d%H%M%S%f}"
    if normalized in {"hour", "hourly"}:
        return f"{now:%Y%m%d%H}"
    if normalized in {"day", "daily"}:
        return f"{now:%Y%m%d}"
    return f"{now:%Y%m%d%H%M}"


def _next_run_fallback(now: datetime, cron: str) -> datetime:
    if cron.startswith("*/"):
        minute = int(cron.split()[0].removeprefix("*/") or "15")
        return now + timedelta(minutes=max(1, min(minute, 60)))
    if cron.startswith("5 ") or cron.startswith("20 ") or cron.startswith("35 ") or cron.startswith("45 "):
        return now + timedelta(hours=1)
    return now + timedelta(minutes=15)


def _default_mihomo_template() -> str:
    return (
        files("src.application.vpn_testing.fixtures")
        .joinpath("premium_smart_ru_mihomo_template.yaml")
        .read_text(encoding="utf-8")
    )


def _context_generated_mihomo_artifact(request_context: Mapping[str, Any] | None) -> Any:
    if not isinstance(request_context, Mapping):
        return None
    payloads = [request_context]
    requested = request_context.get("requested_context")
    if isinstance(requested, Mapping):
        payloads.append(requested)
    for payload in payloads:
        for key in (
            "generated_mihomo_yaml",
            "mihomo_yaml",
            "generated_subscription_yaml",
            "subscription_yaml",
            "generated_mihomo",
            "generated_subscription",
        ):
            value = payload.get(key)
            if value:
                return value
    return None


def _sanitize_run_request_context(request_context: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(request_context, Mapping):
        return {}
    sanitized = {
        key: value
        for key, value in request_context.items()
        if key in PERSISTED_RUN_CONTEXT_KEYS and isinstance(value, str | int | bool | type(None))
    }
    sanitized["generated_mihomo_artifact_supplied"] = _context_generated_mihomo_artifact(request_context) is not None
    return sanitized


class VpnTesterService:
    def __init__(self, repository: VpnTesterRepository, remnawave_client: RemnawaveClient | None = None) -> None:
        self._repository = repository
        self._remnawave_client = remnawave_client

    @staticmethod
    def transient_generated_mihomo_artifact(request_context: Mapping[str, Any] | None) -> Any:
        return _context_generated_mihomo_artifact(request_context)

    async def _generated_mihomo_artifact(self, request_context: Mapping[str, Any] | None) -> Any:
        return _context_generated_mihomo_artifact(request_context)

    async def ensure_seeded(self) -> None:
        for suite in load_default_suites():
            await self._repository.upsert_suite(suite)
        for registry in load_default_route_registries():
            for route in registry.get("routes") or []:
                if isinstance(route, dict):
                    await self._repository.upsert_route_registry_entry(registry, route)
        for schedule in DEFAULT_SCHEDULES:
            await self._repository.upsert_schedule(dict(schedule))

    async def create_manual_run(
        self,
        *,
        suite_key: str,
        mode: str,
        requested_by_admin_id: UUID,
        idempotency_key: str | None,
        request_context: dict,
    ) -> VpnTestRunModel:
        await self.ensure_seeded()
        suite = await self._repository.get_suite(suite_key)
        if suite is None:
            raise ValueError("unknown_suite")
        suite_spec = dict(suite.spec or {})
        return await self._repository.create_run(
            suite_key=suite.suite_key,
            suite_version=suite.version,
            mode=mode or suite.mode,
            trigger="manual",
            requested_by_admin_id=requested_by_admin_id,
            idempotency_key=idempotency_key,
            request_context=_sanitize_run_request_context(request_context),
            runtime_mode="proxy-only" if mode == "runtime" else None,
            route_registry_version=str(suite_spec.get("required_route_registry") or ""),
        )

    async def create_scheduled_run(
        self,
        *,
        suite_key: str,
        mode: str,
        trigger: str,
        request_context: dict[str, Any] | None = None,
    ) -> VpnTestRunModel:
        await self.ensure_seeded()
        suite = await self._repository.get_suite(suite_key)
        if suite is None:
            raise ValueError("unknown_suite")
        suite_spec = dict(suite.spec or {})
        idempotency_key = f"{trigger}:{suite_key}:{mode}:{_utc_now():%Y%m%d%H%M}"
        return await self._repository.create_run(
            suite_key=suite.suite_key,
            suite_version=suite.version,
            mode=mode or suite.mode,
            trigger=trigger,
            requested_by_admin_id=None,
            idempotency_key=idempotency_key,
            request_context=_sanitize_run_request_context(
                {"source": "task_worker", "trigger": trigger, **dict(request_context or {})}
            ),
            runtime_mode="proxy-only" if mode == "runtime" else None,
            route_registry_version=str(suite_spec.get("required_route_registry") or ""),
        )

    async def run_schedule(
        self,
        *,
        schedule_key: str,
        trigger: str,
        execute_immediately: bool,
        idempotency_window: str,
    ) -> dict[str, Any]:
        await self.ensure_seeded()
        now = _utc_now()
        schedule = await self._repository.get_schedule(schedule_key)
        if schedule is None:
            vpn_tester_schedule_runs_total.labels(schedule_key=schedule_key, result="schedule_not_found").inc()
            return {"skipped": True, "reason": "schedule_not_found", "schedule": None, "run": None}

        async def skip(reason: str) -> dict[str, Any]:
            await self._repository.update_schedule_gate_state(
                schedule,
                checked_at=now,
                skipped_reason=reason,
                next_run_at=_next_run_fallback(now, schedule.cron),
            )
            vpn_tester_schedule_runs_total.labels(schedule_key=schedule_key, result=reason).inc()
            return {"skipped": True, "reason": reason, "schedule": schedule, "run": None}

        if not settings.vpn_tester_enabled:
            return await skip("vpn_tester_disabled")
        if not settings.vpn_tester_scheduled_enabled:
            return await skip("scheduled_disabled")
        if not schedule.enabled:
            return await skip("schedule_disabled")

        suite = await self._repository.get_suite(schedule.suite_key)
        if suite is None:
            return await skip("unknown_suite")

        idempotency_key = (
            f"schedule:{schedule.schedule_key}:{schedule.suite_key}:{schedule.mode}:"
            f"{_idempotency_bucket(now, idempotency_window)}"
        )
        suite_spec = dict(suite.spec or {})
        run = await self._repository.create_run(
            suite_key=suite.suite_key,
            suite_version=suite.version,
            mode=schedule.mode or suite.mode,
            trigger=trigger,
            requested_by_admin_id=None,
            idempotency_key=idempotency_key,
            request_context={
                "source": "task_worker_schedule_gate",
                "trigger": trigger,
                "schedule_key": schedule.schedule_key,
                "execute_immediately": execute_immediately,
                "idempotency_window": idempotency_window,
                "lock_policy": dict(schedule.settings or {}).get(
                    "lock_policy",
                    "worker_redis_lock_plus_db_idempotency",
                ),
            },
            runtime_mode="proxy-only" if schedule.mode == "runtime" else None,
            route_registry_version=str(suite_spec.get("required_route_registry") or ""),
        )
        if execute_immediately:
            run = await self.execute_run(run)
        await self._repository.update_schedule_gate_state(
            schedule,
            checked_at=now,
            triggered_at=now,
            last_run_id=run.id,
            last_status=run.status,
            skipped_reason=None,
            next_run_at=_next_run_fallback(now, schedule.cron),
        )
        vpn_tester_schedule_runs_total.labels(schedule_key=schedule_key, result=str(run.status)).inc()
        return {"skipped": False, "reason": None, "schedule": schedule, "run": run}

    async def list_runs(self, *, limit: int = 25, status: str | None = None) -> list[VpnTestRunModel]:
        await self.ensure_seeded()
        return await self._repository.list_runs(limit=limit, status=status)

    async def get_run(self, run_id: UUID) -> VpnTestRunModel | None:
        await self.ensure_seeded()
        return await self._repository.get_run(run_id)

    async def claim_queued_run(self) -> VpnTestRunModel | None:
        await self.ensure_seeded()
        return await self._repository.claim_queued_run()

    async def cancel_run(self, run_id: UUID) -> VpnTestRunModel | None:
        run = await self._repository.get_run(run_id)
        if run is None:
            return None
        return await self._repository.cancel_run(run)

    async def execute_run(self, run: VpnTestRunModel, *, generated_mihomo_artifact: Any = None) -> VpnTestRunModel:
        if run.status == "cancelled":
            return run
        started = perf_counter()
        await self._repository.mark_run_running(run)
        suite = await self._repository.get_suite(run.suite_key, run.suite_version)
        suite_spec = dict(suite.spec if suite is not None else {})
        registry_key = str(suite_spec.get("required_route_registry") or "")
        plans = await self._repository.list_active_plans()
        route_entries = await self._repository.get_route_registry(run.suite_key, registry_key or None)

        if run.mode == "all_tariffs" or run.suite_key == "all_tariffs_contract_v1":
            results = self._all_tariffs_results(plans, route_entries)
        elif run.mode == "balancer_preview":
            results = await self._balancer_preview_results(plans, route_entries)
        elif run.mode == "runtime":
            if generated_mihomo_artifact is None:
                generated_mihomo_artifact = await self._generated_mihomo_artifact(run.request_context)
            results = await self._contract_results(
                suite_spec,
                plans,
                route_entries,
                request_context=run.request_context,
                generated_mihomo_artifact=generated_mihomo_artifact,
            )
            results.extend(
                await self._runtime_results(
                    run,
                    route_entries,
                    generated_mihomo_artifact=generated_mihomo_artifact,
                )
            )
        else:
            results = await self._contract_results(
                suite_spec,
                plans,
                route_entries,
                request_context=run.request_context,
            )

        summary = _summary(results, suite_key=run.suite_key, mode=run.mode)
        summary["route_registry_version"] = registry_key or run.route_registry_version
        evidence = self._evidence(run, suite_spec=suite_spec, results=results, plans=plans)
        status = str(summary["status"])
        completed = await self._repository.replace_run_results(
            run,
            results=results,
            evidence=evidence,
            summary=summary,
            status=status,
        )
        vpn_tester_runs_total.labels(mode=run.mode, trigger=run.trigger, status=status).inc()
        vpn_tester_run_duration_seconds.labels(mode=run.mode).observe(max(0.0, perf_counter() - started))
        if run.mode == "balancer_preview" and settings.vpn_tester_balancer_recommendations_enabled:
            payload = {
                "mutates_live_state": False,
                "status": status,
                "summary": summary,
                "result_keys": [str(item.get("check_key")) for item in results],
            }
            scope = "premium_smart_ru"
            rec_hash = stable_recommendation_hash(scope, payload)
            await self._repository.create_balancer_recommendation(
                completed,
                recommendation_key=recommendation_key(scope, rec_hash),
                recommendation_hash=rec_hash,
                scope=scope,
                summary="Read-only VPN balancer recommendation generated from contract metadata.",
                payload=payload,
                confidence=0.72 if status == "pass" else 0.42,
            )
            vpn_tester_balancer_recommendations_total.labels(status="open").inc()
        return completed

    async def execute_next_queued_run(self) -> VpnTestRunModel | None:
        run = await self.claim_queued_run()
        if run is None:
            return None
        return await self.execute_run(run)

    async def list_schedules(self):
        await self.ensure_seeded()
        return await self._repository.list_schedules()

    async def update_schedule(self, schedule_key: str, *, enabled: bool, schedule_settings: dict | None = None):
        await self.ensure_seeded()
        return await self._repository.update_schedule(schedule_key, enabled=enabled, settings=schedule_settings)

    async def tariff_matrix(self) -> dict[str, Any]:
        await self.ensure_seeded()
        plans = await self._repository.list_active_plans()
        rows = []
        for plan in plans:
            checks = self._plan_contract_checks(plan)
            assignment = expected_remnawave_assignment(plan)
            rows.append(
                {
                    **_safe_plan_payload(plan),
                    "status": _run_status(checks),
                    "checks": checks,
                    "device_limit": plan.device_limit,
                    "remnawave_assignment": assignment,
                }
            )
        return {"rows": rows, "total": len(rows), "generated_at": _utc_now()}

    async def route_matrix(self) -> dict[str, Any]:
        await self.ensure_seeded()
        entries = await self._repository.get_route_registry("premium_smart_ru_v1", "premium_smart_ru_v2")
        rows = []
        for entry in entries:
            metadata = dict(entry.metadata_json or {})
            rows.append(
                {
                    "route_key": entry.route_key,
                    "registry_key": entry.registry_key,
                    "country_code": entry.country_code,
                    "node_tags": list(entry.node_tags or []),
                    "expected_modes": list(entry.expected_modes or []),
                    "expected_policy": metadata.get("expected_policy"),
                    "expected_group": metadata.get("expected_group"),
                    "severity": metadata.get("severity"),
                    "domain": metadata.get("domain"),
                    "enabled": entry.enabled,
                }
            )
        return {"registry_key": "premium_smart_ru_v2", "rows": rows, "total": len(rows), "generated_at": _utc_now()}

    async def overview(self) -> dict[str, Any]:
        await self.ensure_seeded()
        counts = await self._repository.overview_counts()
        latest = await self._repository.list_runs(limit=5)
        schedules = await self._repository.list_schedules()
        return {
            "enabled": bool(settings.vpn_tester_enabled),
            "runtime_enabled": bool(settings.vpn_tester_runtime_enabled),
            "scheduled_enabled": bool(settings.vpn_tester_scheduled_enabled),
            "balancer_recommendations_enabled": bool(settings.vpn_tester_balancer_recommendations_enabled),
            "counts": counts,
            "latest_runs": latest,
            "schedules": schedules,
            "generated_at": _utc_now(),
        }

    async def release_gate(self) -> dict[str, Any]:
        runs = await self._repository.list_runs(limit=10)
        latest = runs[0] if runs else None
        blocking = not _premium_smart_ru_release_evidence_complete(latest)
        active_override = await self._repository.get_active_release_gate_override()
        if active_override is not None:
            vpn_tester_release_gate_blocking.set(1)
            return {
                "status": "blocked",
                "blocking": True,
                "latest_run_id": latest.id if latest else None,
                "reason": "manual_release_gate_override_not_permitted_for_premium_smart_ru",
                "override_allowed_roles": ["owner/super_admin", "super_admin"],
                "active_override": {
                    "id": active_override.id,
                    "latest_run_id": active_override.latest_run_id,
                    "overridden_by_admin_id": active_override.overridden_by_admin_id,
                    "previous_status": active_override.previous_status,
                    "previous_blocking": active_override.previous_blocking,
                    "reason": active_override.reason,
                    "expires_at": active_override.expires_at,
                    "created_at": active_override.created_at,
                },
                "generated_at": _utc_now(),
            }
        vpn_tester_release_gate_blocking.set(1 if blocking else 0)
        return {
            "status": "blocked" if blocking else latest.status,
            "blocking": blocking,
            "latest_run_id": latest.id if latest else None,
            "reason": "latest_vpn_tester_run_missing_required_evidence"
            if blocking
            else "latest_vpn_tester_run_acceptable",
            "override_allowed_roles": ["owner/super_admin", "super_admin"],
            "active_override": None,
            "generated_at": _utc_now(),
        }

    async def create_release_gate_override(
        self,
        *,
        admin_id: UUID,
        admin_role: AdminRole,
        reason: str,
        ttl_minutes: int,
        request_context: dict,
    ) -> dict[str, Any]:
        normalized_reason = reason.strip()
        if len(normalized_reason) < 20:
            raise ValueError("override_reason_too_short")
        max_ttl = 4320 if admin_role == AdminRole.OWNER_SUPER_ADMIN else 1440
        if ttl_minutes < 1 or ttl_minutes > max_ttl:
            raise ValueError("override_ttl_out_of_range")
        runs = await self._repository.list_runs(limit=1)
        latest = runs[0] if runs else None
        gate = await self.release_gate()
        expires_at = _utc_now() + timedelta(minutes=ttl_minutes)
        await self._repository.create_release_gate_override(
            latest_run_id=latest.id if latest else None,
            overridden_by_admin_id=admin_id,
            previous_status=str(gate.get("status") or "unknown"),
            previous_blocking=bool(gate.get("blocking")),
            reason=normalized_reason,
            expires_at=expires_at,
            request_context=request_context,
        )
        return await self.release_gate()

    async def list_balancer_recommendations(self, *, limit: int = 50) -> list[Any]:
        await self.ensure_seeded()
        return await self._repository.list_balancer_recommendations(limit=limit)

    async def acknowledge_balancer_recommendation(self, recommendation_id: UUID, *, admin_id: UUID):
        recommendation = await self._repository.set_balancer_recommendation_status(
            recommendation_id,
            status="acknowledged",
            admin_id=admin_id,
        )
        if recommendation is not None:
            vpn_tester_balancer_recommendations_total.labels(status="acknowledged").inc()
        return recommendation

    async def dismiss_balancer_recommendation(self, recommendation_id: UUID, *, admin_id: UUID, reason: str | None):
        recommendation = await self._repository.set_balancer_recommendation_status(
            recommendation_id,
            status="dismissed",
            admin_id=admin_id,
            reason=reason,
        )
        if recommendation is not None:
            vpn_tester_balancer_recommendations_total.labels(status="dismissed").inc()
        return recommendation

    async def cleanup_expired_evidence(self) -> dict[str, Any]:
        removed = await self._repository.cleanup_expired_evidence()
        if removed:
            vpn_tester_evidence_cleanup_total.inc(removed)
        return {"removed": removed, "cleaned_at": _utc_now()}

    def _plan_contract_checks(self, plan: SubscriptionPlanModel) -> list[dict[str, Any]]:
        plan_target = _plan_target(plan)
        connection_modes = _str_list(plan.connection_modes)
        server_pool = _str_list(plan.server_pool)
        checks = [
            _result(
                check_key="all_tariffs.plan_code",
                check_name="Plan code is stable",
                category="plans",
                status="pass" if plan.plan_code else "fail",
                target=plan_target,
                safe_summary="Plan exposes stable plan_code" if plan.plan_code else "Plan is missing plan_code",
                details=_safe_plan_payload(plan),
            ),
            _result(
                check_key="all_tariffs.connection_modes",
                check_name="Connection modes are declared",
                category="plans",
                status="pass" if connection_modes else "fail",
                target=plan_target,
                safe_summary="Connection modes declared" if connection_modes else "No connection modes declared",
                details={"connection_modes": connection_modes},
            ),
            _result(
                check_key="all_tariffs.routing_policy",
                check_name="Routing policy is bounded",
                category="plans",
                status="pass" if server_pool or (plan.traffic_policy or {}) else "degraded",
                severity="warning",
                target=plan_target,
                safe_summary="Routing policy has pool/policy metadata"
                if server_pool or (plan.traffic_policy or {})
                else "Routing policy metadata is sparse",
                details={"server_pool": server_pool, "traffic_policy_keys": sorted((plan.traffic_policy or {}).keys())},
            ),
            _result(
                check_key="all_tariffs.device_limit",
                check_name="Device limit is explicit",
                category="plans",
                status="pass" if int(plan.device_limit or 0) > 0 else "fail",
                target=plan_target,
                safe_summary=(
                    "Device limit is positive" if int(plan.device_limit or 0) > 0 else "Device limit is missing"
                ),
                details={"device_limit": int(plan.device_limit or 0)},
            ),
            _result(
                check_key="all_tariffs.traffic_policy",
                check_name="Traffic policy is explicit",
                category="plans",
                status="pass" if plan.traffic_limit_bytes or (plan.traffic_policy or {}) else "degraded",
                severity="warning",
                target=plan_target,
                safe_summary="Traffic limit or traffic policy is declared"
                if plan.traffic_limit_bytes or (plan.traffic_policy or {})
                else "Traffic policy is implicit",
                details={
                    "traffic_limit_bytes": plan.traffic_limit_bytes,
                    "traffic_policy_keys": sorted((plan.traffic_policy or {}).keys()),
                },
            ),
            _result(
                check_key="all_tariffs.visibility_policy",
                check_name="Catalog visibility is explicit",
                category="plans",
                status="pass"
                if _visibility(plan) in {"public", "private_code_gated", "admin_only", "internal_test", "hidden"}
                else "degraded",
                severity="warning",
                target=plan_target,
                safe_summary=f"Visibility policy: {_visibility(plan)}",
                details={"visibility": _visibility(plan)},
            ),
        ]
        return checks

    def _all_tariffs_results(
        self, plans: list[SubscriptionPlanModel], route_entries: list[Any]
    ) -> list[dict[str, Any]]:
        if not plans:
            return [
                _result(
                    check_key="all_tariffs.inventory",
                    check_name="Active tariff inventory",
                    category="plans",
                    status="fail",
                    safe_summary="No active tariffs found",
                    details={"total": 0},
                )
            ]
        results: list[dict[str, Any]] = []
        for plan in plans:
            results.extend(self._plan_contract_checks(plan))
            assignment = expected_remnawave_assignment(plan)
            if assignment["is_premium_smart_ru"]:
                configured = bool(assignment["expected_internal_squad_uuid_present"]) and bool(
                    assignment["expected_external_squad_uuid_present"]
                )
                results.append(
                    _result(
                        check_key="all_tariffs.remnawave_assignment",
                        check_name="Tariff Remnawave assignment",
                        category="plans",
                        status="pass" if configured else "fail",
                        target=_plan_target(plan),
                        safe_summary="Premium Smart RU has internal/external squad assignment intent"
                        if configured
                        else "Premium Smart RU Remnawave assignment is incomplete",
                        details={
                            "internal_squad_configured": bool(assignment["expected_internal_squad_uuid_present"]),
                            "external_squad_configured": bool(assignment["expected_external_squad_uuid_present"]),
                            "template_configured": bool(assignment["expected_subscription_template_name_present"]),
                        },
                    )
                )
            results.extend(generated_subscription_checks(plan, route_entries))
        return results

    async def _contract_results(
        self,
        suite_spec: dict[str, Any],
        plans: list[SubscriptionPlanModel],
        route_entries: list[Any],
        *,
        request_context: Mapping[str, Any] | None = None,
        generated_mihomo_artifact: Any = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        results.append(
            _result(
                check_key="suite.dsl.valid",
                check_name="Suite DSL is loadable",
                category="static",
                status="pass" if suite_spec.get("checks") else "fail",
                safe_summary="Suite contains explicit checks"
                if suite_spec.get("checks")
                else "Suite checks are missing",
                details={"suite_key": suite_spec.get("suite_key"), "version": suite_spec.get("version")},
            )
        )

        target_codes = set(_str_list(suite_spec.get("target_plan_codes") or settings.remnawave_smart_ru_plan_codes))
        target_plans = [
            plan for plan in plans if _plan_code(plan).lower() in target_codes or plan.name.lower() in target_codes
        ]
        results.append(
            _result(
                check_key="premium_smart_ru.plan.exists",
                check_name="Premium Smart RU tariff exists",
                category="plans",
                status="pass" if target_plans else "fail",
                safe_summary="Premium Smart RU tariff is active"
                if target_plans
                else "Premium Smart RU tariff was not found among active plans",
                details={"target_plan_codes": sorted(target_codes), "matched_count": len(target_plans)},
            )
        )

        if generated_mihomo_artifact is None:
            generated_mihomo_artifact = await self._generated_mihomo_artifact(request_context)
        generated_artifact_summary = generated_mihomo_artifact_summary(generated_mihomo_artifact)
        remnawave_nodes_result = await self._remnawave_nodes_result()
        remnawave_transport_results = await self._remnawave_transport_results()
        generated_xhttp_ready = int(generated_artifact_summary.get("xhttp_proxy_count") or 0) == 4
        generated_raw_ready = int(generated_artifact_summary.get("vless_reality_tcp_proxy_count") or 0) == 4

        required_modes = set(_str_list(suite_spec.get("required_connection_modes") or []))
        for plan in target_plans:
            modes = set(_str_list(plan.connection_modes))
            effective_modes = set(modes)
            assignment = expected_remnawave_assignment(plan)
            if assignment["requires_xhttp"] and generated_xhttp_ready:
                effective_modes.add("xhttp")
            if assignment["is_premium_smart_ru"] and generated_raw_ready:
                effective_modes.add("raw")
            missing = sorted(required_modes - effective_modes)
            results.append(
                _result(
                    check_key="premium_smart_ru.connection_modes",
                    check_name="Premium Smart RU connection modes",
                    category="plans",
                    status="pass" if not missing else "fail",
                    target=_plan_target(plan),
                    safe_summary="Required connection modes present"
                    if not missing
                    else f"Missing modes: {', '.join(missing)}",
                    details={
                        "required_modes": sorted(required_modes),
                        "actual_modes": sorted(modes),
                        "effective_modes": sorted(effective_modes),
                        "xhttp_satisfied_by_remnawave_assignment": "xhttp" not in modes and "xhttp" in effective_modes,
                        "xhttp_satisfied_by_generated_subscription": generated_xhttp_ready,
                        "raw_satisfied_by_generated_subscription": generated_raw_ready,
                    },
                )
            )

        results.append(
            _result(
                check_key="premium_smart_ru.route_registry",
                check_name="Premium Smart RU route registry",
                category="route_registry",
                status="pass" if len(route_entries) >= 40 else "fail",
                safe_summary="Golden route registry v2 has at least 40 entries"
                if len(route_entries) >= 40
                else "Golden route registry v2 is missing required route coverage",
                details={
                    "route_count": len(route_entries),
                    "required_route_count": 40,
                    "registry_key": suite_spec.get("required_route_registry"),
                    "routes": [
                        {
                            "route_key": item.route_key,
                            "country_code": item.country_code,
                            "node_tags": item.node_tags,
                            "expected_modes": item.expected_modes,
                        }
                        for item in route_entries
                    ],
                },
            )
        )

        mihomo_template = str(suite_spec.get("mihomo_template") or "").strip() or _default_mihomo_template()
        results.extend(analyze_mihomo_template(mihomo_template, route_entries))
        for plan in target_plans:
            results.extend(
                generated_subscription_checks(
                    plan,
                    route_entries,
                    generated_mihomo_artifact=generated_mihomo_artifact,
                )
            )
        results.append(self._feature_flag_result())
        results.append(remnawave_nodes_result)
        results.extend(remnawave_transport_results)
        return results

    async def _runtime_results(
        self,
        run: VpnTestRunModel,
        route_entries: list[Any],
        *,
        generated_mihomo_artifact: Any = None,
    ) -> list[dict[str, Any]]:
        if not settings.vpn_tester_runtime_enabled:
            return [
                _result(
                    check_key="runtime.enabled",
                    check_name="Runtime checks enabled",
                    category="runtime",
                    status="skipped",
                    severity="warning",
                    safe_summary="Runtime checks are disabled by VPN_TESTER_RUNTIME_ENABLED",
                    details={"runtime_enabled": False, "tun_sandbox": False},
                )
            ]
        if not runtime_agent_configured():
            vpn_tester_runtime_agent_unavailable_total.labels(reason="not_configured").inc()
            return [
                _result(
                    check_key="runtime.agent.available",
                    check_name="Runtime agent availability",
                    category="runtime",
                    status="degraded",
                    severity="warning",
                    safe_summary="Runtime agent is not configured",
                    details={"agent_configured": False, "tun_sandbox": False},
                )
            ]
        started = perf_counter()
        try:
            payload = await call_runtime_agent(
                run_id=str(run.id),
                suite_key=run.suite_key,
                mode=run.mode,
                route_entries=route_entries,
                generated_mihomo_artifact=generated_mihomo_artifact,
            )
        except HTTPError as exc:
            vpn_tester_runtime_agent_unavailable_total.labels(reason=type(exc).__name__).inc()
            return [
                _result(
                    check_key="runtime.agent.available",
                    check_name="Runtime agent availability",
                    category="runtime",
                    status="degraded",
                    severity="warning",
                    safe_summary="Runtime agent request failed",
                    details={"error_type": type(exc).__name__, "tun_sandbox": False},
                    started=started,
                )
            ]
        agent_status = str(payload.get("status") or "degraded")
        checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
        if not checks:
            checks = [
                {
                    "check_key": "runtime.agent.response",
                    "check_name": "Runtime agent response",
                    "category": "runtime",
                    "status": agent_status if agent_status in {"pass", "degraded", "fail", "skipped"} else "degraded",
                    "severity": "warning",
                    "target": "runtime-agent",
                    "safe_summary": str(payload.get("reason") or "Runtime agent returned safe status"),
                    "details": {
                        "agent_id": payload.get("agent_id"),
                        "runtime_mode": payload.get("runtime_mode"),
                        "tun_sandbox": bool(payload.get("tun_sandbox")),
                    },
                    "duration_ms": _elapsed_ms(started),
                }
            ]
        normalized: list[dict[str, Any]] = []
        for item in checks:
            if not isinstance(item, dict):
                continue
            normalized.append(
                _result(
                    check_key=str(item.get("check_key") or "runtime.agent.check"),
                    check_name=str(item.get("check_name") or "Runtime agent check"),
                    category="runtime",
                    status=str(item.get("status") or "degraded"),
                    severity=str(item.get("severity") or "warning"),
                    target=str(item.get("target") or "runtime-agent"),
                    safe_summary=str(item.get("safe_summary") or "Runtime check completed"),
                    details=dict(item.get("details") or {}),
                    started=started,
                )
            )
        return normalized or checks

    async def _balancer_preview_results(
        self, plans: list[SubscriptionPlanModel], route_entries: list[Any]
    ) -> list[dict[str, Any]]:
        status = "pass" if plans and route_entries else "degraded"
        summary = (
            "Balancer preview has enough contract metadata"
            if status == "pass"
            else "Balancer preview lacks plan or route metadata"
        )
        return [
            _result(
                check_key="balancer.preview.read_only",
                check_name="Read-only balancer preview",
                category="balancer",
                status=status,
                severity="warning",
                safe_summary=summary,
                details={
                    "active_plan_count": len(plans),
                    "route_count": len(route_entries),
                    "mutates_live_state": False,
                },
            )
        ]

    def _feature_flag_result(self) -> dict[str, Any]:
        xhttp_enabled = bool(settings.remnawave_feature_xhttp_enabled)
        force_disabled = bool(settings.remnawave_feature_xhttp_force_disabled)
        rollout_mode = settings.remnawave_feature_xhttp_rollout_mode
        acceptable = (
            xhttp_enabled
            and not force_disabled
            and rollout_mode in {"premium_smart_ru", "stable", "canary", "internal"}
        )
        return _result(
            check_key="remnawave.xhttp.flags",
            check_name="Remnawave XHTTP rollout flags",
            category="remnawave",
            status="pass" if acceptable else "degraded",
            severity="warning",
            safe_summary="XHTTP rollout flags are compatible"
            if acceptable
            else "XHTTP rollout flags are not fully enabled",
            details={
                "xhttp_enabled": xhttp_enabled,
                "force_disabled": force_disabled,
                "rollout_mode": rollout_mode,
                "allowed_plan_codes": _csv(settings.remnawave_feature_xhttp_allowed_plan_codes),
            },
        )

    async def _remnawave_nodes_result(self) -> dict[str, Any]:
        started = perf_counter()
        if self._remnawave_client is None:
            return _result(
                check_key="remnawave.nodes.contract",
                check_name="Remnawave node contract snapshot",
                category="remnawave",
                status="degraded",
                severity="warning",
                safe_summary="Remnawave client is unavailable",
                details={"source": "not_configured"},
                started=started,
            )
        try:
            payload = await self._remnawave_client.get("/nodes")
        except HTTPError as exc:
            return _result(
                check_key="remnawave.nodes.contract",
                check_name="Remnawave node contract snapshot",
                category="remnawave",
                status="degraded",
                severity="warning",
                safe_summary="Remnawave nodes endpoint is degraded",
                details={"error_type": type(exc).__name__},
                started=started,
            )
        nodes = _extract_nodes(payload)
        target_names = set(PREMIUM_SMART_RU_NODE_HOSTS.values())
        matched_nodes = [node for node in nodes if str(node.get("name") or "") in target_names]
        connected_enabled_names = {
            str(node.get("name") or "")
            for node in matched_nodes
            if bool(node.get("isConnected") if "isConnected" in node else node.get("is_connected"))
            and not bool(node.get("isDisabled") if "isDisabled" in node else node.get("is_disabled"))
        }
        missing_names = sorted(target_names - connected_enabled_names)
        xhttp_count = 0
        ru_count = 0
        for node in nodes:
            tags = _node_tags(node)
            if "xhttp" in tags:
                xhttp_count += 1
            if "ru" in tags or str(node.get("country_code") or node.get("countryCode") or "").upper() == "RU":
                ru_count += 1
        valid = len(matched_nodes) == 4 and not missing_names
        return _result(
            check_key="remnawave.nodes.contract",
            check_name="Remnawave node contract snapshot",
            category="remnawave",
            status="pass" if valid else "fail",
            safe_summary="Four Premium Smart RU nodes are connected and enabled"
            if valid
            else "Premium Smart RU node availability contract is incomplete",
            details={
                "node_count": len(nodes),
                "target_node_count": len(matched_nodes),
                "connected_enabled_target_count": len(connected_enabled_names),
                "missing_or_unavailable_nodes": missing_names,
                "xhttp_tagged_node_count": xhttp_count,
                "ru_node_count": ru_count,
            },
            started=started,
        )

    async def _remnawave_transport_results(self) -> list[dict[str, Any]]:
        started = perf_counter()
        check_specs = (
            (
                "remnawave.inbounds.vless_reality_raw_tcp",
                "Remnawave VLESS Reality RAW/TCP inbound",
            ),
            (
                "remnawave.inbounds.vless_reality_xhttp",
                "Remnawave VLESS Reality XHTTP inbound",
            ),
            ("remnawave.hosts.transport_matrix", "Remnawave Smart RU host transport matrix"),
        )

        def failed_results(reason: str, error_type: str | None = None) -> list[dict[str, Any]]:
            details = {"reason": reason, "secrets_redacted": True}
            if error_type:
                details["error_type"] = error_type
            return [
                _result(
                    check_key=check_key,
                    check_name=check_name,
                    category="remnawave",
                    status="fail",
                    safe_summary="Required Remnawave transport contract could not be verified",
                    details=details,
                    started=started,
                )
                for check_key, check_name in check_specs
            ]

        if self._remnawave_client is None:
            return failed_results("remnawave_client_not_configured")

        try:
            inbounds_payload = await self._remnawave_client.get("/config-profiles/inbounds")
            hosts_payload = await self._remnawave_client.get("/hosts")
            squads_payload = await self._remnawave_client.get("/internal-squads")
            nodes_payload = await self._remnawave_client.get("/nodes")
        except HTTPError as exc:
            return failed_results("remnawave_transport_endpoints_unavailable", type(exc).__name__)

        inbounds = _extract_collection(inbounds_payload, "inbounds")
        hosts = _extract_collection(hosts_payload, "hosts")
        squads = _extract_collection(squads_payload, "internalSquads")
        nodes = _extract_nodes(nodes_payload)
        raw_rows = [row for row in inbounds if str(row.get("tag") or "") == "VLESS_REALITY_443"]
        xhttp_rows = [row for row in inbounds if str(row.get("tag") or "") == "VLESS_XHTTP_REALITY_8443"]

        squad = next(
            (row for row in squads if str(row.get("name") or "") == PREMIUM_SMART_RU_INTERNAL_SQUAD),
            None,
        )
        squad_tags = {
            str(item.get("tag") or "")
            for item in (squad.get("inbounds") if isinstance(squad, dict) else []) or []
            if isinstance(item, dict)
        }
        raw_contract = _safe_raw_inbound_contract(raw_rows[0]) if len(raw_rows) == 1 else {}
        xhttp_contract = _safe_xhttp_inbound_contract(xhttp_rows[0]) if len(xhttp_rows) == 1 else {}
        raw_valid = len(raw_rows) == 1 and all(raw_contract.values()) and "VLESS_REALITY_443" in squad_tags
        xhttp_valid = len(xhttp_rows) == 1 and all(xhttp_contract.values()) and "VLESS_XHTTP_REALITY_8443" in squad_tags
        inbound_tags_by_uuid = {
            str(row.get("uuid")): str(row.get("tag") or "")
            for row in inbounds
            if row.get("uuid") and str(row.get("tag") or "") in PREMIUM_SMART_RU_INBOUND_TAGS
        }
        node_names_by_uuid = {
            str(node.get("uuid")): str(node.get("name") or "")
            for node in nodes
            if node.get("uuid") and node.get("name")
        }
        host_details = _safe_transport_host_matrix(
            hosts,
            inbound_tags_by_uuid=inbound_tags_by_uuid,
            node_names_by_uuid=node_names_by_uuid,
        )
        host_valid = bool(host_details.pop("valid"))

        return [
            _result(
                check_key="remnawave.inbounds.vless_reality_raw_tcp",
                check_name="Remnawave VLESS Reality RAW/TCP inbound",
                category="remnawave",
                status="pass" if raw_valid else "fail",
                safe_summary="VLESS_REALITY_443 satisfies the server contract"
                if raw_valid
                else "VLESS_REALITY_443 server contract is invalid",
                details={
                    "inbound_count": len(raw_rows),
                    "internal_squad_linked": "VLESS_REALITY_443" in squad_tags,
                    "contract": raw_contract,
                    "secrets_redacted": True,
                },
                started=started,
            ),
            _result(
                check_key="remnawave.inbounds.vless_reality_xhttp",
                check_name="Remnawave VLESS Reality XHTTP inbound",
                category="remnawave",
                status="pass" if xhttp_valid else "fail",
                safe_summary="VLESS_XHTTP_REALITY_8443 satisfies the server contract"
                if xhttp_valid
                else "VLESS_XHTTP_REALITY_8443 server contract is invalid",
                details={
                    "inbound_count": len(xhttp_rows),
                    "internal_squad_linked": "VLESS_XHTTP_REALITY_8443" in squad_tags,
                    "contract": xhttp_contract,
                    "secrets_redacted": True,
                },
                started=started,
            ),
            _result(
                check_key="remnawave.hosts.transport_matrix",
                check_name="Remnawave Smart RU host transport matrix",
                category="remnawave",
                status="pass" if host_valid else "fail",
                safe_summary="Eight Smart RU hosts are enabled and linked to the expected nodes"
                if host_valid
                else "Smart RU host transport matrix is incomplete",
                details={**host_details, "secrets_redacted": True},
                started=started,
            ),
        ]

    def _evidence(
        self,
        run: VpnTestRunModel,
        *,
        suite_spec: dict[str, Any],
        results: list[dict[str, Any]],
        plans: list[SubscriptionPlanModel],
    ) -> list[dict[str, Any]]:
        plan_preview = [_safe_plan_payload(plan) for plan in plans[:50]]
        preview, digest = safe_artifact_preview(
            {
                "run_id": str(run.id),
                "suite": {"suite_key": suite_spec.get("suite_key"), "version": suite_spec.get("version")},
                "results": results,
                "plans": plan_preview,
            }
        )
        return [
            {
                "artifact_key": "contract-summary",
                "artifact_type": "json_preview",
                "sha256": digest,
                "preview": preview,
                "storage_uri": None,
                "expires_at": _utc_now() + timedelta(days=max(1, settings.vpn_tester_retention_days)),
            }
        ]


def _extract_nodes(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("nodes", "items", "response"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _extract_collection(payload: Any, collection_key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    direct = payload.get(collection_key)
    if isinstance(direct, list):
        return [item for item in direct if isinstance(item, dict)]
    response = payload.get("response")
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    if isinstance(response, dict):
        nested = response.get(collection_key)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
    return []


def _safe_inbound_parts(inbound: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    raw = inbound.get("rawInbound") or inbound.get("raw_inbound")
    raw = raw if isinstance(raw, Mapping) else {}
    settings_value = raw.get("settings")
    settings_map = settings_value if isinstance(settings_value, Mapping) else {}
    stream_value = raw.get("streamSettings")
    stream = stream_value if isinstance(stream_value, Mapping) else {}
    reality_value = stream.get("realitySettings")
    reality = reality_value if isinstance(reality_value, Mapping) else {}
    return settings_map, stream, reality


def _safe_reality_contract(reality: Mapping[str, Any]) -> dict[str, bool]:
    target = str(reality.get("target") or reality.get("dest") or "")
    server_names = reality.get("serverNames")
    short_ids = reality.get("shortIds")
    target_hostname = target.rsplit(":", 1)[0].strip("[]").lower() if ":" in target else ""
    primary_server_name = (
        str(server_names[0]).strip().lower() if isinstance(server_names, list) and server_names else ""
    )
    return {
        "server_names_present": isinstance(server_names, list) and bool(server_names),
        "server_name_matches_target": bool(target_hostname) and primary_server_name == target_hostname,
        "short_ids_present": isinstance(short_ids, list) and bool(short_ids),
        "private_key_present": bool(reality.get("privateKey")),
        "target_443_present": bool(target) and target.endswith(":443"),
    }


def _safe_raw_inbound_contract(inbound: Mapping[str, Any]) -> dict[str, bool]:
    settings_map, stream, reality = _safe_inbound_parts(inbound)
    raw = inbound.get("rawInbound") or inbound.get("raw_inbound")
    raw = raw if isinstance(raw, Mapping) else {}
    sniffing_value = raw.get("sniffing")
    sniffing = sniffing_value if isinstance(sniffing_value, Mapping) else {}
    overrides = sniffing.get("destOverride")
    override_set = {str(item).lower() for item in overrides} if isinstance(overrides, list) else set()
    return {
        "type_vless": str(inbound.get("type") or raw.get("protocol") or "").lower() == "vless",
        "network_raw_tcp": str(inbound.get("network") or stream.get("network") or "").lower() in {"raw", "tcp"},
        "security_reality": str(inbound.get("security") or stream.get("security") or "").lower() == "reality",
        "port_443": int(inbound.get("port") or raw.get("port") or 0) == 443,
        "decryption_none": str(settings_map.get("decryption") or "") == "none",
        "flow_vision": str(settings_map.get("flow") or "") == "xtls-rprx-vision",
        **_safe_reality_contract(reality),
        "sniffing_enabled": sniffing.get("enabled") is True,
        "dest_override_http_tls_quic": {"http", "tls", "quic"}.issubset(override_set),
    }


def _safe_xhttp_inbound_contract(inbound: Mapping[str, Any]) -> dict[str, bool]:
    settings_map, stream, reality = _safe_inbound_parts(inbound)
    raw = inbound.get("rawInbound") or inbound.get("raw_inbound")
    raw = raw if isinstance(raw, Mapping) else {}
    return {
        "type_vless": str(inbound.get("type") or raw.get("protocol") or "").lower() == "vless",
        "network_xhttp": str(inbound.get("network") or stream.get("network") or "").lower() == "xhttp",
        "security_reality": str(inbound.get("security") or stream.get("security") or "").lower() == "reality",
        "port_8443": int(inbound.get("port") or raw.get("port") or 0) == 8443,
        "decryption_none": str(settings_map.get("decryption") or "") == "none",
        **_safe_reality_contract(reality),
    }


def _safe_transport_host_matrix(
    hosts: list[dict[str, Any]],
    *,
    inbound_tags_by_uuid: Mapping[str, str] | None = None,
    node_names_by_uuid: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    expected = {
        (address, 443, "VLESS_REALITY_443", node_name) for address, node_name in PREMIUM_SMART_RU_NODE_HOSTS.items()
    } | {
        (address, 8443, "VLESS_XHTTP_REALITY_8443", node_name)
        for address, node_name in PREMIUM_SMART_RU_NODE_HOSTS.items()
    }
    actual_counts: Counter[tuple[str, int, str, str]] = Counter()
    candidate_host_count = 0
    disabled_count = 0
    excluded_required_format_count = 0
    inbound_reference_resolved_count = 0
    expanded_node_link_count = 0
    unresolved_node_reference_count = 0
    tag_by_uuid = inbound_tags_by_uuid or {}
    name_by_uuid = node_names_by_uuid or {}
    for host in hosts:
        address = str(host.get("address") or "")
        if address not in PREMIUM_SMART_RU_NODE_HOSTS:
            continue
        inbound_value = host.get("inbound")
        inbound = inbound_value if isinstance(inbound_value, Mapping) else {}
        inbound_uuid = str(inbound.get("configProfileInboundUuid") or inbound.get("uuid") or "")
        embedded_tag = str(inbound.get("tag") or host.get("inboundTag") or "")
        tag = embedded_tag or tag_by_uuid.get(inbound_uuid, "")
        if tag not in PREMIUM_SMART_RU_INBOUND_TAGS:
            continue
        if not embedded_tag and inbound_uuid and tag:
            inbound_reference_resolved_count += 1
        candidate_host_count += 1
        port = int(host.get("port") or 0)
        if bool(host.get("isDisabled") if "isDisabled" in host else host.get("is_disabled")):
            disabled_count += 1
        exclusions = host.get("excludeFromSubscriptionTypes") or host.get("exclude_from_subscription_types") or []
        exclusion_set = {str(item).upper() for item in exclusions} if isinstance(exclusions, list) else set()
        if exclusion_set & {"MIHOMO", "XRAY_BASE64"}:
            excluded_required_format_count += 1
        nodes_value = host.get("nodes")
        nodes = nodes_value if isinstance(nodes_value, list) else []
        linked_node_names: list[str] = []
        for node in nodes:
            if isinstance(node, Mapping):
                node_uuid = str(node.get("uuid") or node.get("nodeUuid") or "")
                node_name = str(node.get("name") or name_by_uuid.get(node_uuid, ""))
            else:
                node_name = name_by_uuid.get(str(node), "")
            if node_name:
                linked_node_names.append(node_name)
            else:
                unresolved_node_reference_count += 1
        for node_name in linked_node_names:
            actual_counts[(address, port, tag, node_name)] += 1
            expanded_node_link_count += 1
    actual = set(actual_counts)
    missing = expected - actual
    unexpected = actual - expected
    duplicate_link_count = sum(count - 1 for count in actual_counts.values() if count > 1)
    raw_host_count = len({item for item in actual if item[2] == "VLESS_REALITY_443"})
    xhttp_host_count = len({item for item in actual if item[2] == "VLESS_XHTTP_REALITY_8443"})
    return {
        "valid": not missing
        and not unexpected
        and candidate_host_count == 8
        and expanded_node_link_count == 8
        and unresolved_node_reference_count == 0
        and duplicate_link_count == 0
        and disabled_count == 0
        and excluded_required_format_count == 0
        and raw_host_count == 4
        and xhttp_host_count == 4,
        "raw_host_count": raw_host_count,
        "xhttp_host_count": xhttp_host_count,
        "candidate_host_count": candidate_host_count,
        "missing_link_count": len(missing),
        "unexpected_link_count": len(unexpected),
        "duplicate_link_count": duplicate_link_count,
        "disabled_host_count": disabled_count,
        "excluded_required_format_count": excluded_required_format_count,
        "inbound_reference_resolved_count": inbound_reference_resolved_count,
        "expanded_node_link_count": expanded_node_link_count,
        "unresolved_node_reference_count": unresolved_node_reference_count,
    }


def _node_tags(node: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    raw_tags = node.get("tags")
    if isinstance(raw_tags, list):
        tags.update(str(item).strip().lower() for item in raw_tags if str(item).strip())
    raw_tag = node.get("tag")
    if isinstance(raw_tag, str) and raw_tag.strip():
        tags.add(raw_tag.strip().lower())
    name = str(node.get("name") or node.get("remark") or "").lower()
    for marker in ("ru", "xhttp", "moscow", "spb", "premium_smart_ru"):
        if marker in name:
            tags.add(marker)
    return tags
