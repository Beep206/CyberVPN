from fastapi import Depends

from src.application.services.cache_service import CacheService
from src.application.services.helix_service import HelixService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.helix.client import get_helix_adapter_client
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.subscription_client import (
    CachedSubscriptionClient,
    RemnawaveSubscriptionClient,
)
from src.presentation.dependencies.remnawave import get_remnawave_client


async def get_helix_service(
    adapter_client=Depends(get_helix_adapter_client),
    remnawave_client: RemnawaveClient = Depends(get_remnawave_client),
    redis_client=Depends(get_redis),
) -> HelixService:
    subscription_client = CachedSubscriptionClient(
        inner=RemnawaveSubscriptionClient(remnawave_client),
        cache=CacheService(redis_client),
    )
    return HelixService(
        adapter_client=adapter_client,
        subscription_client=subscription_client,
    )
