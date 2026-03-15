# Phase 11 Start: Subscription Management Engine

Incredible work on Phase 10! Your zero-panic parsing logic and memory-efficient decoding techniques were spot on. The proxy engine is now truly multi-protocol.

We are now starting **Phase 11: Subscription Management Engine**. This is a highly requested feature that allows users to import and auto-sync dozens of proxy nodes from a single provider URL.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 11.1: Backend Data Modeling
Update our local data store to handle subscription groups.
*   **Update `ipc/models.rs`:** 
    *   Create a new `Subscription` struct:
        ```rust
        #[derive(Debug, Clone, Serialize, Deserialize)]
        #[serde(rename_all = "camelCase")]
        pub struct Subscription {
            pub id: String,
            pub name: String,
            pub url: String,
            pub auto_update: bool,
            pub last_updated: Option<u64>, // Unix timestamp
        }
        ```
    *   Add an optional `subscription_id: Option<String>` to `ProxyNode`.
*   **Update `engine/store.rs`:**
    *   Add `pub subscriptions: Vec<Subscription>` to `AppDataStore`.
    *   Initialize it in `AppDataStore::default()`.

### Task 11.2: The Fetch & Decode Engine
Create a new module `engine::subscription.rs`.
*   Implement an async function `fetch_and_parse_subscription(url: &str) -> Result<Vec<ProxyNode>, AppError>`.
*   Use `reqwest` to HTTP GET the URL.
*   **Decoding Logic:** Most subscription endpoints return a single Base64 encoded string. Decode it.
*   **Parsing Logic:** The decoded string is typically a newline-separated list of share links (`vless://... \n vmess://...`). Iterate over the lines and pass each valid line to your existing `parser::parse_link()`.
*   *Note:* Ignore lines that fail to parse (log a warning, but don't fail the entire subscription).

### Task 11.3: Store Sync Logic & Tauri Commands
Create the IPC commands in `ipc/mod.rs` to manage subscriptions.
*   `get_subscriptions()`
*   `add_subscription(sub: Subscription)`
*   `update_subscription(sub_id: String)`: 
    1. Fetch nodes using `fetch_and_parse_subscription`.
    2. Assign the `sub_id` to all fetched `ProxyNode`s.
    3. Load the store, **remove** all existing nodes where `node.subscription_id == Some(sub_id)`, and **append** the newly fetched nodes.
    4. Update the `last_updated` timestamp on the subscription.
    5. Save the store.

### Task 11.4: Frontend UI (Subscriptions Page)
*   Create a new route/page: `src/pages/Subscriptions/index.tsx`.
*   Build a UI to add a URL, toggle auto-update, and manually trigger an "Update Now" action.
*   Display how many proxy nodes belong to each subscription.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Robust HTTP & Error Handling (`rust-async-patterns` & `rust-engineer`)
*   When fetching the subscription URL via `reqwest`, set a strict **timeout** (e.g., 10 seconds) so the UI doesn't hang indefinitely if the provider's server is down.
*   Check the HTTP status code (`response.status().is_success()`) before attempting to read the body. If it fails, return a descriptive `AppError::System`.

### 2. Base64 Decoding Fallbacks (`rust-best-practices`)
*   Subscription Base64 strings are notoriously messy. They might be Standard, URL-Safe, padded, or unpadded.
*   Reuse the robust fallback decoding pattern you used in the VMess parser:
    ```rust
    BASE64_URL_SAFE_NO_PAD.decode(text)
        .or_else(|_| BASE64_URL_SAFE.decode(text))
        // ... etc
    ```
*   If the text is NOT base64 (some providers return raw plaintext links), your code should detect the decode failure and seamlessly fallback to treating the raw body as the newline-separated list.

### 3. Iterators and Safe Unwrapping (`rust-best-practices`)
*   When parsing the lines of the decoded subscription, use iterator filtering to skip empty lines and safely parse the rest:
    ```rust
    let nodes: Vec<ProxyNode> = decoded_string
        .lines()
        .map(|line| line.trim())
        .filter(|line| !line.is_empty())
        .filter_map(|line| {
            crate::engine::parser::parse_link(line).ok() // Ignore malformed lines silently
        })
        .collect();
    ```

### 4. Background Sync (Optional but recommended)
*   If you implement `auto_update`, do not block the main Tauri thread. Spawn a detached `tokio` task upon application startup that sleeps and periodically calls the update logic for subscriptions where `auto_update == true`.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 11.2 (Fetch & Decode Engine)**. Explain how you will handle the timeout and the plaintext/base64 fallback logic. Do not write the full code until I approve the plan.