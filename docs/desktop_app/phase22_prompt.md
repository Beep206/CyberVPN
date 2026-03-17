# Phase 22 Start: Smart Kill Switch & Network Self-Healing

Incredible work on Phase 21! The Proxy Hotspot feature is a game-changer. Now, we are moving to **Phase 22: Smart Kill Switch & Network Self-Healing**. This is the ultimate security feature that prevents IP leaks if the VPN connection drops and ensures the user's internet is "repaired" even after unexpected app crashes.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 22.1: The "Sentinel" Watchdog & WFP/nftables Integration (Rust)
We need a robust background system that blocks all non-VPN traffic when active.
*   **Implementation:** Create a new Rust module `engine::sys::sentinel.rs`.
*   **The Logic:**
    *   **Windows:** Use the `windows` crate to interact with the **Windows Filtering Platform (WFP)**. Create a filter that blocks all outgoing traffic on the physical network interface except for the traffic destined for the VPN server IP and the `tun0` interface.
    *   **Linux:** Use `nftables` or `iptables` to create similar drop rules.
*   **Self-Healing:** Implement a `repair_network()` command that performs a "Factory Reset" of the OS network stack (clears sysproxy, deletes persistent WFP filters, resets DNS to 8.8.8.8).

### Task 22.2: Process Health Monitor (Async)
*   **Watchdog Task:** Modify `ProcessManager` to include a background `tokio::spawn` loop that checks `is_running()` every 500ms.
*   **Action:** If the `sing-box` process dies while "Kill Switch" is enabled, the Watchdog must immediately trigger the Sentinel to block all traffic and notify the UI.

### Task 22.3: "Safety Center" UI (React)
Create a UI that radiates security and trust.
*   **Location:** `src/pages/Security/index.tsx`.
*   **Features:**
    *   **Panic Button:** A high-visibility "Kill Switch" toggle with a shield icon.
    *   **Leak Protection Status:** Show visual indicators for "DNS Leak Protected", "IPv6 Leak Protected", and "Kill Switch Active".
    *   **The "Repair" Tool:** A dedicated card for "Network Self-Healing". If the user reports "My internet is broken", this button will call the Rust `repair_network()` command.
    *   **Animations:** Use `framer-motion` to animate a protective "Shield" expanding over the Dashboard when Kill Switch is active.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Atomic Cleanup via Drop & Shutdown Signals (`rust-async-patterns`)
*   **CRITICAL:** If the app is closed, the Kill Switch rules must be removed unless "Permanent Kill Switch" is enabled.
*   **Rule:** Implement a `SentinelGuard` struct that removes firewall rules in its `Drop` implementation. Use `tauri::RunEvent::Exit` to ensure cleanup code runs.

### 2. Low-Overhead Polling (`rust-async-patterns`)
*   The health monitor must be extremely lightweight. Use `tokio::time::interval` and avoid any heavy allocations or complex logic inside the 500ms check loop.

### 3. FFI Safety & Documentation (`rust-engineer`)
*   Interacting with WFP (Windows Filtering Platform) involves complex `unsafe` Win32 calls.
*   **Rule:** You MUST use the `windows` crate. Every `unsafe` block must have a `// SAFETY:` comment explaining why the pointers and handles are valid and that we are not causing a kernel panic.

### 4. Descriptive "System" Errors (`rust-best-practices`)
*   Firewall operations often fail due to "Permission Denied". 
*   **Rule:** Do not return generic error strings. Use `thiserror` to define `AppError::FirewallError(String)` and include specific advice: "Failed to enable Kill Switch. Please ensure you have Administrator privileges and no other antivirus is blocking WFP."

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 22.1 (Sentinel/Firewall Logic)**. Specifically, which WFP APIs or `nftables` commands do you plan to use? Do not write the full code until I approve the plan.