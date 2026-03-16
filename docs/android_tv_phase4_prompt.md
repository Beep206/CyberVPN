# Phase 4 Start: TV-Optimized UI Shell (Jetpack Compose)

Outstanding work on Phase 3! Your handling of the `VpnService` lifecycle, correct File Descriptor detachment, and structured concurrency usage is textbook Senior Android engineering.

We are now officially starting **Phase 4: TV-Optimized UI Shell**. This is where we build the visual foundation of our Android TV application using modern Jetpack Compose for TV. We want to deliver a "Console-like" premium experience.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 4.1: Compose for TV Setup
*   **Gradle Dependencies:** Update `apps/android-tv/app/build.gradle.kts` to include Jetpack Compose dependencies. 
    *   You will need the `androidx.compose.ui:ui`, `androidx.compose.material3:material3`, and crucially, the **`androidx.tv:tv-material`** and **`androidx.tv:tv-foundation`** libraries which provide components specifically built for TV (D-Pad navigation).
    *   Enable the `compose = true` feature in the Android buildFeatures block.
    *   Add `androidx.navigation:navigation-compose`.

### Task 4.2: Cyberpunk TV Theming
*   **Location:** Create `com.cybervpn.tv.ui.theme.Theme.kt` and `Color.kt`.
*   **Implementation:** 
    *   Define our signature Cyberpunk color palette (Neon Cyan, Matrix Green, Dark Backgrounds).
    *   Set up a `androidx.tv.material3.MaterialTheme` wrapper.
    *   *Anti-Burn-In Background:* Create a global background modifier or Box in your main theme wrapper that applies a very subtle, dark, moving gradient or noise texture. OLED TVs suffer from burn-in with static dark colors, so a dynamic background is a premium touch.

### Task 4.3: Main TV Activity & Navigation Shell
*   **Location:** Update `MainActivity.kt`.
*   **Implementation:** 
    *   Make `MainActivity` extend `ComponentActivity`. Set content to your main Compose App entry point.
    *   Create `com.cybervpn.tv.ui.AppNavigation.kt`. Define routes for: `Dashboard`, `Profiles`, and `Settings`.
    *   Create a side `androidx.tv.material3.NavigationDrawer`. The drawer should remain collapsed (icons only) when focused on the main content, and expand (show text labels) when the user presses `D-Pad Left` to focus on the drawer.

### Task 4.4: Scaffold Empty Screens
*   **Location:** Create `com.cybervpn.tv.ui.screens.DashboardScreen.kt`, `ProfilesScreen.kt`, and `SettingsScreen.kt`.
*   **Implementation:** Leave them mostly empty for now, just a centered `androidx.tv.material3.Text` so we can verify navigation works with the remote control.

---

## ⚠️ STRICT KOTLIN & COMPOSE SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `android-compose` and `kotlin-specialist` rules:

### 1. TV-Specific Composables ONLY
*   **Do not use standard `androidx.compose.material3.Button` or `Surface`.** 
*   You MUST use `androidx.tv.material3.Surface`, `androidx.tv.material3.Button`, and `androidx.tv.foundation.lazy.list.TvLazyColumn`. Standard Material 3 components do not properly handle D-Pad focus states (Focus Requesters) which are mandatory for Android TV.

### 2. State Hoisting
*   Keep your UI components stateless. Pass state down as values and events up as lambdas.
*   Do not instantiate ViewModels directly deep inside screen components. Pass the ViewModel or state into the top-level Screen composable from your Navigation graph.

### 3. Compose Architecture
*   Group UI files by feature (e.g., `ui/screens/dashboard`, `ui/screens/profiles`, `ui/theme`, `ui/components`).
*   Ensure all standard Compose compiler rules are met (no heavy computations in the composition phase).

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 4.1 and 4.2**. Show me a snippet of your `Color.kt` demonstrating the CyberVPN palette. Do not write the full code until I approve the plan.