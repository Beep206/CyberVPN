# Phase 15: Absolute Protocol Parity (TUIC, Wireguard, SOCKS, HTTP, SSH)

Outstanding work bringing the application to 95% feature parity with Throne! The UI, system integration, and core parsers are flawless.

To achieve **100% absolute feature parity**, we need to close the final gap: parsing the remaining legacy and niche proxy protocols that Throne supports.

We are now starting **Phase 15: Absolute Protocol Parity**.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 15.1: Extend `ProxyNode` Model (If necessary)
Review `ipc/models.rs`. You will need to add new optional fields to support the remaining protocols:
*   **TUIC:** Needs fields like `congestion_control` (e.g., "bbr"), `udp_relay_mode`, `alpn` (already exists).
*   **Wireguard (WG):** Needs fields like `local_address` (Vec<String>), `private_key`, `peer_public_key`, `mtu`.
*   **SSH:** Needs `user` (already standard in URLs), `password` (already exists), and potentially `private_key` (can reuse).
*   **HTTP/SOCKS5:** Basic host, port, user, and password (all exist).

### Task 15.2: Implement the Remaining Parsers
In `engine::parser::rs`, implement these new parsers and route them inside the main `parse_link` function:
*   `parse_tuic(link: &str)`: `tuic://user:pass@host:port?congestion_control=bbr&alpn=h3`
*   `parse_wireguard(link: &str)`: Format varies, but typically `wg://...` or parsing a standard WG config file if imported as text. Let's stick to parsing a standard `wg://[peer_pubkey]@[endpoint_ip]:[port]?private_key=...&address=...` URI format for now.
*   `parse_socks(link: &str)`: `socks5://user:pass@host:port` (handles base64 encoded user:pass as well).
*   `parse_http(link: &str)`: `http://user:pass@host:port`
*   `parse_ssh(link: &str)`: `ssh://user:pass@host:port`

### Task 15.3: Config Generator Alignment
Update `engine::config::generate_singbox_config` to correctly map these new protocols into Sing-box `outbounds`.
*   **Wireguard:** Requires `local_address`, `private_key`, `peers: [{ server, server_port, public_key }]`.
*   **TUIC:** Requires `uuid`, `password`, `congestion_control`.
*   **SOCKS/HTTP/SSH:** Straightforward mapping to Sing-box outbounds.

### Task 15.4: Exhaustive Unit Testing
*   Write unit tests in `engine::parser::tests` for EVERY new protocol added in this phase.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Robust URL Parsing (`rust-best-practices`)
*   When parsing `socks5://` and `http://`, remember that the `userinfo` section is sometimes URL-encoded, and sometimes Base64-encoded depending on the client that generated it. Try basic extraction first, and if it looks like Base64 (no colon present, valid characters), attempt to decode it (using the `or_else` fallback pattern from Phase 11).
*   **No `.unwrap()`**. Use the `?` operator for all parsing errors.

### 2. Efficient Memory Management (`rust-engineer`)
*   When parsing comma-separated query parameters (like `address=10.0.0.1/24,fd00::1/64` in Wireguard), use iterators efficiently:
    `v.split(',').map(|s| s.trim().to_string()).collect::<Vec<_>>()`

### 3. Exhaustive Pattern Matching
*   Ensure that your `match node.protocol.as_str()` in `config.rs` has explicit arms for `"tuic"`, `"wireguard"`, `"socks"`, `"http"`, and `"ssh"`.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 15.1 and 15.2**, specifically showing how you intend to structure the Wireguard URI parsing since there is no single universal standard for `wg://` links (propose the query parameters you will look for). Do not write the full code until I approve the plan.