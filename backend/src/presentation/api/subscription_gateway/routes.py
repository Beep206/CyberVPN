from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.subscription_gateway.resolve import (
    ResolveSubscriptionProductUseCase,
    SubscriptionGatewayNotFoundError,
    SubscriptionGatewayUnavailableError,
)
from src.config.settings import settings
from src.infrastructure.monitoring.subscription_gateway_metrics import (
    subscription_gateway_resolution_total,
    subscription_generation_failures_total,
    subscription_response_total,
)
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.subscription_proxy import (
    RemnawaveSubscriptionProxyClient,
    SubscriptionUpstreamNotFoundError,
    SubscriptionUpstreamUnavailableError,
)
from src.presentation.dependencies.client_ip import resolve_client_ip
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.remnawave import get_remnawave_client
from src.presentation.dependencies.subscription_gateway import get_remnawave_subscription_proxy_client

router = APIRouter(include_in_schema=False)

FORWARDED_CLIENT_HEADERS = frozenset(
    {
        "accept",
        "accept-language",
        "user-agent",
        "x-device-model",
        "x-device-os",
        "x-hwid",
        "x-ver-os",
    }
)


def classify_client_family(request: Request) -> str:
    user_agent = request.headers.get("user-agent", "").lower()
    accept = request.headers.get("accept", "").lower()
    if user_agent.startswith("incy/"):
        return "incy"
    if user_agent.startswith("happ/"):
        return "happ"
    if user_agent.startswith(
        (
            "clashmeta",
            "clash-verge",
            "clash/",
            "mihomo/",
            "stash/",
        )
    ):
        return "mihomo"
    if "text/html" in accept:
        return "browser"
    return "generic"


def response_type_for_client_family(client_family: str) -> str:
    return {
        "browser": "BROWSER",
        "mihomo": "MIHOMO",
        "incy": "XRAY_JSON",
        "happ": "XRAY_JSON",
        "generic": "COMPATIBILITY",
    }[client_family]


def build_upstream_headers(
    request: Request,
    *,
    product_code: str,
    client_family: str,
) -> dict[str, str]:
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() in FORWARDED_CLIENT_HEADERS and len(value) <= 4096
    }

    public_url = urlparse(settings.remnawave_subscription_public_base_url)
    public_host = public_url.hostname or "cyber-vpn.org"
    client_ip = resolve_client_ip(request).ip
    headers.update(
        {
            "Host": public_host,
            "X-Forwarded-Host": public_host,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Port": "443",
            "X-CyberVPN-Product": product_code,
            "X-CyberVPN-Client-Family": client_family,
        }
    )
    if client_ip != "unknown":
        headers["X-Forwarded-For"] = client_ip
    return headers


@router.get("/api/sub/{short_uuid}")
async def get_product_scoped_subscription(
    short_uuid: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    subscription_proxy: RemnawaveSubscriptionProxyClient = Depends(get_remnawave_subscription_proxy_client),
) -> Response:
    client_family = classify_client_family(request)
    try:
        resolved = await ResolveSubscriptionProductUseCase(db, remnawave_client).execute(short_uuid)
    except SubscriptionGatewayNotFoundError:
        subscription_gateway_resolution_total.labels(result="not_found", client=client_family).inc()
        return Response(status_code=status.HTTP_404_NOT_FOUND, headers={"Cache-Control": "no-store"})
    except SubscriptionGatewayUnavailableError:
        subscription_gateway_resolution_total.labels(result="unavailable", client=client_family).inc()
        return Response(
            content=b"Subscription service unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="text/plain",
            headers={"Cache-Control": "no-store", "Retry-After": "30"},
        )

    subscription_gateway_resolution_total.labels(result="resolved", client=client_family).inc()
    try:
        upstream = await subscription_proxy.fetch(
            short_uuid,
            headers=build_upstream_headers(
                request,
                product_code=resolved.product_code,
                client_family=client_family,
            ),
        )
    except SubscriptionUpstreamNotFoundError:
        subscription_generation_failures_total.labels(product=resolved.product_code, client=client_family).inc()
        return Response(status_code=status.HTTP_404_NOT_FOUND, headers={"Cache-Control": "no-store"})
    except SubscriptionUpstreamUnavailableError:
        subscription_generation_failures_total.labels(product=resolved.product_code, client=client_family).inc()
        return Response(
            content=b"Subscription service unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="text/plain",
            headers={"Cache-Control": "no-store", "Retry-After": "30"},
        )

    subscription_response_total.labels(
        product=resolved.product_code,
        client=client_family,
        response_type=response_type_for_client_family(client_family),
    ).inc()
    return Response(content=upstream.content, status_code=status.HTTP_200_OK, headers=upstream.headers)
