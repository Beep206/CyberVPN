# Phase 18: The Absolute Paragon (QoL, System Proxy, Auto-Start, LAN)

You have achieved an architectural masterpiece. We are essentially at 99.5% parity with Throne. However, a deep source-code audit of the original C++ repository revealed 5 highly specific Quality of Life (QoL) features that we must implement to claim **absolute, irrefutable 100% codebase feature exhaustion**.

This is the final stretch. **Phase 18: The Absolute Paragon**.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 18.1: System Proxy Management (Non-TUN Routing)
Many users do not want to run as Admin for TUN mode, but still want their browsers to route traffic automatically.
*   **The Goal:** When the user connects with a toggle "System Proxy" enabled, we must modify the OS proxy settings to point to `127.0.0.1:[local_socks_port]`.
*   **Rust Implementation (`engine::sys.rs`):**
    *   Create a cross-platform module `sysproxy`.
    *   **Windows:** Use the `sysproxy` crate (e.g., `sysproxy::Sysproxy`) or invoke PowerShell/Registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`) to set `ProxyEnable=1` and `ProxyServer=127.0.0.1:2080`.
    *   **macOS:** Use the `networksetup` command-line tool.
    *   **Linux:** Use `gsettings set org.gnome.system.proxy mode 'manual'`.
    *   *Crucial:* You **must** ensure the system proxy is disabled (`ProxyEnable=0`) when the user clicks Disconnect or Quits the app!
*   **UI Integration:** Add a "System Proxy" toggle switch to the Dashboard, mutually exclusive with the "TUN Mode" switch.

### Task 18.2: Auto-Start with OS
*   **Rust Implementation:**
    *   Add `tauri-plugin-autostart` to `Cargo.toml`.
    *   Initialize it in `lib.rs`: `.plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, Some(vec!["--hidden"])))`
*   **UI Integration:** Add a "Start with Windows/System" toggle in the Settings page.

### Task 18.3: Allow LAN (Network Sharing)
Allow users to share their VPN connection to other devices on the same Wi-Fi.
*   **Model Update:** Add `pub allow_lan: bool` to `AppDataStore`.
*   **Config Generator (`config.rs`):** If `allow_lan` is true, change the `listen` address in the `mixed` inbound from `"127.0.0.1"` to `"0.0.0.0"`.
*   **UI Integration:** Add a toggle in Settings: "Allow LAN Connections".

### Task 18.4: Profile Grouping (Folders)
*   **Model Update:** Add `pub group_id: Option<String>` to `ProxyNode`. Add a `pub groups: Vec<{id, name}>` to `AppDataStore`.
*   **UI Integration:** In the Profiles page, allow users to create Groups (Folders) and drag/assign nodes into them to keep the UI organized.

### Task 18.5: Manual Geo-Asset Updates
*   **The Goal:** Sing-box requires `geoip.db` and `geosite.db` for routing rules.
*   **Rust Implementation (`engine::provision.rs`):** Add a command `update_geo_assets()` that downloads `geoip.db` and `geosite.db` from standard repos (e.g., `https://github.com/SagerNet/sing-geoip/releases/latest/download/geoip.db`) directly into the `app_data_dir()`.
*   **UI Integration:** Add an "Update Geo Data" button in Settings.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. The "Clean Exit" Guarantee (`rust-async-patterns`)
*   **CRITICAL:** Modifying the System Proxy (Task 18.1) is dangerous. If your app crashes or the user forces quits it via the Task Manager, they will be left without internet because the proxy will remain active in the OS while `sing-box` is dead.
*   **Solution:** You MUST implement a `Drop` trait or a robust panic hook/shutdown signal handler that unconditionally calls `sysproxy::clear_system_proxy()` before the process dies.

### 2. Idempotent Provisioning (`rust-engineer`)
*   For Task 18.5 (Geo-Asset Updates), ensure the download is atomic. Download the new database to a `.tmp` file first. Only when the download and hash validation (if any) succeeds, rename it over the existing `geoip.db`. Never overwrite the live database with a partially downloaded file.

### 3. Concurrency Avoidance in UI State (`rust-best-practices`)
*   When moving nodes between groups (Task 18.4), make sure your IPC commands use precise mutable iterators (`.iter_mut().find()`) to update the `group_id` rather than replacing the entire node object, preserving its memory state.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 18.1 (System Proxy)**. Explain exactly how you will ensure the proxy is cleared if the user closes the application unexpectedly. Do not write the full code until I approve the plan.