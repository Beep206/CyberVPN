# Phase 23 Start: Cross-Platform Cloud Ecosystem (Sync & Pairing)

Exceptional work on the Kill Switch! The security layer is now Enterprise-grade. Now, we move to **Phase 23: Cross-Platform Cloud Ecosystem**. This is where we transform the standalone app into a unified ecosystem, allowing users to sync their servers and rules across Desktop, Android TV, and Mobile with one click.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 23.1: End-to-End Encrypted (E2EE) Sync Engine (Rust)
We need to push and pull user data to the cloud securely. The server should never see the raw proxy passwords.
*   **Implementation:** Create `engine::sys::sync.rs`.
*   **Encryption:** Use the `aes-gcm` crate. 
    *   Derive an encryption key from a user-provided "Sync Password" or a hardware-bound ID using `argon2` or `pbkdf2`.
    *   Encrypt the entire `AppDataStore` JSON before sending it to the backend.
*   **Networking:** Use `reqwest` to interact with the CyberVPN Cloud API (for this task, you can implement a mock sync endpoint or use a Supabase/PostgreSQL backend if configured).
*   **Commands:** `cloud_push()`, `cloud_pull()`.

### Task 23.2: One-Click Pairing via QR (The "Handover" Feature)
Make it trivial to move configurations from Desktop to an Android TV or Phone.
*   **Desktop Role:** Generate a "Sync Token" QR code. This QR contains the Cloud Sync URL and the temporary encryption key.
*   **Implementation:** Create a command `generate_pairing_qr() -> String` (Base64 QR image).
*   **Logic:** When the TV app scans this, it uses the credentials to perform an immediate `cloud_pull()` and populates its local Room database.

### Task 23.3: "My Account" & Ecosystem UI (React)
Create a beautiful, simple account management page.
*   **Location:** `src/pages/Account/index.tsx`.
*   **Features:**
    *   **Cloud Status:** A visual indicator (Cloud icon with a pulse) showing "Synced" or "Unsynced changes".
    *   **Sync Now Button:** A large button with a "Rotating Neon Arrows" animation during sync.
    *   **Pairing Card:** A dedicated section "Add New Device" that displays the pairing QR code.
    *   **UX Note:** Keep it extremely simple. "Syncing..." should be a background process with a subtle toast notification on success.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Atomic Store Swap (`rust-best-practices`)
*   **CRITICAL:** When pulling data from the cloud, do not overwrite `store.json` immediately. 
*   **Rule:** 
    1. Download and decrypt to a temporary `AppDataStore` struct.
    2. Validate the data (ensure the version matches and it's not empty).
    3. Perform an atomic file swap: `fs::rename(temp_path, live_path)`. This prevents "Half-Synced" states that result in data loss.

### 2. Cryptographic Best Practices (`rust-engineer`)
*   **Never use unsafe for crypto.** Use high-level crates like `aes-gcm`.
*   Store the sync key in the OS-level Keyring/Keychain (use the `keyring` crate) so the user doesn't have to type it every time the app opens.

### 3. Non-Blocking Networking (`rust-async-patterns`)
*   Cloud sync can be slow. You **MUST** ensure `reqwest` calls are asynchronous.
*   Use `tokio::select!` to allow the user to **cancel** a sync operation if it takes too long (e.g., if the network is dead).

### 4. Semantic Error Handling
*   Define specific error variants in `AppError`: `SyncConflict`, `DecryptionFailed`, `CloudUnreachable`. Provide friendly UI messages: "Incorrect Sync Password. Unable to decrypt cloud data."

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 23.1 (Sync Engine)**. Which crate will you use for encryption, and how will you manage the "Staging" of downloaded data before applying it to the local store? Do not write the full code until I approve the plan.