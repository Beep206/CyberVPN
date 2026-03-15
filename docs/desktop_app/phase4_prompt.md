# Phase 4 Start: Core VPN Functionality (Data Flow)

Excellent work on the refactoring! The foundation is now robust, memory-safe, and follows proper async patterns. 

We are now officially starting **Phase 4: Core VPN Functionality (Data Flow)**. In this phase, we will bridge the gap between the beautiful UI and the Sing-box engine. You will implement profile parsing (importing) and the full connection lifecycle.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 4.1: Profile Import Mechanisms
*   Implement parsing for standard share links (e.g., `vless://...`, `hysteria2://...`).
*   **Where:** Create a new Rust module `engine::parser` to handle the decoding (Base64, URL decoding) and mapping to our `ProxyNode` struct.
*   **UI Integration:** Implement a "Paste from Clipboard" button in the `ProfilesPage` (or a global hotkey) that reads the clipboard via Tauri APIs, sends it to a new Rust command `parse_clipboard_link`, and adds the parsed node to the store.

### Task 4.2: Connection Lifecycle Management
*   **The Logic:** When the user clicks the massive "Connect" button on the Dashboard, the frontend must invoke a `start_connection(profile_id)` command.
*   **Backend Flow:** 
    1. Fetch the profile from the `store`.
    2. Pass it to your existing `config::generate_singbox_config(node)` to get the JSON.
    3. Save the JSON to a temporary file (`app_dir().join("run.json")`).
    4. Call your `ProcessManager::start()`.
    5. Update a global state (e.g., a `RwLock<ConnectionStatus>`) in Tauri managed state.
*   **UI Updates:** The frontend should subscribe to `connection_status_changed` events or poll the status to update the UI (Connecting -> Connected -> Error).

### Task 4.3: Real-time Statistics
*   Sing-box writes traffic logs if configured, or we can use its experimental API. For now, focus on extracting the "uploaded/downloaded" metrics.
*   **If parsing stdout/stderr:** Enhance the log listener in `ProcessManager` to regex/parse byte counts and emit a specific `traffic_update` event with structured data `{ up: u64, down: u64 }`.
*   Connect this event to the `TrafficGraph` on the Dashboard.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Error Handling (`rust-best-practices`)
*   Continue using the `AppError` enum (with `thiserror`) created in the refactoring phase. 
*   **Never use `unwrap()` or `expect()`** when parsing URLs, Base64, or JSON. If a clipboard string is not a valid VLESS link, return a clean `AppError::ParseError` and show a neat toast notification on the frontend.
*   Use the `?` operator extensively for error propagation.

### 2. State & Lock Management (`rust-async-patterns`)
*   When managing the global `ConnectionStatus`, use `tokio::sync::RwLock` (preferable for read-heavy state) or `Mutex`.
*   **CRITICAL:** NEVER hold a `MutexGuard` or `RwLockReadGuard` across an `.await` point. This will cause deadlocks.
    *   *Bad:* `let state = lock.read().await; tokio::time::sleep(...).await; println!("{}", state);`
    *   *Good:* Read the state, drop the lock (or copy/clone the data), then `.await`.

### 3. String & Memory Efficiency (`rust-engineer`)
*   When parsing URLs in Task 4.1, prefer borrowing `&str` over cloning into `String` where possible during intermediate steps.
*   Only convert to `String` when constructing the final owned `ProxyNode` struct to be saved in the store.
*   Use the `url` crate for robust URL parsing rather than manual string splitting.
*   Use `base64` crate for decoding (ensure you handle both standard and URL-safe base64, with or without padding).

### 4. Background Tasks (`rust-async-patterns`)
*   When spawning the log-parsing task for real-time statistics (Task 4.3), ensure it is tied to the lifecycle of the Sing-box process. If the process stops, the spawned `tokio::spawn` task should exit cleanly (e.g., the channel closes). Do not leave orphan loops running.

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan (bullet points) for **Task 4.1 (Profile Import Mechanisms)**. Tell me which crates you will add and how you will structure the parser. Do not write the full code until I approve the plan.