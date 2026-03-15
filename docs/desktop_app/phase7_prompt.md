# Phase 7 Start: UI Polish & Desktop Capabilities

Outstanding work on Phase 6! Your use of iterator chains for the routing rules and correct borrowing principles (`&[ProxyNode]`) was perfectly idiomatic and highly performant. The foundation is now completely solid.

We are now moving on to **Phase 7: UI Polish & Desktop Capabilities**. Our goal here is to elevate the application from a "web app running in a window" to a true, premium, native-feeling desktop experience.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 7.1: System Tray Integration
We need the app to live in the system tray, allowing it to run in the background without cluttering the taskbar.
*   **Rust Backend:** 
    *   Configure Tauri to use the `tauri-plugin-tray`.
    *   Create a system tray menu with options: `Show App`, `Connect / Disconnect` (toggle based on state), and `Quit`.
    *   Implement event handlers for these menu items in Rust. If `Quit` is clicked, ensure you gracefully call your `ProcessManager::stop()` before exiting the application to prevent zombie `sing-box` processes.
*   **Window Management:** Modify the `tauri.conf.json` or main Rust setup to intercept the window close event (`app.on_window_event`). When the user clicks the "X" on the window, hide the window instead of exiting the app.

### Task 7.2: Global Hotkeys
Users should be able to quickly toggle their VPN connection without opening the app.
*   **Rust Backend:**
    *   Integrate `tauri-plugin-global-shortcut`.
    *   Register a global hotkey (e.g., `CmdOrControl+Shift+C`).
    *   When triggered, check the current `AppState::status`. If disconnected, connect using the currently selected/active profile. If connected, disconnect.

### Task 7.3: Deep Linking (Custom URI Scheme)
We want users to be able to click a `throne://vless?...` link in their browser and have our app automatically open and parse it.
*   **Rust Backend:**
    *   Use `tauri-plugin-deep-link` (or equivalent supported mechanism for Tauri v2).
    *   Register a custom URI scheme `throne://`.
    *   Set up an event listener in Rust that intercepts deep link invocations. When a link is received, pass it to your existing `parser::parse_link` logic, add it to the store, and optionally emit an event to the frontend to refresh the profile list and show a success toast.

### Task 7.4: Frameless Window & Custom Titlebar
To match our cyberpunk/neon UI, the default OS titlebar looks out of place.
*   **Configuration:** Set `"decorations": false` in `tauri.conf.json`.
*   **Frontend UI:** Create a new `Titlebar` widget in React.
    *   It should sit at the very top of `Layout.tsx`.
    *   It must have a drag region (`data-tauri-drag-region`).
    *   It should implement custom Minimize, Maximize, and Close buttons using Tauri's window API (`getCurrentWindow().minimize()`, etc.).

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-async-patterns` rules:

### 1. Graceful Shutdown & Zombie Prevention (`rust-async-patterns`)
*   When integrating the Tray "Quit" button or handling the physical `Exit` event of the application, you must ensure the Sing-box child process is cleanly terminated.
*   Use your `ProcessManager::stop()` method. Note that `stop()` is `async`, but Tauri's exit handlers are often synchronous or run in a specific context. You may need to use `tauri::async_runtime::block_on` or spawn a detached task that waits for the process to exit before calling `std::process::exit(0)`.

### 2. Plugin Initialization (`rust-engineer`)
*   Tauri v2 relies heavily on plugins for features like Tray and Hotkeys. Ensure you add them via `cargo add tauri-plugin-tray` etc., and initialize them properly in your `tauri::Builder` chain in `lib.rs` (or `main.rs`).
*   Handle initialization errors gracefully; do not `.unwrap()` if a hotkey fails to register (e.g., if another app is already using it). Log a warning instead.

### 3. State Access in Handlers (`rust-async-patterns`)
*   When writing closures for Tray menus or Hotkeys, you will need to access the `AppState`. Use `app.state::<AppState>()` to retrieve it.
*   Remember the rule from Phase 4: Do not hold the `status.read().await` lock across `.await` points when triggering connections/disconnections from the hotkey handler.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 7.1 (System Tray Integration)**. Tell me which Tauri v2 plugins you will use and how you will handle the window close interception vs actual application quit. Do not write the full code until I approve the plan.