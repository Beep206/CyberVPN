# Phase 26 Start: Post-Quantum Security Integration (PQC Era)

Exceptional execution on the AI-Traffic Reshaping! We are now at the absolute bleeding edge of cybersecurity. Phase 26 introduces **Post-Quantum Cryptography (PQC)** to CyberVPN. 

The primary goal is to protect our users against **"Harvest Now, Decrypt Later" (HNDL)** attacks by adversaries who are currently storing encrypted traffic to decrypt it once cryptographically relevant quantum computers (CRQCs) emerge.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 26.1: Quantum-Resistant Handshake Config (Rust)
We need to enable hybrid post-quantum key exchange in our proxy engine.
*   **Implementation:** Update `engine::config::generate_singbox_config`.
*   **Logic:** 
    *   When a user enables "Post-Quantum Protection" for a VLESS-Reality or WireGuard node, inject the **`mlkem768x25519plus`** (hybrid classical/post-quantum) handshake algorithm into the configuration.
    *   This ensures that even if the classical X25519 part is broken in the future, the session remains secured by NIST-standardized ML-KEM (Kyber).
*   **Storage:** Add `pqc_enabled: bool` to `ProxyNode` and a global `pqc_enforcement_mode: bool` to `AppDataStore`.

### Task 26.2: Quantum Readiness Audit Engine (Rust)
Create a diagnostic tool that scans all user profiles.
*   **Implementation:** Create a command `audit_quantum_readiness() -> Vec<AuditResult>`.
*   **Logic:** Iterate through all profiles and check their protocols and settings.
    *   *VLESS-Reality:* Ready (if PQC flag is set).
    *   *Hysteria2/TUIC:* Partially ready (QUIC usually handles PQC at the transport layer).
    *   *Legacy Shadowsocks/SOCKS:* Not ready (marked as vulnerable).
*   **Output:** A structured report indicating which nodes are future-proof.

### Task 26.3: "Quantum Forge" Security UI (React)
Implement a visually stunning security dashboard.
*   **Location:** `src/pages/Security/` (Expand the existing page).
*   **Implementation:**
    *   **The Audit Tool:** A "Quantum Scanner" button with a high-tech "scanning" animation.
    *   **Visual Indicators:** Show a "Quantum Shield" badge (using a shimmering purple/indigo effect) next to servers that have PQC enabled.
    *   **Educational Micro-copy:** Add short, tool-tipped explanations: *"Hybrid ML-KEM-768 is active. This session is mathematically secured against quantum computer decryption."*
    *   **Framer Motion:** Use "Digital Rain" or "Particle Swarm" effects to symbolize quantum-resistant protection.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-best-practices` rules:

### 1. Cryptographic Agility (`rust-best-practices`)
*   Do not hardcode the string `"mlkem768x25519plus"` everywhere. 
*   **Rule:** Create an enum `PqcAlgorithm` in `models.rs` so we can easily swap or add new NIST standards (like ML-KEM-1024) in the future without refactoring the core logic.

### 2. Zero-Copy String Processing (`rust-engineer`)
*   When generating the audit report for 100+ profiles, use iterators and references efficiently. Avoid cloning entire `ProxyNode` objects just to check a protocol field.

### 3. Graceful Error Fallbacks (`rust-engineer`)
*   Some older `Xray` or `Sing-box` versions might not support PQC handshakes. 
*   **Rule:** Implement a version check logic in `Provisioning`. If the local binary is too old to support ML-KEM, return an `AppError::UnsupportedCoreVersion` and prompt the user to update the geo-assets/core.

### 4. Semantic JSON Building
*   The `generate_singbox_config` function is getting large. Group the PQC logic into a separate internal helper function `apply_pqc_settings(config: &mut Map<String, Value>, node: &ProxyNode)`.

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 26.1 (Handshake Config)**. Show me the `PqcAlgorithm` enum and how you plan to modify the `generate_singbox_config` signature to handle the new global enforcement mode. Do not write the full code until I approve the plan.