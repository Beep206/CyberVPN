from src.infrastructure.remnawave.subscription_proxy import (
    RemnawaveSubscriptionProxyClient,
    remnawave_subscription_proxy_client,
)


async def get_remnawave_subscription_proxy_client() -> RemnawaveSubscriptionProxyClient:
    return remnawave_subscription_proxy_client
