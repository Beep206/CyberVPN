# Phase 9 Start: Optimization, QA, and Play Store Prep

Incredible execution on Phase 8! Your handling of the `PackageManager` on the `IO` dispatcher and the reactive `combine` operator in the ViewModel is a perfect demonstration of Senior Kotlin architecture.

We have reached the absolute final stage of our Android TV application. We are now officially starting **Phase 9: Optimization, QA, and Play Store Prep**. This phase ensures our app will not be rejected by Google Play and runs flawlessly on low-end 1GB RAM TVs.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 9.1: Kotlin Unit Testing (`runTest`)
*   **Dependencies:** Add `org.jetbrains.kotlinx:kotlinx-coroutines-test`, `io.mockk:mockk`, and `app.cash.turbine:turbine` to your `build.gradle.kts` (testImplementation).
*   **Implementation:**
    *   Create `VpnViewModelTest.kt` or `PerAppViewModelTest.kt`.
    *   Write a unit test utilizing `runTest { ... }` and Turbine (`uiState.test { ... }`) to assert that the `UiState` correctly transitions from `Loading` to `Success` when the repository emits data.
    *   *Note:* Ensure you inject a `TestDispatcher` (e.g., `UnconfinedTestDispatcher`) to override the Main dispatcher for tests.

### Task 9.2: Leanback Compliance (TV Banner)
*   Google Play **will reject** an Android TV app if it lacks a Leanback Banner.
*   **Implementation:**
    *   Create a simple `320x180` banner image (you can generate a mock placeholder image using `convert` or similar CLI tools, e.g., a black rectangle with the word "CYBERVPN" in neon green).
    *   Save it in `apps/android-tv/app/src/main/res/drawable/banner.png`.
    *   Declare it in the `AndroidManifest.xml` under the `<application>` tag: `android:banner="@drawable/banner"`.

### Task 9.3: Automated Build Pipeline (GitHub Actions)
*   **Location:** Create `.github/workflows/android-tv-release.yml`.
*   **Implementation:**
    *   Trigger on `tags: ['tv-v*']`.
    *   Use `ubuntu-latest` and `actions/setup-java@v4` (Java 17).
    *   Step 1: Grant execute permissions: `chmod +x gradlew`
    *   Step 2: Run Linters & Tests: `./gradlew detekt ktlintCheck testReleaseUnitTest`
    *   Step 3: Build AAB and APK: `./gradlew bundleRelease assembleRelease`
    *   Step 4: Upload artifacts to the GitHub Release.
    *   *(Leave placeholders for signing keystores using environment variables, as is standard practice).*

---

## ⚠️ STRICT KOTLIN & QA SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `kotlin-specialist` rules:

### 1. Coroutine Testing Standards (`runTest`)
*   Never use `runBlocking` in your tests when dealing with `StateFlow` or Delays. 
*   You must use the modern `kotlinx.coroutines.test.runTest` API.
*   Use `Turbine` to test StateFlow emissions cleanly:
    ```kotlin
    viewModel.uiState.test {
        assertEquals(UiState.Loading, awaitItem())
        val successState = awaitItem() as UiState.Success
        assertTrue(successState.data.isNotEmpty())
        cancelAndIgnoreRemainingEvents()
    }
    ```

### 2. Mocking Guidelines (`MockK`)
*   Use `mockk` to mock your `AppManager` and `RoutingRepository`. Do not spin up a real Room database or Android Context in a local JUnit test.
*   Use `coEvery { ... } returns ...` to mock `suspend` functions and flows gracefully.

### 3. CI/CD Strictness
*   Your GitHub Action MUST fail if `detekt` or `ktlintCheck` fails. Do not use `--continue` or ignore failures in the CI pipeline. This guarantees our `main` branch code remains perfectly idiomatic forever.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 9.1 (Kotlin Unit Testing)**. Show me a snippet of how you will set up the `MainDispatcherRule` to inject the `UnconfinedTestDispatcher` for your ViewModel tests. Do not write the full code until I approve the plan.