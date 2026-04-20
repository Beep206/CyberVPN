from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_telegram_channel_parity_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/telegram/bot/user/{{telegram_id}}/subscriptions" in paths
    assert f"{API_V1_PREFIX}/telegram/bot/user/{{telegram_id}}/entitlements" in paths
    assert f"{API_V1_PREFIX}/telegram/bot/user/{{telegram_id}}/orders" in paths
    assert f"{API_V1_PREFIX}/telegram/bot/user/{{telegram_id}}/service-state" in paths

    assert "TelegramBotSubscriptionResponse" in components
    assert "CurrentEntitlementStateResponse" in components
    assert "OrderResponse" in components
    assert "CurrentServiceStateResponse" in components
