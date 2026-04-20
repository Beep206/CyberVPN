# Desktop Client UX Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stabilize the desktop client so connection state, tray/window behavior, navigation behavior, and theming are trustworthy and consistent across Windows light/dark usage.

**Architecture:** Treat the current issues as a small number of systemic failures instead of a long tail of isolated UI bugs. The fix should establish a single source of truth for connection lifecycle and session options, keep the application shell mounted during route changes, define one explicit desktop contract for tray/close/quit behavior, and move the visual layer onto semantic theme tokens instead of hardcoded black/white surfaces.

**Tech Stack:** Tauri 2, Rust, React 19, React Router, Framer Motion, Tailwind CSS 4, Base UI, Sonner, i18next

---

## Current Analysis

### Observed Bug Inventory

The current stabilization scope should explicitly include these already confirmed or strongly evidenced defects:

1. Connection can appear active while real VPN egress is not yet verified.
2. Repeated click on the connect button can fail to disconnect cleanly or visibly.
3. Route changes feel like a full-page reload.
4. Light theme has weak separation between white and gray surfaces.
5. Dark theme dropdowns and overlays can become unreadable.
6. TUN toggle state resets after leaving and returning to the dashboard.
7. Tray `Quit` does not behave like a trustworthy, fully tested real-exit path.
8. Tray and global shortcut reconnect flows ignore last-used `tun_mode` and `system_proxy`.
9. Some backend-to-frontend reconnection hooks exist but are not wired into the React app.

These are not separate root causes. Most of them collapse into missing state ownership, missing persistence for session options, missing desktop-shell lifecycle rules, and incomplete theming.

### Outstanding TODO and Runtime Debt Register

The current desktop client has very few explicit `TODO` comments, but several high-value pieces of implicit debt that should be treated the same way and retired intentionally.

#### Explicit TODO / dead-path debt

1. Tray connect/disconnect toggle is still marked unfinished in [apps/desktop-client/src-tauri/src/tray.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/tray.rs), and the implementation still reconnects with hardcoded `tun=false`, `system_proxy=false`.
2. Backend emits `request-reconnect` in [apps/desktop-client/src-tauri/src/ipc/mod.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/ipc/mod.rs), but the React app has no listener for that event, so the reconnect path is effectively dead code.

#### Production panic / brittle-runtime debt

These are not all guaranteed crashes, but they are avoidable runtime-hardening debt and should be tracked:

1. Tauri startup still uses `.expect("error while building tauri application")` in [apps/desktop-client/src-tauri/src/lib.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/lib.rs).
2. Tray icon setup uses `unreachable!` if the default icon is missing in [apps/desktop-client/src-tauri/src/tray.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/tray.rs).
3. Tray quit uses `tauri::async_runtime::block_on(...)` inside the menu handler in [apps/desktop-client/src-tauri/src/tray.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/tray.rs), which should be replaced by a dedicated async shutdown path.
4. Subscription timestamp persistence uses `duration_since(UNIX_EPOCH).unwrap()` in [apps/desktop-client/src-tauri/src/ipc/mod.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/ipc/mod.rs).
5. Usage-history path and mutex handling use `unwrap()` in [apps/desktop-client/src-tauri/src/engine/sys/stats.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/engine/sys/stats.rs).
6. Stealth diagnostics builds a `reqwest` client with `.unwrap()` in [apps/desktop-client/src-tauri/src/engine/sys/diagnostics.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/engine/sys/diagnostics.rs).
7. Remote-control server task ends with `.await.unwrap()` in [apps/desktop-client/src-tauri/src/engine/sys/remote_control.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/engine/sys/remote_control.rs).
8. Sync key derivation uses `Params::new(...).unwrap()` in [apps/desktop-client/src-tauri/src/engine/sys/sync.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/engine/sys/sync.rs).
9. Config generation still serializes several structures with `serde_json::to_value(...).unwrap()` in [apps/desktop-client/src-tauri/src/engine/config.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/engine/config.rs).

#### Policy for this stabilization program

For this effort, “no TODO debt left behind” means:

1. No explicit unfinished behavior in production code for tray, reconnect, shutdown, or desktop shell flows.
2. No dead events or dead branches in the connection lifecycle.
3. No avoidable production `unwrap!` / `expect!` / `unreachable!` in desktop runtime paths unless they are explicitly documented as process-fatal invariants and reviewed as such.
4. All remaining acceptable hard invariants must be documented in the regression matrix and architecture notes.

### 1. Connection lifecycle is not modeled as one coherent state machine

Evidence:
- [apps/desktop-client/src/pages/Dashboard/index.tsx](/home/beep/projects/VPNBussiness/apps/desktop-client/src/pages/Dashboard/index.tsx) owns the connection UI state locally.
- The connect button behavior is driven by `status.status`, but disconnect errors are swallowed in `handleDisconnect()`.
- Backend status and persisted store can diverge. The latest user snapshot showed `connection_status.activeId` populated while `active_profile_id` in diagnostics was `null`.
- `connect_profile` emits `connected` after process start, not after an actual egress-health confirmation.

Impact:
- The button can say `Подключено` while real traffic is not yet confirmed.
- Repeat click on the button can look broken because UI state, process state, and persisted state are not aligned.
- TUN and non-TUN paths behave differently, but the UI does not model that difference explicitly.

### 2. Route changes remount too much of the app

Evidence:
- [apps/desktop-client/src/main.tsx](/home/beep/projects/VPNBussiness/apps/desktop-client/src/main.tsx) renders `<Routes location={location} key={location.pathname}>`.
- The same file wraps the whole route tree in app-level `Suspense` and `AnimatePresence`.
- This causes the shell and nested route tree to remount on every navigation, which explains the user-visible “page reload” effect.
- [apps/desktop-client/src/widgets/Layout.tsx](/home/beep/projects/VPNBussiness/apps/desktop-client/src/widgets/Layout.tsx) also owns side effects like updater checks and routing assistant listeners, so remounting the shell risks repeated setup work.

Impact:
- Navigation looks like a hard refresh instead of a native desktop route transition.
- In-page state resets more often than necessary.
- The app feels unstable even when data is technically correct.

### 3. Session options and dashboard affordances are not persisted coherently

Evidence:
- [apps/desktop-client/src/pages/Dashboard/index.tsx](/home/beep/projects/VPNBussiness/apps/desktop-client/src/pages/Dashboard/index.tsx) initializes `tunMode` with `useState(false)` and does not hydrate it from backend or persisted store.
- The TUN switch is disabled while connected, but the current checked value is page-local only, so revisiting the page can show `false` even if the live session is using TUN.
- [apps/desktop-client/src-tauri/src/engine/store.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/engine/store.rs) persists `stealth_mode_enabled`, but there is no equivalent persisted model for `last_used_tun_mode`, `last_used_system_proxy`, or a normalized `last_connection_options`.
- [apps/desktop-client/src-tauri/src/tray.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/tray.rs) hardcodes `false, false` when reconnecting from the tray.
- [apps/desktop-client/src-tauri/src/lib.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/lib.rs) does the same in the global shortcut handler.
- [apps/desktop-client/src-tauri/src/ipc/mod.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/ipc/mod.rs) emits `request-reconnect`, but there is no React listener for that event.

Impact:
- The dashboard can lie about whether TUN is currently active.
- Tray reconnect, hotkey reconnect, and UI reconnect do not necessarily use the same connection options.
- User intent is lost as soon as the page remounts or a non-dashboard surface triggers the connection.

### 4. Tray, close-to-tray, and real-exit behavior are not defined as one desktop contract

Evidence:
- [apps/desktop-client/src-tauri/src/lib.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/lib.rs) intercepts window close and always hides the window.
- [apps/desktop-client/src-tauri/src/tray.rs](/home/beep/projects/VPNBussiness/apps/desktop-client/src-tauri/src/tray.rs) handles `quit` separately by calling `process_manager.stop()` and then `app.exit(0)`.
- The tray menu label is static `Connect / Disconnect` instead of reflecting the actual state.
- There is no explicit shutdown service shared by titlebar close, tray quit, process exit, and future command surfaces.
- There is no documented acceptance matrix for right-click tray actions on Windows.

Impact:
- Users cannot build trust in whether the app is hidden, minimized to tray, or actually exiting.
- The tray quit path can diverge from the normal lifecycle and is harder to reason about or test.
- Desktop behavior feels improvised instead of intentional.

### 5. Theme architecture is fragmented and cannot support a high-quality light theme

Evidence:
- The app uses a custom theme provider in [apps/desktop-client/src/app/theme-provider.tsx](/home/beep/projects/VPNBussiness/apps/desktop-client/src/app/theme-provider.tsx).
- The toaster wrapper in [apps/desktop-client/src/components/ui/sonner.tsx](/home/beep/projects/VPNBussiness/apps/desktop-client/src/components/ui/sonner.tsx) imports `useTheme` from `next-themes`, which is not the same provider.
- The shell and many pages use hardcoded `bg-black/*`, `bg-white/*`, `text-white`, and `border-white/*` classes instead of semantic tokens.
- Quick audit counts in `apps/desktop-client/src`: `bg-black` references `160`, `bg-white` references `24`, `text-white` references `39`, `border-white` references `31`.

Impact:
- Light theme looks unfinished because most surfaces were designed for dark mode only.
- Dropdowns, titlebar surfaces, overlays, and shell components can render with mismatched contrast.
- Theme regressions are expensive because colors are duplicated everywhere.

### 6. Motion density is too high for a desktop utility app

Evidence:
- Quick audit found `153` motion-related references across `pages/` and `widgets/`.
- Route-level transitions, card-level transitions, and animated overlays all compete visually.
- Several transitions use scale and opacity combinations that exaggerate the perception of a full reload.

Impact:
- Navigation feels heavier than it should.
- UI polish reads as instability.
- Repeated animations make diagnostics harder because users cannot distinguish loading, remounting, and real state transitions.

### 7. State ownership is overly fragmented across the app

Evidence:
- Quick audit found `59` `useState` hooks in `pages/` alone.
- Connection state is page-local in dashboard, language menu state is widget-local, theme is provider-local, and session preferences are partially persisted and partially ephemeral.
- The current architecture relies on page remounts not happening too often, which is already false because of the router setup.

Impact:
- Small UX bugs multiply because the same concern is represented in multiple places.
- The user experiences “random” resets that are actually deterministic remount/persistence gaps.

### 8. The project lacks a regression net for desktop UX

Evidence:
- There is logging for runtime/debug flows, but no explicit UI acceptance matrix for dark/light shell behavior, connect/disconnect across routes, or dropdown contrast.
- There is no shared contract test for the connection state lifecycle between Rust and React.

Impact:
- Small changes keep reintroducing visible desktop bugs.
- The team is relying on manual user discovery instead of a stable release gate.

## Root-Cause Summary

Most reported “small issues” come from six root problems:

1. No canonical connection state model shared by Rust and React.
2. No persisted session-options model shared by dashboard, tray, hotkeys, and reconnect flows.
3. Route transitions are implemented by remounting the route tree.
4. Desktop shell behavior for hide, show, minimize-to-tray, and quit is not defined as one contract.
5. Theme tokens exist, but the UI still mostly bypasses them with hardcoded colors.
6. There is no desktop-specific regression checklist covering interaction, navigation, tray behavior, persistence, and contrast.

## Phased Plan

### Phase 0: Stabilization Baseline and Acceptance Contract

Objective:
- Turn the current bug cluster into an explicit acceptance target before more UI changes happen.

Files:
- Create: `docs/plans/2026-04-19-desktop-client-ux-stabilization-plan.md`
- Create: `docs/plans/2026-04-19-desktop-client-ux-regression-matrix.md`
- Modify: `apps/desktop-client/src/shared/i18n/locales/en-EN.json`
- Modify: `apps/desktop-client/src/shared/i18n/locales/ru-RU.json`

Steps:
1. Write the desktop UX acceptance matrix for Windows with these axes: `dark/light`, `tun on/off`, `connect/disconnect`, `route switching while connected`, `dashboard re-entry`, `tray show/hide/quit`, `hotkey toggle`, `dropdown/open overlay readability`.
2. Define the canonical connection states: `disconnected`, `connecting`, `connected`, `disconnecting`, `error`, `degraded`.
3. Define the canonical desktop shell states: `visible`, `hidden-to-tray`, `quitting`, `exited`.
4. Define what each state means in UI terms, backend terms, and persistence terms.
5. Define one source of truth for session options: profile id, tun mode, system proxy, chosen core, and last requested action.
6. Add missing user-facing copy for `disconnecting`, degraded/runtime-warning, and tray lifecycle states.
7. Freeze any new cosmetic UI work until the contract is accepted.

Verification:
- Review the matrix with product/test stakeholders.
- Confirm every reported bug maps to at least one matrix row.

### Phase 1: Connection Lifecycle and Disconnect Reliability

Objective:
- Make the button truthful and make connect/disconnect deterministic across TUN and non-TUN modes.

Files:
- Create: `apps/desktop-client/src/shared/model/connection-store.ts`
- Create: `apps/desktop-client/src/shared/model/use-connection.ts`
- Modify: `apps/desktop-client/src/pages/Dashboard/index.tsx`
- Modify: `apps/desktop-client/src/widgets/ConnectButton.tsx`
- Modify: `apps/desktop-client/src/shared/api/ipc.ts`
- Modify: `apps/desktop-client/src-tauri/src/ipc/mod.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/manager.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/diagnostics.rs`
- Modify: `apps/desktop-client/src-tauri/src/ipc/models.rs`

Steps:
1. Write a frontend state chart document that maps Rust events to the six canonical connection states.
2. Create a shared connection store so the app shell does not depend on `Dashboard` as the only live owner of connection status.
3. Move connect/disconnect command orchestration out of page-local state into the shared store.
4. Add an explicit `disconnecting` state and disable repeat clicks while disconnect is in progress.
5. Stop swallowing disconnect errors in `Dashboard`; surface them in toast and diagnostics.
6. Ensure Rust updates `status`, `active_id`, `active_core`, `proxy_url`, and persisted `active_profile_id` atomically during connect and disconnect.
7. Add backend diagnostics for disconnect success, disconnect failure, and timeout while stopping elevated runtimes.
8. Add a readiness gate so the UI cannot show `connected` until the runtime is usable.
9. For TUN mode, add a post-connect health probe that verifies real outbound routing before the UI flips to fully connected.
10. Add a degraded state when runtime starts but egress verification fails.
11. Make disconnect idempotent from UI perspective so repeated user clicks cannot leave the button in a misleading state.
12. Add a backend event for `disconnect_started`, `disconnect_completed`, and `disconnect_failed`.

Verification:
- Manual: connect and disconnect five times each in `tun=false` and `tun=true`.
- Manual: connect, navigate across five routes, then disconnect from the dashboard.
- Manual: disconnect while runtime is still starting and confirm button/state do not wedge.
- Rust/TS tests: lifecycle transitions match the accepted state chart.

Exit criteria:
- “Connected but still on my real IP” is impossible without a visible degraded/error state.
- Repeat-click disconnect no longer silently fails.

### Phase 2: Session Options Persistence and Cross-Surface Command Consistency

Objective:
- Make `tun_mode`, `system_proxy`, selected profile, and last-used connection options survive route changes and stay consistent across dashboard, tray, hotkey, and reconnect paths.

Files:
- Modify: `apps/desktop-client/src-tauri/src/engine/store.rs`
- Modify: `apps/desktop-client/src-tauri/src/ipc/models.rs`
- Modify: `apps/desktop-client/src-tauri/src/ipc/mod.rs`
- Modify: `apps/desktop-client/src/shared/api/ipc.ts`
- Modify: `apps/desktop-client/src/pages/Dashboard/index.tsx`
- Modify: `apps/desktop-client/src-tauri/src/tray.rs`
- Modify: `apps/desktop-client/src-tauri/src/lib.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/sys/remote_control.rs`

Steps:
1. Add a persisted `last_connection_options` model to the Rust store with at least: `profile_id`, `tun_mode`, `system_proxy`, `active_core`, `source_surface`, and timestamps.
2. Add Tauri IPC commands to read and update these options explicitly.
3. Hydrate the dashboard TUN toggle from persisted or live session data instead of `useState(false)`.
4. Make the dashboard reflect live session options when revisiting the route while already connected.
5. Update tray reconnect logic to use the same persisted options rather than hardcoded `false, false`.
6. Update the global hotkey toggle to use the same persisted options.
7. Decide whether `request-reconnect` should be fully implemented or removed; do not leave it as a dead event path.
8. Add diagnostics that record which surface initiated connect/disconnect and which options were used.
9. Add explicit reconciliation logic on app startup so live runtime state and persisted session options cannot drift silently.

Verification:
- Manual: enable TUN, connect, switch to another route, return to dashboard, confirm the TUN toggle still reflects the active session.
- Manual: connect from dashboard, disconnect from tray, reconnect from hotkey, verify the same TUN/system-proxy options are reused.
- Manual: restart the app while connected or after an unclean exit and verify the restored state is truthful.

Exit criteria:
- Dashboard re-entry never resets the TUN affordance visually while the session is still active.
- Tray and hotkey toggles use the same connection options as the dashboard.

### Phase 3: Tray, Window, and Shutdown Lifecycle Hardening

Objective:
- Turn hide/show/quit behavior into an explicit, testable desktop contract.

Files:
- Modify: `apps/desktop-client/src-tauri/src/tray.rs`
- Modify: `apps/desktop-client/src-tauri/src/lib.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/lifecycle.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/diagnostics.rs`
- Modify: `apps/desktop-client/src/widgets/Titlebar.tsx`
- Modify: `apps/desktop-client/src/shared/i18n/locales/en-EN.json`
- Modify: `apps/desktop-client/src/shared/i18n/locales/ru-RU.json`

Steps:
1. Create a unified shutdown service in Rust that all exit surfaces call.
2. Route tray `quit`, future titlebar exit, and app process exit through the same shutdown path.
3. Define and document the difference between `hide window`, `close to tray`, and `real quit`.
4. Make tray menu items dynamic so labels and enabled/disabled states reflect actual connection and window state.
5. Add explicit diagnostics for tray menu actions, hide-to-tray events, and real-exit completion.
6. Verify that quitting from tray works whether or not a VPN process is active.
7. Decide whether right-click tray should only show the menu or also support additional behavior, then test it on packaged Windows builds.

Verification:
- Manual: hide window with the titlebar close button, reopen from tray, then quit from tray.
- Manual: quit from tray while disconnected.
- Manual: quit from tray while connected in `tun=false` and `tun=true`.
- Manual: confirm lifecycle exit is marked cleanly and no zombie runtime remains.

Exit criteria:
- Users can reliably distinguish “hidden to tray” from “fully exited”.
- Tray `Quit` is a first-class, trusted exit path.

### Phase 4: Router and Application Shell Stabilization

Objective:
- Remove the pseudo-refresh feeling during navigation and keep shell state mounted.

Files:
- Modify: `apps/desktop-client/src/main.tsx`
- Modify: `apps/desktop-client/src/widgets/Layout.tsx`
- Create: `apps/desktop-client/src/widgets/RouteTransition.tsx`
- Create: `apps/desktop-client/src/widgets/PageSkeleton.tsx`

Steps:
1. Remove `key={location.pathname}` from the top-level `<Routes>` tree.
2. Keep `Layout` mounted across navigation so titlebar, sidebar, updater listener, and routing listener initialize once.
3. Move route transitions below the persistent shell, around the outlet content only.
4. Replace the full-screen `RouteLoadingFallback` with per-page skeletons or lightweight in-place placeholders.
5. Tune route animation timing to desktop-safe values and avoid scale-based transitions for normal navigation.
6. Verify that scrolling, focus, and local page state behave predictably when changing routes.

Verification:
- Manual: open each sidebar route in sequence and confirm the shell does not flash or reset.
- Manual: keep a connection active while navigating and confirm no “workspace reloading” effect.
- Performance: compare route switch timings before and after the change.

Exit criteria:
- Sidebar navigation feels like in-app routing, not a reload.
- Shell listeners are initialized once per app session.

### Phase 5: Theme Foundation and Token Refactor

Objective:
- Make light and dark themes coherent by moving the shell and primitives to semantic tokens.

Files:
- Modify: `apps/desktop-client/src/index.css`
- Modify: `apps/desktop-client/src/app/theme-provider.tsx`
- Modify: `apps/desktop-client/src/components/ui/sonner.tsx`
- Modify: `apps/desktop-client/src/widgets/Layout.tsx`
- Modify: `apps/desktop-client/src/widgets/Titlebar.tsx`
- Modify: `apps/desktop-client/src/widgets/LanguageSelector.tsx`
- Modify: `apps/desktop-client/src/components/ui/select.tsx`
- Modify: `apps/desktop-client/src/components/ui/dialog.tsx`
- Modify: `apps/desktop-client/src/components/ui/button.tsx`
- Modify: `apps/desktop-client/src/components/ui/input.tsx`

Steps:
1. Choose one theme source of truth and remove the split between the custom provider and `next-themes` usage.
2. Redefine light theme surface tokens so cards, sidebars, popovers, and borders have stronger hierarchy.
3. Add shell-level semantic tokens for `titlebar`, `sidebar`, `panel`, `overlay`, and `interactive-hover`.
4. Replace hardcoded black/white classes in shell primitives with semantic tokens.
5. Make the toast system consume the same theme source and token palette as the rest of the app.
6. Re-test typography and icon contrast in both themes.

Verification:
- Visual review of dashboard, settings, logs, profiles, subscriptions, and onboarding in `dark` and `light`.
- Contrast spot-check for text, secondary text, borders, and active states.

Exit criteria:
- Light theme has visible surface separation and readable borders.
- Dark theme overlays and shell surfaces do not accidentally switch to light backgrounds.

### Phase 6: Dropdowns, Overlays, and Component Consistency

Objective:
- Fix the component-level contrast and surface mismatches the user sees in dropdowns and popovers.

Files:
- Modify: `apps/desktop-client/src/components/ui/select.tsx`
- Modify: `apps/desktop-client/src/widgets/LanguageSelector.tsx`
- Modify: `apps/desktop-client/src/components/ui/dialog.tsx`
- Modify: `apps/desktop-client/src/components/ui/switch.tsx`
- Modify: `apps/desktop-client/src/pages/Settings/index.tsx`
- Modify: `apps/desktop-client/src/pages/Profiles/index.tsx`
- Modify: `apps/desktop-client/src/pages/Subscriptions/index.tsx`

Steps:
1. Audit every dropdown, modal, and popover against both themes.
2. Standardize background, border, text, hover, selected, and disabled states for overlay components.
3. Remove one-off styling in pages where shared UI primitives should own the appearance.
4. Normalize focus rings and keyboard navigation on interactive controls.
5. Make dropdown widths, spacing, and typography consistent with desktop usage.

Verification:
- Manual: open each dropdown and dialog in both themes.
- Manual: test keyboard navigation with `Tab`, arrow keys, and `Esc`.

Exit criteria:
- No overlay is unreadable in dark mode.
- No component uses a page-local color hack for its default theme behavior.

### Phase 7: Motion Budget and Micro-Polish

Objective:
- Keep the cyberpunk identity while removing the sense of instability and over-animation.

Files:
- Modify: `apps/desktop-client/src/main.tsx`
- Modify: `apps/desktop-client/src/widgets/ConnectButton.tsx`
- Modify: `apps/desktop-client/src/widgets/Layout.tsx`
- Modify: `apps/desktop-client/src/pages/Dashboard/index.tsx`
- Modify: `apps/desktop-client/src/pages/Settings/index.tsx`
- Modify: `apps/desktop-client/src/pages/Profiles/index.tsx`
- Modify: `apps/desktop-client/src/pages/Subscriptions/index.tsx`

Steps:
1. Define a motion budget for route changes, overlays, and status indicators.
2. Remove scale animations from standard page navigation.
3. Keep expressive motion only where it communicates real state change, such as connect progress or active navigation.
4. Shorten transition durations so the UI feels responsive on desktop hardware.
5. Add `prefers-reduced-motion` handling for expensive or decorative effects.

Verification:
- Manual: navigate quickly through the sidebar and verify there is no motion backlog.
- Manual: compare connected, connecting, disconnecting, and error button states for clarity.

Exit criteria:
- Motion reinforces state instead of disguising remounts.
- The desktop app feels fast, not theatrical.

### Phase 8: QA Net, Tooling, and Release Gate

Objective:
- Prevent this class of bugs from returning silently.

Files:
- Create: `docs/plans/2026-04-19-desktop-client-ux-regression-matrix.md`
- Create: `apps/desktop-client/src/shared/model/__tests__/connection-store.test.ts`
- Create: `apps/desktop-client/src/shared/model/__tests__/session-options-store.test.ts`
- Create: `apps/desktop-client/src/components/ui/__tests__/theme-surfaces.test.tsx`
- Create: `apps/desktop-client/src/widgets/__tests__/route-transition.test.tsx`
- Create: `apps/desktop-client/src-tauri/tests/tray_shutdown_contract.rs`
- Modify: `apps/desktop-client/package.json`

Steps:
1. Add lightweight unit tests for the shared connection store and lifecycle transitions.
2. Add tests for persisted session options and dashboard rehydration.
3. Add component-level tests for theme surface tokens in key primitives.
4. Add a route transition smoke test to confirm the shell stays mounted.
5. Add a tray/shutdown contract test or scripted validation harness on packaged Windows builds.
6. Add a manual release checklist for Windows installer validation.
7. Require the regression matrix to be completed before shipping UX-facing desktop builds.

Verification:
- Run the desktop client test suite.
- Run the manual Windows matrix on a packaged build.
- Attach logs/screenshots for any failed acceptance item.

Exit criteria:
- New releases have a repeatable UX validation gate.
- Regressions are caught before user testing.

### Phase 9: TODO and Runtime Debt Burn-Down

Objective:
- Finish the stabilization by eliminating leftover explicit TODOs, dead events, and brittle production panic points in desktop runtime code.

Files:
- Modify: `apps/desktop-client/src-tauri/src/tray.rs`
- Modify: `apps/desktop-client/src-tauri/src/ipc/mod.rs`
- Modify: `apps/desktop-client/src-tauri/src/lib.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/sys/stats.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/sys/diagnostics.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/sys/remote_control.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/sys/sync.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/config.rs`
- Modify: `docs/plans/2026-04-19-desktop-client-ux-regression-matrix.md`

Steps:
1. Remove the explicit tray toggle TODO by wiring tray actions to the canonical shared session-options model.
2. Implement or delete `request-reconnect`; do not keep the event emitted without a live consumer.
3. Replace tray `block_on` shutdown with the shared async shutdown service from the tray/window lifecycle phase.
4. Replace `unreachable!` in tray icon initialization with a recoverable fallback path and diagnostics.
5. Replace production `unwrap()` on time, paths, client builders, Argon parameters, server tasks, and JSON serialization with proper error propagation or controlled fallback behavior.
6. Audit remaining production `expect()`/`unwrap()` usage in desktop runtime code and classify each one as:
   - removed
   - converted to `Result`
   - kept intentionally as documented fatal invariant
7. Add a “runtime hardening audit” section to the regression matrix so future reviews cannot reintroduce silent panic points casually.

Verification:
- Run desktop build and relevant test suites after each debt-removal cluster.
- Manually verify tray, reconnect, sync, and diagnostics flows still function after panic-point cleanup.
- Produce a final checklist showing each tracked debt item as `removed`, `reworked`, or `documented invariant`.

Exit criteria:
- No explicit TODO comments remain in production desktop runtime paths.
- No dead reconnect/tray lifecycle events remain.
- Remaining production hard invariants are intentional, documented, and minimal.

## Recommended Execution Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7
9. Phase 8
10. Phase 9

This order matters. Fixing theme and micro-polish before state and routing stability would only make the app prettier while the core UX remained unreliable.

## Immediate Priorities

If the team wants the fastest user-visible improvement, the first implementation slice should be:

1. Phase 1 steps 1-7
2. Phase 2 steps 1-6
3. Phase 3 steps 1-4
4. Phase 4 steps 1-4
5. Phase 9 steps 1-4

That combination removes the most damaging symptoms:
- lying connect/disconnect state
- tray/hotkey/dashboard using different connection options
- TUN toggle lying after dashboard re-entry
- untrusted tray quit behavior
- explicit TODO / dead reconnect debt in tray and IPC flows
- fake full-page reload feeling on navigation
- broken light/dark shell surfaces

## Risks and Watchouts

- The current codebase has many page-local visual overrides. Theme work will uncover more duplication than the initial audit shows.
- State is fragmented both visually and behaviorally. Fixing only the dashboard will not stabilize tray or hotkey behavior.
- Connection fixes must be validated on packaged Windows builds, not only in browser-like local dev mode.
- Tray and shutdown behavior must be validated on real Windows tray builds, because dev-mode behavior can differ.
- If route-shell stabilization is done partially, the app may still remount expensive listeners and keep the “reload” feel.
- If the team keeps hardcoded shell colors during the light theme pass, the UI will regress again quickly.
- If session options are not persisted centrally, new surfaces will keep reintroducing `tun=false` defaults.
- If runtime hardening is skipped at the end, the team will still carry silent crash vectors even after the visible UX is improved.

## Definition of Done

The stabilization effort is complete only when all of the following are true:

1. Connect and disconnect behave consistently in `tun=false` and `tun=true`.
2. The UI never shows fully connected until the runtime is actually usable.
3. Dashboard re-entry preserves truthful visual state for the active connection, including TUN mode.
4. Tray, hotkey, dashboard, and reconnect surfaces all use the same last-known connection options.
5. Sidebar navigation keeps the shell mounted and no longer feels like a page reload.
6. Tray quit reliably exits the app and is distinct from hide-to-tray behavior.
7. Light theme has clear surface hierarchy, readable borders, and legible overlays.
8. Dark theme dropdowns, dialogs, and menus are readable without one-off hacks.
9. Explicit TODO/dead-event debt is removed from production desktop runtime code.
10. The Windows desktop build passes a documented regression matrix before release.
