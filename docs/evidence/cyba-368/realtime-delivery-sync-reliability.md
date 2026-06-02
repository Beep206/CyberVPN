# CYBA-368 realtime delivery and sync reliability evidence

## Executive summary

- Added a shared messaging realtime sync contract helper so WebSocket and SSE recovery messages use the same opaque `sync_cursor` format.
- Strengthened SSE backpressure behavior: when a subscriber queue overflows, the backend emits `sync_required` with `reason=subscriber_backpressure`, `sync_cursor`, and `recovery=rest_sync`.
- Refreshed Redis advisory presence for active SSE streams on heartbeat/event chunks so long-lived streams do not expire while healthy.
- Added regression coverage for SSE overflow recovery metadata and SSE presence TTL refresh.

## Decisions needed from Board

- None for this change. Scope stays inside approved CYBA-360/CYBA-368 non-production implementation boundaries.

## Proposed next tasks

- Quill QA can use this as input for CYBA-374 synthetic multi-user isolation and reconnect/sync evidence.
- SecurityEngineer can use this as input for CYBA-373 private channel authorization and no cross-customer leakage review.

## Risks

- Browser delivery remains best-effort by design; authoritative recovery is REST sync after connect, reconnect, `sync_required`, or local cursor gaps.
- Existing workspace contains many unrelated dirty/untracked files from parallel work. This change only targeted realtime/messaging files listed below.

## Approval requests

- None.

## Verification plan

- `REMNAWAVE_TOKEN=local-remnawave-token CRYPTOBOT_TOKEN=local-cryptobot-token JWT_SECRET=0123456789abcdef0123456789abcdef uv run --extra dev pytest --no-cov tests/unit/infrastructure/test_messaging_realtime_gateway.py tests/unit/infrastructure/test_nats_messaging_runtime.py tests/integration/test_messaging_api.py -q`
  - Result: `20 passed in 25.15s`
- `uv run --extra dev ruff check src/infrastructure/messaging/realtime_contract.py src/infrastructure/messaging/sse_manager.py src/presentation/api/v1/messaging/routes.py tests/unit/infrastructure/test_messaging_realtime_gateway.py`
  - Result: `All checks passed!`
- Coverage note: the same narrow pytest set without `--no-cov` passed all selected tests but failed the repo-wide coverage gate because the selected slice reports total coverage below the global threshold.

## What was not done

- No production deploy.
- No production secrets or customer/payment data access.
- No production NATS/Remnawave/VPN configuration changes.
- No changes to payments, authentication policy, admin permissions, VPN provisioning, or Remnawave runtime.

## Context7 docs checked

- Context7 MCP: unavailable, monthly quota exceeded.
- `ctx7` CLI fallback: unavailable, monthly quota exceeded.
- Fallback documentation checked: official FastAPI WebSocket and StreamingResponse docs; existing repo NATS/JetStream realtime specs and tests.

## Files touched

- `backend/src/infrastructure/messaging/realtime_contract.py`
- `backend/src/infrastructure/messaging/sse_manager.py`
- `backend/src/presentation/api/v1/messaging/routes.py`
- `backend/tests/unit/infrastructure/test_messaging_realtime_gateway.py`
- `docs/realtime/messaging-gateway.md`
- `docs/evidence/cyba-368/realtime-delivery-sync-reliability.md`
