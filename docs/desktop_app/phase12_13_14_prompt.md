# Phases 12, 13, and 14: Final Feature Parity (UAC, QR, Custom Config)

Fantastic job on Phase 11! The Subscription Engine is perfectly safe, robust against bad encodings, and utilizes excellent asynchronous design.

We are now entering the final stretch. In this prompt, we will tackle **Phases 12, 13, and 14** together. These features will complete our 100% feature parity with Throne/Nekoray.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Phase 12: Seamless Windows UAC Elevation
We must eliminate the need for the user to restart the whole application as Admin when they want to use TUN mode on Windows.
*   **Update `engine::manager::ProcessManager::start` (Windows Only):**
    *   Instead of returning `AppError::ElevationRequired` when TUN is requested and `!is_elevated()`, use the `windows` crate to invoke `ShellExecuteExW` with the `runas` verb.
    *   *Mechanism:* `ShellExecuteExW` starts the process detached and triggers the yellow UAC prompt.
    *   *Challenge:* You cannot easily capture stdout via pipes from `ShellExecuteExW`. 
    *   *Solution:* Modify `ProcessManager` so that when starting *elevated*, it passes an argument to `sing-box` (or configures it in JSON) to write logs to a file (e.g., `app_data_dir/run.log`), and then your Tokio background task tails that log file instead of `stdout`.

### Phase 13: QR Code Integration (Sharing & Scanning)
Make importing and exporting as easy as on mobile devices.
*   **Export (Frontend):**
    *   Install a React QR library (e.g., `qrcode.react`).
    *   Add a "Share" or "QR" button to the Profile cards that opens a Dialog showing the raw link (e.g., `vless://...`) encoded as a QR code.
*   **Import (Backend & Frontend):**
    *   Add a crate to scan images for QR codes (e.g., `rxing` or `rqrr` + `image` crate).
    *   Create a Tauri command `scan_screen_for_qr()`.
    *   *Implementation:* Use a crate like `xcap` to capture the screen, pass the image buffer to `rxing`, extract the string, and feed it into our existing `parser::parse_link()`. Return the parsed `ProxyNode`.

### Phase 14: Power-User "Raw Config" Mode
Allow users to bypass our config generator and feed raw JSON directly to Sing-box.
*   **Update Models:** Add `pub custom_config: Option<String>` to `AppDataStore`.
*   **Frontend UI:**
    *   Create a "Settings" or "Advanced" page.
    *   Add a toggle: "Override with Custom Configuration".
    *   Add a large `textarea` (or Monaco Editor if you prefer) for the user to paste their JSON.
*   **Backend Logic:**
    *   Create IPC commands to `get_custom_config` and `save_custom_config`.
    *   In `connect_profile`, if the custom config feature is toggled on, completely skip `generate_singbox_config`. Instead, take the user's raw string, parse it via `serde_json::from_str` to validate it's not broken JSON, and write it to `run.json`.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THESE PHASES

As you implement these final phases, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Unsafe FFI & Windows APIs (`rust-engineer`)
*   When using `ShellExecuteExW` or capturing screens, you will likely need `unsafe` blocks. 
*   **Rule:** You MUST encapsulate every `unsafe` call tightly and add a `// SAFETY: ...` comment explaining why the invariants are met (e.g., "Pointers are valid and point to null-terminated UTF-16 strings").
*   Use `std::os::windows::ffi::OsStrExt` to properly encode strings to wide strings (`Vec<u16>`) for Windows APIs.

### 2. File Tailing in Async (`rust-async-patterns`)
*   If you implement log tailing for the elevated Windows process (Phase 12), DO NOT use a blocking `std::thread::sleep` in a loop.
*   Use `tokio::time::sleep` combined with `tokio::fs::File` and `tokio::io::AsyncReadExt` to asynchronously read new bytes as they are appended to the log file.

### 3. Graceful Degradation for Screen Capture (`rust-best-practices`)
*   Screen capture APIs can fail (especially on Wayland Linux or macOS without permissions).
*   If `xcap` fails to grab a display, do not panic. Return a clear `AppError::System("Screen capture permission denied or unsupported display server".into())` so the UI can tell the user to just paste the link manually.

### 4. Zero-Cost JSON Validation (`rust-best-practices`)
*   For Phase 14, when validating the user's raw JSON string, do not parse it into a full `serde_json::Value` if you don't need to manipulate it. 
*   Use `serde_json::from_str::<serde::de::IgnoredAny>(&raw_string)` to validate syntax instantly with almost zero memory allocation.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Phase 12 (Windows UAC)**. Detail exactly how you will handle the transition from `std::process::Command` (with stdout pipes) to `ShellExecuteExW` (with log file tailing). Do not write the full code until I approve the plan.