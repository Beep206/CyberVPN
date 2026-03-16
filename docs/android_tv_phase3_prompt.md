# Phase 3 Start: Android Native Core & VpnService

Excellent work on Phase 2! Your `VpnParser` and `ConfigGenerator` implementations are highly idiomatic. The use of `runCatching`, safe Base64 fallback decoding, and the `kotlinx.serialization` JSON builder DSL perfectly aligns with Senior Kotlin standards.

We are now moving to **Phase 3: Android Native Core & VpnService**. This is where we integrate the Android OS networking layer with the official `libbox.aar` engine to intercept and route the TV's traffic.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 3.1: Sing-box Engine Wrapper
*   **Location:** Create `com.cybervpn.tv.core.engine.SingboxEngine.kt`.
*   **Implementation:** Create a Singleton object or an interface/implementation (e.g., `SingboxEngineImpl`) that manages the `libbox` lifecycle.
*   **Methods:** It should expose `suspend fun start(configJson: String, tunFd: Int)` and `suspend fun stop()`.
*   *Note:* The actual classes inside `libbox.aar` usually revolve around `libbox.Box` or `libbox.CommandClient`. You will need to start the engine and pass the file descriptor of the TUN interface to it so it can process raw packets.

### Task 3.2: CyberVpnService Implementation
*   **Location:** Create `com.cybervpn.tv.service.CyberVpnService.kt` extending `android.net.VpnService`.
*   **Manifest:** Don't forget to declare this service in `AndroidManifest.xml` with `android:permission="android.permission.BIND_VPN_SERVICE"`. Add the `<intent-filter>` for `android.net.VpnService`.
*   **Implementation:**
    *   In `onStartCommand`, extract the JSON configuration string passed via the Intent extras.
    *   Use `Builder()` to configure the TUN interface:
        *   `addAddress("172.19.0.1", 30)`
        *   `addDnsServer("1.1.1.1")`
        *   `setMtu(1500)`
        *   `establish()` -> This returns a `ParcelFileDescriptor`.
    *   Pass the `fd.detachFd()` (the raw integer file descriptor) and the JSON config to your `SingboxEngine.start(...)` within a coroutine.

### Task 3.3: Foreground Service Notification
*   Android 8+ strictly requires VPNs to run as Foreground Services.
*   **Implementation:** Inside `CyberVpnService`, create a Notification Channel and build a persistent notification indicating "CyberVPN is active". Call `startForeground(NOTIFICATION_ID, notification)`.

### Task 3.4: Always-On & Boot Receiver
*   **Location:** Create `com.cybervpn.tv.receiver.BootReceiver.kt` extending `BroadcastReceiver`.
*   **Implementation:** Listen for `Intent.ACTION_BOOT_COMPLETED`. Check SharedPreferences/DataStore if the VPN was active before shutdown. If yes, automatically start `CyberVpnService`.
*   **Manifest:** Declare the receiver and request `android.permission.RECEIVE_BOOT_COMPLETED`.

---

## ⚠️ STRICT KOTLIN SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following Senior Kotlin patterns:

### 1. Service Lifecycle & Coroutine Scopes (`rust-async-patterns` equivalent)
*   **Never use `GlobalScope`** to launch the Sing-box engine inside the Service.
*   The `VpnService` should have its own `CoroutineScope` bound to the Service's lifecycle.
*   **The "Clean Teardown" Guarantee:** In the service's `onDestroy()` method, you MUST call `scope.cancel()` and explicitly call `SingboxEngine.stop()` to ensure the `libbox` binary process terminates and does not leak memory or lock the TUN interface.

### 2. File Descriptor Safety
*   When dealing with the `ParcelFileDescriptor` returned by `Builder.establish()`, ensure it is safely closed if the engine fails to start. Use the `.use { }` block or a `try-finally` block to prevent file descriptor leaks.

### 3. Intent Extras Nullability
*   When extracting the configuration JSON from the intent in `onStartCommand`:
    `val config = intent?.getStringExtra(EXTRA_CONFIG) ?: return START_NOT_STICKY`
    Handle null intents gracefully (they occur when the system restarts the service automatically).

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 3.1 and 3.2**. Explain how you will structure the `CoroutineScope` inside the `VpnService` to ensure the Sing-box engine is cleanly stopped when the user disconnects. Do not write the full code until I approve the plan.