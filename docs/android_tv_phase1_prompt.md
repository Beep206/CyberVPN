# Phase 1 Start: Android TV Project Scaffold & Core Architecture

Welcome! We are building a premium, highly optimized VPN client for Android TV (**CyberVPN TV**), following a "Pure Kotlin" architecture (no Rust/JNI bridging). 

We are officially starting **Phase 1: Workspace Initialization & Core Architecture**.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 1.1: Android Studio Project Scaffold
Create the base Android TV project structure.
*   **Location:** Create a new Android project inside `apps/android-tv`.
*   **Configuration (`build.gradle.kts`):**
    *   Use Kotlin DSL for all Gradle files.
    *   Target API 34, Minimum SDK 26 (Android 8.0).
    *   Set up Leanback support (in `AndroidManifest.xml`, declare `<uses-feature android:name="android.software.leanback" android:required="true" />`).
*   **Linting & Quality (`detekt` & `ktlint`):**
    *   Integrate the `detekt` and `ktlint` (or `spotless`) Gradle plugins.
    *   Configure the build to **fail** if any code quality rules are violated. This is non-negotiable.

### Task 1.2: Dependency Injection & Async Setup
Establish the structural foundation for the app.
*   **Hilt (DI):** Add Dagger Hilt dependencies and apply the Hilt plugin. Create the base `CyberVpnApplication.kt` class annotated with `@HiltAndroidApp`.
*   **Coroutines & Flow:** Add `kotlinx-coroutines-android`. Prepare the architecture to use `ViewModel` with `viewModelScope` and `StateFlow` for state management. 
*   **Serialization:** Add `kotlinx-serialization-json` for future data parsing.

### Task 1.3: Sing-box Library Integration (`libbox.aar`)
Instead of compiling raw binaries, we will use the official Sing-box Android library.
*   **Download & Integrate:** Write a Gradle script task or a shell script (e.g., `scripts/download_libbox.sh`) to download the latest `libbox.aar` from the official [Sing-box GitHub releases](https://github.com/SagerNet/sing-box/releases).
*   **Module Setup:** Add the `.aar` file as a local dependency in your `build.gradle.kts` (e.g., `implementation(files("libs/libbox.aar"))`).

---

## ⚠️ STRICT KOTLIN SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following Senior Kotlin patterns:

### 1. Immutability & Constructor Injection
*   When setting up Hilt, **always use primary constructor injection** with `private val` for dependencies. Do not use field injection (`@Inject lateinit var`) unless strictly required by Android framework components (like Activities/Services).
    ```kotlin
    @HiltViewModel
    class VpnViewModel @Inject constructor(
        private val repository: VpnRepository // Idiomatic and immutable
    ) : ViewModel() { ... }
    ```

### 2. Structured Concurrency
*   Never use `GlobalScope`. 
*   Bind all coroutines to a proper lifecycle using `viewModelScope.launch` or custom `CoroutineScope` bounded to service lifecycles. Ensure proper cancellation is inherently supported.

### 3. Null Safety & State Modeling
*   Prepare your base state models using `sealed interface` or `sealed class`. 
    ```kotlin
    sealed interface UiState<out T> {
        data object Loading : UiState<Nothing>
        data class Success<out T>(val data: T) : UiState<T>
        data class Error(val message: String, val cause: Throwable? = null) : UiState<Nothing>
    }
    ```
*   Use null safety explicitly (`?`, `?.`, `?:`). **Do not use the `!!` operator** anywhere in the codebase unless you document a strict mathematical proof of why it cannot be null.

### 4. Validation Before Committing
*   Before completing this phase, you MUST run `./gradlew detekt ktlintCheck` (or equivalent). Fix all warnings before submitting the code.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 1.1 and 1.2**. Tell me exactly which Gradle plugins and dependency versions you plan to add for Hilt, Coroutines, and Detekt. Do not write the full code until I approve the plan.