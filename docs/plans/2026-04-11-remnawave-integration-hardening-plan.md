# Remnawave 2.7.4 Integration Hardening Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove Remnawave version drift, harden the backend contract against Remnawave `2.7.4`, align webhook handling with the current upstream contract, selectively adopt useful `2.7.x` surfaces, and clean internal docs without coupling `Helix` to Remnawave `Node Plugins`.

**Architecture:** Keep `Remnawave` as the source of truth for nodes, subscriptions, and baseline VPN orchestration. Keep `Helix` as a separate control-plane/runtime layer. Improve the integration only at the adapter boundary: version alignment, typed response validation, webhook contract compliance, shared schemas/adapters, and selective observability coverage.

**Tech Stack:** Ansible, Docker Compose, FastAPI, Pydantic v2, httpx, pytest, Next.js admin, Remnawave `2.7.4`.

---

## Scope Decisions

- Do not embed `Helix` into Remnawave `Node Plugins`.
- Treat Remnawave `Node Plugins` as optional node-side helpers only.
- Target upstream contract: `Remnawave 2.7.4`.
- Staging rollout is the mandatory gate before any production rollout.
- Contract hardening must not change end-user subscription behavior.
- Documentation cleanup happens only after runtime and test alignment.

## Current Baseline

- Control-plane Remnawave image is already pinned to `remnawave/backend:2.7.4` in [infra/docker-compose.yml](/home/beep/projects/VPNBussiness/infra/docker-compose.yml:19).
- Edge Remnawave node image is still pinned to `remnawave/node:2.6.1` in:
  - [infra/ansible/inventories/staging/group_vars/remnawave_edge_staging/main.yml](/home/beep/projects/VPNBussiness/infra/ansible/inventories/staging/group_vars/remnawave_edge_staging/main.yml:2)
  - [infra/ansible/inventories/production/group_vars/remnawave_edge_production/main.yml](/home/beep/projects/VPNBussiness/infra/ansible/inventories/production/group_vars/remnawave_edge_production/main.yml:2)
  - [infra/ansible/roles/remnawave_edge/defaults/main.yml](/home/beep/projects/VPNBussiness/infra/ansible/roles/remnawave_edge/defaults/main.yml:18)
- Backend already has a validated Remnawave client in [backend/src/infrastructure/remnawave/client.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/client.py:24), but several route and gateway paths still use legacy raw calls.
- Webhook handling still expects `X-Webhook-Signature` and reuses the API token as the validation secret in [backend/src/presentation/api/v1/webhooks/routes.py](/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/webhooks/routes.py:17).
- Response schemas already exist in [backend/src/presentation/schemas/remnawave_responses.py](/home/beep/projects/VPNBussiness/backend/src/presentation/schemas/remnawave_responses.py:1).
- Admin already models `node plugins` and `helix` as separate infrastructure surfaces in [admin/src/lib/api/infrastructure.ts](/home/beep/projects/VPNBussiness/admin/src/lib/api/infrastructure.ts:29).

## Phase 1: Remove Version Drift And Revalidate Edge Compatibility

**Goal:** Make the deployed Remnawave control-plane and edge nodes version-compatible on `2.7.4`.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/infra/ansible/inventories/staging/group_vars/remnawave_edge_staging/main.yml`
- Modify: `/home/beep/projects/VPNBussiness/infra/ansible/inventories/production/group_vars/remnawave_edge_production/main.yml`
- Modify: `/home/beep/projects/VPNBussiness/infra/ansible/roles/remnawave_edge/defaults/main.yml`
- Review: `/home/beep/projects/VPNBussiness/infra/ansible/playbooks/remnawave-rollout.yml`
- Review: `/home/beep/projects/VPNBussiness/infra/ansible/playbooks/remnawave-verify.yml`
- Review: `/home/beep/projects/VPNBussiness/docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md`
- Review: `/home/beep/projects/VPNBussiness/docs/runbooks/PRODUCTION_EDGE_CANARY_RUNBOOK.md`

**Work**
- Change all Remnawave edge image defaults and inventory overrides from `remnawave/node:2.6.1` to `remnawave/node:2.7.4`.
- Verify there are no hidden overrides in vault files, CI variables, or Terraform-generated inventory.
- Run staging rollout first.
- Extend staging smoke verification beyond the current ansible checks so it covers:
  - node registration in Remnawave panel/API
  - backend `monitoring/health`
  - backend `monitoring/stats`
  - backend `node-plugins` routes
  - backend `subscriptions/active`
  - backend `subscriptions/cancel`
- Keep rollback path unchanged and documented.

**Validation**
- `cd infra && make ansible-remnawave-rollout-staging`
- `cd infra && make ansible-remnawave-verify-staging`
- `cd backend && pytest backend/tests/unit/infrastructure/test_remnawave_client.py -v`
- `cd backend && pytest backend/tests/integration/api/v1/subscriptions/test_subscription_flows.py -v`
- Manual staging smoke:
  - `GET /api/v1/monitoring/health`
  - `GET /api/v1/monitoring/stats`
  - `GET /api/v1/node-plugins/`
  - `GET /api/v1/subscriptions/active`
  - `POST /api/v1/subscriptions/cancel`

**Exit criteria**
- Staging edge nodes connect and remain healthy on `2.7.4`.
- `node-plugins` endpoints still respond correctly after the node upgrade.
- Subscription flows still work through the backend facade.
- Production rollout is blocked until staging evidence is recorded.

**Rollback**
- `cd infra && make ansible-remnawave-rollback-staging`

## Phase 2: Finish Contract Hardening For Backend Remnawave Calls

**Goal:** Remove legacy raw Remnawave calls from application-critical backend paths and standardize on validated schemas.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/subscriptions/routes.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/settings/routes.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/snippets/routes.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/squads/routes.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/billing/routes.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/user_gateway.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/server_gateway.py`
- Modify if schemas are missing: `/home/beep/projects/VPNBussiness/backend/src/presentation/schemas/remnawave_responses.py`
- Test: `/home/beep/projects/VPNBussiness/backend/tests/unit/infrastructure/test_remnawave_client.py`
- Test: `/home/beep/projects/VPNBussiness/backend/tests/unit/infrastructure/test_remnawave_user_gateway.py`
- Test: `/home/beep/projects/VPNBussiness/backend/tests/unit/test_remnawave_responses.py`
- Test: `/home/beep/projects/VPNBussiness/backend/tests/integration/api/v1/subscriptions/test_subscription_flows.py`

**Work**
- Inventory every remaining `client.get/post/put/delete/patch` usage against Remnawave.
- Categorize each call:
  - existing schema available
  - schema missing but endpoint important
  - legacy endpoint that should be retired
- Replace raw calls with `*_validated()` methods where schemas already exist.
- Add missing schemas only for endpoints that are still in active use.
- Keep raw passthrough only for endpoints where upstream payload is intentionally opaque.
- Add a short engineering rule to forbid new raw Remnawave calls without an explicit justification comment.

**Validation**
- `cd backend && pytest backend/tests/unit/test_remnawave_responses.py -v`
- `cd backend && pytest backend/tests/unit/infrastructure/test_remnawave_client.py -v`
- `cd backend && pytest backend/tests/unit/infrastructure/test_remnawave_user_gateway.py -v`
- `cd backend && pytest backend/tests/integration/api/v1/subscriptions/test_subscription_flows.py -v`
- `cd backend && pytest backend/tests/integration/api/v1 -k remnawave -v`

**Exit criteria**
- All critical subscription, settings, snippet, squad, billing, and gateway paths use validated responses.
- Any intentionally unvalidated call is documented inline with a reason.
- Schema coverage becomes a visible review standard.

**Notes**
- Prioritize subscription and user flows first.
- Do not widen schema scope just because upstream exposes more endpoints.

## Phase 3: Align Webhook Integration With Remnawave 2.7.x Contract

**Goal:** Bring webhook verification, headers, and secrets in line with the current upstream contract without breaking existing event processing.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/webhooks/routes.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/webhook_validator.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/application/use_cases/webhooks/remnawave_webhook.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/config/settings.py`
- Review: `/home/beep/projects/VPNBussiness/SDK/python-sdk-production/remnawave/controllers/webhooks.py`
- Create or modify: `/home/beep/projects/VPNBussiness/backend/tests/unit/infrastructure/test_remnawave_webhook_validator.py`
- Create or modify: `/home/beep/projects/VPNBussiness/backend/tests/integration/api/v1/webhooks/test_remnawave_webhook.py`
- Review: `/home/beep/projects/VPNBussiness/infra/.env.example`
- Review: `/home/beep/projects/VPNBussiness/docs/secret-rotation.md`

**Work**
- Introduce a dedicated `REMNAWAVE_WEBHOOK_SECRET` setting instead of reusing the API token.
- Update header parsing to support current Remnawave headers:
  - `X-Remnawave-Signature`
  - `X-Remnawave-Timestamp`
- Decide compatibility mode explicitly:
  - short transitional support for `X-Webhook-Signature`, or
  - hard cut to the new headers
- Add replay-window validation if Remnawave timestamp semantics support it operationally.
- Log rejected webhooks with enough context for debugging but without leaking secrets or full payloads.
- Update runbooks and example env files.

**Validation**
- `cd backend && pytest backend/tests/unit/infrastructure/test_remnawave_webhook_validator.py -v`
- `cd backend && pytest backend/tests/integration/api/v1/webhooks/test_remnawave_webhook.py -v`
- Replay fixture coverage:
  - valid signature + valid timestamp
  - missing signature
  - missing timestamp
  - invalid signature
  - stale timestamp if replay window is enabled

**Exit criteria**
- Backend accepts the documented Remnawave webhook contract for `2.7.x`.
- Webhook secret is independent from the API token.
- Rotation steps are documented and testable.

## Phase 4: Consolidate To One Internal Remnawave Contract Layer

**Goal:** Reduce long-term maintenance cost by making one internal contract layer the only supported integration path.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/client.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/adapters.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/schemas/remnawave_responses.py`
- Review: `/home/beep/projects/VPNBussiness/backend/src/presentation/dependencies/remnawave.py`
- Review: `/home/beep/projects/VPNBussiness/backend/src/infrastructure/remnawave/subscription_client.py`
- Review: `/home/beep/projects/VPNBussiness/SDK/python-sdk-production/remnawave/models/**`
- Review: `/home/beep/projects/VPNBussiness/SDK/python-sdk-production/tests/test_remnawave27_models.py`
- Create: `/home/beep/projects/VPNBussiness/backend/tests/contracts/test_remnawave_274_contract.py`
- Possibly create: `/home/beep/projects/VPNBussiness/backend/tests/contracts/fixtures/remnawave_274/*.json`

**Work**
- Decide the internal source of truth for Remnawave payload shapes:
  - backend-local schemas in `src/presentation/schemas/remnawave_responses.py`, or
  - a shared internal package extracted from current backend schemas and SDK fixtures
- Do not let route handlers directly choose between local schema and vendored SDK models.
- Standardize:
  - request/response logging
  - retries/timeouts
  - validation failure behavior
  - envelope normalization
  - error translation into backend HTTP responses
- Add contract tests against Remnawave `2.7.4` payload fixtures for the endpoints that matter to your product:
  - health
  - system stats
  - system recap
  - nodes
  - users
  - subscriptions
  - node plugins
  - webhooks payload parsing

**Validation**
- `cd backend && pytest backend/tests/contracts/test_remnawave_274_contract.py -v`
- `cd backend && pytest backend/tests/unit -k remnawave -v`
- `cd backend && pytest backend/tests/integration/api/v1/subscriptions/test_subscription_flows.py -v`

**Exit criteria**
- Engineers have one approved way to integrate with Remnawave.
- Contract regressions against `2.7.4` are caught by tests before deployment.
- Vendored SDK remains optional reference material, not an alternate runtime contract path.

## Phase 5: Selectively Adopt Useful Remnawave 2.7.x Surfaces

**Goal:** Add only the `2.7.x` capabilities that improve operations or UX without widening maintenance scope.

**Candidate surfaces**
- `system/metadata`
- `metadata/user/{uuid}`
- `metadata/node/{uuid}`
- `system/stats/recap`
- node health and governance surfaces already relevant to the backend/admin

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/backend/src/application/use_cases/monitoring/server_bandwidth.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/application/use_cases/monitoring/system_health.py`
- Modify: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/monitoring/routes.py`
- Modify if new facade is added: `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/settings/routes.py`
- Modify if new admin surface is added: `/home/beep/projects/VPNBussiness/admin/src/lib/api/infrastructure.ts`
- Modify if new admin widgets are justified: `/home/beep/projects/VPNBussiness/admin/src/features/infrastructure/components/infrastructure-overview.tsx`
- Modify if new admin widgets are justified: `/home/beep/projects/VPNBussiness/admin/src/features/infrastructure/components/servers-console.tsx`

**Work**
- Rank candidate `2.7.x` endpoints by concrete value:
  - operational visibility
  - admin diagnosis speed
  - end-user impact
  - cost of schema/testing support
- Implement only the top items.
- Preferred first additions:
  - move monitoring stats to typed `stats + recap`
  - expose safe build/version metadata for admin diagnostics
  - expose node-level metadata only if it directly improves support workflows
- Explicitly defer features that are interesting but not valuable enough right now.

**Validation**
- `cd backend && pytest backend/tests/unit -k monitoring -v`
- `cd backend && pytest backend/tests/integration/api/v1 -k monitoring -v`
- `cd admin && npm run lint`
- `cd admin && npm run build`

**Exit criteria**
- New `2.7.x` coverage clearly improves operations or support.
- No “API completeness” work is merged without a product or ops use case.
- Monitoring data comes from typed payloads, not ad hoc dictionary parsing.

## Phase 6: Clean Internal Documentation And Add Upgrade Guardrails

**Goal:** Make the repository self-consistent so the next Remnawave upgrade is easier and safer.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/docs/PROJECT_OVERVIEW.md`
- Modify: `/home/beep/projects/VPNBussiness/docs/menu-frontend/USER_MENU_STRUCTURE.md`
- Modify: `/home/beep/projects/VPNBussiness/docs/menu-frontend/user_menu_structure.md`
- Modify if still relevant: `/home/beep/projects/VPNBussiness/docs/plans/legacy/vpn-technical-blueprint-ru.md`
- Modify: `/home/beep/projects/VPNBussiness/SDK/python-sdk-production/README.md`
- Possibly create: `/home/beep/projects/VPNBussiness/docs/runbooks/REMNAWAVE_UPGRADE_PLAYBOOK.md`

**Work**
- Replace stale references to `Remnawave SDK 2.4.4` with the current supported contract version.
- Document the integration boundary clearly:
  - Remnawave owns VPN source-of-truth and node/plugin primitives
  - Helix owns rollout/runtime policy and remains separate
- Add one short upgrade playbook:
  - version bump checklist
  - staging rollout
  - contract test suite
  - webhook verification
  - admin/manual smoke list
- Record the decision not to migrate Helix into Remnawave `Node Plugins`.

**Validation**
- Manual grep sweep:
  - `rg -n "2\\.4\\.4|2\\.6\\.1|Remnawave SDK" docs SDK infra backend admin`
- Confirm all docs refer to the same target contract version and rollout process.

**Exit criteria**
- No high-signal docs point to stale Remnawave versions.
- Upgrade path is documented and reusable.
- Architectural boundary between `Helix` and Remnawave is explicit.

## Suggested Delivery Order

1. Phase 1: version drift removal
2. Phase 3: webhook contract alignment
3. Phase 2: contract hardening on active backend flows
4. Phase 4: single internal contract layer
5. Phase 5: selective `2.7.x` adoption
6. Phase 6: docs cleanup and guardrails

## Why This Order

- Version compatibility is the highest operational risk and should be fixed first.
- Webhooks are contract-sensitive and easy to isolate.
- Raw-call hardening reduces regression risk before widening API coverage.
- Contract unification should happen after the most urgent runtime mismatches are corrected.
- New `2.7.x` endpoints should be adopted only after the baseline is stable.
- Docs cleanup is final so it reflects the real implementation, not intent.

## Risks To Watch

- Remnawave node `2.7.4` may require node host capability or nftables assumptions that differ between staging and production.
- Existing mocked tests may still patch raw client methods and need to be rewritten once validated calls become the standard path.
- Webhook provider configuration may still send old headers during the transition window.
- Admin UI can accidentally expose low-value metadata that adds support burden without operational benefit.
- Contract tests can become noisy if they cover too many endpoints; keep them focused on the product-critical paths.

## Definition Of Done

- Remnawave control-plane and edge nodes run on a compatible `2.7.4` baseline.
- Product-critical backend Remnawave calls use typed validation.
- Webhooks follow the current Remnawave `2.7.x` header and secret contract.
- There is one documented internal contract path for Remnawave integrations.
- Only high-value `2.7.x` surfaces are adopted.
- Internal docs and upgrade runbooks match the deployed reality.
