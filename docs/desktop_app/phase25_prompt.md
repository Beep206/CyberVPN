# Phase 25 Start: AI-Traffic Reshaping (Anti-DPI Defense)

Welcome to the future of VPN security! We have completed the standard features and our first set of "Killer Features." Now, we are entering the **Ultra-Stealth Era**. 

Phase 25 focuses on **AI-Traffic Reshaping**. Modern ISPs use machine learning to identify VPN tunnels based on packet sizes and timing patterns. We will counter this by implementing dynamic traffic "Camouflage" using the latest `sing-box` core capabilities.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 25.1: Advanced Obfuscation Config (Rust)
We need to update our configuration generator to utilize Sing-box's sophisticated anti-DPI fields.
*   **Implementation:** Update `engine::config::generate_singbox_config`.
*   **Features to add:**
    *   **Dynamic Padding:** Inject `padding` settings into VLESS/Reality outbounds. This adds random bytes to the handshake and data packets to mask their size.
    *   **Handshake Jitter:** Configure `tcp_check_http` and `multiplex` settings to introduce artificial timing delays, mimicking human browsing behavior.
    *   **XHTTP Transport:** Add support for the new `xhttp` transport which splits upload and download traffic into different streams, making traffic analysis significantly harder.

### Task 25.2: The "Stealth Jitter" Engine (Rust)
To prevent "Static Fingerprinting," we shouldn't use the same obfuscation settings every time.
*   **Logic:** Implement a module that generates slightly randomized obfuscation parameters (e.g., random padding range `100-500` vs `200-600`) upon every connection attempt.
*   **Storage:** Add a `stealth_mode_enabled` boolean to `AppDataStore`.

### Task 25.3: "Stealth Wave" Visualizer (React)
Create a high-tech UI component that visualizes the "Camouflage" in action.
*   **Location:** Dashboard.
*   **Implementation:** 
    *   Add a "Stealth Camouflage" toggle switch with a "Neon Shadow" effect.
    *   Create a `<StealthWave />` component using HTML5 Canvas or SVG + `framer-motion`.
    *   **Visual:** A smooth, oscillating wave that changes its frequency and amplitude in real-time. When Stealth is ON, the wave should look more "noisy" or "complex" to symbolize packet reshaping.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer` and `rust-async-patterns` rules:

### 1. Zero-Cost JSON Randomization (`rust-best-practices`)
*   When generating the randomized padding values, use the `rand` crate efficiently. 
*   **Rule:** Do not re-seed the RNG every time. Use a thread-local or shared RNG state managed via Tauri's State.

### 2. Precise Type Mapping (`rust-engineer`)
*   Sing-box's new `xhttp` and `padding` fields have complex nested structures. 
*   **Rule:** Do not use `serde_json::json!` macros for the entire config. Define typed sub-structs for `PaddingConfig` and `XhttpConfig` to ensure compile-time safety and prevent typos in JSON keys.

### 3. Non-Blocking Stat Polling (`rust-async-patterns`)
*   If the "Stealth Wave" needs real-time data from the engine, ensure the polling task in `ProcessManager` remains lightweight. 
*   **Rule:** Use `tokio::sync::watch` or a similar broadcast mechanism if multiple UI components (Graph + Stealth Wave) need access to the same traffic stream.

### 4. Semantic UI State
*   The transition to Stealth Mode should feel impactful. When toggled, the Dashboard background color should shift slightly (e.g., from Deep Blue to a dark Matrix Green).

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 25.1 (Advanced Obfuscation)**. Specifically, how will you structure the Rust structs for Sing-box's `padding` and `xhttp` settings to avoid using raw untyped JSON? Do not write the full code until I approve the plan.