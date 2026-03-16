# Android TV VPN Client: Comprehensive Development Plan (Pure Kotlin Edition)

**Target Device:** Android TV (Xiaomi, Sony, TCL, Philips, Google TV, etc.)
**Architecture:** Pure Kotlin (Android System/VpnService) + Jetpack Compose for TV (UI) + Sing-box (via official `libbox.aar`).
**Methodology:** Incremental, Phase-by-Phase Development for AI Agent execution following strict Kotlin Expert Guidelines.

This document outlines the step-by-step roadmap for building a premium, highly optimized VPN client for Android TV. This version utilizes a **100% Pure Kotlin** approach for parsing and config generation to ensure a rapid, native Android development cycle without the overhead of Rust NDK/JNI bridging. 

*All phases must strictly adhere to modern Kotlin 1.9+ idioms, including sealed classes for state modeling, structured concurrency (Coroutines & Flow), and strict null safety.*

---

## 🏗️ Phase 1: Workspace Initialization & Core Architecture
**Objective:** Set up the Android project and establish the foundational Clean Architecture using modern Android tech stacks.

*   **Task 1.1: Android Studio Project Scaffold**
    *   Create a new Android project (`apps/android-tv`) targeting Android TV (Leanback).
    *   Configure `build.gradle.kts` for Kotlin DSL, targeting minimum SDK 26 (Android 8.0).
    *   Integrate **Detekt** and **ktlint** into the Gradle build to enforce strict code quality rules before any commit.
*   **Task 1.2: Dependency Injection & Async**
    *   Integrate **Hilt** for Dependency Injection. Use primary constructors for injecting dependencies to promote immutability (`val`).
    *   Set up Kotlin Coroutines and Flow for reactive, non-blocking state management. Ensure strict adherence to structured concurrency (never use `GlobalScope`).
*   **Task 1.3: Sing-box Library Integration (`libbox.aar`)**
    *   Download the official `libbox.aar` release from the Sing-box repository.
    *   Include it as a module in the Android project. This provides a direct Kotlin API to start/stop the Sing-box engine without compiling raw binaries.

---

## 🧠 Phase 2: The Kotlin Parsing Engine (Porting Logic)
**Objective:** Rewrite the desktop Rust parsing logic into clean, type-safe Kotlin.

*   **Task 2.1: Data Models Definition**
    *   Create Kotlin `data class` structures for `ProxyNode` and `Subscription` using `kotlinx.serialization`. 
    *   Leverage Kotlin's null-safety (`?`) to explicitly define optional fields.
*   **Task 2.2: The URI Parser (`Parser.kt`)**
    *   Implement URL parsing utilizing Android's `android.net.Uri` or `java.net.URI`.
    *   Port the logic for parsing `vless://`, `vmess://`, `trojan://`, `ss://`, and `hysteria2://`.
    *   *Crucial:* Implement safe Base64 decoding using idiomatic scope functions (`let`, `run`) to handle URL-safe and standard padding variations gracefully without `!!` assertions.
*   **Task 2.3: Configuration Generator (`ConfigGenerator.kt`)**
    *   Create a class responsible for transforming a `ProxyNode` into the massive Sing-box JSON configuration string using `kotlinx.serialization` for type-safe JSON mapping.

---

## 🛡️ Phase 3: Android Native Core & VpnService
**Objective:** Implement the low-level Android networking logic using the official Sing-box library.

*   **Task 3.1: Android VpnService Implementation**
    *   Create `CyberVpnService.kt` extending Android's native `VpnService`.
    *   Use the `VpnService.Builder` to establish the `tun0` interface, setting MTU and intercepting DNS (e.g., `1.1.1.1`).
    *   Pass the TUN file descriptor (`fd`) to the `libbox` engine.
*   **Task 3.2: Foreground Service & Auto-Start**
    *   Implement a silent Foreground Service notification ("VPN Active") required by Android 8+.
    *   **Always-On VPN:** Register a `BroadcastReceiver` for `Intent.ACTION_BOOT_COMPLETED`. If the VPN was active before the TV lost power, immediately restart `CyberVpnService` on boot.
*   **Task 3.3: Lifecycle & Cancellation**
    *   Ensure proper teardown of resources in `onDestroy()`. Use `CoroutineScope.cancel()` to prevent memory leaks and dangling sockets when the service stops.

---

## 🎨 Phase 4: TV-Optimized UI Shell (Jetpack Compose)
**Objective:** Build the foundational UI layer optimized strictly for TV remotes (Spatial Navigation / D-Pad focus).

*   **Task 4.1: Compose for TV Setup**
    *   Integrate the `androidx.tv.material3` library (vital for `TvSurface`, `ImmersiveList`, and D-Pad focus states).
*   **Task 4.2: Cyberpunk Theming & Particle Engine**
    *   Implement our neon/dark-matrix theme using Compose `MaterialTheme`.
    *   **OLED Burn-in Protection:** Create a custom Compose Canvas background with slow-moving particles to ensure pixels are constantly shifting.
*   **Task 4.3: Layout & Navigation Shell**
    *   Implement a side navigation rail (Drawer) that expands when focused via D-Pad Left.
    *   Create scaffold screens: Dashboard, Profiles, Settings.

---

## 💾 Phase 5: Data Layer & Subscription Sync
**Objective:** Connect the UI to local storage and the network.

*   **Task 5.1: Local Database (Room)**
    *   Set up Android Room database with Kotlin Coroutine DAO interfaces (`suspend fun`) for `ProxyNode` and `Subscription`.
*   **Task 5.2: Subscription Fetcher (Ktor Client)**
    *   Implement an HTTP client using **Ktor Client** (idiomatic Kotlin networking) to download subscription URLs.
    *   Implement logic to decode Base64 subscription lists and parse Clash YAML using `jackson-dataformat-yaml`. Handle exceptions exhaustively to prevent crashes.
*   **Task 5.3: Repository & Flow State Modeling**
    *   Create `VpnRepository` using `sealed interface UiState<out T>` (Loading, Success, Error) to explicitly model the connection and data states.
    *   Expose Kotlin `StateFlow<UiState<ConnectionData>>` to the UI to reactively update the giant "Connect" button.

---

## 📺 Phase 6: The "Console" UX & Home Screen Widget
**Objective:** Make the application feel like a AAA commercial product, not a GitHub side-project.

*   **Task 6.1: D-Pad Focus Highlighting**
    *   Use `Modifier.onFocusChanged()`. Focused items must scale up slightly, gain a bright neon border (`--color-matrix-green`), and emit a soft drop-shadow.
*   **Task 6.2: Dashboard Connection UI**
    *   Build a massive, glowing connection toggle button. Use `collectAsStateWithLifecycle()` to safely consume the repository flows.
*   **Task 6.3: Android TV Home Screen Channel (Play Next)**
    *   Implement the `TvContractCompat` API to push a "Quick Connect" widget directly to the Android TV Home Screen.

---

## 📲 Phase 7: Frictionless Import (Device Code Flow)
**Objective:** Typing URLs on a TV screen is terrible UX. Implement a commercial-grade pairing system.

*   **Task 7.1: Local Web Server (Ktor Server)**
    *   Embed a lightweight **Ktor Server** inside the Android TV app (using `Netty` or `CIO` engine) utilizing coroutines for non-blocking requests.
*   **Task 7.2: The "Device Code" UI**
    *   When the user clicks "Import Profile", display a 6-character code and a local IP address (e.g., `http://192.168.1.50:8080`).
*   **Task 7.3: Mobile Pairing API**
    *   Create Ktor routing endpoints to receive `POST` requests.
    *   The user opens the IP on their phone browser, pastes their `vless://` link or Subscription URL, and clicks "Send to TV".
    *   The TV app receives the payload, parses it via `Parser.kt`, saves it to Room, and updates the `StateFlow` to refresh the UI instantly.

---

## ⚙️ Phase 8: Advanced Routing (Split Tunneling)
**Objective:** Give the user control over which TV apps use the proxy (e.g., YouTube) and which bypass it.

*   **Task 8.1: Installed Apps Retriever**
    *   Use Android `PackageManager` to fetch a list of installed applications with `suspend` functions and `Dispatchers.IO`.
*   **Task 8.2: Per-App Proxy UI**
    *   Build a TV-optimized list for users to toggle "Use VPN" per app.
*   **Task 8.3: VpnService Enforcement**
    *   Pass selected package names to `VpnService.Builder.addAllowedApplication()` or `addDisallowedApplication()`.

---

## 🚦 Phase 9: Optimization, QA, and Testing
**Objective:** Ensure the app passes Google's strict TV guidelines, is thoroughly tested, and runs smoothly.

*   **Task 9.1: Kotlin Testing & Coroutines (`runTest`)**
    *   Write multiplatform/unit tests using JUnit 5 and `MockK`.
    *   Use `runTest` and the `Turbine` library to test `StateFlow` emissions and repository logic rigorously.
*   **Task 9.2: Memory Profiling**
    *   Profile `libbox` memory usage and ensure all Kotlin coroutine scopes are correctly bound to Android lifecycles (e.g., `viewModelScope`).
*   **Task 9.3: Automated Build Pipeline**
    *   Set up a GitHub Actions workflow to build signed `.apk` (for USB sideloading) and `.aab` (for Google Play). Ensure `detekt` and `ktlint` checks run in CI and block failing builds.