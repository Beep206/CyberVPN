# CyberVPN Desktop: The "Killer Features" Roadmap

**Architecture:** Tauri v2 (Rust Backend) + React 19 (FSD Frontend)
**Objective:** Surpass Throne/Nekoray by implementing high-demand, enterprise-grade features with a "Newcomer-Friendly" premium UX.
**Methodology:** Incremental implementation using strict Rust safety patterns and hardware-accelerated UI animations.

---

## 🚀 Phase 20: Intelligent Split Tunneling (Per-App Routing)
**Goal:** Allow users to choose specific applications (Games, Browsers) to route through VPN or bypass it, using a simple visual checklist.

### Task 20.1: Rust Process Enumerator (`engine::sys::apps`)
*   **Implementation:** Use the `sysinfo` or `powershell/procfs` calls to scan running processes and installed `.exe` (Windows) or `.desktop` (Linux) files.
*   **Logic:** Create a command `get_installed_apps() -> Vec<AppInfo>` that returns icons, names, and executable paths.
*   **Safety:** Ensure the heavy process scan is offloaded to `tokio::task::spawn_blocking`.

### Task 20.2: Sing-box Rule Mapping
*   **Implementation:** Map selected application paths to Sing-box `route.rules` using the `process_name` field.
*   **UX/UI:** 
    *   Create a "App Routing" page with a sleek search bar.
    *   Visual "Switch" toggles for each app.
    *   **Preset Buttons:** "Gaming Mode" (only games), "Browser Mode" (only browsers), "Privacy Mode" (everything except system updates).

---

## 📡 Phase 21: One-Click Proxy Hotspot (LAN Share Pro)
**Goal:** Share the PC's VPN connection with LG/Samsung TVs, Consoles, and phones via Wi-Fi with zero manual configuration.

### Task 21.1: Local Gateway Logic
*   **Implementation:** Modify the Rust `ConfigGenerator` to automatically enable `allow_lan: true` and set the gateway IP.
*   **Networking:** Implement OS-specific calls to enable IP Forwarding (`sysctl` on Unix, `netsh` on Windows).

### Task 21.2: Hotspot UI Dashboard
*   **UX/UI:** 
    *   A dedicated "Share VPN" tab.
    *   A massive "Start Hotspot" button with a glowing pulse effect.
    *   Display a large QR code and "Password" for the Wi-Fi. 
    *   **Live View:** Show a list of "Connected Devices" (e.g., "LG TV", "iPhone 15") with real-time bandwidth consumption per device.

---

## 🛡️ Phase 22: Smart Kill Switch & Network Self-Healing
**Goal:** Prevent IP leaks and guarantee internet recovery even if the app crashes.

### Task 22.1: The "Sentinel" Watchdog (Rust)
*   **Implementation:** Create a detached background thread in Rust that monitors the `sing-box` process.
*   **Logic:** If the VPN process dies unexpectedly, the Sentinel immediately clears the system proxy and restores original DNS settings.
*   **Firewall Integration:** Use `nftables` (Linux) or `Windows Filtering Platform` (WFP) to block all traffic that does not originate from the `tun0` interface when the Kill Switch is active.

### Task 22.2: User-Friendly Safety UI
*   **UX/UI:** 
    *   A simple "Panic Mode" toggle.
    *   A "Repair My Internet" button in the footer for cases where the OS settings get stuck. It performs a factory reset of network configurations.

---

## ☁️ Phase 23: Cross-Platform Cloud Ecosystem
**Goal:** Sync servers and rules between Desktop, Android TV, and Mobile.

### Task 23.1: CyberVPN Sync API
*   **Implementation:** Integrate a secure backend (Supabase or custom Rust API) to store encrypted user profiles.
*   **Rust Logic:** Implement `push_to_cloud` and `pull_from_cloud` commands using `reqwest` with end-to-end encryption (E2EE) so the server never sees the raw server passwords.

### Task 23.2: One-Click Pairing
*   **UX/UI:** 
    *   "Sync with Mobile" button.
    *   Displays a QR code that, when scanned by the CyberVPN Mobile/TV app, instantly imports all configurations.

---

## 🤖 Phase 24: Intelligent Routing Assistant
**Goal:** Automate complex routing rules using real-time traffic analysis.

### Task 24.1: Traffic Analyzer (Rust)
*   **Implementation:** Parse the Sing-box real-time logs to detect "Connection Timed Out" or "DNS Refused" errors for specific domains.
*   **Logic:** If a site fails repeatedly, the app detects it.

### Task 24.2: The "Magic Fix" UI
*   **UX/UI:** 
    *   A subtle notification pops up: "Site `youtube.com` seems blocked. Fix it?"
    *   Upon clicking "Yes", the app automatically creates a `Proxy` routing rule and restarts the connection.
    *   **Preset Library:** A curated list of "Social Media Pack", "Crypto Pack", "Streamer Pack" that users can enable with one click to auto-generate hundreds of rules.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR ALL KILLER PHASES

As you implement these advanced features, you **MUST** strictly adhere to the following `rust-engineer` and `rust-async-patterns` rules:

1. **Hardware Interaction Safety (`rust-engineer`):** When modifying Windows Firewall (WFP) or network adapters, use the `windows` crate with exhaustive `// SAFETY:` documentation for every FFI call.
2. **Resource Throttling (`rust-async-patterns`):** The "Sentinel" watchdog must have a low CPU footprint. Use `tokio::time::interval` with a reasonable delay (e.g., 500ms) rather than a tight `loop`.
3. **Atomic State Updates (`rust-best-practices`):** When syncing 500+ nodes from the cloud, use a temporary "Staging" store. Only swap it with the live `store.json` if the full download and validation succeed.
4. **Impeccable Error Messages:** Errors like "Process Enumeration Failed" are not allowed. Use `thiserror` to provide actionable advice: "Failed to list apps: Permission denied. Please grant App List permissions in Windows Settings."
