# Phase 27 Start: Integrated DNS Sinkhole & Privacy Shield

Excellent work on the Post-Quantum integration! CyberVPN is now mathematically future-proof. Now, we move to **Phase 27: Integrated DNS Sinkhole & Privacy Shield**. 

The goal is to provide network-level protection against advertisements, trackers, and malicious domains (similar to Pi-hole or AdGuard) directly within the CyberVPN client. This not only enhances privacy but also reduces data consumption and increases browsing speed.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 27.1: Blocklist Engine (Rust Backend)
We need to fetch, store, and apply massive domain blocklists to the proxy engine.
*   **Implementation:** Create `engine::sys::adblock.rs`.
*   **Source:** Implement an async task to download high-quality blocklists (e.g., StevenBlack's Hosts or OISD) via `reqwest`.
*   **Optimization:** Since blocklists can contain 100,000+ domains, you **must not** load them all as raw strings into the memory every time. 
*   **Sing-box Integration:** Convert the fetched blocklists into Sing-box's native **`rule_set`** format (JSON or Binary) and save them to the `app_data_dir`. Update `config.rs` to include these `rule_set` references in the routing logic with an "always block" action.

### Task 27.2: Live Tracker Monitor (Rust Backend)
*   **Implementation:** Enhance the `ProcessManager` log sniffer.
*   **Logic:** Detect when Sing-box blocks a connection based on our Privacy Shield rules.
*   **Stats:** Implement an atomic counter (`Arc<AtomicU64>`) to track:
    *   Total threats blocked.
    *   Blocked domains by category (Ads, Tracking, Social).
*   **Events:** Emit a `tracker-blocked` event to the UI whenever a real-time block occurs.

### Task 27.3: "Privacy Shield" Dashboard (React Frontend)
Create a UI that visually demonstrates the value of the protection.
*   **Location:** Dashboard (Primary Widget) and a new "Privacy Shield" tab.
*   **Features:**
    *   **The Shield Toggle:** A large, elegant toggle to enable/disable protection.
    *   **Live Counter:** A high-impact "shimmering" counter showing the number of trackers blocked.
    *   **Activity Feed:** A scrolling "Security Log" showing recently blocked domains (e.g., `google-analytics.com`, `doubleclick.net`) with their respective icons.
    *   **Protection Levels:** Presets for "Standard" (Ads/Malware) and "Strict" (Ads/Malware/Social/Tracking).

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. High-Performance File I/O (`rust-async-patterns`)
*   **Rule:** Downloading and parsing a 5MB+ hosts file is a **heavy blocking operation**.
*   **Implementation:** You MUST use `tokio::task::spawn_blocking` for the parsing logic. Use `tokio::fs` for all file writes. 
*   **Atomic Saves:** Use the "Staging" pattern (Phase 23) to ensure the `adblock.db` is never corrupted during a download interruption.

### 2. Efficient Memory Usage (`rust-best-practices`)
*   **Rule:** Avoid `String` allocations when parsing host files. Use `line.split_whitespace()` and `collect` into a `HashSet<&str>` or directly stream into the JSON builder to minimize peak RAM usage.

### 3. Thread-Safe Atomic Counters (`rust-engineer`)
*   **Rule:** Do not use a `Mutex` for the "Blocked Count" stats if a simple `AtomicU64` suffices. Atomics are much faster for high-frequency updates (like DNS logs).

### 4. Descriptive Error Handling
*   Blocklist updates can fail due to DNS issues or server downtime. 
*   **Rule:** Use `AppError::System` to provide a clear UI message: "Failed to update Privacy Shield databases. Check your internet connection."

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 27.1 (Blocklist Engine)**. Specifically, how will you transform a standard "Hosts" file format into a Sing-box compatible `rule_set` without exhausting the device's RAM? Do not write the full code until I approve the plan.