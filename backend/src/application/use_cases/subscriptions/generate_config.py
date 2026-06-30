import logging
from uuid import UUID

from fastapi import HTTPException, status
from httpx import HTTPStatusError

from src.config.settings import settings
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
    def _xhttp_enabled_for_output() -> bool:
        if settings.remnawave_feature_xhttp_force_disabled:
            return False
        if not settings.remnawave_feature_xhttp_enabled:
            return False
        return settings.remnawave_feature_xhttp_rollout_mode != "disabled"

    async def execute(self, user_uuid: UUID | str) -> dict:
        try:
            data = await self._client.get_validated(
                f"/subscriptions/by-uuid/{user_uuid}",
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
        xhttp_allowed = self._xhttp_enabled_for_output()
        if candidate_xhttp_links and not xhttp_allowed:
            links = self._filter_xhttp_links(links)
            remnawave_xhttp_rollback_total.labels(rollout_mode=rollout_mode).inc()
            logger.info(
                "remnawave_xhttp_links_filtered",
                extra={
                    "rollout_mode": rollout_mode,
                    "force_disabled": settings.remnawave_feature_xhttp_force_disabled,
                    "candidate_count": len(candidate_xhttp_links),
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
