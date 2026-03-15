# Phase 16: The Final Polish (Portable Mode, Extra Cores, Clash Parsing)

You have done an extraordinary job! We have reached 99% parity with the original Throne client. Our UI is superior, and our Rust backend is incredibly safe and fast.

To achieve **100.0% absolute feature parity** with the documented capabilities of Throne, we need to address three specific architectural nuances: Portable Mode, Alternative Cores (Xray), and Clash Subscription Parsing.

This is **Phase 16: The Final Polish**.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 16.1: Portable Mode Implementation
Throne allows users to run the app from a USB drive without touching `%APPDATA%`.
*   **The Logic:** When resolving the path to `store.json`, `run.json`, and `sing-box.exe`, the application should check if a specific flag file (e.g., `.portable`) exists in the *same directory as the executable*.
*   **Rust Implementation:** Modify `engine::store::get_store_path` and `engine::provision` to use `std::env::current_exe()`. If `current_exe().parent().join(".portable").exists()`, then store everything in that local directory. Otherwise, fall back to Tauri's default `app_data_dir()`.

### Task 16.2: Alternative Core Support (Xray Preparation)
Throne allows users to switch between `sing-box` and `Xray`.
*   **Update Model:** Add a field to `AppDataStore` (e.g., `pub active_core: String` defaulting to `"sing-box"`).
*   **Process Manager Update:** Update `ProcessManager::start` to accept the core type. 
*   **Provisioning:** If the user selects "xray", your `engine::provision` module must be capable of downloading the `Xray-core` binary from GitHub instead of `sing-box`.
*   *(Note for this phase: You do NOT need to write a full Xray JSON config generator yet. Focus purely on the architecture allowing the user to select the core and the app downloading the correct binary. When connecting with Xray, simply log a warning that the Xray config generator is pending).*

### Task 16.3: Clash Subscription Parsing (YAML)
Many modern proxy providers return a Clash YAML file instead of Base64 strings.
*   **Add Dependency:** Add the `serde_yaml` crate to `Cargo.toml`.
*   **Update Subscription Engine:** In `engine::subscription::fetch_and_parse_subscription`, after fetching the text, check if it's valid YAML.
*   **Clash Parsing Logic:** If the text parses as a Clash YAML (e.g., it has a `proxies:` array), extract the nodes.
    *   Map Clash proxy types (`vless`, `vmess`, `trojan`, `ss`) to our internal `ProxyNode` format.
    *   *Hint:* You can use a generic `serde_yaml::Value` to traverse the `proxies` array, map the fields, and return `Vec<ProxyNode>`. If it's NOT a YAML, fall back to the existing Base64/Plaintext parser you built in Phase 11.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Robust File System Paths (`rust-engineer`)
*   When implementing Portable Mode using `std::env::current_exe()`, remember that this function can fail (e.g., due to OS permission issues or being run in strange environments).
*   **Never unwrap paths.** Handle `current_exe` failures gracefully and always fall back to the system `app_data_dir()`.

### 2. Zero-Panic Parsing for External Data (`rust-best-practices`)
*   When parsing Clash YAML subscriptions, you are dealing with untrusted third-party data.
*   Do not use `.unwrap()` when extracting fields from `serde_yaml::Value`. If a Clash `vless` proxy is missing a `server` field, simply `continue` (skip that node) or use `.filter_map()` to drop it, rather than crashing the subscription sync.

### 3. Asynchronous File Operations (`rust-async-patterns`)
*   If you need to check for the `.portable` file during async operations, use `tokio::fs::try_exists` instead of the synchronous `std::path::Path::exists` to avoid blocking the executor, especially if the file is on a slow network or USB drive.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 16.1 (Portable Mode) and 16.3 (Clash Parsing)**. Show me a rough snippet of how you will attempt YAML parsing before falling back to Base64 in the subscription engine. Do not write the full code until I approve the plan.