# Wave 1 File-Level Change Map

## Purpose

This file maps Wave 1 work to concrete repo files and clarifies whether each file is expected to be:

- `Modify`
- `Create`
- `Verify`

It is not a promise that every listed file must change, but it is the expected implementation surface.

## Backend — Shared Runtime Context

| File | Action | Why |
|---|---|---|
| `backend/src/presentation/dependencies/auth_realms.py` | Modify | Align runtime context with auth realm resolution |
| `backend/src/presentation/dependencies/partner_workspace.py` | Modify | Tenant-aware partner workspace resolution hooks |
| `backend/src/presentation/api/v1/auth/realm_context.py` | Modify | Shared runtime context handoff |
| `backend/src/domain/entities/auth_realm.py` | Verify | Ensure realm model can support Wave 1 assumptions |
| `backend/src/domain/entities/storefront.py` | Verify | Check compatibility with future partner-branded runtime |
| `backend/src/domain/entities/customer_commercial_binding.py` | Modify | Runtime commercial policy linkage |
| `backend/src/domain/entities/attribution_touchpoint.py` | Modify | Attribution fields for `start_param`, partner, surface |
| `backend/src/domain/entities/order_attribution_result.py` | Modify | Preserve attribution into order/payment flow |
| `backend/src/application/use_cases/auth_realms/resolve_realm.py` | Modify | Resolve realm into runtime context |
| `backend/src/application/use_cases/commerce_sessions/context_resolution.py` | Modify | Shared context resolution logic |
| `backend/src/application/use_cases/attribution/*` | Modify | Attribution resolution and recording alignment |

## Backend — Alembic / Migration Group 1

| File / Area | Action | Why |
|---|---|---|
| `backend/alembic/versions/` new revision | Create | Runtime context and attribution schema support |
| `backend/alembic/versions/20260417_phase1_auth_realms.py` | Verify | Existing realm foundation baseline |
| `backend/alembic/versions/20260417_phase1_storefront_core.py` | Verify | Existing storefront baseline |
| `backend/alembic/versions/20260417_phase1_partner_workspace.py` | Verify | Existing partner workspace baseline |
| `backend/alembic/versions/20260421_phase14_mobile_telegram_oidc_subject.py` | Verify | Existing Telegram identity-related migration context |

## Backend — Mini App Namespace

| File | Action | Why |
|---|---|---|
| `backend/src/presentation/api/v1/miniapp/` | Create | New Mini App API namespace |
| `backend/src/presentation/api/v1/auth/routes.py` | Modify | Reuse or adapt Mini App auth handoff |
| `backend/src/presentation/api/v1/telegram/routes.py` | Modify | Align Telegram bot and Mini App commercial contracts |
| `backend/src/presentation/api/v1/trial/routes.py` | Verify / Modify | Reuse for Mini App trial actions |
| `backend/src/presentation/api/v1/payments/routes.py` | Verify / Modify | Payment status and shared payment views |
| `backend/src/presentation/api/v1/quotes/routes.py` | Verify / Modify | Quote reuse or adaptation |
| `backend/src/presentation/api/v1/payment_attempts/routes.py` | Verify / Modify | Payment state visibility |
| `backend/src/application/use_cases/auth/telegram_miniapp.py` | Modify | Bootstrap/session integration |
| `backend/src/application/use_cases/trial/activate_trial.py` | Verify | Trial eligibility reuse |
| `backend/src/application/use_cases/payments/checkout.py` | Modify | Quote and checkout semantics for Mini App |
| `backend/src/application/use_cases/payments/commit_checkout.py` | Modify | Align with Stars and authoritative flow |
| `backend/src/application/use_cases/subscriptions/get_current_entitlements.py` | Verify | Bootstrap and post-payment access state |

## Backend — Payment and Fulfillment Correctness

| File | Action | Why |
|---|---|---|
| `backend/src/domain/entities/payment.py` | Modify | Explicit payment state support |
| `backend/src/domain/entities/payment_attempt.py` | Modify | Attempt tracking for invoice and reconciliation |
| `backend/src/domain/entities/quote_session.py` | Modify | Quote persistence and integrity |
| `backend/src/domain/entities/checkout_session.py` | Modify | Checkout session semantics |
| `backend/src/application/use_cases/payments/post_payment.py` | Modify | Authoritative success handling |
| `backend/src/application/use_cases/payments/payment_webhook.py` | Modify | Payment event reconciliation path |
| `backend/src/application/use_cases/orders/create_order_from_checkout.py` | Modify | Fulfillment bridge to order creation |
| `backend/src/application/services/entitlements_service.py` | Verify / Modify | Authoritative entitlement activation |
| `backend/src/presentation/api/v1/refunds/*` | Verify | Refund extension path |
| `backend/src/presentation/api/v1/payment_disputes/*` | Verify | Dispute and refund readiness |

## Frontend — Mini App Route and Auth Continuity

| File | Action | Why |
|---|---|---|
| `frontend/src/app/[locale]/miniapp/page.tsx` | Modify | Fix root redirect into Mini App namespace |
| `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx` | Modify | Keep auth success inside Mini App |
| `frontend/src/stores/auth-store.ts` | Modify | Align Mini App auth state and follow-up behavior |
| `frontend/src/features/auth/lib/pending-twofa-client.ts` | Modify | Preserve Mini App-safe return path |
| `frontend/src/i18n/navigation.ts` | Verify | Ensure router helpers remain compatible |
| `frontend/src/stores/__tests__/auth-store-miniapp.test.ts` | Modify | Route/auth continuity regression coverage |

## Frontend — Bootstrap and Runtime

| File | Action | Why |
|---|---|---|
| `frontend/src/app/[locale]/miniapp/layout.tsx` | Modify | Runtime providers and bootstrap boundary |
| `frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts` | Modify | Runtime lifecycle, invoice integration hooks |
| `frontend/src/app/[locale]/miniapp/home/page.tsx` | Modify | Bootstrap-driven home rendering |
| `frontend/src/app/[locale]/miniapp/plans/page.tsx` | Modify | Quote and invoice UX |
| `frontend/src/lib/api/miniapp.ts` | Create | Mini App-specific API client |
| `frontend/src/lib/api/auth.ts` | Verify / Modify | Mini App session interactions |
| `frontend/src/lib/api/payments.ts` | Verify / Modify | Payment status helpers |
| `frontend/src/lib/api/vpn.ts` | Verify | Config and entitlement reads |
| `frontend/src/lib/api/referral.ts` | Verify | Referral integration path |
| `frontend/src/lib/api/servers.ts` | Verify | Future server recommendation compatibility |

## Frontend — Tests

| File | Action | Why |
|---|---|---|
| `frontend/src/app/[locale]/miniapp/home/__tests__/page.test.tsx` | Modify | Bootstrap/home contract changes |
| `frontend/src/app/[locale]/miniapp/plans/__tests__/page.test.tsx` | Modify | Quote/invoice behavior |
| `frontend/src/lib/api/__tests__/payments.test.ts` | Modify | Payment contract changes |
| `frontend/src/stores/__tests__/auth-store.test.ts` | Verify / Modify | Auth state side-effects |

## Telegram Bot Service — Payment Path

| File | Action | Why |
|---|---|---|
| `services/telegram-bot/src/handlers/payment.py` | Modify | Replace placeholder pre-checkout rejection and unexpected success handling |
| `services/telegram-bot/src/services/payment_stars.py` | Modify | Align Stars invoice and status semantics |
| `services/telegram-bot/src/services/api_client.py` | Modify | Backend calls for quote, invoice, payment status, and fulfillment |
| `services/telegram-bot/src/services/payment_service.py` | Verify / Modify | Shared payment orchestration |
| `services/telegram-bot/src/handlers/subscription.py` | Verify / Modify | Subscription flow integration with Stars path |
| `services/telegram-bot/src/keyboards/payment.py` | Verify / Modify | Payment CTA and retry behavior |
| `services/telegram-bot/src/utils/deep_links.py` | Modify | Signed `startapp` and Mini App link generation |
| `services/telegram-bot/src/handlers/support.py` | Modify | Payment-support path |

## Partner Repo — Watch List

| File | Action | Why |
|---|---|---|
| `partner/src/features/storefront-shell/lib/runtime.ts` | Verify | Future compatibility with runtime context contract |
| `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts` | Verify | No Wave 1 implementation expected, but contract alignment matters |

## File-Level Notes from Current Baseline

### Verified Mini App Routing Gap

- `frontend/src/app/[locale]/miniapp/page.tsx` currently redirects outside the Mini App namespace.

### Verified Mini App Auth Gap

- `frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx` currently sends success paths outside the canonical Mini App route space.

### Verified Telegram Bot Payment Gap

- `services/telegram-bot/src/handlers/payment.py` currently rejects pre-checkout in the Stars flow and treats `successful_payment` as unexpected.

This makes the bot payment handler a mandatory Wave 1 file, not an optional follow-up.

## Suggested First PR Sequence

### PR 1

- runtime context contract
- migration group 1

### PR 2

- Mini App root routing
- Mini App auth and 2FA return continuity

### PR 3

- Mini App bootstrap API
- frontend bootstrap adoption

### PR 4

- quote and invoice foundation
- bot pre-checkout and successful payment handling

### PR 5

- tests, observability, and payment-to-entitlement hardening
