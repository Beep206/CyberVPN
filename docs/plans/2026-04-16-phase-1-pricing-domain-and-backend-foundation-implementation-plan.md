# Phase 1 Pricing Domain And Backend Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the legacy tier/remnawave-proxied pricing model with a backend-owned pricing catalog that supports direct `start/basic/plus/pro/max/test/development` plan codes, hidden/public visibility, add-ons, quote/commit flows, plan-level invite bundles, and mobile-user trial entitlements.

**Architecture:** Treat CyberVPN backend as the single source of truth for the commercial catalog. Stop using the current `backend/src/presentation/api/v1/plans/routes.py` as a thin Remnawave proxy for storefront data. Introduce a first-class plan catalog in PostgreSQL, a first-class add-on catalog, explicit quote and entitlement endpoints, and plan-level invite bundle rules. Keep Remnawave as a downstream network/config surface rather than the pricing source.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic v2, PostgreSQL, pytest, OpenAPI

---

## Delivery Order

1. Canonical plan domain and DB migration
2. Add-on catalog and entitlement model
3. Public/admin plan APIs
4. Quote/commit and current entitlement APIs
5. Trial migration to `mobile_users`
6. Invite bundle migration from config to plan catalog
7. OpenAPI export and backend regression coverage

---

## Task 1: Replace legacy plan tier with canonical plan catalog fields

**Files:**
- Modify: `backend/src/domain/enums/enums.py`
- Modify: `backend/src/domain/entities/subscription_plan.py`
- Modify: `backend/src/domain/repositories/subscription_plan_repository.py`
- Modify: `backend/src/infrastructure/database/models/subscription_plan_model.py`
- Modify: `backend/src/infrastructure/database/repositories/subscription_plan_repo.py`
- Create: `backend/alembic/versions/20260416_010000_pricing_catalog_standard.py`
- Test: `backend/tests/unit/test_domain_entities.py`
- Create: `backend/tests/unit/pricing/test_subscription_plan_catalog.py`

**Work:**
- Replace legacy `PlanTier` usage with a new canonical enum such as:
  - `PlanCode = start|basic|plus|pro|max|test|development`
  - `CatalogVisibility = public|hidden`
- Extend `SubscriptionPlan` to carry:
  - `plan_code`
  - `display_name`
  - `catalog_visibility`
  - `sale_channels`
  - `traffic_policy`
  - `connection_modes`
  - `server_pool`
  - `support_sla`
  - `dedicated_ip`
  - `invite_bundle`
  - `trial_eligible`
- Keep `duration_days`, `price_usd`, `price_rub`, `is_active`, `sort_order`.
- Make the Alembic migration transform the existing `subscription_plans` table instead of introducing a second parallel catalog.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/unit/test_domain_entities.py backend/tests/unit/pricing/test_subscription_plan_catalog.py -q`

**Acceptance Criteria:**
- no production code depends on `basic|pro|ultra|cyber` as the canonical catalog
- the DB model can represent public and hidden plans directly
- the entity can represent `Unlimited / fair use` without public hard data caps

---

## Task 2: Add first-class add-on catalog and subscription add-on persistence

**Files:**
- Create: `backend/src/domain/entities/plan_addon.py`
- Create: `backend/src/domain/repositories/plan_addon_repository.py`
- Create: `backend/src/infrastructure/database/models/plan_addon_model.py`
- Create: `backend/src/infrastructure/database/models/subscription_addon_model.py`
- Create: `backend/src/infrastructure/database/repositories/plan_addon_repo.py`
- Modify: `backend/src/infrastructure/database/models/payment_model.py`
- Modify: `backend/src/infrastructure/database/models/__init__.py`
- Modify: `backend/alembic/versions/20260416_010000_pricing_catalog_standard.py`
- Create: `backend/tests/unit/pricing/test_plan_addons.py`

**Work:**
- Introduce add-on catalog records for:
  - `extra_device`
  - `dedicated_ip`
- Persist catalog-level configuration:
  - `display_name`
  - `duration_mode`
  - `is_stackable`
  - `quantity_step`
  - `max_quantity_by_plan`
  - `delta_entitlements`
  - `requires_location`
- Add subscription-scoped purchased add-ons so entitlements survive beyond the quote request.
- Extend payment persistence so addon lines can be traced in payment metadata or a companion relation.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/unit/pricing/test_plan_addons.py -q`

**Acceptance Criteria:**
- add-ons are no longer implicit UI-only concepts
- purchased add-ons can be attached to an active subscription
- the payment layer can explain which add-ons were bought

---

## Task 3: Rebuild `/plans` from CyberVPN DB instead of Remnawave proxy

**Files:**
- Modify: `backend/src/presentation/api/v1/plans/routes.py`
- Modify: `backend/src/presentation/api/v1/plans/schemas.py`
- Modify: `backend/src/presentation/api/v1/router.py`
- Modify: `backend/src/presentation/dependencies/remnawave.py`
- Modify: `backend/src/presentation/dependencies/services.py`
- Create: `backend/tests/integration/api/test_plans_catalog_api.py`

**Work:**
- Stop using `RemnawaveClient` as the source for consumer pricing catalog responses.
- Make public `GET /plans` return:
  - active
  - public
  - allowed-for-channel plans only
- Introduce admin catalog endpoints that can return hidden plans and full structured fields.
- Remove the old `features: list[str]` response contract from the canonical path.
- Return structured catalog objects instead.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/integration/api/test_plans_catalog_api.py -q`

**Acceptance Criteria:**
- public API no longer leaks hidden plans by default
- admin API can see `start`, `test`, and `development`
- the consumer contract is emitted by CyberVPN backend, not by Remnawave proxy DTOs

---

## Task 4: Introduce quote, commit, entitlements, upgrade, and addon-purchase APIs

**Files:**
- Modify: `backend/src/presentation/api/v1/payments/routes.py`
- Modify: `backend/src/presentation/api/v1/payments/schemas.py`
- Modify: `backend/src/application/use_cases/payments/checkout.py`
- Modify: `backend/src/application/use_cases/payments/complete_zero_gateway.py`
- Create: `backend/src/application/services/entitlements_service.py`
- Create: `backend/src/application/use_cases/payments/quote_checkout.py`
- Create: `backend/src/application/use_cases/subscriptions/get_current_entitlements.py`
- Create: `backend/src/application/use_cases/subscriptions/purchase_addons.py`
- Create: `backend/src/application/use_cases/subscriptions/upgrade_subscription.py`
- Create: `backend/src/presentation/api/v1/subscriptions/entitlements_routes.py`
- Modify: `backend/src/presentation/api/v1/subscriptions/routes.py`
- Create: `backend/tests/unit/pricing/test_checkout_quote.py`
- Create: `backend/tests/integration/api/test_entitlements_api.py`

**Work:**
- Split the current `/payments/checkout` semantics into:
  - quote
  - commit/payment creation
- Make quote accept:
  - plan
  - add-ons
  - promo
  - wallet
- Make current entitlements return a stable snapshot for all channels.
- Add upgrade and add-on purchase flows that recalculate effective entitlements.
- Ensure `extra_device` and `dedicated_ip` affect the snapshot.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/unit/pricing/test_checkout_quote.py backend/tests/integration/api/test_entitlements_api.py -q`

**Acceptance Criteria:**
- quote and commit are separate concepts
- every consumer channel can request the same final entitlements snapshot
- add-ons change the final entitlement state rather than only the payment amount

---

## Task 5: Migrate trial from `admin_users` to `mobile_users`

**Files:**
- Modify: `backend/src/application/use_cases/trial/activate_trial.py`
- Modify: `backend/src/application/use_cases/trial/get_trial_status.py`
- Modify: `backend/src/presentation/api/v1/trial/routes.py`
- Modify: `backend/src/presentation/api/v1/trial/schemas.py`
- Modify: `backend/src/infrastructure/database/models/mobile_user_model.py`
- Modify: `backend/src/infrastructure/database/repositories/mobile_user_repo.py`
- Create: `backend/alembic/versions/20260416_020000_trial_to_mobile_users.py`
- Create: `backend/tests/integration/api/test_trial_mobile_users.py`

**Work:**
- Add canonical trial fields to `mobile_users`.
- Stop reading or mutating trial state on `admin_users`.
- Enforce the canonical trial contract:
  - `7 days`
  - `1 device`
  - `shared pool only`
  - `standard mode only`
  - `no add-ons`
  - `no premium/exclusive nodes`
- Make the trial API authenticate against mobile users only.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/integration/api/test_trial_mobile_users.py -q`

**Acceptance Criteria:**
- trial eligibility and activation belong to the customer domain
- trial behavior is no longer tied to the staff/admin user table
- trial responses are ready for frontend and Telegram bot copy sync

---

## Task 6: Move invite bundles from `system_config` rules into plan catalog

**Files:**
- Modify: `backend/src/application/use_cases/invites/generate_invites.py`
- Modify: `backend/src/application/services/config_service.py`
- Modify: `backend/src/presentation/api/v1/invites/routes.py`
- Modify: `backend/src/presentation/api/v1/plans/schemas.py`
- Modify: `backend/src/presentation/api/v1/plans/routes.py`
- Create: `backend/tests/unit/pricing/test_plan_level_invites.py`

**Work:**
- Make invite generation read `invite_bundle` from the purchased plan SKU rather than from `invite.plan_rules`.
- Keep manual admin invite creation as a separate support tool.
- Expose invite-bundle editing in plan admin schemas so the admin UI can control:
  - count
  - friend_days
  - expiry_days
- Mark global `invite.plan_rules` as deprecated and stop depending on it for purchase-generated invites.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/unit/pricing/test_plan_level_invites.py -q`

**Acceptance Criteria:**
- invite generation is a property of the plan catalog
- admin can manage invite rules at the plan level
- purchase-generated invites and manual support invites remain separate flows

---

## Task 7: Export canonical OpenAPI and add regression guardrails

**Files:**
- Modify: `backend/tests/integration/test_api.py`
- Create: `backend/tests/contract/test_pricing_openapi_contract.py`
- Modify: `backend/src/presentation/api/v1/router.py`
- Review: `frontend/src/lib/api/generated/types.ts`
- Review: `admin/src/lib/api/generated/types.ts`

**Work:**
- Ensure the new plan, addon, quote, entitlements, and trial routes are present in OpenAPI.
- Add contract tests that prevent regression back to legacy `features: list[str]` or Remnawave proxy shape on the canonical consumer endpoints.
- Regenerate downstream OpenAPI types only after the backend contract is stable.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/backend && python -m pytest backend/tests/contract/test_pricing_openapi_contract.py backend/tests/integration/test_api.py -q`

**Acceptance Criteria:**
- frontend/admin/bot can regenerate clients from the same canonical backend contract
- the new pricing standard has test coverage at the API-contract layer

---

## Phase 1 Done Means

- backend owns the pricing catalog
- hidden/public plans exist in the DB and API
- add-ons exist as first-class entities
- quote and entitlements APIs exist
- trial is fixed on `mobile_users`
- invite bundles are attached to plans
- downstream clients can begin consuming the new contract
