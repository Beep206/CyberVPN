#!/usr/bin/env python3
"""Render and validate the P2.6 event-backbone scaffold."""

from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
from typing import Any


REPO_PARTNER_EVENTS = Path("backend/src/application/events/partner_platform_events.py")
REPO_OUTBOX = Path("backend/src/application/events/outbox.py")
REPO_OUTBOX_REPO = Path("backend/src/infrastructure/database/repositories/outbox_repo.py")
REPO_OUTBOX_CONTRACT = Path("docs/api/platform-foundation-outbox-contract.md")
REPO_CONSUMER_CONTRACT = Path("docs/api/platform-foundation-consumer-contract.md")
REPO_STREAM_SPEC = Path("docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md")
REPO_LEGACY_SSE = Path("services/task-worker/src/services/sse_publisher.py")
REPO_LEGACY_WEBSOCKET = Path("backend/src/infrastructure/messaging/websocket_manager.py")

EXPECTED_OUTBOX_CONSUMERS = ("analytics_mart", "operational_replay")
RESERVED_SERVICE_CONSUMERS = ("notification_delivery", "realtime_gateway_projection")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def load_literal_assignment(path: Path, symbol_name: str) -> Any:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == symbol_name:
                    return ast.literal_eval(node.value)
    raise ValueError(f"Unable to find {symbol_name} in {path}")


def load_partner_event_families(repo_root: Path) -> dict[str, tuple[str, ...]]:
    payload = load_literal_assignment(repo_root / REPO_PARTNER_EVENTS, "PARTNER_PLATFORM_EVENT_FAMILIES")
    if not isinstance(payload, dict):
        raise ValueError("PARTNER_PLATFORM_EVENT_FAMILIES is not a dictionary")
    normalized: dict[str, tuple[str, ...]] = {}
    for family, events in payload.items():
        normalized[str(family)] = tuple(str(event_name) for event_name in events)
    return normalized


def load_default_outbox_consumers(repo_root: Path) -> tuple[str, ...]:
    payload = load_literal_assignment(repo_root / REPO_OUTBOX, "DEFAULT_OUTBOX_CONSUMERS")
    if not isinstance(payload, tuple):
        raise ValueError("DEFAULT_OUTBOX_CONSUMERS is not a tuple")
    return tuple(str(item) for item in payload)


def build_partner_subjects(event_families: dict[str, tuple[str, ...]]) -> list[str]:
    subjects = {f"partner.{event_name}.v1" for events in event_families.values() for event_name in events}
    return sorted(subjects)


def render_root_readme(*, event_count: int, consumer_count: int) -> str:
    return f"""# P2.6 event-backbone scaffold

This scaffold freezes the first repo-side event backbone contract for CyberVPN.

Current active baseline:

- the existing PostgreSQL-backed outbox remains the canonical publication boundary;
- the first active transport stream is `PARTNER_EVENTS`;
- the first active durable consumers are:
  - `analytics_mart`
  - `operational_replay`
- service-side notification and realtime gateway consumers remain reserved for `P2.7`, not silently active in `P2.6`.

Current render summary:

- partner-platform transport subjects: `{event_count}`
- active durable consumers rendered: `{consumer_count}`
- reserved service-side consumers rendered: `{len(RESERVED_SERVICE_CONSUMERS)}`

Important boundaries:

- this scaffold does not claim a live NATS dispatcher, live JetStream stream creation, or live consumer reconciliation already exists;
- this scaffold does not replace the persisted outbox tables or the current lease-and-status state machine;
- this scaffold exists to keep later P2 cut-in work aligned with the frozen outbox and consumer contracts instead of inventing a second event model.
"""


def render_backend_readme(*, event_count: int) -> str:
    return f"""# backend event backbone

This scaffold models the first application-side event backbone contract for `P2.6`.

Frozen decisions:

- the existing `outbox_events` and `outbox_publications` tables remain the durable publication anchor;
- transport subject mapping is derived from the current frozen partner-platform event taxonomy;
- the first active stream is `PARTNER_EVENTS`;
- the first active durable consumers are `analytics_mart` and `operational_replay`;
- direct Redis SSE and direct WebSocket fan-out remain temporary downstream delivery paths until `P2.7`.

Rendered active transport subjects: `{event_count}`
"""


def render_dispatcher_env_example() -> str:
    return """OUTBOX_DISPATCHER_LEASE_OWNER=backend-outbox-dispatcher
OUTBOX_DISPATCHER_BATCH_SIZE=100
OUTBOX_DISPATCHER_LEASE_SECONDS=30
OUTBOX_DISPATCHER_SUBMITTED_STATE_REQUIRED=true
NATS_URL=nats://REPLACE_ME_NATS_HOST:4222
NATS_ACCOUNT=platform-apps
NATS_PUBLISH_ACK_TIMEOUT=5s
NATS_MSG_ID_HEADER=Nats-Msg-Id
STREAM_DECLARATIONS_FILE=./dispatcher/stream-declarations.yaml
SUBJECT_ROUTE_MAP_FILE=./dispatcher/subject-route-map.yaml
CONSUMER_REGISTRY_DIR=./dispatcher/consumers
REPLAY_PLAN_DIR=./replay
"""


def render_stream_declarations(subjects: list[str]) -> str:
    subject_lines = "\n".join(f"      - {subject}" for subject in subjects)
    return f"""streams:
  - stream_name: PARTNER_EVENTS
    status: active_for_p2_6
    account: platform-apps
    source_of_truth_boundary: postgres.partner_control_db
    storage: file
    replicas: 3
    retention_policy: limits
    discard_policy: old
    deduplication_header: Nats-Msg-Id
    deduplication_window: 2m
    subjects:
{subject_lines}
reserved_future_streams:
  - BILLING_EVENTS
  - SUBSCRIPTION_EVENTS
  - NODE_LIFECYCLE_EVENTS
  - NODE_HEALTH_EVENTS
  - ANALYTICS_EVENTS
  - SYSTEM_ADVISORIES
"""


def render_subject_route_map(event_families: dict[str, tuple[str, ...]]) -> str:
    lines = ["routes:"]
    for family in sorted(event_families):
        lines.append(f"  # family: {family}")
        for event_name in event_families[family]:
            lines.extend(
                (
                    f"  - event_name: {event_name}",
                    f"    subject: partner.{event_name}.v1",
                    "    stream: PARTNER_EVENTS",
                    "    event_version: 1",
                )
            )
    return "\n".join(lines) + "\n"


def render_active_consumer_contract(
    *,
    consumer_name: str,
    consumer_class: str,
    owning_service: str,
    side_effect_type: str,
    runbook_url: str,
) -> str:
    return f"""consumer_name: {consumer_name}
consumer_class: {consumer_class}
status: active_for_p2_6
owning_service: {owning_service}
owning_team: backend-platform
stream: PARTNER_EVENTS
filter_subjects:
  - partner.>
input_schema_refs:
  - docs/api/partner-platform-event-taxonomy.md
  - docs/api/platform-foundation-event-taxonomy.md
delivery_policy: all
ack_policy: explicit
ack_wait: 30s
max_deliver: 10
backoff:
  - 1s
  - 5s
  - 30s
  - 5m
max_ack_pending: 200
consumer_mode: durable_pull
idempotency_store: postgres.outbox_publications
idempotency_key_rule: outbox_event_id
side_effect_type: {side_effect_type}
source_of_truth_boundary: postgres.partner_control_db
retry_policy: retry_then_alert
dlq_policy: backlog_and_operator_review
replay_policy: full_replay_supported
alert_policy:
  lag_warning_seconds: 30
  lag_critical_seconds: 120
  failure_rate_window: 15m
slo:
  p95_end_to_end_seconds: 1
runbook_url: {runbook_url}
"""


def render_reserved_service_consumer(
    *,
    consumer_name: str,
    side_effect_type: str,
    owning_service: str,
) -> str:
    return f"""consumer_name: {consumer_name}
status: reserved_for_p2_7
consumer_class: {"notification" if consumer_name == "notification_delivery" else "projection"}
owning_service: {owning_service}
owning_team: transport-backend
stream: PARTNER_EVENTS
filter_subjects:
  - partner.>
consumer_mode: durable_pull
idempotency_store: REPLACE_ME_DURABLE_IDEMPOTENCY_STORE
idempotency_key_rule: REPLACE_ME_DETERMINISTIC_KEY_RULE
side_effect_type: {side_effect_type}
source_of_truth_boundary: postgres.partner_control_db
why_reserved:
  - P2.6 freezes the durable contract only
  - live notification or realtime fan-out cut-in belongs to P2.7
"""


def render_replay_readme() -> str:
    return """# replay

This directory freezes the operator-facing replay model for `P2.6`.

Rules frozen here:

- business-critical durable consumers use durable pull consumers by default;
- ordered or replay-original consumers are inspection or operator tooling paths, not the default business side-effect path;
- replay never replaces the PostgreSQL outbox as the publication source of truth;
- replay approval, scope, and recovery notes must be recorded before live use.
"""


def render_replay_plan_example() -> str:
    return """replay_name: partner-events-projection-rebuild
approval_required: true
stream: PARTNER_EVENTS
target_consumer: analytics_mart
replay_mode: durable_pull_rebuild
starting_position:
  deliver_policy: by_start_time
  opt_start_time: 2026-04-22T00:00:00Z
operator_notes:
  - use durable pull replay for projection rebuilds and deterministic side effects
  - use ordered push replay only for inspection or timing-sensitive staging analysis
success_evidence:
  - backlog drained
  - replay lag returned to zero
  - target projection checksum or row-count verification recorded
"""


def render_services_readme() -> str:
    return """# task-worker reserved consumers

The current task-worker runtime still contains legacy notification and SSE fan-out paths.

`P2.6` does not silently activate those paths as durable NATS consumers. Instead it freezes the
reserved-next contract that must be implemented in `P2.7`.

Reserved service-side consumers:

- `notification_delivery`
- `realtime_gateway_projection`
"""


def render_check_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-REPLACE_ME_REPO_ROOT}"

python "${REPO_ROOT}/infra/scripts/event_backbone_bootstrap.py" validate --repo-root "${REPO_ROOT}"
echo "Scaffold root: ${OUTPUT_DIR}"
"""


def render_versions_env(*, event_count: int) -> str:
    return f"""EVENT_BACKBONE_SPEC_VERSION=2026-04-22
ACTIVE_STREAM=PARTNER_EVENTS
ACTIVE_CONSUMERS=analytics_mart,operational_replay
RESERVED_SERVICE_CONSUMERS=notification_delivery,realtime_gateway_projection
PARTNER_EVENT_SUBJECT_COUNT={event_count}
"""


def render_spec_manifest() -> str:
    return """documents:
  stream_spec: docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md
  outbox_contract: docs/api/platform-foundation-outbox-contract.md
  consumer_contract: docs/api/platform-foundation-consumer-contract.md
repo_anchors:
  outbox_module: backend/src/application/events/outbox.py
  partner_event_taxonomy: backend/src/application/events/partner_platform_events.py
  outbox_repository: backend/src/infrastructure/database/repositories/outbox_repo.py
legacy_delivery_paths:
  - services/task-worker/src/services/sse_publisher.py
  - backend/src/infrastructure/messaging/websocket_manager.py
"""


def command_render_scaffold(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()

    event_families = load_partner_event_families(repo_root)
    subjects = build_partner_subjects(event_families)

    write_text(output_dir / "README.md", render_root_readme(event_count=len(subjects), consumer_count=2))
    write_text(output_dir / "versions.env", render_versions_env(event_count=len(subjects)))
    write_text(output_dir / "spec-manifest.yaml", render_spec_manifest())
    write_text(output_dir / "scripts" / "check-event-backbone.sh", render_check_script(), mode=0o750)

    write_text(output_dir / "backend" / "README.md", render_backend_readme(event_count=len(subjects)))
    write_text(output_dir / "backend" / "dispatcher" / "dispatcher-runtime.env.example", render_dispatcher_env_example())
    write_text(output_dir / "backend" / "dispatcher" / "stream-declarations.yaml", render_stream_declarations(subjects))
    write_text(output_dir / "backend" / "dispatcher" / "subject-route-map.yaml", render_subject_route_map(event_families))
    write_text(
        output_dir / "backend" / "dispatcher" / "consumers" / "analytics-mart.yaml",
        render_active_consumer_contract(
            consumer_name="analytics_mart",
            consumer_class="projection",
            owning_service="backend-reporting",
            side_effect_type="reporting_mart_projection",
            runbook_url="docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md",
        ),
    )
    write_text(
        output_dir / "backend" / "dispatcher" / "consumers" / "operational-replay.yaml",
        render_active_consumer_contract(
            consumer_name="operational_replay",
            consumer_class="orchestration",
            owning_service="backend-reporting",
            side_effect_type="replay_pack_and_backlog_analysis",
            runbook_url="docs/testing/partner-platform-phase5-service-access-replay-pack.md",
        ),
    )
    write_text(output_dir / "backend" / "replay" / "README.md", render_replay_readme())
    write_text(output_dir / "backend" / "replay" / "replay-plan.example.yaml", render_replay_plan_example())

    write_text(output_dir / "services" / "task-worker" / "README.md", render_services_readme())
    write_text(
        output_dir / "services" / "task-worker" / "reserved-consumers" / "notification-delivery.yaml",
        render_reserved_service_consumer(
            consumer_name="notification_delivery",
            side_effect_type="email_telegram_or_sms_delivery",
            owning_service="task-worker",
        ),
    )
    write_text(
        output_dir / "services" / "task-worker" / "reserved-consumers" / "realtime-gateway-projection.yaml",
        render_reserved_service_consumer(
            consumer_name="realtime_gateway_projection",
            side_effect_type="server_side_realtime_projection",
            owning_service="realtime-gateway",
        ),
    )
    return 0


def validate_repo(repo_root: Path) -> list[str]:
    errors: list[str] = []
    consumers = load_default_outbox_consumers(repo_root)
    if consumers != EXPECTED_OUTBOX_CONSUMERS:
        errors.append(
            "DEFAULT_OUTBOX_CONSUMERS drifted from the frozen P2.6 baseline: "
            f"expected {EXPECTED_OUTBOX_CONSUMERS}, got {consumers}"
        )

    families = load_partner_event_families(repo_root)
    if not families:
        errors.append("Partner event families are empty")
    elif "growth_code" not in families or "settlement" not in families:
        errors.append("Partner event families are missing required baseline families")

    required_paths = (
        REPO_PARTNER_EVENTS,
        REPO_OUTBOX,
        REPO_OUTBOX_REPO,
        REPO_OUTBOX_CONTRACT,
        REPO_CONSUMER_CONTRACT,
        REPO_STREAM_SPEC,
        REPO_LEGACY_SSE,
        REPO_LEGACY_WEBSOCKET,
    )
    for relative_path in required_paths:
        if not (repo_root / relative_path).exists():
            errors.append(f"Missing required P2.6 repo anchor: {relative_path}")

    outbox_repo_text = (repo_root / REPO_OUTBOX_REPO).read_text(encoding="utf-8")
    for marker in (
        "claim_publications(",
        "mark_publication_submitted(",
        "mark_publication_published(",
        "mark_publication_failed(",
    ):
        if marker not in outbox_repo_text:
            errors.append(f"Missing outbox repository marker: {marker}")

    outbox_contract_text = (repo_root / REPO_OUTBOX_CONTRACT).read_text(encoding="utf-8")
    if "future NATS publication must sit downstream of the outbox" not in outbox_contract_text:
        errors.append("Outbox contract no longer freezes the NATS-downstream boundary")

    consumer_contract_text = (repo_root / REPO_CONSUMER_CONTRACT).read_text(encoding="utf-8")
    for marker in ("analytics_mart", "operational_replay", "notification and real-time gateway consumers"):
        if marker not in consumer_contract_text:
            errors.append(f"Consumer contract marker missing: {marker}")

    stream_spec_text = (repo_root / REPO_STREAM_SPEC).read_text(encoding="utf-8")
    for marker in ("PARTNER_EVENTS", "analytics_mart", "reserved_for_p2_7"):
        if marker not in stream_spec_text:
            errors.append(f"Stream spec marker missing: {marker}")

    return errors


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    errors = validate_repo(repo_root)
    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        return 1

    event_families = load_partner_event_families(repo_root)
    subjects = build_partner_subjects(event_families)
    print("P2.6 event-backbone validation passed")
    print(f"default_outbox_consumers={','.join(EXPECTED_OUTBOX_CONSUMERS)}")
    print(f"partner_event_families={len(event_families)}")
    print(f"partner_transport_subjects={len(subjects)}")
    print(f"reserved_service_consumers={','.join(RESERVED_SERVICE_CONSUMERS)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render or validate the P2.6 event-backbone scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_scaffold = subparsers.add_parser("render-scaffold", help="Render the repo-side P2.6 scaffold.")
    render_scaffold.add_argument("--repo-root", default=".")
    render_scaffold.add_argument("--output-dir", required=True)
    render_scaffold.set_defaults(func=command_render_scaffold)

    validate = subparsers.add_parser("validate", help="Validate repo-side P2.6 anchors.")
    validate.add_argument("--repo-root", default=".")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
