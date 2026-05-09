> CyberVPN Launch Program
> Дата evidence: 2026-05-06
> Backlog ID: `S1-FE-002`
> Статус: PASS for local/no-cost frontend implementation. Not a go-live clearance.

# S1-FE-002 Dashboard States Evidence

## Purpose

`S1-FE-002` proves that the customer web dashboard renders the Stage 1 beta states clearly enough for a real B2C user and support/admin operator to understand the current access path.

Required states:

- active;
- trial;
- grace;
- expired;
- payment pending/failed/final;
- provisioning pending/failed/ready/unavailable.

## Implemented Scope

| Area | Result |
|---|---|
| Customer dashboard model | Added a Stage 1 state matrix for `access`, `payment` and `provisioning` in `frontend/src/widgets/customer-cabinet/customer-cabinet-model.ts` |
| Customer dashboard UI | Added three explicit state cards to `frontend/src/widgets/customer-cabinet/customer-cabinet-dashboard.tsx` |
| Grace handling | `grace`, `grace_period` and `in_grace` are treated as `attention`, not immediate `critical`, because paid S1 access has the approved 72-hour grace contract |
| Payment state inputs | Dashboard accepts current/future backend markers from `effective_entitlements.stage1_payment_state`, `payment_state` or `latest_payment_state` |
| Provisioning state inputs | Dashboard accepts current/future backend markers from `effective_entitlements.stage1_provisioning_state`, `provisioning_state` or `vpn_provisioning_state` |
| Fallback behavior | If backend state is absent, dashboard derives a conservative state from entitlement, trial, Remnawave service state and query errors |
| i18n | Added EN/RU copy and English fallback copy for other enabled locales; regenerated 39 locale bundles |
| Build blocker found during verification | Fixed a pre-existing `wallet-cabinet-dashboard.tsx` TypeScript refetch typing issue that blocked full frontend production build |

## UI Evidence

Local screenshot:

```text
docs/cybervpn_stage1_launch_docs/evidence/s1-fe-002/dashboard-stage1-states-en-EN.png
```

Screenshot context:

- local Next dev server on `localhost:9001`;
- development-only `DEV_BYPASS_AUTH=true` cookie;
- no real backend session or payment/provider data;
- backend API unavailable, so the screenshot intentionally shows degraded/no-access/remnawave-unavailable fallback states.

This is UI evidence only. It does not replace deployed staging/RC screenshots with real backend, payment and Remnawave states.

## State Matrix

| Card | States covered locally | Primary action behavior |
|---|---|---|
| Access | `checking`, `active`, `trial_active`, `grace`, `expired`, `payment_pending`, `provisioning_pending`, `no_access` | No CTA while checking; config for active/trial; renewal for grace/expired/payment/no-access; provisioning action for provisioning pending |
| Payment | `checking`, `paid`, `not_started`, `pending`, `processing`, `failed`, `expired`, `refunded`, `reconciliation_required` | No CTA while checking or paid; plan/payment management for unresolved states |
| Provisioning | `checking`, `ready`, `pending`, `retrying`, `failed`, `remnawave_unavailable`, `reconciliation_required`, `not_required` | No CTA while checking/not required; config for ready; provisioning action for unresolved delivery states |

## Validation Commands

| Check | Command | Result |
|---|---|---|
| Customer dashboard model/UI tests | `npm --prefix frontend run test:run -- src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx` | PASS: 2 files, 18 tests |
| Customer dashboard lint | `npm --prefix frontend run lint -- src/widgets/customer-cabinet/customer-cabinet-model.ts src/widgets/customer-cabinet/customer-cabinet-dashboard.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-model.test.ts src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx` | PASS |
| Wallet dashboard regression test after build-blocker fix | `npm --prefix frontend run test:run -- src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx` | PASS: 1 file, 17 tests |
| Wallet dashboard lint after build-blocker fix | `npm --prefix frontend run lint -- src/widgets/billing-cabinet/wallet-cabinet-dashboard.tsx` | PASS |
| Frontend production build | `npm --prefix frontend run build` | PASS: Next.js 16.2.4 production build, TypeScript, 2684 static pages generated |
| i18n bundle generation | Triggered by frontend scripts | PASS: 39 locale bundles generated |
| Frontend dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory through `next` remains tracked because `npm audit fix --force` proposes a breaking Next downgrade |
| Secret-pattern scan over touched frontend/docs/message files | High-confidence `rg` token/private-key pattern scan | PASS: no matches |
| Dangerous-pattern scan over touched frontend/docs files | `rg` for `eval`, dynamic `Function`, `dangerouslySetInnerHTML`, shell execution patterns | PASS for touched code; only pre-existing docs text describing earlier dangerous-pattern scans matched |

## Security and Privacy Notes

- The dashboard cards render normalized status labels and help text only.
- No raw subscription URL, QR payload, config file, provider snapshot, idempotency key, webhook payload, Remnawave credential or token is rendered by this task.
- Payment/provisioning states are deliberately coarse-grained. Detailed provider/debug data remains support/admin-only.
- Development screenshot used only a local bypass cookie and contains no production secrets.

## Remaining Go-Live Evidence

Before S1 Controlled Public Beta go-live, the following evidence is still required:

1. Deployed staging/RC screenshots for active, trial, grace, expired, payment pending/failed and provisioning failed/ready states.
2. Backend/worker evidence that real payment and Remnawave transitions populate the dashboard state markers or equivalent API fields.
3. Real provider/Remnawave failure samples proving paid-but-no-access and orphan-payment policy integration.
4. Support/admin queue proof for `reconciliation_required` states.
5. Final RC artifact scan and deployed HTTPS/browser proof.

## Acceptance Result

`S1-FE-002` is **completed locally** for implementation, UI rendering, i18n, focused tests, screenshot evidence and production frontend build.

This does **not** clear go-live by itself. It closes the no-cost/local frontend dashboard-state implementation step and leaves deployed staging/RC evidence open.

Next ID to execute: `S1-FE-009` - i18n critical-path validation. `S1-FE-003`...`S1-FE-008` are completed locally through `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`.
