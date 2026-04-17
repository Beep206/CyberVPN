# Phase 2 Frontend And Admin Pricing Rollout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Roll out the canonical pricing standard to the public marketing site, Mini App purchase surface, and admin control plane so all human-facing catalog management uses `Basic / Plus / Pro / Max`, hidden plans, add-ons, entitlement snapshots, and plan-level invite bundles.

**Architecture:** Consume the backend catalog as the single contract and stop hardcoding or inferring plan meaning from old tier names or legacy feature arrays. The public marketing page shows only the four public plans. The Mini App uses quote-driven checkout and entitlement-driven rendering. The admin app becomes the control plane for public/hidden plans, add-ons, visibility, invite bundles, connection modes, server pools, and dedicated-IP policy.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, TanStack Query v5, next-intl, OpenAPI-generated types, Tailwind CSS 4

---

## Delivery Order

1. Regenerate typed clients for frontend and admin
2. Rebuild the public pricing page
3. Rebuild the Mini App purchase flow
4. Rebuild admin plan management
5. Add admin add-on and invite-bundle controls
6. Sync translations, tests, and build validation

---

## Task 1: Regenerate API clients and add canonical pricing consumers

**Files:**
- Modify: `frontend/src/lib/api/generated/types.ts`
- Modify: `frontend/src/lib/api/plans.ts`
- Modify: `frontend/src/lib/api/payments.ts`
- Create: `frontend/src/lib/api/addons.ts`
- Create: `frontend/src/lib/api/entitlements.ts`
- Modify: `frontend/src/lib/api/index.ts`
- Modify: `admin/src/lib/api/generated/types.ts`
- Modify: `admin/src/lib/api/plans.ts`
- Modify: `admin/src/lib/api/payments.ts`
- Create: `admin/src/lib/api/addons.ts`
- Create: `admin/src/lib/api/entitlements.ts`
- Modify: `admin/src/lib/api/index.ts`
- Test: `frontend/src/lib/api/__tests__/payments.test.ts`
- Test: `admin/src/lib/api/__tests__/commerce-admin.test.ts`

**Work:**
- Regenerate frontend and admin OpenAPI types from the Phase 1 backend contract.
- Replace any client assumptions tied to:
  - `basic/pro/elite`
  - `features: string[]`
  - raw hard caps as the public merchandising surface
- Add clients for:
  - plan catalog
  - addon catalog
  - quote
  - current entitlements
  - upgrade
  - addon purchase

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run lint -w frontend`
- `cd /home/beep/projects/VPNBussiness && npm run lint -w admin`

**Acceptance Criteria:**
- frontend and admin speak only the canonical backend pricing contract
- no new UI work depends on legacy tier naming

---

## Task 2: Replace the public pricing page with the new 4-plan merchandising model

**Files:**
- Modify: `frontend/src/app/[locale]/(marketing)/pricing/page.tsx`
- Modify: `frontend/src/widgets/pricing/pricing-dashboard.tsx`
- Modify: `frontend/src/widgets/pricing/tier-cards.tsx`
- Modify: `frontend/src/widgets/pricing/feature-matrix.tsx`
- Modify: `frontend/src/widgets/pricing/faq-accordion.tsx`
- Modify: `frontend/messages/en-EN/Pricing.json`
- Modify: `frontend/messages/ru-RU/Pricing.json`

**Work:**
- Replace the current `basic / pro / elite` pricing story with:
  - `Basic`
  - `Plus`
  - `Pro`
  - `Max`
- Make the marketing page talk in product language:
  - `Unlimited / fair use`
  - `Standard`
  - `Stealth`
  - `Manual / Advanced`
  - `Dedicated IP`
- Do not expose raw protocol names on plan cards.
- Make `Plus` the default “Most Popular”.
- Make `Max` the flagship plan with `1 included dedicated IP`.
- Add a compact add-ons section for:
  - `+1 device`
  - `Dedicated IP`

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run build -w frontend`

**Acceptance Criteria:**
- the public storefront exposes only the four public plans
- the messaging aligns with the canonical pricing document
- hard data-cap marketing is gone from public plan cards

---

## Task 3: Rebuild Mini App plans around quote and effective entitlements

**Files:**
- Modify: `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- Modify: `frontend/src/lib/api/plans.ts`
- Modify: `frontend/src/lib/api/payments.ts`
- Create: `frontend/src/lib/api/addons.ts`
- Create: `frontend/src/lib/api/entitlements.ts`
- Modify: `frontend/messages/en-EN/MiniApp.json`
- Modify: `frontend/messages/ru-RU/MiniApp.json`
- Test: `frontend/src/app/[locale]/miniapp/plans/__tests__/page.test.tsx`
- Test: `frontend/src/app/[locale]/miniapp/plans/components/__tests__/PlansClient.test.tsx`

**Work:**
- Stop treating the Mini App page as “select plan and directly create invoice”.
- Add quote-driven flow:
  - choose plan
  - choose period
  - optionally choose add-ons
  - show final entitlements and price
  - commit checkout
- Show only public plans by default.
- Make hidden plans inaccessible unless the backend intentionally exposes them to the channel.
- Use the entitlement snapshot to render:
  - device count
  - connection modes
  - server pool
  - dedicated IP count
  - support SLA

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run lint -w frontend`
- `cd /home/beep/projects/VPNBussiness && npm run build -w frontend`

**Acceptance Criteria:**
- Mini App uses quote and entitlements instead of raw plan cards only
- `extra_device` and `dedicated_ip` are purchasable in the Mini App
- trial copy matches the canonical `7d / 1 device / shared only` policy

---

## Task 4: Rebuild admin plan editor around the new catalog standard

**Files:**
- Modify: `admin/src/features/commerce/components/plan-editor-modal.tsx`
- Modify: `admin/src/features/commerce/components/plans-console.tsx`
- Modify: `admin/src/app/[locale]/(dashboard)/commerce/plans/page.tsx`
- Modify: `admin/src/lib/api/plans.ts`
- Modify: `admin/messages/en-EN/commerce.json`
- Modify: `admin/messages/ru-RU/commerce.json`
- Test: `admin/src/lib/api/__tests__/commerce-admin.test.ts`

**Work:**
- Replace the current plan editor fields:
  - `name`
  - `price`
  - `duration_days`
  - `data_limit_gb`
  - `max_devices`
  - `features`
with a structured editor for:
  - `plan_code`
  - `display_name`
  - `catalog_visibility`
  - `sale_channels`
  - `duration_days`
  - `devices_included`
  - `traffic_policy`
  - `connection_modes`
  - `server_pool`
  - `support_sla`
  - `dedicated_ip.included`
  - `dedicated_ip.eligible`
  - `invite_bundle`
  - `trial_eligible`
- Make hidden plans visible and editable in admin.

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run lint -w admin`
- `cd /home/beep/projects/VPNBussiness && npm run build -w admin`

**Acceptance Criteria:**
- admin can fully author `start/basic/plus/pro/max/test/development`
- hidden/public visibility is a first-class admin concept
- invite bundle is editable on the plan itself

---

## Task 5: Add admin controls for add-ons and invite policy

**Files:**
- Create: `admin/src/features/commerce/components/addons-console.tsx`
- Modify: `admin/src/features/commerce/components/commerce-overview.tsx`
- Modify: `admin/src/features/commerce/config/navigation.ts`
- Modify: `admin/src/app/[locale]/(dashboard)/commerce/page.tsx`
- Create: `admin/src/app/[locale]/(dashboard)/commerce/addons/page.tsx`
- Modify: `admin/src/features/growth/components/invite-codes-console.tsx`
- Modify: `admin/src/features/growth/components/growth-overview.tsx`
- Modify: `admin/src/features/growth/config/navigation.ts`
- Modify: `admin/src/lib/api/invites.ts`
- Create: `admin/src/lib/api/addons.ts`
- Modify: `admin/messages/en-EN/growth.json`
- Modify: `admin/messages/ru-RU/growth.json`

**Work:**
- Add an add-on catalog management screen for:
  - `extra_device`
  - `dedicated_ip`
- Surface max-quantity rules by plan in admin.
- Keep manual invite generation console, but clearly separate it from plan-based invite policy.
- Add read/write controls for plan-level invite bundle data so growth rules are not hidden in raw JSON only.

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run lint -w admin`

**Acceptance Criteria:**
- admin can manage add-ons without editing raw DB state
- invite policy is visible at the plan level, not only in growth notes or system config

---

## Task 6: Synchronize copy, FAQ, and cross-surface states

**Files:**
- Modify: `frontend/messages/en-EN/Pricing.json`
- Modify: `frontend/messages/ru-RU/Pricing.json`
- Modify: `frontend/messages/en-EN/MiniApp.json`
- Modify: `frontend/messages/ru-RU/MiniApp.json`
- Modify: `admin/messages/en-EN/commerce.json`
- Modify: `admin/messages/ru-RU/commerce.json`
- Modify: `admin/messages/en-EN/growth.json`
- Modify: `admin/messages/ru-RU/growth.json`

**Work:**
- Remove stale consumer wording around:
  - hard traffic caps
  - old plan names
  - old trial semantics
  - old plan feature arrays
- Ensure the public site, Mini App, and admin use the same canonical vocabulary:
  - `Basic / Plus / Pro / Max`
  - `Start / Test / Development`
  - `Unlimited / fair use`
  - `Standard / Stealth / Manual / Dedicated IP`

**Validation:**
- `cd /home/beep/projects/VPNBussiness && npm run build -w frontend`
- `cd /home/beep/projects/VPNBussiness && npm run build -w admin`

**Acceptance Criteria:**
- there is no conflicting pricing terminology between frontend and admin
- hidden plan names exist only where they are operationally relevant

---

## Phase 2 Done Means

- public website sells the new 4-plan ladder
- Mini App checks out via quote and entitlement snapshot
- admin manages the new plan catalog directly
- add-ons and invite bundles are operable from admin
- UI copy is aligned with the backend contract
