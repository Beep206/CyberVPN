# Phase 8 & 9 Start: Testing, Security, and CI/CD Deployment

Incredible work! The core functionality, UI polish, and deep system integrations (Tray, Hotkeys, TUN) are all in place. The codebase is clean, memory-safe, and highly performant. 

We are now moving into the final stages: **Phase 8 (Testing & Security)** and **Phase 9 (CI/CD & Deployment)**. This is where we ensure the application is production-ready, secure, and can be automatically distributed to users.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 8.1: Security Auditing & IPC Validation
We must treat the React frontend as an untrusted client. 
*   Review all `#[tauri::command]` functions in `ipc/mod.rs`.
*   Ensure that file paths (like writing to `run.json`) are strictly bound to the `app_data_dir()` and immune to Path Traversal attacks.
*   Add bounds checking or sanitization to the `ProxyNode` fields (e.g., ensuring `port` is a valid u16, `server` doesn't contain shell injection payloads, even though `Command` prevents most of it).

### Task 8.2: Automated Rust Testing
Implement unit tests for the core engine logic to prevent regressions.
*   Create a `tests` module within `engine/parser.rs` and `engine/config.rs`.
*   Write tests for parsing valid and invalid `vless://` links.
*   Write tests for `generate_singbox_config` to ensure routing rules are mapped correctly (especially the new Phase 6 multi-hop logic).

### Task 9.1: Auto-Updater Integration
Tauri provides a powerful auto-updater mechanism.
*   **Rust:** Add `tauri-plugin-updater` to `Cargo.toml`. Initialize it in `lib.rs` and set up the public key for signature verification.
*   **Tauri Config:** Configure the `"updater"` block in `tauri.conf.json` with your update endpoint (e.g., a GitHub Releases URL or a custom server JSON).
*   **React:** Implement a UI listener (perhaps in `Layout.tsx` or `Dashboard/index.tsx`) that listens for `tauri://update-available` events and shows a beautiful prompt asking the user to install the update.

### Task 9.2: CI/CD GitHub Actions Configuration
Set up the automated build pipeline.
*   Create `.github/workflows/release.yml`.
*   Configure a matrix build for `ubuntu-latest`, `macos-latest`, and `windows-latest`.
*   Include steps to run `cargo fmt`, `cargo clippy`, and `cargo test`.
*   Add the `tauri-action` to automatically build the binaries and upload them as GitHub release assets. (Leave placeholders for code-signing secrets like `APPLE_CERTIFICATE` and `WINDOWS_CERT_BASE64`).

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement these final phases, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Automated Testing Standards (`rust-best-practices`)
*   **Descriptive Naming:** Name your tests descriptively. Example: `parse_vless_should_return_error_when_uuid_is_missing()`.
*   **Targeted Assertions:** Keep tests focused. Ideally, one logical assertion concept per test.
*   **Doc Tests:** Add `///` doc comments with examples for public utility functions (like the parser) to ensure the documentation itself is verified by `cargo test`.

### 2. CI/CD Linting Enforcement (`rust-best-practices`)
*   In your GitHub Actions YAML, the linting step **MUST** use the following strict command to ensure no warnings slip into production:
    `cargo clippy --all-targets --all-features --locked -- -D warnings`
*   Also enforce formatting: `cargo fmt --check`.

### 3. Security & Error Handling (`rust-engineer`)
*   During the security audit, ensure you are not using `unwrap()` or `expect()` *anywhere* in the production code path (tests are fine).
*   Use `AppError` variants to handle malformed IPC inputs. 
*   If testing async code (e.g., testing the store logic), use `#[tokio::test]` properly.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 8.1 & 8.2 (Security & Testing)**. Show me a snippet of how you will structure the tests in `parser.rs`. Do not write the full code until I approve the plan.