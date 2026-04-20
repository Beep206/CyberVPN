# Desktop Client UX Regression Matrix

## Purpose

This matrix is the release gate for Windows desktop UX-facing builds of `apps/desktop-client`.

A build is not considered shippable until:

1. the automated gate passes;
2. the manual Windows matrix is executed on a packaged installer build;
3. every failed item has attached evidence and an explicit disposition.

## Automated Gate

Run these commands from `apps/desktop-client` unless stated otherwise.

| Step | Command | Expected result |
| --- | --- | --- |
| 1 | `npm run test:unit` | Vitest suite passes |
| 2 | `npm run test:rust` | Rust tray/shutdown contract tests pass |
| 3 | `npm run build` | Production frontend build passes |
| 4 | `PATH="$HOME/.cargo/bin:$PATH" npm exec tauri build -- --runner cargo-xwin --target x86_64-pc-windows-msvc --no-bundle` | Windows x64 executable builds |
| 5 | `PATH="$HOME/.cargo/bin:$PATH" npm exec tauri build -- --runner cargo-xwin --target x86_64-pc-windows-msvc --config '{"bundle":{"targets":["nsis"]}}'` | Windows NSIS installer builds |

## Manual Windows Release Checklist

- Installer launches and upgrades an existing install without wiping profiles or subscriptions.
- App opens without a console window during normal non-TUN connect.
- App opens without a console window during TUN connect.
- `Dashboard` connect button reaches truthful `Connecting` / `Connected` / `Disconnecting` / `Disconnected` states.
- `Connected` is only shown after real traffic egress is verified.
- Disconnect from dashboard works after both `tun=false` and `tun=true`.
- Switching routes while connected does not feel like a full reload and does not reset shell chrome.
- Returning to `Dashboard` preserves truthful state for the active profile and TUN toggle.
- Tray `Show`, `Hide to Tray`, `Connect`, `Disconnect`, and `Quit` all behave correctly.
- Global shortcut reconnect uses the same last-used profile, TUN mode, and system-proxy settings.
- Light theme surfaces are readable and do not use harsh white/gray collisions.
- Dark theme overlays, dropdowns, dialogs, and toast surfaces are readable.
- `Logs` page can export usable diagnostics after a forced connection failure.

## Manual Acceptance Matrix

| ID | Surface | Scenario | Expected result | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| UX-01 | Dashboard | Connect with `tun=false` | Status progresses cleanly to `Connected`; external IP changes or proxy path is verifiably active |  | Pending |
| UX-02 | Dashboard | Disconnect after `tun=false` connect | Button transitions through `Disconnecting`; runtime stops; state returns to `Disconnected` |  | Pending |
| UX-03 | Dashboard | Connect with `tun=true` | TUN path connects without crashing; truthful final state; external IP changes |  | Pending |
| UX-04 | Dashboard | Disconnect after `tun=true` connect | No stuck state; repeat click does not wedge UI |  | Pending |
| UX-05 | Dashboard | Start connect and click disconnect while still connecting | UI does not wedge; final state is truthful |  | Pending |
| UX-06 | Dashboard | Leave dashboard while connected and return | TUN toggle, active profile, and connection status are still truthful |  | Pending |
| UX-07 | Navigation | Switch across at least five sections while connected | Shell stays mounted; no hard reload feel; no state wipe in titlebar/sidebar |  | Pending |
| UX-08 | Tray | Right-click tray and choose `Show App` while hidden | Existing session is restored; no duplicate window |  | Pending |
| UX-09 | Tray | Right-click tray and choose `Hide to Tray` | Main window hides; app remains running |  | Pending |
| UX-10 | Tray | Right-click tray and choose `Connect` from disconnected state | Uses last saved connection options |  | Pending |
| UX-11 | Tray | Right-click tray and choose `Disconnect` from connected state | Disconnects the live session and updates dashboard truthfully |  | Pending |
| UX-12 | Tray | Right-click tray and choose `Quit` | App fully exits; tray icon disappears; relaunch starts cleanly |  | Pending |
| UX-13 | Hotkey | Use global shortcut from disconnected state | Reconnect uses last profile and last session options |  | Pending |
| UX-14 | Hotkey | Use global shortcut from connected state | Disconnects the active session cleanly |  | Pending |
| UX-15 | Theme | Switch to `light` | Surfaces remain soft, readable, and clearly separated |  | Pending |
| UX-16 | Theme | Switch to `dark` | Dropdowns, dialogs, and overlays stay legible |  | Pending |
| UX-17 | Overlays | Open language menu, dialogs, selects, and logs support panel | Overlay surfaces use consistent tokens and readable contrast |  | Pending |
| UX-18 | Logs | Reproduce a connection failure and capture diagnostics | Snapshot, timeline, and tails are available and copyable |  | Pending |
| UX-19 | Installer | Upgrade from previous desktop build | Profiles, subscriptions, and persisted session options survive upgrade |  | Pending |
| UX-20 | Shell | Close main window via titlebar | App hides to tray, does not silently quit |  | Pending |

## Runtime Hardening Audit

Track desktop runtime panic points and dead branches here. Each item must be marked as one of:

- `removed`
- `reworked`
- `documented invariant`
- `pending`

| Area | Item | Status | Notes |
| --- | --- | --- | --- |
| Tray lifecycle | Shared async shutdown path replaces tray-local blocking exit flow | reworked | Completed in stabilization Phase 3 |
| Tray icon setup | Missing default icon no longer relies on `unreachable!` | reworked | Completed in stabilization Phase 3 |
| Reconnect eventing | `request-reconnect` has a live consumer or is deleted | removed | No emitter/listener remains; reconnect flows use `connect_with_last_options` directly |
| IPC time handling | Subscription timestamp write avoids panic on clock skew | reworked | Returns `AppError::System` instead of panicking |
| Diagnostics runtime | Avoidable production `unwrap()` removed or classified | reworked | Reqwest client init failure now degrades probe result instead of panicking |
| Remote control runtime | Background server task panic path removed or classified | reworked | Axum task exit is logged to diagnostics instead of panicking |
| Sync runtime | Argon parameter construction panic path removed or classified | reworked | Argon2 parameter init is validated and returned as `AppError::System` |
| Config generation | Avoidable `serde_json::to_value(...).unwrap()` paths removed or classified | reworked | Stealth transport fragments now build JSON objects without fallible serialization |
| Stats runtime | Usage history path/session flush no longer panics on app-dir lookup or poisoned mutex | reworked | Corrupted usage history is rotated, logged, and recreated cleanly |
| App startup build path | Tauri app build failure no longer panics before run loop | reworked | Build failure is persisted through lifecycle panic marker and printed to stderr |
| Manager regex literals | Static traffic/failure regex compilation remains a documented invariant | documented invariant | Hard-coded literals compile at startup and are covered by build/test gate |
| Discovery regex literals | Static LAN discovery regex compilation remains a documented invariant | documented invariant | Hard-coded literals compile at startup and are covered by build/test gate |

## Release Sign-Off

| Role | Name | Date | Result | Notes |
| --- | --- | --- | --- | --- |
| Engineering |  |  |  |  |
| QA / Manual validation |  |  |  |  |
| Product sign-off |  |  |  |  |
