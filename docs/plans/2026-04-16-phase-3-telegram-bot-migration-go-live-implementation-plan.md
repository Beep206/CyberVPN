# Phase 3 Telegram Bot Migration And Go-Live Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the Telegram bot, rollout data, and go-live processes to the canonical pricing standard so the bot sells the same public catalog, understands hidden plans safely, honors the canonical trial policy, and ships with seeded plan/add-on data plus cross-channel QA coverage.

**Architecture:** Keep the backend contract as the source of truth and make the bot consume the same catalog, add-on, quote, and entitlement APIs as the web surfaces. The bot should default to the four public plans and only surface hidden plans through explicit channel rules. Go-live should seed the new plan catalog, preserve manual admin control for hidden plans, and validate parity across backend, frontend, admin, and bot.

**Tech Stack:** Python 3.13, aiogram 3, pydantic, httpx, Redis, FastAPI backend contract, pytest

---

## Delivery Order

1. Update bot DTOs and API client methods
2. Rebuild user purchase flow for plans, periods, add-ons, and quote
3. Harmonize trial and hidden-plan logic
4. Update bot admin plan views
5. Seed environments and run cross-channel QA
6. Prepare release and rollback checklist

---

## Task 1: Replace legacy bot subscription DTOs with the canonical pricing contract

**Files:**
- Modify: `services/telegram-bot/src/models/subscription.py`
- Modify: `services/telegram-bot/src/services/api_client.py`
- Modify: `services/telegram-bot/src/services/subscription_service.py`
- Test: `services/telegram-bot/tests/test_services.py`
- Create: `services/telegram-bot/tests/unit/test_pricing_contract.py`

**Work:**
- Replace DTO assumptions tied to:
  - legacy plan type enums
  - hard traffic caps as the primary display surface
  - ad-hoc duration parsing from mixed payloads
- Add support for:
  - `plan_code`
  - `display_name`
  - `catalog_visibility`
  - `period_days`
  - `connection_modes`
  - `server_pool`
  - `dedicated_ip`
  - `invite_bundle`
  - `effective_entitlements`
- Add client methods for:
  - `GET /plans`
  - `GET /addons/catalog`
  - `POST /checkout/quote`
  - `POST /checkout/commit`
  - `GET /subscriptions/current/entitlements`

**Validation:**
- `cd /home/beep/projects/VPNBussiness/services/telegram-bot && python -m pytest tests/test_services.py tests/unit/test_pricing_contract.py -q`

**Acceptance Criteria:**
- bot code no longer needs to reverse-engineer pricing from mixed legacy payload shapes
- bot DTOs can represent public and hidden catalog fields cleanly

---

## Task 2: Rebuild bot user purchase flow around plans, periods, add-ons, and quote

**Files:**
- Modify: `services/telegram-bot/src/handlers/subscription.py`
- Modify: `services/telegram-bot/src/handlers/payment.py`
- Modify: `services/telegram-bot/src/keyboards/subscription.py`
- Modify: `services/telegram-bot/src/keyboards/payment.py`
- Modify: `services/telegram-bot/src/states/subscription.py`
- Modify: `services/telegram-bot/src/services/payment_service.py`
- Test: `services/telegram-bot/tests/test_handlers_subscription.py`
- Test: `services/telegram-bot/tests/test_handlers_payment.py`

**Work:**
- Replace the current flow:
  - choose plan
  - choose duration
  - choose payment
with:
  - choose public plan
  - choose period
  - optionally choose add-ons
  - show quote summary
  - confirm checkout
  - continue to payment
- Make the summary show:
  - final price
  - devices
  - connection modes
  - server pool
  - dedicated IP count
  - support SLA
- Respect the canonical add-on rules:
  - `extra_device`
  - `dedicated_ip`

**Validation:**
- `cd /home/beep/projects/VPNBussiness/services/telegram-bot && python -m pytest tests/test_handlers_subscription.py tests/test_handlers_payment.py -q`

**Acceptance Criteria:**
- bot sells the same four public plans as the web surfaces
- the quote shown in the bot matches backend entitlements
- add-ons are visible and understandable in chat UX

---

## Task 3: Harmonize trial and hidden-plan behavior in the bot

**Files:**
- Modify: `services/telegram-bot/src/handlers/trial.py`
- Modify: `services/telegram-bot/src/handlers/start.py`
- Modify: `services/telegram-bot/src/handlers/menu.py`
- Modify: `services/telegram-bot/src/keyboards/subscription.py`
- Modify: `services/telegram-bot/src/locales/ru/messages.ftl`
- Modify: `services/telegram-bot/src/locales/ru/buttons.ftl`
- Modify: `services/telegram-bot/src/locales/en/messages.ftl`
- Modify: `services/telegram-bot/src/locales/en/buttons.ftl`

**Work:**
- Align the bot trial experience with the canonical standard:
  - `7 days`
  - `1 device`
  - `shared only`
  - no dedicated IP
  - no add-ons
- Make hidden plans unavailable in the default public bot flow.
- Permit hidden plans only when:
  - backend flags them for the Telegram channel
  - a bot deep-link or admin-triggered flow explicitly requests them
- Remove stale copy around `2 days / 2 GB`.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/services/telegram-bot && python -m pytest tests/test_handlers_subscription.py -q`

**Acceptance Criteria:**
- bot trial copy matches frontend and backend
- hidden plans are not accidentally exposed to all users

---

## Task 4: Update bot admin plan management for the new catalog

**Files:**
- Modify: `services/telegram-bot/src/handlers/admin/plans.py`
- Modify: `services/telegram-bot/src/keyboards/admin_plans.py`
- Modify: `services/telegram-bot/src/handlers/admin/access.py`
- Modify: `services/telegram-bot/src/locales/ru/admin.ftl`
- Modify: `services/telegram-bot/src/locales/en/admin.ftl`

**Work:**
- Update admin plan listing to show:
  - plan code
  - display name
  - hidden/public visibility
  - period
  - active state
- Stop relying on legacy fields like `bandwidth_limit` or free-form plan descriptions as the main admin view.
- Add basic visibility for invite bundle and dedicated IP policy.
- Keep the bot admin plan tools useful for support/ops, even if the web admin remains the richer editor.

**Validation:**
- `cd /home/beep/projects/VPNBussiness/services/telegram-bot && python -m pytest tests/test_handlers_admin.py -q`

**Acceptance Criteria:**
- bot admin screens understand the canonical plan catalog
- support staff can distinguish hidden plans from public catalog entries

---

## Task 5: Seed plans, add-ons, and hidden offers across environments

**Files:**
- Modify: `backend/alembic/versions/20260416_010000_pricing_catalog_standard.py`
- Create: `backend/scripts/seed_pricing_catalog.py`
- Create: `docs/plans/2026-04-16-pricing-seed-matrix.md`
- Review: `infra/`

**Work:**
- Seed all public plan families and periods:
  - `basic_*`
  - `plus_*`
  - `pro_*`
  - `max_*`
- Seed hidden plan families:
  - `start_*`
  - `test_*`
  - `development_*`
- Seed add-ons:
  - `extra_device`
  - `dedicated_ip`
- Seed starter invite bundles and hidden visibility defaults.
- Ensure `development` is not exposed to public channels.

**Validation:**
- run the seed in local/staging and verify all catalog rows exist
- verify `GET /plans` does not return hidden plans
- verify admin surfaces can see hidden plans

**Acceptance Criteria:**
- go-live environments can be recreated deterministically
- hidden/public separation is encoded in seed data, not only in UI assumptions

---

## Task 6: Run cross-channel QA and produce go-live checklist

**Files:**
- Create: `docs/plans/2026-04-16-pricing-go-live-checklist.md`
- Create: `docs/plans/2026-04-16-pricing-qa-matrix.md`
- Review: `frontend/src/app/[locale]/(marketing)/pricing/page.tsx`
- Review: `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- Review: `admin/src/app/[locale]/(dashboard)/commerce/plans/page.tsx`
- Review: `services/telegram-bot/src/handlers/subscription.py`

**Work:**
- Build a QA matrix covering:
  - public pricing page
  - miniapp checkout
  - admin plan editing
  - bot plan selection
  - bot trial activation
  - add-on purchase
  - hidden plan invisibility
  - Max bundled dedicated IP
- Produce a go-live checklist with:
  - seed verification
  - API smoke
  - OpenAPI regeneration
  - frontend/admin builds
  - bot smoke flow
  - rollback note

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run build -w frontend`
- `cd /home/beep/projects/VPNBussiness && npm run build -w admin`
- `cd /home/beep/projects/VPNBussiness/services/telegram-bot && python -m pytest -q`

**Acceptance Criteria:**
- every surface has a concrete verification path before release
- rollback steps exist before production rollout

---

## Phase 3 Done Means

- Telegram bot sells the canonical public catalog
- hidden plans are controlled safely
- trial is synchronized across all channels
- plan/add-on seeds exist for reproducible rollout
- release readiness is documented with QA and go-live checklists
