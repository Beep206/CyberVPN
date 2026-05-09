# Stage 1 Frontend Evidence

This category tracks customer-facing web and Mini App frontend proof for `S1 Controlled Public Beta`.

## Current Local Evidence

| ID | Evidence | State |
|---|---|---|
| `S1-FE-010` | [`80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`](../../../80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md) | `LOCAL_PASS`; RC/staging/production artifact scan remains required |
| `S1-FE-001` | [`107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`](../../../107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots, mirror/redirect proof and final artifact/domain evidence remain required |
| `S1-FE-002` | [`99_STAGE1_FE_002_DASHBOARD_STATES_EVIDENCE.md`](../../../99_STAGE1_FE_002_DASHBOARD_STATES_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots and real state transitions remain required |
| `S1-FE-003` | [`100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md`](../../../100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots, real Remnawave payload and VPN client import evidence remain required |
| `S1-FE-004` | [`101_STAGE1_FE_004_DEVICES_PAGE_EVIDENCE.md`](../../../101_STAGE1_FE_004_DEVICES_PAGE_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots, real backend sessions and real device enforcement evidence remain required |
| `S1-FE-005` | [`102_STAGE1_FE_005_WALLET_PAGE_EVIDENCE.md`](../../../102_STAGE1_FE_005_WALLET_PAGE_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots, real provider payment records and final RC artifact scan remain required |
| `S1-FE-006` | [`103_STAGE1_FE_006_GROWTH_UI_GATES_EVIDENCE.md`](../../../103_STAGE1_FE_006_GROWTH_UI_GATES_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots, final public env inventory and final RC artifact scan remain required |
| `S1-FE-007` | [`104_STAGE1_FE_007_OPERATOR_SURFACE_AUDIT_EVIDENCE.md`](../../../104_STAGE1_FE_007_OPERATOR_SURFACE_AUDIT_EVIDENCE.md) | `LOCAL_PASS`; deployed staging/RC route browser proof remains required |
| `S1-FE-008` | [`105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`](../../../105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md) | `LOCAL_PASS`; deployed screenshots and real Remnawave/client import proof remain required |
| `S1-FE-009` | [`106_STAGE1_FE_009_I18N_CRITICAL_PATH_EVIDENCE.md`](../../../106_STAGE1_FE_009_I18N_CRITICAL_PATH_EVIDENCE.md) | `LOCAL_PASS`; deployed EN/RU/RTL browser spot-checks and RC rerun remain required |

## Current Screenshot Evidence

```text
docs/cybervpn_stage1_launch_docs/evidence/s1-fe-002/dashboard-stage1-states-en-EN.png
```

## Go-Live Required Evidence

- Deployed staging/RC customer dashboard screenshots for active, trial, grace, expired, payment pending/failed and provisioning failed/ready states.
- Real backend/payment/Remnawave state transition samples feeding the dashboard state matrix.
- Deployed config delivery UI proof for QR/subscription URL/config file without raw URL leakage.
- Deployed wallet page proof for safe customer-scoped payment history without raw provider field exposure.
- Deployed public growth UI gate proof for web and Mini App referral/promo/gift/checkout-code surfaces.
- Deployed route audit proof that analytics/monitoring/users/partner remain hidden from the customer dashboard.
- Deployed `/servers` proof that config delivery works without operator load/traffic/online-user/inbound/node-version metrics.
- Deployed devices UI proof for real device sessions, entitlement-derived device limit and safe revoke actions.
- Deployed platform-guide screenshots for Android, iOS, Windows, macOS, Linux and Telegram Mini App, plus real generated Remnawave payload import proof for the supported client stack.
- Deployed i18n spot-checks for `en-EN`, `ru-RU` and at least one RTL fallback-supported locale; no public claim that secondary locales are fully translated without separate human review.
- Final frontend RC bundle/env scan and deployed artifact/CDN scan.
- Deployed marketing critical-page screenshots for pricing, features, devices, help, status and legal pages in `en-EN` and `ru-RU`, plus `.net` primary and `.org` mirror/redirect proof.

## Rules

- Do not commit raw subscription URLs, QR payload contents, config files, provider payloads or secrets as screenshots/transcripts.
- Redact user identifiers in deployed screenshots unless the account is disposable and clearly labelled as test data.
- Treat local screenshots as UI evidence only; they do not prove staging/prod readiness.
