# Phase 20 Start: Intelligent Split Tunneling (Per-App Routing)

Congratulations on achieving full feature parity with Throne! Now, we are going beyond by implementing our first "Killer Feature": **Intelligent Split Tunneling**. This will allow users to visually select which Windows/Linux applications (like Chrome, Steam, or Discord) should go through the VPN and which should bypass it.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 20.1: Rust App Scanner (`engine::sys::apps`)
We need a way to list user-facing applications installed on the system.
*   **Implementation:** Create a new Rust module `engine::sys::apps.rs`.
    *   **Windows:** Use the `sysinfo` crate to get running processes OR scan the Registry (`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`) to find installed `.exe` paths. 
    *   **Linux:** Scan `/usr/share/applications` for `.desktop` files.
*   **Command:** Create a Tauri command `get_installed_apps() -> Result<Vec<AppInfo>, AppError>`. 
*   **Data Structure:** `AppInfo { name: String, package_name: String, icon_base64: Option<String>, exec_path: String }`.

### Task 20.2: Backend Rules Persistence
*   **Model Update:** Add `pub split_tunneling_apps: Vec<String>` (list of executable names like `chrome.exe`) and `pub split_tunneling_mode: String` ("allow" or "disallow") to `AppDataStore`.
*   **Config Generator Integration:** Update `config.rs` to dynamically inject `process_name` rules into the Sing-box `route.rules` array based on this list.

### Task 20.3: Premium "App Picker" UI (React)
Create a UI that feels like a high-end console or a modern smartphone settings page.
*   **Location:** `src/pages/SplitTunneling/index.tsx`.
*   **Features:**
    *   **Search Bar:** Quickly find apps by name.
    *   **App Cards:** Beautiful grid or list of apps with their icons.
    *   **Skeleton States:** Use `framer-motion` to show a shimmering loading state while Rust is scanning the system.
    *   **Presets:** Buttons for "Gaming" (pre-select Steam, Epic, etc.) and "Browsing" (pre-select Chrome, Firefox).

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-async-patterns` rules:

### 1. Offload Blocking I/O (`rust-async-patterns`)
*   Scanning the Windows Registry or walking the Linux file system is a **heavy, blocking operation**. 
*   **Rule:** You MUST perform the app scanning inside `tokio::task::spawn_blocking(move || { ... })` to ensure the Tauri main thread remains reactive. Do not block the async executor.

### 2. High-Performance Metadata Extraction (`rust-engineer`)
*   Extracting icons from `.exe` files (on Windows) can be slow. 
*   **Optimization:** Implement a caching mechanism or only extract icons for the first 50 visible apps. Use the `ico` or `winapi` calls safely. 
*   **FFI Safety:** Every `unsafe` block used for Windows API calls MUST have a `// SAFETY: ...` comment explaining why it won't crash the system.

### 3. Error Resilience (`rust-best-practices`)
*   If scanning one specific directory fails due to permission errors, do not fail the entire command. Use `.filter_map()` or `continue` to skip inaccessible folders and return the apps you *could* find.

### 4. Memory-Efficient Strings (`rust-engineer`)
*   When filtering process names, prefer `&str` comparisons before allocating new `String` objects for the `AppInfo` struct.

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 20.1 (App Scanner)**. Which crate will you use for icon extraction on Windows, and how will you ensure the search is non-blocking? Do not write the full code until I approve the plan.