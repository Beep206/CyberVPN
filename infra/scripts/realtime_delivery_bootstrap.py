#!/usr/bin/env python3
"""Render and validate the P2.7 realtime-delivery scaffold."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


REPO_P2_6_SPEC = Path("docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md")
REPO_OUTBOX_CONTRACT = Path("docs/api/platform-foundation-outbox-contract.md")
REPO_SSE_PUBLISHER = Path("services/task-worker/src/services/sse_publisher.py")
REPO_SSE_MANAGER = Path("backend/src/infrastructure/messaging/sse_manager.py")
REPO_WEBSOCKET_MANAGER = Path("backend/src/infrastructure/messaging/websocket_manager.py")
REPO_NOTIFICATION_HANDLER = Path("backend/src/application/events/handlers/notification_handler.py")
REPO_REMNAWAVE_WEBHOOK = Path("backend/src/application/use_cases/webhooks/remnawave_webhook.py")
REPO_WS_MONITORING = Path("backend/src/presentation/api/v1/ws/monitoring.py")
REPO_WS_NOTIFICATIONS = Path("backend/src/presentation/api/v1/ws/notifications.py")
REPO_ADMIN_REALTIME_LIB = Path("admin/src/features/integrations/lib/realtime.ts")
REPO_PARTNER_REALTIME_LIB = Path("partner/src/features/integrations/lib/realtime.ts")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def render_root_readme() -> str:
    return """# P2.7 realtime-delivery scaffold

This scaffold freezes the first canonical browser-delivery path for CyberVPN.

Frozen realtime path:

- PostgreSQL business commit
  -> persisted outbox
  -> NATS `PARTNER_EVENTS`
  -> `realtime_gateway_projection`
  -> server-side realtime gateway
  -> browser delivery

For the first business/browser path:

- primary browser delivery protocol: `SSE`
- secondary or interactive protocol: `WebSocket`
- selected first flow: `partner.workspace.feed`

Important boundaries:

- the existing monitoring websocket remains operational-only and is not the canonical business feed;
- the existing `/ws/notifications` path remains legacy until later cutover;
- direct Redis pub/sub SSE and direct backend WebSocket broadcast remain temporary delivery surfaces, not the authoritative backbone.
"""


def render_versions_env() -> str:
    return """REALTIME_GATEWAY_SPEC_VERSION=2026-04-22
PRIMARY_BROWSER_DELIVERY=sse
SECONDARY_BROWSER_DELIVERY=websocket
FIRST_CANONICAL_CHANNEL=partner.workspace.feed
FIRST_ACTIVE_STREAM=PARTNER_EVENTS
FIRST_PROJECTION_CONSUMER=realtime_gateway_projection
"""


def render_spec_manifest() -> str:
    return """documents:
  p2_6_stream_spec: docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md
  outbox_contract: docs/api/platform-foundation-outbox-contract.md
  realtime_gateway_spec: docs/api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md
repo_anchors:
  sse_publisher: services/task-worker/src/services/sse_publisher.py
  sse_manager: backend/src/infrastructure/messaging/sse_manager.py
  websocket_manager: backend/src/infrastructure/messaging/websocket_manager.py
  monitoring_ws_route: backend/src/presentation/api/v1/ws/monitoring.py
  notifications_ws_route: backend/src/presentation/api/v1/ws/notifications.py
legacy_operational_surfaces:
  - admin/src/features/integrations/lib/realtime.ts
  - partner/src/features/integrations/lib/realtime.ts
"""


def render_check_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-REPLACE_ME_REPO_ROOT}"

python "${REPO_ROOT}/infra/scripts/realtime_delivery_bootstrap.py" validate --repo-root "${REPO_ROOT}"
echo "Scaffold root: ${OUTPUT_DIR}"
"""


def render_gateway_readme() -> str:
    return """# realtime gateway

This scaffold models the canonical `P2.7` business/browser realtime bridge.

Frozen decisions:

- the realtime gateway sits downstream of the persisted outbox and NATS stream contract frozen in `P2.6`;
- the first canonical business/browser feed is `partner.workspace.feed`;
- the first browser delivery protocol is `SSE`;
- WebSocket remains available for interactive or operational topics but is not the default business dashboard protocol;
- operational monitoring sockets remain separate from the business/browser realtime path.
"""


def render_channel_registry() -> str:
    return """channels:
  - channel_name: partner.workspace.feed
    status: active_target_for_p2_7
    source_stream: PARTNER_EVENTS
    source_consumer: realtime_gateway_projection
    source_subjects:
      - partner.growth_code.>
      - partner.order.>
      - partner.settlement.>
      - partner.reporting.>
    source_of_truth_boundary: postgres.partner_control_db
    projection_store: postgres.realtime_gateway_projection_offsets
    browser_delivery_primary: sse
    browser_delivery_secondary: websocket
    browser_cursor_model: last_event_id
    fanout_mode: server_side_projection_then_push
  - channel_name: monitoring.topics
    status: operational_only
    backend_route: /api/v1/ws/monitoring
    browser_delivery_primary: websocket
    source_of_truth_boundary: operational_monitoring_only
  - channel_name: notifications.user
    status: legacy_temporary
    backend_route: /api/v1/ws/notifications
    browser_delivery_primary: websocket
    source_of_truth_boundary: legacy_direct_broadcast
"""


def render_projection_contract() -> str:
    return """projection_name: partner_workspace_feed
status: active_target_for_p2_7
consumer_name: realtime_gateway_projection
stream: PARTNER_EVENTS
filter_subjects:
  - partner.growth_code.>
  - partner.order.>
  - partner.settlement.>
  - partner.reporting.>
projection_store: postgres.realtime_gateway_projection_offsets
source_of_truth_boundary: postgres.partner_control_db
delivery_boundary:
  browser_protocol: sse
  downstream_push_only: true
idempotency_key_rule: event_id
replay_policy: rebuild_from_stream_supported
"""


def render_sse_endpoints() -> str:
    return """sse_endpoints:
  - path: /api/v1/realtime/partner/events
    status: active_target_for_p2_7
    auth_mode: same_app_session_or_bearer
    workspace_scope_required: true
    content_type: text/event-stream
    channel_name: partner.workspace.feed
    event_fields:
      - id
      - event
      - data
      - retry
    last_event_id_supported: true
    source_of_truth_boundary: realtime_gateway_projection
  - path: /api/v1/realtime/monitoring/stream
    status: prohibited_for_business_path
    reason: operational monitoring remains on websocket and must not become the business feed by accident
"""


def render_websocket_endpoints() -> str:
    return """websocket_endpoints:
  - path: /api/v1/ws/realtime/partner
    status: reserved_for_future_interactive_cases
    auth_mode: same_app_session_or_bearer
    channel_name: partner.workspace.feed
    allowed_use:
      - explicit interactive topic subscription
      - future bidirectional operator tooling
    not_default_for:
      - one_way_dashboard_fact_delivery
  - path: /api/v1/ws/monitoring
    status: operational_only_existing_surface
    topic_model: monitoring_topic_authorization
  - path: /api/v1/ws/notifications
    status: legacy_temporary
    migration_target: /api/v1/realtime/partner/events or other explicit business-specific channels
"""


def render_browser_event_contract() -> str:
    return """browser_event_contract:
  event_id: durable event identifier
  channel: partner.workspace.feed
  event_type: partner.* event type
  aggregate_type: owning aggregate type
  aggregate_id: owning aggregate identifier
  occurred_at: business occurrence timestamp
  delivered_at: realtime gateway delivery timestamp
  cursor: last_event_id compatible cursor
  payload: sanitized browser-facing payload
rules:
  - no provider-native event aliases
  - no raw internal publication rows exposed to browser clients
  - no raw outbox lease or broker metadata exposed to browser clients unless explicitly required for diagnostics
"""


def render_legacy_boundaries() -> str:
    return """legacy_realtime_boundaries:
  direct_redis_sse:
    path: services/task-worker/src/services/sse_publisher.py
    status: temporary
    source_of_truth: no
    migration_note: keep only as downstream compatibility path while canonical gateway cutover is incomplete
  direct_backend_websocket:
    path: backend/src/infrastructure/messaging/websocket_manager.py
    status: temporary
    source_of_truth: no
    migration_note: keep only for operational or explicitly legacy routes until the gateway path is live
  monitoring_socket:
    path: backend/src/presentation/api/v1/ws/monitoring.py
    status: operational_only
    source_of_truth: operational_signals_only
"""


def render_legacy_ui_notes() -> str:
    return """# legacy ui notes

Current admin and partner integrations consoles already build a monitoring websocket URL.

That surface remains:

- operational-only
- ticket-gated
- separate from the canonical business/browser realtime feed

`P2.7` does not reclassify that socket as the product dashboard feed.
"""


def command_render_scaffold(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    write_text(output_dir / "README.md", render_root_readme())
    write_text(output_dir / "versions.env", render_versions_env())
    write_text(output_dir / "spec-manifest.yaml", render_spec_manifest())
    write_text(output_dir / "scripts" / "check-realtime-delivery.sh", render_check_script(), mode=0o750)

    write_text(output_dir / "backend" / "realtime-gateway" / "README.md", render_gateway_readme())
    write_text(output_dir / "backend" / "realtime-gateway" / "channel-registry.yaml", render_channel_registry())
    write_text(
        output_dir / "backend" / "realtime-gateway" / "projections" / "partner-workspace-feed.yaml",
        render_projection_contract(),
    )
    write_text(output_dir / "backend" / "realtime-gateway" / "delivery" / "sse-endpoints.yaml", render_sse_endpoints())
    write_text(
        output_dir / "backend" / "realtime-gateway" / "delivery" / "websocket-endpoints.yaml",
        render_websocket_endpoints(),
    )
    write_text(
        output_dir / "backend" / "realtime-gateway" / "delivery" / "browser-event-contract.yaml",
        render_browser_event_contract(),
    )
    write_text(output_dir / "backend" / "realtime-gateway" / "legacy-boundaries.yaml", render_legacy_boundaries())
    write_text(output_dir / "frontend" / "legacy-ui-notes.md", render_legacy_ui_notes())
    return 0


def validate_repo(repo_root: Path) -> list[str]:
    errors: list[str] = []
    required_paths = (
        REPO_P2_6_SPEC,
        REPO_OUTBOX_CONTRACT,
        REPO_SSE_PUBLISHER,
        REPO_SSE_MANAGER,
        REPO_WEBSOCKET_MANAGER,
        REPO_NOTIFICATION_HANDLER,
        REPO_REMNAWAVE_WEBHOOK,
        REPO_WS_MONITORING,
        REPO_WS_NOTIFICATIONS,
        REPO_ADMIN_REALTIME_LIB,
        REPO_PARTNER_REALTIME_LIB,
    )
    for relative_path in required_paths:
        if not (repo_root / relative_path).exists():
            errors.append(f"Missing required P2.7 repo anchor: {relative_path}")

    p2_6_text = (repo_root / REPO_P2_6_SPEC).read_text(encoding="utf-8")
    for marker in ("realtime_gateway_projection", "reserved_for_p2_7", "PARTNER_EVENTS"):
        if marker not in p2_6_text:
            errors.append(f"P2.6 stream spec marker missing: {marker}")

    outbox_text = (repo_root / REPO_OUTBOX_CONTRACT).read_text(encoding="utf-8")
    for marker in ("transient SSE/WebSocket delivery to UI", "Direct Redis pub/sub SSE path", "Direct backend WebSocket broadcast path"):
        if marker not in outbox_text:
            errors.append(f"Outbox contract marker missing: {marker}")

    sse_text = (repo_root / REPO_SSE_PUBLISHER).read_text(encoding="utf-8")
    if 'SSE_CHANNEL = "cybervpn:sse:events"' not in sse_text:
        errors.append("Legacy SSE publisher no longer exposes the tracked cybervpn:sse:events channel marker")

    websocket_text = (repo_root / REPO_WEBSOCKET_MANAGER).read_text(encoding="utf-8")
    for marker in ("async def broadcast(", 'channel: str = "default"'):
        if marker not in websocket_text:
            errors.append(f"WebSocket manager marker missing: {marker}")

    monitoring_text = (repo_root / REPO_WS_MONITORING).read_text(encoding="utf-8")
    for marker in ('@router.websocket("/ws/monitoring")', '"available_topics"', '"subscribe"'):
        if marker not in monitoring_text:
            errors.append(f"Monitoring websocket marker missing: {marker}")

    notifications_text = (repo_root / REPO_WS_NOTIFICATIONS).read_text(encoding="utf-8")
    if '@router.websocket("/ws/notifications")' not in notifications_text:
        errors.append("Notifications websocket route marker missing")

    ui_markers = (
        (REPO_ADMIN_REALTIME_LIB, "buildMonitoringSocketUrl"),
        (REPO_PARTNER_REALTIME_LIB, "buildMonitoringSocketUrl"),
    )
    for path, marker in ui_markers:
        if marker not in (repo_root / path).read_text(encoding="utf-8"):
            errors.append(f"Legacy UI realtime marker missing in {path}: {marker}")

    return errors


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    errors = validate_repo(repo_root)
    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        return 1

    print("P2.7 realtime-delivery validation passed")
    print("primary_browser_delivery=sse")
    print("secondary_browser_delivery=websocket")
    print("first_canonical_channel=partner.workspace.feed")
    print("legacy_operational_socket=/api/v1/ws/monitoring")
    print("legacy_notifications_socket=/api/v1/ws/notifications")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render or validate the P2.7 realtime-delivery scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the repo-side P2.7 scaffold.")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.set_defaults(func=command_render_scaffold)

    validate = subparsers.add_parser("validate", help="Validate repo-side P2.7 anchors.")
    validate.add_argument("--repo-root", default=".")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
