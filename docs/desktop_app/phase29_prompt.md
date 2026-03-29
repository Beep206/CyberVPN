# Phase 29 Start: Stealth Lab & Censorship Probe (Advanced Diagnostics)

Outstanding work on the automation engine! We are now at the final implementation phase of the "Ultra-Stealth & Quantum" roadmap: **Phase 29: Stealth Lab**. 

This is the most advanced feature yet—a built-in "Connection Doctor." When a user says "It's not working," instead of technical support, they click a button. The app performs a forensic analysis of their ISP's censorship methods and automatically reconfigures the protocol to bypass them.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 29.1: Censorship Probe Engine (Rust Backend)
We need to implement a diagnostic suite that "probes" the network without using the proxy core.
*   **Implementation:** Create `engine::sys::diagnostics.rs`.
*   **The Probes:**
    1.  **IP Connectivity Probe:** Perform raw `TcpStream::connect` to the server IP (Check if the IP itself is blocked).
    2.  **SNI Filter Probe:** Try a TLS handshake with a forbidden SNI (e.g., `google.com`) vs. a neutral SNI. If the forbidden one fails but the neutral one works, SNI filtering is active.
    3.  **UDP/QUIC Block Probe:** Attempt a UDP handshake (Hysteria2 style). If timed out, the ISP is blocking or throttling UDP.
    4.  **TLS Handshake Audit:** Check if the ISP is using "TLS Reset" or "TLS interception" by comparing cert fingerprints.
*   **Command:** `run_stealth_diagnostics() -> Result<CensorshipReport, AppError>`.

### Task 29.2: Intelligent Protocol Resolver (Rust Backend)
*   **Implementation:** Create a logic engine that interprets the `CensorshipReport`.
*   **Logic:**
    *   If UDP is blocked -> Recommend **XHTTP** (TCP-based).
    *   If SNI is filtered -> Recommend **Reality** with a specific local SNI mask.
    *   If IP is blocked -> Recommend using a **Cloudflare Warp** entry node or a different server.
    *   If AI-Pattern recognition is suspected -> Automatically enable **Phase 25 Stealth Reshaping**.

### Task 29.3: "Stealth Lab" Wizard UI (React Frontend)
Create a UI that feels like a high-end diagnostic laboratory.
*   **Location:** New "Stealth Lab" tab or an "Emergency" button on the Dashboard.
*   **Features:**
    *   **The Diagnostic Terminal:** A "Matrix-style" scrolling log showing the probes in real-time: *"Probing UDP connectivity... [BLOCKED]. Analyzing TLS Fingerprint... [INTERCEPTED]"*.
    *   **Actionable Results:** A summary screen: *"Diagnosis: Your ISP is using Advanced DPI to block UDP. Solution: XHTTP Camouflage."*
    *   **"Fix It For Me" Button:** A single button that applies the recommended settings to the current profile and reconnects.
    *   **Visual Design:** Use dark indigo and neon magenta accents to differentiate this "Expert Mode" from the standard UI.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Parallel Probing (`rust-async-patterns`)
*   **Rule:** Do not run probes sequentially. The user shouldn't wait 30 seconds for diagnostics.
*   **Implementation:** Use `tokio::join!` or `JoinSet` to run the TCP, UDP, and SNI probes concurrently. Set a strict `5-second` timeout for each probe.

### 2. Raw Socket Handling & Safety (`rust-engineer`)
*   If you use the `tokio::net::UdpSocket` or specialized TLS crates for probing, ensure no raw pointers are left dangling. 
*   **Rule:** Every network error must be caught and categorized. Never let a timeout in a diagnostic probe result in a `panic!`.

### 3. Non-Intrusive Probing (`rust-best-practices`)
*   **Rule:** Diagnostics must not modify the global `AppDataStore` until the user clicks "Fix It." 
*   **Implementation:** Store the `CensorshipReport` in-memory only (using a Tauri State) until the final confirmation.

### 4. Descriptive Diagnostic Errors
*   Provide "Expert" reasons in the `AppError`: `AppError::IspHandshakeReset`, `AppError::UdpThrottlingDetected`. This helps power users debug their environment.

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 29.1 (Probe Engine)**. Specifically, how will you perform an SNI filtering test without triggering a permanent IP ban from the ISP? Do not write the full code until I approve the plan.