# Phase 6 Start: The "Console" UX & Home Screen Widget

Exceptional work on Phase 5! The repository layer perfectly utilizes `Dispatchers.Default` for heavy mapping, and the Room transaction safety combined with Ktor's strict timeouts is textbook Senior Kotlin engineering.

We are now officially starting **Phase 6: The "Console" UX & Home Screen Widget**. It is time to make the application feel like a AAA console product through TV-specific micro-interactions and deep OS integration.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 6.1: D-Pad Focus Highlighting
*   **Location:** Create a reusable modifier `com.cybervpn.tv.ui.components.TvFocusHighlight.kt`.
*   **Implementation:**
    *   Create a custom Compose `Modifier` that utilizes `onFocusChanged`.
    *   When the element gains focus, smoothly animate its scale (e.g., from `1.0f` to `1.05f`) using `animateFloatAsState`.
    *   Add a subtle drop shadow and a glowing border using our `NeonCyan` or `MatrixGreen` colors from the theme when focused.
    *   Apply this modifier to the `Card` or `Surface` components used in the `ProfilesScreen`.

### Task 6.2: Dashboard Connection UI
*   **Location:** `com.cybervpn.tv.ui.screens.dashboard.DashboardScreen.kt`.
*   **Implementation:**
    *   Inject the `VpnViewModel` (which should expose the `ConnectionState` from the repository). Use `collectAsStateWithLifecycle()` to safely observe the state.
    *   Build a massive, centralized "Connect / Disconnect" `androidx.tv.material3.Button` (or `Surface` acting as a button).
    *   The button should heavily utilize your new focus modifier and pulse/glow based on the current `UiState`.
    *   Add mock text elements below it for "Current IP" and "Upload/Download" speeds (we will wire these to real stats later).

### Task 6.3: Android TV Home Screen Channel (Play Next)
*   **Goal:** Allow users to connect to the VPN directly from the Android TV launcher, without opening the app.
*   **Dependencies:** Add `androidx.tvprovider:tvprovider` to `build.gradle.kts`.
*   **Implementation:** Create `com.cybervpn.tv.core.tv.TvChannelManager.kt`.
    *   Write a function to create a "Watch Next" program or a Custom Channel containing a "Quick Connect" card.
    *   The card's intent should directly launch `CyberVpnService` with the default configuration, bypassing the UI entirely.
    *   Call this initialization function once during the app's `MainActivity.onCreate` or via an `App Startup` initializer.

---

## ⚠️ STRICT KOTLIN & COMPOSE SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `android-compose` and `kotlin-specialist` rules:

### 1. Safe State Observation (`android-compose`)
*   Never use standard `.collectAsState()` in UI components. 
*   **You MUST use `.collectAsStateWithLifecycle()`** from the `androidx.lifecycle:lifecycle-runtime-compose` library. This ensures flows stop collecting when the TV app is put in the background, saving critical RAM and CPU cycles.

### 2. Composition Performance
*   When animating focus scale (Task 6.1), use `Modifier.graphicsLayer { scaleX = scale; scaleY = scale }` instead of wrapping the element in a resizing layout. `graphicsLayer` bypasses the expensive Layout and Measure phases of Compose, rendering the animation directly on the GPU.

### 3. Separation of Concerns
*   Keep the `TvChannelManager` entirely separated from the UI logic. Inject it via Hilt where necessary.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 6.1 (D-Pad Focus)**. Show me a snippet of the custom `Modifier` utilizing `graphicsLayer` and `animateFloatAsState`. Do not write the full code until I approve the plan.