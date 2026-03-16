# Phase 8 Start: Advanced Routing (Split Tunneling)

Fantastic execution on Phase 7! The embedded Ktor server runs flawlessly on a background thread without blocking the UI, and the HTML response perfectly bridges the gap between the user's phone and the TV. 

We are now officially starting **Phase 8: Advanced Routing (Split Tunneling)**. This is a critical feature for Android TV. Users often want to route specific apps (like YouTube) through the VPN, while letting local apps (like their local IPTV provider or Plex) bypass it entirely.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 8.1: Installed Apps Retriever
*   **Location:** Create `com.cybervpn.tv.core.system.AppManager.kt` (injected via Hilt).
*   **Implementation:**
    *   Use the Android `PackageManager` (`context.packageManager`) to fetch a list of installed applications (`getInstalledPackages`).
    *   Filter out core system apps that shouldn't be routed (e.g., `com.android.systemui`). Focus on user-facing apps.
    *   Return a data class: `data class TvApp(val packageName: String, val name: String, val icon: Drawable)`.
    *   *Crucial:* Fetching this list is slow. Ensure this function is marked `suspend` and runs on `Dispatchers.IO`.

### Task 8.2: Per-App Proxy UI
*   **Location:** Update `com.cybervpn.tv.ui.screens.settings.SettingsScreen.kt` (or create a dedicated `PerAppScreen.kt`).
*   **Implementation:**
    *   Use `androidx.tv.foundation.lazy.list.TvLazyColumn` to display the list of fetched `TvApp` objects.
    *   Add a `androidx.tv.material3.Switch` or `Checkbox` (if standard switch doesn't map well to TV Focus) next to each app.
    *   When the user toggles an app, save its `packageName` to the Room Database or DataStore (e.g., a list of `bypass_packages`).

### Task 8.3: VpnService Enforcement
*   **Location:** `com.cybervpn.tv.service.CyberVpnService.kt`.
*   **Implementation:**
    *   Before calling `builder.establish()`, you must read the user's routing preferences from your Repository/DataStore.
    *   Iterate through the saved list of package names.
    *   Call `builder.addDisallowedApplication(packageName)` for apps that should bypass the VPN, OR call `addAllowedApplication(packageName)` for apps that must use it (depending on how you structure the "Mode" toggle: Bypass vs Route).
    *   *Note:* Ensure you catch `PackageManager.NameNotFoundException` if an app was uninstalled between the time it was saved and the VPN starting.

---

## ⚠️ STRICT KOTLIN & ANDROID SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `kotlin-specialist` and Android guidelines:

### 1. The PackageManager Performance Trap
*   Calling `getPackageManager().getInstalledPackages()` and extracting icons (`loadIcon`) is a notoriously heavy IPC operation that will freeze the Main Thread and cause skipped frames.
*   You **MUST** wrap the entire fetching and mapping process inside `withContext(Dispatchers.IO)`. Do not pass raw `Drawable` objects around in ViewModels; if necessary, cache them or hold them in a tightly bound state.

### 2. UI State Modeling for the App List
*   Use your established `sealed interface UiState<T>` to manage the loading of the app list.
*   Show a loading spinner (`CircularProgressIndicator`) while `Dispatchers.IO` is fetching the 100+ installed packages.

### 3. VpnService Immutability Rule
*   Changes to `addDisallowedApplication` **do not take effect** while the VPN is actively running.
*   If the user changes their Split Tunneling settings while connected, you must either automatically disconnect and reconnect the `CyberVpnService`, or show a Toast/Snackbar telling the user: "Settings saved. Please reconnect the VPN for changes to apply."

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 8.1 and 8.3**. Explain how you will handle the `PackageManager` call asynchronously without blocking the UI. Do not write the full code until I approve the plan.