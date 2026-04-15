#![forbid(unsafe_code)]

use sha2::{Digest, Sha256};
use tracing_subscriber::{EnvFilter, fmt};

pub mod fields {
    pub const EVENT_NAME: &str = "event.name";
    pub const SESSION_ID: &str = "session.id";
    pub const DEVICE_ID: &str = "device.id";
    pub const MANIFEST_ID: &str = "manifest.id";
    pub const POLICY_EPOCH: &str = "policy.epoch";
    pub const BRIDGE_REQUEST_ID: &str = "bridge.req_id";
    pub const CARRIER_KIND: &str = "carrier.kind";
    pub const ROUTE: &str = "http.route";
    pub const BACKEND_NAME: &str = "backend.name";
    pub const BACKEND_SCOPE: &str = "backend.scope";
    pub const ENDPOINT_HASH: &str = "endpoint.hash";
    pub const AVAILABLE: &str = "available";
    pub const OPERATION: &str = "operation";
    pub const FAILURE_KIND: &str = "failure.kind";
    pub const STATUS_CODE: &str = "status.code";
    pub const CLOSE_REASON: &str = "close.reason";
    pub const REASON: &str = "reason";
    pub const LIMIT_NAME: &str = "limit.name";
    pub const LIMIT_VALUE: &str = "limit.value";
}

pub fn redact_secret(value: &str) -> String {
    if value.is_empty() {
        return "<empty>".to_owned();
    }

    let digest = Sha256::digest(value.as_bytes());
    format!("sha256:{:x}", digest)[..19].to_owned()
}

pub fn init_tracing(service_name: &str, json_logs: bool) {
    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(format!("{service_name}=info")));

    let builder = fmt().with_env_filter(filter).with_target(false);
    if json_logs {
        builder.json().init();
    } else {
        builder.compact().init();
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BridgeStoreServiceHealthEvent {
    pub event_name: &'static str,
    pub backend_name: String,
    pub backend_scope: String,
    pub endpoint_hash: String,
    pub available: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BridgeStoreServiceFailureEvent {
    pub event_name: &'static str,
    pub backend_name: String,
    pub backend_scope: String,
    pub endpoint_hash: String,
    pub operation: String,
    pub failure_kind: String,
    pub status_code: Option<u16>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BridgeHttpBodyRejectedEvent {
    pub event_name: &'static str,
    pub route: &'static str,
    pub limit_name: &'static str,
    pub limit_value: usize,
    pub actual_bytes: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GatewayRelayGuardEvent {
    pub event_name: &'static str,
    pub reason: &'static str,
    pub limit_name: &'static str,
    pub limit_value: u64,
    pub actual_value: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CarrierRelayClosedEvent {
    pub event_name: &'static str,
    pub reason: String,
    pub bytes_from_client: u64,
    pub bytes_to_client: u64,
    pub client_half_closed: bool,
    pub upstream_half_closed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CarrierDatagramSelectionEvent {
    pub event_name: &'static str,
    pub selection: &'static str,
    pub datagram_mode: &'static str,
    pub carrier_available: bool,
    pub fallback_allowed: bool,
    pub rollout_stage: &'static str,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CarrierDatagramGuardEvent {
    pub event_name: &'static str,
    pub reason: &'static str,
    pub limit_name: &'static str,
    pub limit_value: u64,
    pub actual_value: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CarrierDatagramIoEvent {
    pub event_name: &'static str,
    pub direction: &'static str,
}

pub fn bridge_store_service_health_event(
    backend_name: &str,
    backend_scope: &str,
    endpoint: &str,
    available: bool,
) -> BridgeStoreServiceHealthEvent {
    BridgeStoreServiceHealthEvent {
        event_name: "verta.bridge.store.service_health",
        backend_name: backend_name.to_owned(),
        backend_scope: backend_scope.to_owned(),
        endpoint_hash: redact_secret(endpoint),
        available,
    }
}

pub fn bridge_store_service_failure_event(
    backend_name: &str,
    backend_scope: &str,
    endpoint: &str,
    operation: &str,
    failure_kind: &str,
    status_code: Option<u16>,
) -> BridgeStoreServiceFailureEvent {
    BridgeStoreServiceFailureEvent {
        event_name: "verta.bridge.store.service_failure",
        backend_name: backend_name.to_owned(),
        backend_scope: backend_scope.to_owned(),
        endpoint_hash: redact_secret(endpoint),
        operation: operation.to_owned(),
        failure_kind: failure_kind.to_owned(),
        status_code,
    }
}

pub fn bridge_http_body_rejected_event(
    route: &'static str,
    limit_name: &'static str,
    limit_value: usize,
    actual_bytes: usize,
) -> BridgeHttpBodyRejectedEvent {
    BridgeHttpBodyRejectedEvent {
        event_name: "verta.bridge.http.body_rejected",
        route,
        limit_name,
        limit_value,
        actual_bytes,
    }
}

pub fn gateway_relay_guard_event(
    reason: &'static str,
    limit_name: &'static str,
    limit_value: u64,
    actual_value: Option<u64>,
) -> GatewayRelayGuardEvent {
    GatewayRelayGuardEvent {
        event_name: "verta.gateway.relay.guard",
        reason,
        limit_name,
        limit_value,
        actual_value,
    }
}

pub fn carrier_relay_closed_event(
    reason: &str,
    bytes_from_client: u64,
    bytes_to_client: u64,
    client_half_closed: bool,
    upstream_half_closed: bool,
) -> CarrierRelayClosedEvent {
    CarrierRelayClosedEvent {
        event_name: "verta.carrier.relay.closed",
        reason: reason.to_owned(),
        bytes_from_client,
        bytes_to_client,
        client_half_closed,
        upstream_half_closed,
    }
}

pub fn carrier_datagram_selection_event(
    selection: &'static str,
    datagram_mode: &'static str,
    carrier_available: bool,
    fallback_allowed: bool,
    rollout_stage: &'static str,
) -> CarrierDatagramSelectionEvent {
    CarrierDatagramSelectionEvent {
        event_name: "verta.carrier.datagram.selection",
        selection,
        datagram_mode,
        carrier_available,
        fallback_allowed,
        rollout_stage,
    }
}

pub fn carrier_datagram_guard_event(
    reason: &'static str,
    limit_name: &'static str,
    limit_value: u64,
    actual_value: Option<u64>,
) -> CarrierDatagramGuardEvent {
    CarrierDatagramGuardEvent {
        event_name: "verta.carrier.datagram.guard",
        reason,
        limit_name,
        limit_value,
        actual_value,
    }
}

pub fn carrier_datagram_io_event(direction: &'static str) -> CarrierDatagramIoEvent {
    CarrierDatagramIoEvent {
        event_name: "verta.carrier.datagram.io",
        direction,
    }
}

pub fn record_bridge_store_backend_selected(backend_name: &str, backend_scope: &str) {
    tracing::info!(
        event_name = "verta.bridge.store.backend_selected",
        counter = 1_u64,
        backend_name,
        backend_scope,
        "bridge store backend selected"
    );
}

pub fn record_bridge_store_service_health(
    backend_name: &str,
    backend_scope: &str,
    endpoint: &str,
    available: bool,
) {
    let event = bridge_store_service_health_event(backend_name, backend_scope, endpoint, available);
    tracing::info!(
        event_name = event.event_name,
        counter = 1_u64,
        backend_name = event.backend_name,
        backend_scope = event.backend_scope,
        endpoint_hash = event.endpoint_hash,
        available = event.available,
        "bridge store service health evaluated"
    );
}

pub fn record_bridge_store_service_failure(
    backend_name: &str,
    backend_scope: &str,
    endpoint: &str,
    operation: &str,
    failure_kind: &str,
    status_code: Option<u16>,
) {
    let event = bridge_store_service_failure_event(
        backend_name,
        backend_scope,
        endpoint,
        operation,
        failure_kind,
        status_code,
    );
    tracing::warn!(
        event_name = event.event_name,
        counter = 1_u64,
        backend_name = event.backend_name,
        backend_scope = event.backend_scope,
        endpoint_hash = event.endpoint_hash,
        operation = event.operation,
        failure_kind = event.failure_kind,
        status_code = event.status_code,
        "bridge store service request failed"
    );
}

pub fn record_bridge_http_body_rejected(
    route: &'static str,
    limit_name: &'static str,
    limit_value: usize,
    actual_bytes: usize,
) {
    let event = bridge_http_body_rejected_event(route, limit_name, limit_value, actual_bytes);
    tracing::warn!(
        event_name = event.event_name,
        counter = 1_u64,
        route = event.route,
        limit_name = event.limit_name,
        limit_value = event.limit_value,
        actual_bytes = event.actual_bytes,
        "bridge HTTP request body rejected by budget"
    );
}

pub fn record_gateway_relay_guard(
    reason: &'static str,
    limit_name: &'static str,
    limit_value: u64,
    actual_value: Option<u64>,
) {
    let event = gateway_relay_guard_event(reason, limit_name, limit_value, actual_value);
    tracing::warn!(
        event_name = event.event_name,
        counter = 1_u64,
        reason = event.reason,
        limit_name = event.limit_name,
        limit_value = event.limit_value,
        actual_value = event.actual_value,
        "gateway relay guard triggered"
    );
}

pub fn record_carrier_relay_closed(
    reason: &str,
    bytes_from_client: u64,
    bytes_to_client: u64,
    client_half_closed: bool,
    upstream_half_closed: bool,
) {
    let event = carrier_relay_closed_event(
        reason,
        bytes_from_client,
        bytes_to_client,
        client_half_closed,
        upstream_half_closed,
    );
    tracing::info!(
        event_name = event.event_name,
        counter = 1_u64,
        reason = event.reason,
        bytes_from_client = event.bytes_from_client,
        bytes_to_client = event.bytes_to_client,
        client_half_closed = event.client_half_closed,
        upstream_half_closed = event.upstream_half_closed,
        "carrier relay runtime closed"
    );
}

pub fn record_carrier_datagram_selection(
    selection: &'static str,
    datagram_mode: &'static str,
    carrier_available: bool,
    fallback_allowed: bool,
    rollout_stage: &'static str,
) {
    let event = carrier_datagram_selection_event(
        selection,
        datagram_mode,
        carrier_available,
        fallback_allowed,
        rollout_stage,
    );
    tracing::info!(
        event_name = event.event_name,
        counter = 1_u64,
        selection = event.selection,
        datagram_mode = event.datagram_mode,
        carrier_available = event.carrier_available,
        fallback_allowed = event.fallback_allowed,
        rollout_stage = event.rollout_stage,
        "carrier datagram transport mode selected"
    );
}

pub fn record_carrier_datagram_guard(
    reason: &'static str,
    limit_name: &'static str,
    limit_value: u64,
    actual_value: Option<u64>,
) {
    let event = carrier_datagram_guard_event(reason, limit_name, limit_value, actual_value);
    tracing::warn!(
        event_name = event.event_name,
        counter = 1_u64,
        reason = event.reason,
        limit_name = event.limit_name,
        limit_value = event.limit_value,
        actual_value = event.actual_value,
        "carrier datagram guard triggered"
    );
}

pub fn record_carrier_datagram_io(direction: &'static str) {
    let event = carrier_datagram_io_event(direction);
    tracing::info!(
        event_name = event.event_name,
        counter = 1_u64,
        direction = event.direction,
        "carrier datagram processed"
    );
}

#[cfg(test)]
mod tests {
    use super::{
        bridge_http_body_rejected_event, bridge_store_service_failure_event,
        bridge_store_service_health_event, carrier_datagram_guard_event, carrier_datagram_io_event,
        carrier_datagram_selection_event, carrier_relay_closed_event, gateway_relay_guard_event,
        redact_secret,
    };

    #[test]
    fn redaction_does_not_return_the_secret() {
        let redacted = redact_secret("super-secret-token");
        assert_ne!(redacted, "super-secret-token");
        assert!(redacted.starts_with("sha256:"));
    }

    #[test]
    fn bridge_store_service_events_expose_stable_low_cardinality_fields() {
        let health = bridge_store_service_health_event(
            "service",
            "shared_durable",
            "https://store.internal",
            false,
        );
        assert_eq!(health.event_name, "verta.bridge.store.service_health");
        assert_eq!(health.backend_name, "service");
        assert_eq!(health.backend_scope, "shared_durable");
        assert!(health.endpoint_hash.starts_with("sha256:"));
        assert!(!health.available);

        let failure = bridge_store_service_failure_event(
            "service",
            "shared_durable",
            "https://store.internal",
            "check_health",
            "timeout",
            Some(503),
        );
        assert_eq!(failure.operation, "check_health");
        assert_eq!(failure.failure_kind, "timeout");
        assert_eq!(failure.status_code, Some(503));
    }

    #[test]
    fn bridge_and_gateway_budget_events_keep_stable_fields() {
        let bridge =
            bridge_http_body_rejected_event("/v0/token/exchange", "max_json_body_bytes", 96, 128);
        assert_eq!(bridge.event_name, "verta.bridge.http.body_rejected");
        assert_eq!(bridge.route, "/v0/token/exchange");
        assert_eq!(bridge.limit_name, "max_json_body_bytes");

        let guard = gateway_relay_guard_event(
            "relay_idle_timeout",
            "relay_idle_timeout_ms",
            30_000,
            Some(30_100),
        );
        assert_eq!(guard.event_name, "verta.gateway.relay.guard");
        assert_eq!(guard.reason, "relay_idle_timeout");
        assert_eq!(guard.limit_name, "relay_idle_timeout_ms");

        let overload = gateway_relay_guard_event("relay_overloaded", "max_active_relays", 1, None);
        assert_eq!(overload.event_name, "verta.gateway.relay.guard");
        assert_eq!(overload.reason, "relay_overloaded");
        assert_eq!(overload.limit_name, "max_active_relays");
    }

    #[test]
    fn carrier_relay_close_event_keeps_stable_reason_fields() {
        let event = carrier_relay_closed_event("upstream_finished", 64, 32, true, true);
        assert_eq!(event.event_name, "verta.carrier.relay.closed");
        assert_eq!(event.reason, "upstream_finished");
        assert_eq!(event.bytes_from_client, 64);
        assert_eq!(event.bytes_to_client, 32);
        assert!(event.client_half_closed);
        assert!(event.upstream_half_closed);

        let timeout = carrier_relay_closed_event("idle_timeout", 0, 0, false, false);
        assert_eq!(timeout.event_name, "verta.carrier.relay.closed");
        assert_eq!(timeout.reason, "idle_timeout");
    }

    #[test]
    fn carrier_datagram_events_keep_stable_low_cardinality_fields() {
        let datagram = carrier_datagram_selection_event(
            "datagram",
            "available_and_enabled",
            true,
            true,
            "automatic",
        );
        assert_eq!(datagram.event_name, "verta.carrier.datagram.selection");
        assert_eq!(datagram.selection, "datagram");
        assert_eq!(datagram.datagram_mode, "available_and_enabled");
        assert!(datagram.carrier_available);
        assert!(datagram.fallback_allowed);
        assert_eq!(datagram.rollout_stage, "automatic");

        let selection = carrier_datagram_selection_event(
            "stream_fallback",
            "unavailable",
            false,
            true,
            "automatic",
        );
        assert_eq!(selection.event_name, "verta.carrier.datagram.selection");
        assert_eq!(selection.selection, "stream_fallback");
        assert_eq!(selection.datagram_mode, "unavailable");
        assert!(!selection.carrier_available);
        assert!(selection.fallback_allowed);
        assert_eq!(selection.rollout_stage, "automatic");

        let disabled = carrier_datagram_selection_event(
            "stream_fallback",
            "disabled_by_policy",
            true,
            true,
            "disabled",
        );
        assert_eq!(disabled.event_name, "verta.carrier.datagram.selection");
        assert_eq!(disabled.selection, "stream_fallback");
        assert_eq!(disabled.datagram_mode, "disabled_by_policy");
        assert!(disabled.carrier_available);
        assert!(disabled.fallback_allowed);
        assert_eq!(disabled.rollout_stage, "disabled");

        let canary = carrier_datagram_selection_event(
            "stream_fallback",
            "available_and_enabled",
            true,
            true,
            "canary",
        );
        assert_eq!(canary.event_name, "verta.carrier.datagram.selection");
        assert_eq!(canary.selection, "stream_fallback");
        assert_eq!(canary.datagram_mode, "available_and_enabled");
        assert!(canary.carrier_available);
        assert!(canary.fallback_allowed);
        assert_eq!(canary.rollout_stage, "canary");

        let guard = carrier_datagram_guard_event(
            "udp_payload_too_large",
            "max_udp_payload_bytes",
            1200,
            Some(1400),
        );
        assert_eq!(guard.event_name, "verta.carrier.datagram.guard");
        assert_eq!(guard.reason, "udp_payload_too_large");
        assert_eq!(guard.limit_name, "max_udp_payload_bytes");
        assert_eq!(guard.limit_value, 1200);
        assert_eq!(guard.actual_value, Some(1400));

        let queue_full = carrier_datagram_guard_event(
            "udp_datagram_queue_full",
            "max_buffered_datagram_bytes",
            8192,
            Some(9000),
        );
        assert_eq!(queue_full.event_name, "verta.carrier.datagram.guard");
        assert_eq!(queue_full.reason, "udp_datagram_queue_full");
        assert_eq!(queue_full.limit_name, "max_buffered_datagram_bytes");
        assert_eq!(queue_full.limit_value, 8192);
        assert_eq!(queue_full.actual_value, Some(9000));

        let session_burst = carrier_datagram_guard_event(
            "udp_datagram_session_burst_exceeded",
            "max_buffered_datagrams",
            8,
            Some(9),
        );
        assert_eq!(session_burst.event_name, "verta.carrier.datagram.guard");
        assert_eq!(session_burst.reason, "udp_datagram_session_burst_exceeded");
        assert_eq!(session_burst.limit_name, "max_buffered_datagrams");
        assert_eq!(session_burst.limit_value, 8);
        assert_eq!(session_burst.actual_value, Some(9));

        let flow_burst = carrier_datagram_guard_event(
            "udp_datagram_flow_burst_exceeded",
            "max_buffered_datagrams_per_flow",
            4,
            Some(5),
        );
        assert_eq!(flow_burst.event_name, "verta.carrier.datagram.guard");
        assert_eq!(flow_burst.reason, "udp_datagram_flow_burst_exceeded");
        assert_eq!(flow_burst.limit_name, "max_buffered_datagrams_per_flow");
        assert_eq!(flow_burst.limit_value, 4);
        assert_eq!(flow_burst.actual_value, Some(5));

        let mismatch = carrier_datagram_guard_event(
            "udp_associated_stream_mismatch",
            "associated_stream_id",
            0,
            None,
        );
        assert_eq!(mismatch.event_name, "verta.carrier.datagram.guard");
        assert_eq!(mismatch.reason, "udp_associated_stream_mismatch");
        assert_eq!(mismatch.limit_name, "associated_stream_id");
        assert_eq!(mismatch.limit_value, 0);
        assert_eq!(mismatch.actual_value, None);

        let inbound = carrier_datagram_io_event("inbound");
        assert_eq!(inbound.event_name, "verta.carrier.datagram.io");
        assert_eq!(inbound.direction, "inbound");

        let outbound = carrier_datagram_io_event("outbound");
        assert_eq!(outbound.event_name, "verta.carrier.datagram.io");
        assert_eq!(outbound.direction, "outbound");
    }
}
