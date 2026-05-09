> CyberVPN Launch Program
> Дата evidence: 2026-05-06
> Backlog ID: `S1-FE-004`
> Статус: PASS for local/no-cost frontend implementation. Not a go-live clearance.

# S1-FE-004 Devices Page Evidence

## Purpose

`S1-FE-004` proves that the authenticated customer device surface shows:

- active devices/sessions;
- current plan device limit;
- remaining capacity / over-limit state;
- safe customer actions for revoking stale sessions;
- no raw VPN config, payment provider payload or secret material.

## Implemented Scope

| Area | Result |
|---|---|
| Customer surface | Enhanced the authenticated settings device surface at `/settings#devices` in `frontend/src/widgets/settings-cabinet/settings-cabinet-dashboard.tsx` |
| Route decision | Kept public `/devices` as the existing marketing/SEO route; S1 customer device controls live under the authenticated settings cabinet to avoid a route conflict |
| Device data | Continues to use `authApi.listDevices()` and `authApi.logoutDevice()` |
| Device limit | Added `entitlementsApi.getCurrent()` and reads `effective_entitlements.device_limit`, with fallback keys `devices` and `max_devices` |
| Limit states | Added local model states: available, near limit, at limit, over limit and unknown |
| Safe actions | Keeps current-device protection, single remote revoke and revoke-others actions; current session is not revocable from the UI |
| i18n | Added EN/RU copy and regenerated generated message bundles |

## UI / Safety Notes

| Risk | Local control |
|---|---|
| Customer sees plan limit as a hardcoded value | Limit is read from current entitlement API data, not static UI copy |
| Current session accidentally revoked | UI still hides revoke action for `is_current` device and explains current session protection |
| Over-limit state is hidden | UI shows explicit over-limit status and recommends revoke/support instead of silently allowing more devices |
| Unknown entitlement data blocks device management | If entitlement loading fails or lacks a limit, active devices and revoke actions remain usable |
| Raw secrets/configs exposed | The surface only renders session metadata, short device IDs, IP if provided by the authenticated device API and coarse entitlement counts |

## Validation Commands

| Check | Command | Result |
|---|---|---|
| Settings device model/UI tests | `npm --prefix frontend run test:run -- src/widgets/settings-cabinet/__tests__/settings-cabinet-model.test.ts src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx` | PASS: 2 files, 27 tests |
| Settings device lint | `npm --prefix frontend run lint -- src/widgets/settings-cabinet/settings-cabinet-model.ts src/widgets/settings-cabinet/settings-cabinet-dashboard.tsx src/widgets/settings-cabinet/__tests__/settings-cabinet-model.test.ts src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx` | PASS |
| Frontend production build | `npm --prefix frontend run build` | PASS: Next.js 16.2.4 production build, TypeScript, 2684 static pages generated |
| i18n bundle generation | Triggered by frontend scripts | PASS: 39 locale bundles generated |
| Frontend dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory through `next` remains tracked because `npm audit fix --force` proposes a breaking Next downgrade |
| High-confidence secret-pattern scan over touched runtime/message files | `rg` for private keys, common live token prefixes and secret-like assignments | PASS: no matches |
| Dangerous-pattern scan over touched runtime files | `rg` for `eval`, dynamic `Function`, `dangerouslySetInnerHTML`, `innerHTML`, `document.write` and shell execution patterns | PASS: no matches |
| Whitespace/diff check | `git diff --check` over touched runtime/message files | PASS |

## Documentation / Library References Used

- Next.js official App Router docs: `use client` directive for client-side interactive surfaces.
- TanStack Query official React `useQuery` docs for authenticated client data fetching.
- React official `useState` docs for local UI state.
- Testing Library official `ByRole` docs for accessible action assertions.

## Remaining Go-Live Evidence

Before S1 Controlled Public Beta go-live, this local proof must be repeated on staging/RC:

1. Disposable beta account shows real backend device sessions and entitlement-derived `device_limit`.
2. Browser screenshot proves `/settings#devices` shows devices, limit, remaining slots and revoke controls.
3. Remote revoke and revoke-others actions work against the deployed backend and update the device list.
4. Backend device/session policy is aligned with Remnawave/device credential enforcement.
5. Support/admin proof confirms staff can diagnose device-limit issues without seeing raw VPN config secrets.

## Acceptance Result

`S1-FE-004` is **completed locally** for implementation, i18n, focused tests, lint and production frontend build.

This does **not** clear go-live by itself. It closes the no-cost/local devices UI step and leaves deployed staging/RC evidence open.

Next ID to execute: `S1-FE-009` - i18n critical-path validation. `S1-FE-005`...`S1-FE-008` are completed locally through `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`.
