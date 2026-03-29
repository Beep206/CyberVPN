# Phase 28 Start: Context-Aware Security Profiles (SSID Automation)

Incredible progress on the Privacy Shield! Now, we are making CyberVPN "Smart." Phase 28 introduces **Context-Aware Security Profiles**. 

The goal is to eliminate manual toggling. The application will "recognize" Wi-Fi networks: it should stay invisible at Home, but automatically activate the highest level of protection (Stealth Mode + Kill Switch) the moment the user connects to a public Wi-Fi at a cafe or airport.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 28.1: Wi-Fi SSID Monitor (Rust Backend)
We need a cross-platform way to detect the current network name (SSID) and monitor changes.
*   **Implementation:** Create `engine::sys::net_monitor.rs`.
*   **Logic:**
    *   **Windows:** Use the `windows` crate to call the `WlanQueryInterface` API or parse `netsh wlan show interfaces`.
    *   **Linux:** Use `nmcli` or parse `/proc/net/wireless`.
    *   **macOS:** Use the `airport` CLI or `CoreWLAN` framework.
*   **Watchdog:** Implement a background `tokio::spawn` task that checks the current SSID every 10 seconds. If the SSID changes, emit a Tauri event `network-changed`.

### Task 28.2: Trusted Networks Logic (Rust Backend)
*   **Data Structure:** Update `AppDataStore` to include `pub network_rules: HashMap<String, NetworkProfile>`.
*   **NetworkProfile:** `{ auto_connect: bool, stealth_required: bool, kill_switch_required: bool, icon_type: String }`.
*   **Automation Engine:** When a `network-changed` event occurs:
    1. Look up the new SSID in the rules.
    2. If it's a "Trusted" network (e.g., Home) -> Prompt to disconnect or switch to "Direct" mode.
    3. If it's an "Unknown" or "Untrusted" network -> Automatically trigger `connect_profile` with maximum security settings.

### Task 28.3: "Smart Connect" Management UI (React Frontend)
Create a UI that feels like an intelligent concierge.
*   **Location:** New "Automation" tab or a widget on the Dashboard.
*   **Features:**
    *   **Current Status Card:** Shows the current SSID with a "Trust this Network" button.
    *   **Network History:** A list of previously visited Wi-Fi networks with customizable icons (House, Office, Coffee cup).
    *   **Master Toggle:** "Enable Intelligent Automation" switch with a neon "Brain" icon.
    *   **Visual Feedback:** Use `framer-motion` to show a "Network Scanning" radar animation when the app is detecting the environment.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Robust FFI for Wlan API (`rust-engineer`)
*   **Rule:** Interacting with the Windows WLAN API requires complex `unsafe` calls. 
*   **Implementation:** You MUST encapsulate the raw pointers and handles in a safe wrapper. Use `// SAFETY:` comments to justify that we are checking for null handles and properly freeing the `WLAN_INTERFACE_INFO_LIST` using `WlanFreeMemory`.

### 2. Debounced Event Emission (`rust-async-patterns`)
*   Network status can flutter (e.g., during a weak signal). 
*   **Rule:** Do not emit `network-changed` 10 times in a row. Implement a "Debounce" or "Change Detection" logic in Rust: only emit the event and trigger automation if the SSID remains the same for at least 3 seconds after a change is detected.

### 3. Graceful Fallback for Ethernet (`rust-best-practices`)
*   Users might be on an Ethernet cable (no SSID). 
*   **Rule:** Handle the "No Wi-Fi" state gracefully. Treat Ethernet as a "Trusted Wired Connection" by default, or allow the user to configure it. Never return an error just because a Wi-Fi adapter is missing.

### 4. Semantic Error Handling
*   Wlan APIs often fail if the service is disabled. 
*   **Rule:** Use `AppError::System` to provide actionable advice: "Wi-Fi monitoring disabled. Please ensure the 'WLAN AutoConfig' service is running in Windows Services."

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 28.1 (SSID Monitor)**. Specifically, how will you implement the cross-platform abstraction for SSID detection? Will you use a crate or raw OS commands? Do not write the full code until I approve the plan.