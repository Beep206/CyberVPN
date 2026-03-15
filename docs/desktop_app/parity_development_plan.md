# Throne Feature Parity: Extended Development Plan

**Target Agent:** Gemini 3.1 PRO (Antigravity Environment)
**Context:** This plan continues from the successful completion of Phases 1-9. The core VPN engine, TUN interface, basic UI, and CI/CD are fully operational.
**Goal:** Achieve 100% feature parity with the original Qt-based Throne/Nekoray client by implementing advanced protocols, subscription management, native UAC elevation, and power-user customization.

---

## 🌐 Phase 10: Expanded Protocol Support (The Parser Matrix)

**Objective:** Extend the `engine::parser` module to support the vast array of protocols provided by Sing-box, beyond just VLESS.

*   **Task 10.1: VMess & Shadowsocks Parsing**
    *   **VMess:** Parse `vmess://` links. Note that VMess links are typically base64 encoded JSON strings (unlike VLESS which uses standard URI components).
    *   **Shadowsocks (SS):** Parse `ss://` links. Handle both the legacy Base64 format and the newer SIP002 format (e.g., `ss://user:pass@host:port#name`).
*   **Task 10.2: Modern Protocols (Trojan, Hysteria2, TUIC)**
    *   **Trojan:** Parse `trojan://` links. Similar structure to VLESS.
    *   **Hysteria2:** Parse `hy2://` or `hysteria2://` links. Extract specific parameters like `obfs`, `obfs-password`, `sni`, and `insecure`.
    *   **TUIC:** Parse `tuic://` links.
*   **Task 10.3: Config Generator Alignment**
    *   Update `engine::config::generate_singbox_config` to correctly map the newly parsed fields (e.g., Hysteria2 obfuscation settings, VMess alterId, Shadowsocks encryption methods) into their respective Sing-box outbound JSON structures.
*   **Task 10.4: Automated Testing**
    *   Write exhaustive unit tests in `engine::parser::tests` covering valid and invalid inputs for ALL new protocols. Use real-world examples (anonymized) from standard proxy providers.

---

## 📡 Phase 11: Subscription Management Engine

**Objective:** Allow users to import lists of dozens or hundreds of proxies via a single URL that automatically syncs.

*   **Task 11.1: Backend Data Modeling**
    *   Update `AppDataStore` to include a `subscriptions: Vec<Subscription>` field.
    *   Create a `Subscription` struct: `{ id, name, url, auto_update: bool, last_updated: timestamp }`.
    *   Add a `subscription_id` field to the `ProxyNode` struct to track which nodes belong to which subscription.
*   **Task 11.2: The Fetch & Decode Engine**
    *   Create a new module `engine::subscription`.
    *   Implement an async function that uses `reqwest` to fetch the URL.
    *   Implement decoding: Most subscription URLs return a Base64 encoded string. Decode it. The result is usually a plaintext list of `vless://`, `vmess://`, etc., separated by newlines.
    *   Pass each line to the existing `parser::parse_link` function.
*   **Task 11.3: Store Sync Logic**
    *   Implement logic to cleanly merge new nodes from a subscription: remove old nodes belonging to that `subscription_id` and insert the new ones, preserving the user's selected `active_id` if possible.
*   **Task 11.4: Frontend UI (Subscriptions Page)**
    *   Create `src/pages/Subscriptions/index.tsx`.
    *   Build a UI to add a URL, trigger a manual "Update Now", and view how many nodes belong to each subscription.

---

## 🔐 Phase 12: Seamless Windows UAC Elevation

**Objective:** Eliminate the need for the user to manually restart the entire application as Administrator when toggling TUN mode on Windows.

*   **Task 12.1: Windows ShellExecuteExW Integration**
    *   In `engine::manager::ProcessManager::start`, modify the Windows `#[cfg(target_os = "windows")]` block.
    *   Instead of returning `AppError::ElevationRequired`, use the `windows` crate (specifically `ShellExecuteExW`) to launch `sing-box.exe` with the `runas` verb.
    *   *Note:* This will natively trigger the yellow Windows UAC prompt. If the user clicks "Yes", the child process starts as Admin. If they click "No", `ShellExecuteExW` fails and you return a user-friendly error.
*   **Task 12.2: Process Handle Management for Elevated Children**
    *   When a process is launched via `ShellExecuteExW`, capturing `stdout`/`stderr` via standard pipes is highly complex (often requiring named pipes with custom security descriptors).
    *   *Alternative/Simpler approach:* For elevated TUN execution, configure Sing-box to write logs to a file (`app_dir().join("sing-box.log")`) instead of `stdout`, and have your Tokio background task tail that log file to feed the React UI.

---

## 📱 Phase 13: QR Code Integration (Sharing & Scanning)

**Objective:** Make sharing and importing configurations frictionless, just like mobile clients.

*   **Task 13.1: Generate QR Codes (Export)**
    *   Add a dependency like `qrcode.react` to the React frontend.
    *   In the `Profiles` page, add a "Share" button to each node card.
    *   Clicking it opens a Modal displaying the QR code of the raw share link (e.g., `vless://...`).
*   **Task 13.2: Scan QR from Screen (Import)**
    *   Integrate a Rust crate like `rxing` (or `zbar-rust`) and `image` to scan the user's screen.
    *   Create a Tauri command `scan_screen_for_qr()`.
    *   Rust backend captures a screenshot (using `xcap` or `enigo`), searches for a QR code, decodes the string, passes it to the parser, and adds the new node.

---

## 🛠️ Phase 14: Power-User "Raw Config" Mode

**Objective:** Cater to extreme power users who want to write Sing-box JSON manually, bypassing our visual generators.

*   **Task 14.1: UI Editor Integration**
    *   Install `@monaco-editor/react` (the editor powering VS Code).
    *   Create a "Custom Config" tab in the Settings or Profiles page.
*   **Task 14.2: Execution Bypass**
    *   Update `AppDataStore` to store an optional `custom_config_raw: String`.
    *   Update `connect_profile`. If the user has toggled "Use Custom Config", bypass `generate_singbox_config` entirely. Save `custom_config_raw` directly to `run.json` and start the engine.
*   **Task 14.3: JSON Validation**
    *   Implement a Tauri command `validate_json` that uses `serde_json::from_str` to verify the user's raw text is valid JSON before attempting to start the process, preventing cryptic crashes.