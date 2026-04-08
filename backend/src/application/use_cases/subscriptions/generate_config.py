from uuid import UUID

from fastapi import HTTPException, status
from httpx import HTTPStatusError

from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.schemas.remnawave_responses import RemnawaveSubscriptionDetailsResponse


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
        for link in links:
            if link and not cls._is_placeholder_link(link):
                return link
        return subscription_url or (links[0] if links else "")

    @staticmethod
    def _detect_client_type(config: str) -> str:
        if not config or "://" not in config:
            return "subscription"
        scheme = config.split("://", 1)[0].lower()
        return "subscription" if scheme in {"http", "https"} else scheme

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

        config = self._select_primary_config(
            links=data.links,
            subscription_url=data.subscription_url,
        )
        return {
            "config": config,
            "config_string": config,
            "client_type": self._detect_client_type(config),
            "is_found": data.is_found,
            "links": data.links,
            "ss_conf_links": data.ss_conf_links,
            "subscription_url": data.subscription_url,
        }
