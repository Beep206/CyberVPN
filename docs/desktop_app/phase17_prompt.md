# Phase 17: Ultimate Feature Exhaustion (Speedtest, Tailscale, Mux, Custom Inbounds)

Incredible work! We have successfully cloned and modernized the entire core architecture of Throne. However, a deep code audit of the original C++ repository revealed 4 hyper-specific power-user features that we are missing. 

To achieve *absolute, irrefutable 100% codebase feature exhaustion*, we must implement these final 4 items.

This is **Phase 17: Ultimate Feature Exhaustion**.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 17.1: The Asynchronous Ping & Speedtest Engine
Throne allows users to test the latency and download speed of dozens of nodes simultaneously.
*   **The Logic:** You cannot simply ICMP ping these nodes (they are proxies, ICMP might be blocked). You must measure TCP handshake latency to the `server:port`.
*   **Rust Implementation (`engine::ping.rs`):**
    *   Create `async fn test_latency(node: &ProxyNode) -> Result<u32, AppError>`.
    *   Use `tokio::net::TcpStream::connect` with a `tokio::time::timeout` (e.g., 3000ms). Measure the elapsed time for the connection to establish.
    *   Create a Tauri command `test_all_latencies(app: AppHandle)` that spawns concurrent tasks (using `tokio::task::JoinSet` or `futures::stream::StreamExt::buffer_unordered`) to test all profiles in the store and update their `ping` field in the database. Emits an event to the UI to trigger a React state refresh.
    *   *(Note: True URL speed testing through the proxy requires starting a local core instance for each node, which is too heavy for now. TCP Latency is sufficient for 95% of use cases).*

### Task 17.2: Tailscale Outbound Integration
Throne experimentally supports using Tailscale as a Sing-box outbound.
*   **Model Update:** Ensure `ProxyNode` can represent a Tailscale node. (It mostly just needs `protocol: "tailscale"` and an optional `state_directory` or `control_url` which we can store in the `network` or `server` fields for now).
*   **Parser:** Update `parse_link` to accept `tailscale://`.
*   **Config Generator:** In `config.rs`, match `"tailscale"` and generate the corresponding outbound:
    ```json
    { "type": "tailscale", "tag": "proxy" }
    ```

### Task 17.3: Multiplexing (Mux) Configuration
Power users need to toggle Mux (h2mux, smux, yamux) to bypass certain DPI firewalls.
*   **Model Update:** Add `pub mux: Option<String>` to `ProxyNode`.
*   **UI Update:** In the "Add/Edit Node" dialog, add a dropdown for Mux: `None`, `h2mux`, `smux`, `yamux`.
*   **Config Generator:** In `config.rs`, if `mux` is present and not "none", inject the `multiplex` block into the outbound:
    ```json
    "multiplex": { "enabled": true, "protocol": node.mux }
    ```

### Task 17.4: Customizable Local Inbounds
Currently, our `mixed-in` port is hardcoded to `2080`. Users might have port conflicts.
*   **Model Update:** Add `pub local_socks_port: Option<u16>` to `AppDataStore`.
*   **UI Update:** In the Settings page, add an input field for "Local Mixed Port" (default 2080).
*   **Config Generator:** Update `generate_singbox_config` to read this setting from the store and replace the hardcoded `2080` in the `mixed` inbound.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-async-patterns` rules:

### 1. High-Concurrency Asynchronous Tasks (`rust-async-patterns`)
*   When implementing `test_all_latencies` (Task 17.1), **do not** test nodes sequentially (`for` loop with `.await`), as testing 100 nodes would take forever.
*   **Do not** spawn 100 uncontrolled `tokio::spawn` tasks simultaneously, as this could exhaust open file descriptors (socket limits).
*   **Rule:** You MUST use `futures::stream::iter(...).buffer_unordered(CONCURRENCY_LIMIT)` (e.g., limit of 10-20) OR `tokio::task::JoinSet` to test latencies concurrently but with a strict upper bound.

### 2. Precise Time Measurement (`rust-engineer`)
*   Use `std::time::Instant::now()` immediately before the `TcpStream::connect` call, and `.elapsed().as_millis() as u32` immediately after it succeeds to calculate the ping.
*   Handle connection refused, DNS resolution failures, and timeouts elegantly by returning `None` or `0` for the ping (do not fail the entire batch test if one node is dead).

### 3. IPC State Mutability (`rust-best-practices`)
*   When updating the `ping` values of 50 profiles in the `AppDataStore`, read the store, apply the updates in memory, and do **one single** `store::save_store` operation at the end of the batch process. Do not write to the disk 50 times in a loop.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 17.1 (Concurrent Latency Testing)**. Show me a snippet of the Rust code using `buffer_unordered` or `JoinSet` to respect the concurrency limits. Do not write the full code until I approve the plan.