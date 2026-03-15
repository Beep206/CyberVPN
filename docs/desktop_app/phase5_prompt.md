# Phase 5 Start: System Integration & Privilege Management

Brilliant execution on Phase 4! Your lock management and error handling were strictly idiomatic and safe. The data flow between the React UI and the Sing-box engine is now solid.

We are now entering the most critical and complex part of a VPN desktop application: **Phase 5: System Integration & Privilege Management**. Here we will implement the logic to route *all* system traffic through the proxy using TUN interfaces, which strictly requires elevated permissions (Admin/Root).

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 5.1: TUN Interface Preparation & Privilege Check
Before starting Sing-box in TUN mode, we must ensure the environment is ready and we have the necessary permissions.
*   **Create a new module:** `engine::sys` (or similar) to encapsulate OS-specific logic.
*   **Privilege Checking Function:** Implement a cross-platform function `is_elevated() -> bool`.
    *   **Windows:** Use Windows API (via `windows` crate) to check if the current process token has elevated privileges.
    *   **Linux/macOS:** Check if `libc::geteuid() == 0`.
*   **Wintun Provisioning (Windows Only):** If the OS is Windows, write logic to ensure the `wintun.dll` driver is present alongside the `sing-box.exe` binary. If not, download/extract it just like we did with the Sing-box binary.

### Task 5.2: Elevation Trigger (The "Run as Admin" flow)
If the user wants to connect with "TUN Mode" enabled, but the app is *not* running as Admin/Root, we must handle this gracefully.
*   **UI Update:** Add a "TUN Mode" toggle switch to the Dashboard or Settings page.
*   **Backend Flow:** If TUN is requested but `is_elevated()` is false:
    *   **Do not** crash or panic.
    *   Return a specific error variant: `AppError::ElevationRequired`.
    *   **Linux/macOS:** Attempt to execute the proxy command via `pkexec` or `sudo` directly using `tokio::process::Command`, OR prompt the user that they must restart the app as root. (For this phase, let's start by modifying the `ProcessManager::start` to wrap the execution in an elevation wrapper if requested and not currently elevated).
    *   *Note: True background daemon services are better, but for this iteration, let's focus on the simpler "elevated child process" approach.*

### Task 5.3: Strict DNS Leak Protection (System DNS modification)
When TUN is active, we must ensure DNS requests don't bypass the tunnel.
*   Update your `config::generate_singbox_config` to inject robust DNS routing rules into the JSON when TUN mode is enabled.
*   Ensure the `tun` inbound in the Sing-box config has `auto_route: true`, `strict_route: true`, and `auto_redirect: true` (adjust based on the exact Sing-box v1.11 schema).

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Conditional Compilation (`#[cfg(...)]`)
*   System APIs are highly platform-dependent. You MUST use conditional compilation correctly.
*   Create separate files or strictly scoped blocks for OS logic:
    ```rust
    #[cfg(target_os = "windows")]
    pub fn is_elevated() -> bool { ... }

    #[cfg(unix)]
    pub fn is_elevated() -> bool { ... }
    ```
*   Ensure the code compiles on ALL targets. Do not leave syntax errors in the Windows block just because you are developing on Linux.

### 2. Unsafe Rust & FFI (`rust-engineer`)
*   If you need to use `unsafe` to call Windows APIs or libc (e.g., `geteuid`), you **MUST** wrap the unsafe block as tightly as possible.
*   You **MUST** add a `// SAFETY: ...` comment above every single `unsafe` block explaining why the invariants of the unsafe function are upheld.

### 3. Graceful Error Handling (`rust-best-practices`)
*   Expand your `AppError` enum to include elevation-specific errors (e.g., `ElevationRequired`, `DriverMissing(String)`).
*   When executing OS-level network commands (if any), capture both `stdout` and `stderr` and include them in the error message if the command fails. "Command failed with exit code 1" is not enough; we need to know *why*.

### 4. Zero-Cost Abstractions (`rust-engineer`)
*   When building OS-specific command arguments (like prepending `pkexec` or `sudo` to a `Command`), use `impl Iterator` or `Vec<&str>` efficiently without unnecessary String allocations.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 5.1 & 5.2** focusing on how you will structure the OS-specific privilege checking and how you plan to handle the execution of an elevated child process. Tell me what crates (e.g., `windows`, `libc`) you will add. Do not write the full code until I approve the plan.