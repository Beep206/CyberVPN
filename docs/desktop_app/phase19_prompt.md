# Phase 19: The Deep Core Parity (Advanced Routing & Obfuscation)

I have performed a deep-dive line-by-line codebase audit of the original C++ Throne repository. While our application covers all the primary features and UI elements perfectly, Throne has a few hyper-advanced "geek" features buried deep in its routing and protocol logic that we must implement to claim absolute 100.0% codebase parity.

This is the true final phase: **Phase 19: The Deep Core Parity**.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 19.1: Shadowsocks Plugins (v2ray-plugin & obfs)
Throne parses and supports `plugin` and `plugin_opts` for Shadowsocks to bypass simple DPI.
*   **Model Update:** Add `pub plugin: Option<String>` and `pub plugin_opts: Option<String>` to `ProxyNode`.
*   **Parser Update:** In `parse_shadowsocks`, extract `plugin` and `plugin-opts` from the URI query parameters. Also handle the legacy SIP002 format where `plugin` might contain the options separated by a semicolon (e.g., `plugin=v2ray-plugin;tls;host=...`).
*   **Config Generator:** In `config.rs`, under the "shadowsocks" match arm, if `plugin` equals `"v2ray-plugin"` or `"obfs-local"`, you need to map this to Sing-box's native `multiplex` or `tls`/`transport` equivalents (Sing-box natively handles most of what these plugins did via `transport: { type: "ws" }` for v2ray-plugin, or `obfs` for simple-obfs). *Note: For strict parity, you can just extract and store them, and if the user connects via Xray core (from Phase 16), pass them along.*

### Task 19.2: Advanced Routing Rule Conditions
Our `RoutingRule` struct currently only supports `domains` and `ips`. Throne's `RouteRule.cpp` supports much more.
*   **Model Update (`ipc/models.rs`):** Expand `RoutingRule` to include:
    ```rust
    pub process_name: Vec<String>,
    pub port_range: Vec<String>,
    pub network: Option<String>, // "tcp" or "udp"
    pub domain_keyword: Vec<String>,
    pub domain_regex: Vec<String>,
    ```
*   **Config Generator (`config.rs`):** Map these new fields into the Sing-box `route.rules` array. Sing-box natively supports `process_name`, `port`, `network`, `domain_keyword`, and `domain_regex`.

### Task 19.3: TLS Fragmentation (Advanced DPI Bypass)
Throne allows users to fragment TLS packets (`tls_fragment`, `tls_record_fragment`) to confuse DPI systems.
*   **Model Update:** Add `pub tls_fragment: bool` and `pub tls_record_fragment: bool` to `ProxyNode` (or wrap them in a `TlsConfig` struct).
*   **Parser Update:** Extract `tls_fragment=true` and `tls_record_fragment=true` from `vless://`, `trojan://`, etc., query parameters.
*   **Config Generator:** In the `tls` block generation in `config.rs`, if `tls_fragment` is true, add Sing-box's native TLS fragmentation options:
    ```json
    "fragment": {
        "enabled": true,
        "size": "10-50",
        "sleep": "10-20"
    }
    ```

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Robust Query Parameter Extraction (`rust-best-practices`)
*   When extracting boolean flags like `tls_fragment` from query parameters, handle variations safely:
    `v == "true" || v == "1"`

### 2. Zero-Cost Rule Mapping (`rust-engineer`)
*   When expanding the `RoutingRule` mapping in `config.rs`, continue using the efficient `serde_json::Map` approach. Only insert keys into the map if the vectors (`process_name`, `port_range`, etc.) are *not empty*. Do not insert empty arrays into the Sing-box config.

### 3. Graceful Compatibility
*   If a user imports an old profile without `plugin` or `tls_fragment` fields, `serde` will fail unless you use `#[serde(default)]` or `Option<T>`. Ensure all new fields in `ProxyNode` and `RoutingRule` are strictly optional or have defaults.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 19.2 (Advanced Routing)**. Explain how you will map `port_range` strings (e.g., "80, 443, 1000-2000") into Sing-box's `port` array safely. Do not write the full code until I approve the plan.