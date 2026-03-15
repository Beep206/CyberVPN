# Phase 6 Start: Advanced Routing & Customization

Great job on Phase 5! The code is compiling cleanly across platforms, privilege checking works, and `tun_mode` is properly propagated into the config.

We are now moving on to **Phase 6: Advanced Routing & Customization**. In this phase, we will implement power-user features: custom routing rules and outbound chains (multi-hop), similar to Nekoray but with a vastly superior FSD-based React UI.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 6.1: Visual Rule Builder (Backend Data Structures)
Before we build the UI, we need to update our Rust data models to support custom routing rules and persist them.
*   **Update `AppDataStore`:** Add a new field `pub routing_rules: Vec<RoutingRule>` to `engine::store::AppDataStore`.
*   **Create `RoutingRule` struct:**
    ```rust
    #[derive(Serialize, Deserialize, Clone)]
    pub struct RoutingRule {
        pub id: String,
        pub enabled: bool,
        pub domains: Vec<String>,    // e.g., ["*.openai.com", "geosite:google"]
        pub ips: Vec<String>,        // e.g., ["geoip:telegram", "192.168.1.0/24"]
        pub outbound: String,        // e.g., "proxy", "direct", "block"
    }
    ```
*   **Tauri Commands:** Create `get_routing_rules`, `add_routing_rule`, `update_routing_rule`, and `delete_routing_rule` commands.
*   **Config Generator Integration:** Update `engine::config::generate_singbox_config` to read these rules and dynamically inject them into the `route.rules` array of the JSON. Ensure user rules are evaluated *before* the default catch-all rules.

### Task 6.2: Visual Rule Builder (Frontend UI)
*   **Create new page:** `src/pages/Routing/index.tsx` (Add it to `Layout.tsx` and React Router).
*   **UI Implementation:** Build a clean, table-based or card-based UI where users can add/edit/delete rules.
    *   Use a modern modal or drawer for the "Add Rule" form.
    *   Input fields for Domains and IPs (comma separated).
    *   A Select/Dropdown for the Outbound action (`Proxy`, `Direct`, `Block`).

### Task 6.3: Outbound Chains (Multi-hop) - Preparation
To support Multi-hop, a profile should be able to reference another profile.
*   **Update `ProxyNode`:** Add an optional `pub next_hop_id: Option<String>` to the `ProxyNode` struct in `ipc/models.rs`.
*   **Config Generator Integration:** When generating the config for a node, if `next_hop_id` is set, you must:
    1. Look up the `next_hop` node from the store.
    2. Add *both* outbounds to the Sing-box config.
    3. Modify the first outbound's `detour` field to point to the `tag` of the `next_hop` outbound.
    *(Note: For this to work, `generate_singbox_config` will now need access to the full `store.profiles` list, not just a single node).*

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Data Structure Updates & Borrowing (`rust-best-practices`)
*   When updating `generate_singbox_config` to accept a list of profiles (for Task 6.3), pass the profiles as a slice (`&[ProxyNode]`) rather than taking ownership or cloning the entire `Vec`.
*   Example signature: `pub fn generate_singbox_config(target_node: &ProxyNode, all_nodes: &[ProxyNode], tun_enabled: bool, rules: &[RoutingRule]) -> Value`.

### 2. Error Handling for Missing Hops (`rust-engineer`)
*   If `next_hop_id` is specified on a node, but that ID no longer exists in the store (e.g., the user deleted it), your configuration generator must not panic or use `.unwrap()`.
*   Instead, log a warning (using `println!` or the `tracing` crate if available) and either fall back to direct internet connection (no detour) or return a formal `AppError` so the connection process aborts gracefully.

### 3. Iterators and Performance (`rust-best-practices`)
*   When transforming `RoutingRule` into `serde_json::Value` rules, use idiomatic Iterator chains (`.iter().filter_map(...).map(...).collect()`) rather than manual `for` loops with mutable vectors where possible.

### 4. IPC Serialization Consistency (`rust-engineer`)
*   Ensure that all new structs (`RoutingRule`) derive `Serialize`, `Deserialize`, and `Clone`.
*   Use `#[serde(rename_all = "camelCase")]` on `RoutingRule` to ensure the TypeScript interfaces map perfectly to the Rust structs without manual casing conversion in the UI.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 6.1 (Backend Data Structures)**. Tell me exactly how you will modify `engine/store.rs`, `ipc/models.rs`, and `engine/config.rs`. Do not write the full code until I approve the plan.