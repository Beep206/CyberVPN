# Phase 21 Start: One-Click Proxy Hotspot (LAN Share Pro)

Congratulations on completing Phase 20! The Split Tunneling feature is a massive leap forward. Now, we are implementing our second "Killer Feature": **One-Click Proxy Hotspot**. This will allow users to turn their PC into a secure gateway for devices that don't support VPNs natively, like LG/Samsung Smart TVs, PlayStations, or Xboxes.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 21.1: Local Gateway & IP Forwarding Logic (Rust)
We need to configure the OS to allow other devices to route traffic through the PC.
*   **Implementation:** Create a new Rust module `engine::sys::net.rs`.
*   **IP Forwarding:** 
    *   **Windows:** Execute `netsh interface ipv4 set interface "Wi-Fi" forwarding=enabled` (and for other active adapters).
    *   **Linux:** Execute `sysctl -w net.ipv4.ip_forward=1`.
*   **Local Discovery:** Implement a command `get_lan_connection_info() -> Result<LanInfo, AppError>` that returns the PC's current LAN IP address and the active Proxy Port.
*   **Config Integration:** Update `generate_singbox_config` to ensure that when "LAN Share" is enabled, the `mixed` inbound listens on `0.0.0.0` instead of `127.0.0.1`.

### Task 21.2: Hotspot Dashboard UI (React)
Create a high-impact, futuristic UI for the hotspot feature.
*   **Location:** `src/pages/Hotspot/index.tsx`.
*   **Features:**
    *   **The Pulse:** A massive, glowing "Start Sharing" button with a slow CSS/Framer-Motion pulse effect.
    *   **Connection Guide:** Display the "Proxy Server IP" and "Port" in large, readable font.
    *   **Auto-QR:** Generate a QR code that encodes the proxy settings (some mobile apps can scan this to auto-configure).
    *   **Active Clients:** Implement a real-time list of "Connected Devices". 
        *   *Hint:* In Rust, use `arp -a` or parse `/proc/net/arp` to find devices in the same subnet.
    *   **Traffic Stats:** Show real-time bandwidth consumption *specifically* for the LAN-shared traffic if possible.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Elevated Command Execution (`rust-engineer`)
*   Changing IP forwarding requires Administrator/Root privileges. 
*   **Rule:** Reuse your `is_elevated()` logic from Phase 5. If the user tries to start the Hotspot without Admin rights, return `AppError::ElevationRequired` and show a "Request Admin Rights" button.
*   Use `std::process::Command` safely. Never pass raw user input into shell commands to prevent injection.

### 2. Async Discovery & Polling (`rust-async-patterns`)
*   Scanning for connected LAN devices (ARP scan) is a periodic task. 
*   **Rule:** Use `tokio::spawn` with a `tokio::time::interval` to refresh the device list every 5-10 seconds. Ensure the loop terminates cleanly when the user leaves the Hotspot page or stops sharing.

### 3. Cross-Platform Abstraction (`rust-best-practices`)
*   Define a trait `GatewayManager` with methods `enable_forwarding()` and `disable_forwarding()`.
*   Implement this trait separately for Windows and Linux using `#[cfg(target_os = ...)]`. This keeps the main logic clean and testable.

### 4. Zero-Panic Parsing (`rust-engineer`)
*   When parsing the output of `arp -a` or system network commands, use `filter_map` and regular expressions safely. **Do not use `.unwrap()`** on string splitting; the output format of `netsh` or `ip` commands can vary between OS versions.

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 21.1 (Gateway Logic)**. Specifically, how will you handle the different command-line tools for Windows (`netsh`) and Linux (`sysctl/iptables`)? Do not write the full code until I approve the plan.