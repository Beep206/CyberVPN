import logging
from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from httpx import HTTPStatusError

from src.config.settings import settings
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.monitoring.metrics import (
    remnawave_xhttp_canary_enabled_total,
    remnawave_xhttp_rollback_total,
    remnawave_xhttp_subscription_failed_total,
    remnawave_xhttp_subscription_generated_total,
    remnawave_xhttp_users_total,
)
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveSubscriptionDetailsResponse
from src.infrastructure.remnawave.subscription_urls import (
    normalize_public_subscription_url,
    normalize_public_subscription_urls,
)

logger = logging.getLogger(__name__)


class GenerateConfigUseCase:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    @staticmethod
    def _is_placeholder_link(link: str) -> bool:
        lowered = link.lower()
        return (
            "00000000-0000-0000-0000-000000000000@0.0.0.0:1" in lowered
            or "no%20hosts%20found" in lowered
            or "check%20hosts%20tab" in lowered
            or "check%20internal%20squads%20tab" in lowered
        )

    @classmethod
    def _select_primary_config(
        cls,
        *,
        links: list[str],
        subscription_url: str | None,
    ) -> str:
        if subscription_url:
            return subscription_url

        for link in links:
            if link and not cls._is_placeholder_link(link):
                return link
        return links[0] if links else ""

    @staticmethod
    def _detect_client_type(config: str) -> str:
        if not config or "://" not in config:
            return "subscription"
        scheme = config.split("://", 1)[0].lower()
        return "subscription" if scheme in {"http", "https"} else scheme

    @staticmethod
    def _is_xhttp_link(link: str) -> bool:
        lowered = link.lower()
        return "type=xhttp" in lowered or "xhttp" in lowered

    @classmethod
    def _xhttp_links(cls, links: list[str]) -> list[str]:
        return [link for link in links if cls._is_xhttp_link(link)]

    @classmethod
    def _filter_xhttp_links(cls, links: list[str]) -> list[str]:
        return [link for link in links if not cls._is_xhttp_link(link)]

    @staticmethod
    def _csv_values(raw: str) -> set[str]:
        return {item.strip().lower() for item in raw.split(",") if item.strip()}

    @classmethod
    def _xhttp_enabled_for_output(
        cls,
        *,
        plan_code: str | None = None,
        user_segments: Sequence[str] | None = None,
    ) -> bool:
        if settings.remnawave_feature_xhttp_force_disabled:
            return False
        if not settings.remnawave_feature_xhttp_enabled:
            return False
        rollout_mode = settings.remnawave_feature_xhttp_rollout_mode
        if rollout_mode == "disabled":
            return False
        if rollout_mode == "stable":
            return True

        normalized_plan_code = (plan_code or "").strip().lower()
        allowed_plan_codes = cls._csv_values(settings.remnawave_feature_xhttp_allowed_plan_codes)
        normalized_segments = {segment.strip().lower() for segment in user_segments or () if segment.strip()}
        allowed_segments = cls._csv_values(settings.remnawave_feature_xhttp_allowed_user_segments)

        if rollout_mode == "premium_smart_ru":
            return normalized_plan_code in allowed_plan_codes
        if rollout_mode in {"canary", "internal"}:
            return bool(normalized_segments & allowed_segments)
        return False

    async def execute(
        self,
        user_ref: RemnawaveUserRef | int,
        *,
        plan_code: str | None = None,
        user_segments: Sequence[str] | None = None,
    ) -> dict:
        numeric_user_id = user_ref.require_numeric_id() if isinstance(user_ref, RemnawaveUserRef) else user_ref
        if isinstance(numeric_user_id, bool) or not isinstance(numeric_user_id, int) or numeric_user_id <= 0:
            raise ValueError("Remnawave 3.x config reads require a reconciled numeric user id")
        return await self._execute_subscription_path(
            f"/subscriptions/by-id/{numeric_user_id}",
            plan_code=plan_code,
            user_segments=user_segments,
        )

    async def _execute_subscription_path(
        self,
        subscription_path: str,
        *,
        plan_code: str | None,
        user_segments: Sequence[str] | None,
    ) -> dict:
        try:
            data = await self._client.get_validated(
                subscription_path,
                RemnawaveSubscriptionDetailsResponse,
            )
        except HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription config not found",
                ) from exc
            raise

        if not data.is_found or data.user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription config not found",
            )

        if (data.user.user_status or "").upper() == "EXPIRED":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Subscription expired",
            )

        links = normalize_public_subscription_urls([*data.links, *data.xhttp_links])
        subscription_url = normalize_public_subscription_url(data.subscription_url)
        rollout_mode = settings.remnawave_feature_xhttp_rollout_mode
        candidate_xhttp_links = self._xhttp_links(links)
        xhttp_allowed = self._xhttp_enabled_for_output(plan_code=plan_code, user_segments=user_segments)
        if candidate_xhttp_links and not xhttp_allowed:
            links = self._filter_xhttp_links(links)
            remnawave_xhttp_rollback_total.labels(rollout_mode=rollout_mode).inc()
            logger.info(
                "remnawave_xhttp_links_filtered",
                extra={
                    "rollout_mode": rollout_mode,
                    "force_disabled": settings.remnawave_feature_xhttp_force_disabled,
                    "candidate_count": len(candidate_xhttp_links),
                    "plan_code_present": bool(plan_code),
                    "segment_count": len(user_segments or ()),
                },
            )
        elif candidate_xhttp_links:
            remnawave_xhttp_users_total.labels(rollout_mode=rollout_mode).inc()
            remnawave_xhttp_canary_enabled_total.labels(rollout_mode=rollout_mode).inc()
            logger.info(
                "remnawave_xhttp_links_allowed",
                extra={
                    "rollout_mode": rollout_mode,
                    "candidate_count": len(candidate_xhttp_links),
                    "mihomo_enabled": settings.remnawave_feature_xhttp_mihomo_enabled,
                },
            )
        elif settings.remnawave_feature_xhttp_enabled and rollout_mode != "disabled":
            remnawave_xhttp_subscription_failed_total.labels(
                rollout_mode=rollout_mode,
                reason="no_xhttp_candidates",
            ).inc()

        remnawave_xhttp_subscription_generated_total.labels(
            rollout_mode=rollout_mode,
            status="xhttp" if candidate_xhttp_links and xhttp_allowed else "stable_only",
        ).inc()
        config = self._select_primary_config(
            links=links,
            subscription_url=subscription_url,
        )
        return {
            "config": config,
            "config_string": config,
            "client_type": self._detect_client_type(config),
            "is_found": data.is_found,
            "links": links,
            "ss_conf_links": data.ss_conf_links,
            "subscription_url": subscription_url,
            "xhttp_enabled": bool(candidate_xhttp_links and xhttp_allowed),
            "xhttp_links": candidate_xhttp_links if xhttp_allowed else [],
        }


class GenerateConfigLegacyRollbackUseCase:
    """Explicit Remnawave 2.x UUID reader, isolated from normal 3.x paths."""

    def __init__(self, client: RemnawaveClient) -> None:
        self._delegate = GenerateConfigUseCase(client)

    async def execute(
        self,
        legacy_uuid: UUID,
        *,
        plan_code: str | None = None,
        user_segments: Sequence[str] | None = None,
    ) -> dict:
        if not isinstance(legacy_uuid, UUID):
            raise ValueError("Legacy rollback config reads require a UUID")
        return await self._delegate._execute_subscription_path(
            f"/subscriptions/by-uuid/{legacy_uuid}",
            plan_code=plan_code,
            user_segments=user_segments,
        )
