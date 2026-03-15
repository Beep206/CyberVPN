# Throne-Alternative Desktop Client: Comprehensive Development Plan

**Target Agent:** Gemini 3.1 PRO (Antigravity Environment)
**Architecture:** Tauri v2 (UI) + Rust (System/Backend) + Sing-box (Core Engine as Child Process)
**Frontend Methodology:** Feature-Sliced Design (FSD)
**Language:** English

This document provides a highly detailed, step-by-step roadmap for developing a modern, high-performance cross-platform VPN/Proxy desktop application for Windows, macOS, and Linux. The goal is to surpass the original Qt-based Throne/Nekoray in UI/UX quality, memory safety, and maintainability by leveraging the absolute latest capabilities of the Rust and Web ecosystems.

---

## 🏗️ 0. Tech Stack & Architectural Guidelines

**Backend (System Logic):**
*   **Language:** Rust (Latest stable edition, strict Clippy rules).
*   **Framework:** Tauri v2 (Leveraging the latest IPC mechanisms, system tray, and native capabilities).
*   **Async Runtime:** `tokio` for handling non-blocking I/O, process management, and IPC.
*   **Serialization:** `serde`, `serde_json` for config generation.
*   **Core Engine:** `sing-box` (managed as a standalone binary/child process).
*   **Privilege Management:** Custom Rust implementations or Tauri plugins for UAC (Windows), Polkit (Linux), and Authorization Services (macOS).

**Frontend (UI/UX):**
*   **Framework:** React 19 + TypeScript (Strict mode).
*   **Build Tool:** Vite.
*   **Architecture:** Feature-Sliced Design (FSD) for supreme modularity and scalability.
*   **Styling:** Tailwind CSS v4 (or latest v3 with JIT) + `shadcn/ui` for accessible, highly customizable base components.
*   **Animations:** `framer-motion` for fluid, native-feeling transitions and micro-interactions.
*   **State Management:** Zustand (for lightweight global state) + TanStack Query (for asynchronous IPC calls to Rust).
*   **Data Visualization:** `recharts` or `visx` for real-time traffic speed graphs.

---

## 🚀 Phase 1: Project Initialization & Workspace Setup

**Objective:** Establish a solid foundation with the latest tools, ensuring the boundary between the frontend (Web) and backend (Rust) is cleanly defined.

*   **Task 1.1: Scaffold the Tauri v2 Workspace**
    *   Initialize a new Tauri v2 project (`npm create tauri-app@latest`).
    *   Configure the Rust environment (Cargo.toml). Set up optimal release profiles (LTO, opt-level = 'z' for binary size reduction, strip symbols).
    *   Set up absolute path aliases in both Vite (`@/*`) and TSConfig to support FSD.
*   **Task 1.2: Establish Frontend FSD Structure**
    *   Create the standard FSD directories inside `src/`:
        *   `app/` (Global providers, routing, global styles)
        *   `pages/` (Page-level components like Home, Settings, Logs)
        *   `widgets/` (Complex layout blocks like Sidebar, ConnectionCard)
        *   `features/` (User interactions like StartConnection, ImportProfile)
        *   `entities/` (Business logic domains like ProxyProfile, Node, RoutingRule)
        *   `shared/` (UI kit, utilities, API/IPC wrappers, types).
*   **Task 1.3: UI Framework & Theme Initialization**
    *   Install Tailwind CSS and configure it.
    *   Initialize `shadcn/ui` and configure the theme palette to match the web frontend's visual identity (Dark mode by default, high-contrast accents).
    *   Set up a global ThemeProvider in `app/`.
*   **Task 1.4: Sing-box Binary Provisioning Strategy**
    *   Create a Rust build script (`build.rs`) or a startup routine that automatically downloads the correct `sing-box` binary for the target OS and architecture if it is not embedded.
    *   Define the directory structure for storing binaries, configs, and logs (using Tauri's `AppDirs` API for standard OS paths).

---

## ⚙️ Phase 2: Rust Backend Foundation & IPC

**Objective:** Build a robust, memory-safe backend capable of managing the Sing-box process and securely communicating with the React frontend.

*   **Task 2.1: Tauri IPC Commands Setup**
    *   Define the core Rust commands (`#[tauri::command]`) to handle frontend requests.
    *   Implement strictly typed request/response models using `serde`.
    *   Create a `shared/api/ipc.ts` file on the frontend to wrap Tauri's `invoke` calls with strict TypeScript interfaces mirroring the Rust structs.
*   **Task 2.2: Sing-box Process Manager**
    *   Implement a stateful manager in Rust using `tokio::process::Command`.
    *   Features required: Start, Stop, Restart, and Check Status.
    *   Capture `stdout` and `stderr` asynchronously from Sing-box and forward them to the frontend using Tauri Events (`app.emit_all`).
*   **Task 2.3: Configuration Generator (The Bridge)**
    *   Create Rust data structures representing the vast Sing-box JSON configuration schema.
    *   Implement a builder pattern that takes user settings (from the frontend/database) and constructs a valid, highly optimized `config.json` for Sing-box.
*   **Task 2.4: Local State Persistence**
    *   Integrate a lightweight embedded database or structured file storage on the Rust side (e.g., `sled`, `sqlite` via `sqlx`, or simply serialized JSON files managed by Rust) to store user profiles, routing rules, and application settings securely.

---

## 🎨 Phase 3: Frontend Foundation & Core UX

**Objective:** Construct the "skeleton" of the application with a focus on a breathtaking, modern, native-feeling user experience.

*   **Task 3.1: Application Layout & Navigation**
    *   Develop the main application shell (`widgets/Layout`).
    *   Implement a sleek, collapsible sidebar navigation with active state indicators.
    *   Use Framer Motion to animate page transitions (e.g., sliding or fading smoothly between 'Dashboard', 'Profiles', and 'Settings').
*   **Task 3.2: The Dashboard (Main View)**
    *   Design a massive, beautiful central "Connect" button. It should have idle, connecting, connected, and error states with intricate micro-animations.
    *   Integrate a real-time traffic graph component (`widgets/TrafficGraph`) below the connection status.
    *   Display current IP, active node, and connection duration.
*   **Task 3.3: Profile Management UI (Entities & Features)**
    *   Create a clean, list-based or grid-based view for proxy nodes (`entities/Node/ui`).
    *   Implement Ping/Latency indicators with color-coding (Green < 100ms, Yellow < 200ms, Red > 200ms).
    *   Add features to sort, search, and group profiles.

---

## 🔌 Phase 4: Core VPN Functionality (Data Flow)

**Objective:** Connect the beautiful UI to the Rust backend to make the application actually work.

*   **Task 4.1: Profile Import Mechanisms**
    *   Implement parsers (first in Rust, optionally in TS) for standard share links (e.g., `vless://`, `hysteria2://`, `trojan://`).
    *   Support importing via clipboard (`features/ImportFromClipboard`).
    *   Support importing via subscription URLs (fetching and decoding base64 data).
*   **Task 4.2: Connection Lifecycle Management**
    *   Wire the central "Connect" button to a Tauri command (`start_proxy`).
    *   Pass the selected profile ID to Rust.
    *   Rust generates the Sing-box config, writes it to a secure temp directory, and spawns the Sing-box process.
    *   Rust emits a `connection_status_changed` event back to the frontend to update the UI (Connecting -> Connected).
*   **Task 4.3: Real-time Statistics**
    *   Configure Sing-box to expose its experimental stats API, or parse its logs.
    *   Rust reads the upload/download byte counts and emits a `traffic_update` event every 1 second.
    *   Frontend consumes this event to update the Dashboard graphs and current speed labels.

---

## 🛡️ Phase 5: System Integration & Privilege Management (Crucial)

**Objective:** Implement the complex, OS-specific logic required for TUN interfaces and System DNS.

*   **Task 5.1: TUN Interface Preparation (OS Specific)**
    *   **Windows:** Implement logic to ensure Wintun drivers are available or utilize Sing-box's built-in stack. Require UAC elevation when TUN is toggled on.
    *   **Linux:** Implement `pkexec` or capability manipulation (`setcap`) to allow the Sing-box process to manage `tun0` without running the entire GUI as root.
    *   **macOS:** Utilize Apple's NetworkExtension framework (very complex, requires specific entitlements) or fallback to generic TUN with `osascript` privilege prompts.
*   **Task 5.2: System Helper Service (Optional but Recommended)**
    *   To avoid prompting for admin rights every time, design a lightweight Rust background service (Daemon) that runs as root/admin.
    *   The user-facing Tauri app communicates with this Daemon via Local Sockets/Named Pipes to request interface changes securely.
*   **Task 5.3: Strict DNS Leak Protection**
    *   Implement logic in Rust to backup system DNS settings before connection and forcefully route DNS through the Sing-box `dns` outbound module.
    *   Ensure perfect cleanup (restoring original DNS) even if the app crashes unexpectedly (using panic hooks and signal handlers in Rust).

---

## 🔀 Phase 6: Advanced Routing & Customization

**Objective:** Provide power-user features comparable to Nekoray, but with a drastically improved UX.

*   **Task 6.1: Visual Rule Builder**
    *   Create a UI for defining routing rules (e.g., "Route domain `*.openai.com` to `Proxy`, route `*.ru` to `Direct`).
    *   Translate these visual rules into Sing-box's complex JSON routing structure via the Rust backend.
*   **Task 6.2: Outbound Chains (Multi-hop)**
    *   Build a UI feature allowing users to drag-and-drop nodes to create a chain (e.g., User -> Server A -> Server B -> Internet).
    *   Implement the backend logic to generate the nested `outbounds` array in the Sing-box configuration.
*   **Task 6.3: Custom Configuration Override**
    *   Provide an advanced code editor view (using Monaco Editor or CodeMirror in React) for users who want to write raw JSON configuration.

---

## ✨ Phase 7: UI Polish & Desktop Capabilities

**Objective:** Make the application feel like a native, premium desktop tool.

*   **Task 7.1: System Tray Integration**
    *   Use Tauri's System Tray API to create a context menu (Connect/Disconnect, Quit, Show App).
    *   Implement tray icon color changes based on connection status.
    *   Allow the app to minimize to the tray instead of closing.
*   **Task 7.2: Global Hotkeys**
    *   Register system-wide shortcuts via Tauri (e.g., `Ctrl+Shift+C` to toggle connection).
*   **Task 7.3: Deep Linking**
    *   Register a custom URI scheme (e.g., `throne://`) in the OS registry via Tauri configuration so that clicking links in a web browser directly opens the app and imports a profile.
*   **Task 7.4: Window Management**
    *   Implement frameless window design (custom title bar with window controls styled to match the app theme) using Tauri's window customization flags.

---

## 🧪 Phase 8: Testing, Security & Optimization

*   **Task 8.1: Memory Profiling**
    *   Profile the Rust backend to ensure no memory leaks occur during prolonged Sing-box execution.
*   **Task 8.2: Security Auditing**
    *   Ensure IPC payload validation. Do not blindly execute or parse parameters passed from the frontend without strict sanitization in Rust.
*   **Task 8.3: E2E Testing**
    *   Set up Playwright or WebdriverIO to test the Tauri application end-to-end (simulating clicks on the React UI and verifying Rust backend responses).

---

## 📦 Phase 9: CI/CD & Deployment

*   **Task 9.1: GitHub Actions Configuration**
    *   Set up matrix builds to compile the application for `windows-latest`, `macos-latest`, and `ubuntu-latest`.
    *   Configure code signing for Windows (Authenticode) and macOS (Developer ID and Notarization) to prevent "Unknown Publisher" warnings.
*   **Task 9.2: Auto-Updater**
    *   Integrate Tauri's built-in auto-updater.
    *   Set up a mechanism (e.g., GitHub Releases or a custom update server) to serve update manifests.
    *   Implement a subtle, non-intrusive UI notification when a new version is available.
