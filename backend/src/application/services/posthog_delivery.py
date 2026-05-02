from __future__ import annotations

from typing import Any

import httpx

from src.application.services.posthog_bridge import PostHogCaptureRecord
from src.config.settings import settings


class PostHogDeliveryService:
    async def deliver(self, record: PostHogCaptureRecord) -> dict[str, Any]:
        if not settings.posthog_enabled:
            return {"status": "disabled"}

        host = settings.posthog_host.rstrip("/")
        project_key = settings.posthog_project_api_key.get_secret_value().strip()
        if not host or not project_key:
            return {"status": "misconfigured"}

        payload = {
            "api_key": project_key,
            "distinct_id": record.distinct_id,
            "event": record.event,
            "properties": dict(record.properties),
        }

        async with httpx.AsyncClient(timeout=settings.posthog_timeout_seconds) as client:
            response = await client.post(f"{host}/capture/", json=payload)
            response.raise_for_status()

        return {"status": "captured", "event": record.event}
