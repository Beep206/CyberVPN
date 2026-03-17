# Phase 24 Start: Intelligent Routing Assistant (The "Magic Fix")

Exceptional work on the Cloud Sync ecosystem! We are now at the final implementation phase of our "Killer Features" roadmap: **Phase 24: Intelligent Routing Assistant**. 

The goal is to make routing "invisible" for the average user. Instead of manually writing complex rules, the app will monitor traffic logs, detect blocked sites, and offer a one-click "Magic Fix."

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 24.1: Traffic Failure Detector (Rust Backend)
We need to "sniff" the proxy engine's logs to identify connection failures in real-time.
*   **Implementation:** Extend `engine::manager::ProcessManager`.
*   **Log Analysis:** Inside the existing log-reading loop, add logic to scan for keywords like `connection reset`, `timeout`, or `dns failure`. 
*   **Domain Extraction:** Use a `lazy_static` Regex to extract the domain name from the failed log line.
*   **Tracking Logic:** Use a thread-safe `HashMap` (e.g., `Arc<Mutex<HashMap<String, u32>>>`) to count failures per domain.
*   **Event Emission:** When a specific domain fails more than 3 times in a short window, emit a Tauri event `routing-suggestion` with the payload `{ domain: "youtube.com", reason: "Connection Timeout" }`.

### Task 24.2: Automated Rule Generator (Rust Backend)
*   **Implementation:** Create a command `apply_routing_fix(domain: String, action: String, app: AppHandle) -> Result<(), AppError>`.
*   **Logic:** This command should automatically create a new `RoutingRule` (e.g., matching the keyword or domain) and save it to the store. 
*   **Live Reload:** Once saved, trigger a `connect_profile` restart (or just a config rewrite) so the fix takes effect immediately.

### Task 24.3: The "Magic Fix" UI (React Frontend)
Create a UI that feels like an intelligent assistant.
*   **Notification:** When the `routing-suggestion` event is received, show a beautiful, non-intrusive "Cyber-Toast" in the corner: *"Site [domain] seems blocked. Route through VPN?"*
*   **Quick Actions:** Provide two buttons on the toast: "Yes, Fix It" and "Ignore".
*   **Preset Library:** In the `Routing` page, add a "Preset Gallery" with cards like:
    *   **"Social Media Pack"** (Twitter, Meta, Instagram rules).
    *   **"Developer Pack"** (Docker, GitHub, OpenAI rules).
    *   **"Streamer Pack"** (YouTube, Netflix, Twitch).
    *   Clicking a card bulk-inserts the corresponding rules into the store.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. High-Performance Log Scanning (`rust-best-practices`)
*   **Rule:** Do not create a new `Regex` object for every log line. Use `lazy_static!` or `once_cell` to compile the regex patterns once at startup.
*   **Rule:** Keep the log-scanning logic extremely lean. Avoid heavy allocations inside the loop that processes Sing-box output.

### 2. Thread-Safe State Management (`rust-engineer`)
*   When tracking domain failure counts across multiple async tasks, use `tokio::sync::Mutex` or `DashMap`.
*   **Critical:** Ensure the failure history is automatically cleared or aged out (using a `tokio::time::sleep` or a timestamp check) so it doesn't grow indefinitely and leak memory.

### 3. Graceful Config Reloading (`rust-async-patterns`)
*   When applying a fix, the user might be in the middle of another operation. 
*   **Rule:** Use `tokio::select!` or a state-check to ensure we don't try to restart the engine if it's already in the middle of a "Connecting" state.

### 4. Semantic UI States
*   The "Magic Fix" should be rewarding. Use `framer-motion` to animate the transition when a new rule is added to the list. Use "Matrix-style" text-scrolling effects for the "Analyzing traffic..." state.

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 24.1 (Failure Detector)**. Which specific log patterns from Sing-box will you look for, and how will you implement the "aging" logic to prevent the failure map from filling up memory? Do not write the full code until I approve the plan.