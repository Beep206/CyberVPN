# Phase 10 Start: Expanded Protocol Support (The Parser Matrix)

Excellent progress! Our core application is robust and fully functional. Now it's time to expand its capabilities to reach true parity with advanced clients like Throne/Nekoray. 

We are officially starting **Phase 10: Expanded Protocol Support**. In this phase, we will expand our `engine::parser` and `engine::config` to support a wide array of modern and legacy proxy protocols.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 10.1: Refactor `ProxyNode` Model (If necessary)
To support diverse protocols, you may need to add optional fields to the `ProxyNode` struct in `ipc/models.rs`.
*   **VMess:** Requires fields like `alterId` (usually `u16`) and `security` (cipher).
*   **Shadowsocks:** Requires `method` (cipher) and `password`.
*   **Hysteria2 / TUIC:** Requires fields like `obfs`, `obfs_password`, `up_mbps`, `down_mbps`, `alpn`.
*   *Action:* Add any missing optional fields to `ProxyNode` as needed, ensuring they derive `Serialize` and `Deserialize` properly.

### Task 10.2: Implement Protocol Parsers
In `engine::parser::rs`, implement the following parsing functions and integrate them into the main `parse_link` function:
*   `parse_vmess(link: &str)`: Note that `vmess://` links are usually a Base64-encoded JSON string. You must decode the Base64 and parse the JSON.
*   `parse_shadowsocks(link: &str)`: Support `ss://`. Handle the SIP002 standard (where user info is base64 encoded cipher:password, and the rest is standard URI format).
*   `parse_trojan(link: &str)`: Very similar to `vless://`.
*   `parse_hysteria2(link: &str)`: Parse `hy2://` or `hysteria2://`. Extract specific query parameters like `obfs` and `insecure`.

### Task 10.3: Config Generator Alignment
Update `engine::config::generate_singbox_config` to correctly map these new protocols.
*   Match on `proxy.protocol.as_str()`.
*   Generate the correct `outbound` JSON object for Sing-box based on the protocol type. For example, a `vmess` outbound has a different structure than `vless` or `shadowsocks`. Consult the Sing-box documentation for exact outbound structures if needed.

### Task 10.4: Exhaustive Unit Testing
*   Write unit tests in `engine::parser::tests` for EVERY new protocol.
*   Test both valid links (to ensure all fields extract correctly) and invalid links (to ensure graceful error handling).

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Zero-Panic Parsing (`rust-engineer` & `rust-best-practices`)
*   **NEVER use `.unwrap()` or `.expect()`** when parsing URLs, Base64 strings, or JSON data from links.
*   Use `?` to propagate errors.
*   If `base64::engine::general_purpose::STANDARD.decode` fails, or if `serde_json::from_slice` fails on a VMess link, return an elegant `AppError::System` (or add specific `AppError::ParseError` variants) so the UI can show a friendly toast to the user instead of crashing the backend.

### 2. Efficient Memory Management (`rust-best-practices`)
*   When decoding base64 (e.g., for VMess or Shadowsocks), avoid unnecessary `String` conversions if you are just going to pass the bytes into a JSON parser.
    *   *Good:* `let bytes = base64::decode(...)?; let vmess_json: VmessFormat = serde_json::from_slice(&bytes)?;`
*   Define a temporary internal struct with `#[derive(Deserialize)]` inside your parser module to strictly type the parsed VMess JSON, rather than relying on untyped `serde_json::Value`.

### 3. Idiomatic Error Handling (`rust-engineer`)
*   When parsing standard URIs using the `url` crate, handle missing fields gracefully.
    *   *Example:* `let host = url.host_str().ok_or_else(|| AppError::System("Missing host".into()))?;`

### 4. Test Naming and Structure (`rust-best-practices`)
*   Use descriptive, behavior-driven names for your tests.
    *   *Example:* `parse_vmess_should_fail_gracefully_on_invalid_base64()`
    *   *Example:* `parse_shadowsocks_should_extract_sip002_parameters_correctly()`
*   Ensure all tests compile and pass via `cargo test`. Ensure no warnings are emitted via `cargo clippy`.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 10.1 & 10.2 (Models & Parsers)**. Show me a snippet of the internal struct you plan to use for decoding VMess JSON. Do not write the full code until I approve the plan.