# Stage 3 Partner Portal Disabled-State Boundary

**Stage:** `S3-STAGE-05`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-04: Outbox Dispatcher And Consumer Proof`

---

## 1. Назначение

Этот этап нужен, чтобы partner portal и partner/reseller backend-код можно было держать в монорепозитории и деплоить вместе с CyberVPN, но не открыть публичный self-serve доступ раньше времени.

S3-STAGE-05 не включает полноценный партнёрский запуск. Он фиксирует безопасное состояние:

```text
partner code exists in runtime
partner public/self-serve surfaces are hidden or blocked
admin preview remains behind existing admin auth/RBAC/host boundary
partner payouts/webhooks/storefronts remain disabled
```

---

## 2. Decision

Production default state remains:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_EVENT_BACKBONE_ENABLED=false
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=false
```

`PARTNER_EVENT_BACKBONE_ENABLED` must remain `false` even after S3-STAGE-04 local proof. Real production partner fan-out still requires later staging/production evidence.

---

## 3. Backend Boundary

Implemented middleware:

```text
backend/src/presentation/middleware/partner_disabled_boundary.py
```

When `PARTNER_PORTAL_ENABLED=false`, public/self-serve partner API prefixes return `404` with a machine-readable disabled payload:

```json
{
  "detail": {
    "code": "partner_portal_disabled",
    "message": "Partner portal is not enabled for this release.",
    "stage": "S3-STAGE-05"
  }
}
```

The response includes:

```text
Cache-Control: no-store
X-CyberVPN-Partner-Boundary: partner_portal_disabled
```

### 3.1 Blocked Public Partner Prefixes

| Prefix | Reason |
|---|---|
| `/api/v1/partner/` | Legacy/mobile-user partner dashboard, bind and code endpoints must not self-launch. |
| `/api/v1/partner-workspaces` | Partner workspace access remains gated. |
| `/api/v1/partner-session` | Partner session bootstrap remains gated. |
| `/api/v1/partner-notifications` | Partner notification surface remains gated. |
| `/api/v1/partner-bots` | Partner-managed bot/device expansion remains gated. |
| `/api/v1/partner-statements` | Partner finance/reporting remains gated. |
| `/api/v1/reporting/partner-workspaces` | Partner reporting API remains gated. |

### 3.2 Partner Application Boundary

S3-STAGE-06 adds a separate onboarding flag:

```text
PARTNER_APPLICATIONS_ENABLED=false
```

`/api/v1/partner-application-drafts` requires both:

```text
PARTNER_PORTAL_ENABLED=true
PARTNER_APPLICATIONS_ENABLED=true
```

If the portal flag is disabled, the route stays hidden as `partner_portal_disabled`.
If the portal is enabled but onboarding is still disabled, it returns:

```text
partner_applications_disabled
```

This lets ops test admin preview and partner portal shell without accidentally opening self-serve partner applications.

### 3.3 Payout Boundary

When `PARTNER_PAYOUTS_ENABLED=false`, payout API prefixes return `404` with:

```text
partner_payouts_disabled
```

Blocked prefixes:

```text
/api/v1/partner-payout-accounts
/api/v1/payouts
```

### 3.4 Storefront Boundary

When `PARTNER_STOREFRONTS_ENABLED=false`, storefront API prefixes return `404` with:

```text
partner_storefronts_disabled
```

Reserved blocked prefixes:

```text
/api/v1/storefronts
/api/v1/storefront-profiles
```

### 3.5 Admin Preview Boundary

Admin partner preview paths under:

```text
/api/v1/admin/partner...
```

are not blocked by the public partner boundary. They continue to depend on existing controls:

1. canonical admin host guard;
2. admin authentication;
3. admin RBAC;
4. admin 2FA where required by environment;
5. audit logging in later workflow stages.

This preserves operator visibility without exposing partner self-serve launch.

---

## 4. Frontend Boundary

Implemented flag:

```text
frontend/src/shared/lib/stage3-partner-flags.ts
```

Default:

```text
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=false
```

### 4.1 Mini App

When the flag is false:

1. Mini App profile does not call `/partner/dashboard`;
2. `Partner Dashboard` section is hidden;
3. bind-code form is hidden;
4. partner earnings/codes are not displayed.

### 4.2 Dashboard Partner Surface

The dashboard partner client has a disabled state:

```text
Partner Portal Locked
S3-STAGE-05 disabled boundary
```

The customer dashboard route `/partner` remains excluded by the existing customer surface policy, so normal users still cannot open it from navigation.

---

## 5. Exit Criteria Check

| Exit Criteria | Result |
|---|---|
| Portal can be deployed without public access | Passed. Backend public/self-serve routes return disabled boundary. |
| Unauthorized user does not see partner workspace | Passed. Workspace paths are blocked before workspace lookup while flag is false. |
| UI explains gated state for operator/admin preview | Passed. Partner client has disabled-state copy. |
| Mini App does not expose public partner bind/dashboard | Passed. Section hidden and query disabled. |
| Payout UI/API not enabled | Passed. Payout API prefixes blocked by separate flag. |
| Storefront public routes not enabled | Passed. Reserved storefront prefixes blocked by separate flag. |
| Admin preview remains protected by admin boundary | Passed. `/api/v1/admin/partner...` is not blocked by public boundary. |

---

## 6. Validation

Commands:

```bash
cd backend
. .venv/bin/activate
ruff check src/config/settings.py src/main.py src/presentation/middleware/partner_disabled_boundary.py tests/unit/presentation/middleware/test_partner_disabled_boundary.py
pytest tests/unit/presentation/middleware/test_partner_disabled_boundary.py -q --no-cov
```

```bash
cd frontend
npm run test -- --run 'src/app/[locale]/(dashboard)/partner/components/__tests__/PartnerClient.disabled-boundary.test.tsx' 'src/app/[locale]/(dashboard)/partner/components/__tests__/PartnerClient.test.tsx' 'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx'
npm run lint -- 'src/app/[locale]/(dashboard)/partner/components/PartnerClient.tsx' 'src/app/[locale]/(dashboard)/partner/hooks/usePartner.ts' 'src/app/[locale]/miniapp/profile/page.tsx' 'src/shared/lib/stage3-partner-flags.ts' 'src/app/[locale]/(dashboard)/partner/components/__tests__/PartnerClient.disabled-boundary.test.tsx' 'src/app/[locale]/(dashboard)/partner/components/__tests__/PartnerClient.test.tsx' 'src/app/[locale]/miniapp/profile/__tests__/page.test.tsx'
```

Observed result:

```text
backend ruff: passed
backend tests: 5 passed
frontend tests: 25 passed
frontend eslint targeted: passed
git diff --check: passed
```

---

## 7. Production Rules

Before production deploy of S3 code, keep:

```text
PARTNER_PORTAL_ENABLED=false
PARTNER_APPLICATIONS_ENABLED=false
PARTNER_STOREFRONTS_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
NEXT_PUBLIC_PARTNER_PORTAL_ENABLED=false
```

Do not enable `PARTNER_PORTAL_ENABLED=true` until at least:

1. S3-STAGE-06 onboarding flow evidence exists;
2. S3-STAGE-07 workspace/team/RBAC evidence exists;
3. S3-STAGE-08 partner code/attribution anti-abuse evidence exists;
4. S3-STAGE-15 full rehearsal is complete;
5. S3-STAGE-16 production disabled-state proof is complete;
6. owner approves controlled pilot activation.

---

## 8. Next Stage

Proceed to:

```text
S3-STAGE-06: Partner Application And Onboarding Flow
```

Keep production partner self-serve disabled while implementing S3-STAGE-06.
