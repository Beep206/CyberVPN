from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_growth_notification_conformance_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    expected_paths = [
        f"{API_V1_PREFIX}/growth-notifications",
        f"{API_V1_PREFIX}/growth-notifications/counters",
        f"{API_V1_PREFIX}/growth-notifications/preferences",
        f"{API_V1_PREFIX}/growth-notifications/{{notification_id}}",
        f"{API_V1_PREFIX}/growth-notifications/{{notification_id}}/recovery",
        f"{API_V1_PREFIX}/growth-notifications/{{notification_id}}/support-escalation",
        f"{API_V1_PREFIX}/admin/growth-notification-deliveries",
        f"{API_V1_PREFIX}/admin/growth-notification-deliveries/{{delivery_id}}",
        f"{API_V1_PREFIX}/admin/growth-notification-deliveries/{{delivery_id}}/export",
        f"{API_V1_PREFIX}/admin/growth-notification-deliveries/{{delivery_id}}/resolve",
        f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}",
    ]

    for path in expected_paths:
        assert path in paths

    expected_components = [
        "GrowthNotificationDetailResponse",
        "GrowthNotificationDeliveryDetailResponse",
        "GrowthNotificationSupportHandoffResponse",
        "GrowthNotificationPreferencesResponse",
        "GrowthNotificationPreferencesUpdateRequest",
        "GrowthNotificationSupportEscalationRequest",
        "AdminGrowthNotificationDeliveryResponse",
        "AdminGrowthNotificationDeliveryDetailResponse",
        "AdminGrowthNotificationDeliveryActionRequest",
        "AdminUpdateMobileUserRequest",
    ]

    for component in expected_components:
        assert component in components


def test_growth_notification_conformance_components_expose_repair_and_forensics_fields() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]

    detail_properties = components["GrowthNotificationDetailResponse"]["properties"]
    assert "deliveries" in detail_properties
    assert "support_handoff" in detail_properties

    delivery_detail_properties = components["GrowthNotificationDeliveryDetailResponse"]["properties"]
    assert "troubleshooting_state" in delivery_detail_properties
    assert "customer_message_key" in delivery_detail_properties
    assert "recovery_allowed" in delivery_detail_properties
    assert "support_required" in delivery_detail_properties
    assert "repair_target" in delivery_detail_properties
    assert "events" in delivery_detail_properties

    support_handoff_properties = components["GrowthNotificationSupportHandoffResponse"]["properties"]
    assert "reference_code" in support_handoff_properties
    assert "suggested_escalation_channel" in support_handoff_properties
    assert "contact_subject" in support_handoff_properties
    assert "contact_body" in support_handoff_properties

    admin_delivery_properties = components["AdminGrowthNotificationDeliveryResponse"]["properties"]
    assert "can_resolve" in admin_delivery_properties
    assert "queue_error_message" in admin_delivery_properties

    admin_detail_properties = components["AdminGrowthNotificationDeliveryDetailResponse"]["properties"]
    assert "event_timeline" in admin_detail_properties
    assert "queue_snapshot" in admin_detail_properties
    assert "source_summary" in admin_detail_properties
    assert "support_summary" in admin_detail_properties

    action_request_properties = components["AdminGrowthNotificationDeliveryActionRequest"]["properties"]
    assert "reason_code" in action_request_properties
