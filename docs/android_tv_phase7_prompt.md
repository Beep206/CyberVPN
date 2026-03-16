# Phase 7 Start: Frictionless Import (Device Code Flow)

Incredible execution on Phase 6! The hardware-accelerated `graphicsLayer` animations and the `TvContractCompat` integration are top-tier Android Engineering.

We are now officially starting **Phase 7: Frictionless Import (Device Code Flow)**. Typing a 100-character `vless://` URL with a TV remote is impossible. We will solve this by embedding a lightweight Ktor HTTP Server inside the Android TV app, allowing users to pair their mobile phone to the TV via a 6-digit code to seamlessly push configurations.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 7.1: Local Web Server (Ktor Embedded)
*   **Dependencies:** Add `io.ktor:ktor-server-core`, `ktor-server-cio`, `ktor-server-content-negotiation`, `ktor-server-cors`, and `ktor-serialization-kotlinx-json` to your `build.gradle.kts`.
*   **Implementation:** Create `com.cybervpn.tv.core.network.LocalServerManager.kt` (Singleton injected via Hilt).
    *   Create an `embeddedServer(CIO, port = 8080)`.
    *   Add CORS plugin allowing `anyHost()` (since it's a LAN-only server).
    *   Add ContentNegotiation for JSON.
    *   Start the server on a background thread when requested.

### Task 7.2: Mobile Pairing API Routing
*   **Implementation:** Inside the Ktor routing block, define two endpoints:
    *   `GET /`: Return a simple, beautiful HTML page (raw string) with an input field for a URL/Link and a "Send to TV" button. The button should perform a POST request to `/api/import` via JavaScript.
    *   `POST /api/import`: Accept a JSON payload `{"payload": "vless://..."}` or raw text.
    *   When the POST is received, pass the payload to `VpnParser.parse(payload)`. If successful, use the `VpnDao` to save it to the Room database, and return `200 OK`.

### Task 7.3: The "Device Code" State & UI
*   **Implementation:** 
    *   In the `VpnViewModel` (or a dedicated `ImportViewModel`), fetch the local LAN IP address of the Android TV (e.g., `192.168.1.50`).
    *   Generate a random 6-character visual code (e.g., `639-AKQ`).
    *   Map this code to the current session (for security, the POST request can require this code, or we can just rely on LAN security for now).
    *   In `ProfilesScreen.kt`, add a massive button "Import from Phone". When clicked, open a Dialog showing: "Go to http://192.168.1.50:8080 on your phone to paste your link."

---

## ⚠️ STRICT KOTLIN SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `kotlin-specialist` and `ktor-server` rules:

### 1. Non-Blocking Ktor Server (`ktor-server` & `rust-async-patterns` equivalent)
*   **CRITICAL:** `embeddedServer(...).start(wait = true)` will block the thread forever. Since we are running this inside an Android app, you MUST use `start(wait = false)`.
*   Ensure the Ktor server is bound to an Android `CoroutineScope`. When the application is killed, you MUST call `server.stop(1000, 2000)` to release the `8080` port, otherwise, the app will crash with `BindException: Address already in use` on the next launch.

### 2. Coroutines and Room Interaction from Ktor
*   Ktor route handlers (`get`, `post`) are `suspend` functions. 
*   When the POST request hits `/api/import`, you can safely call your Room `VpnDao` `suspend fun insertNodes()` directly inside the route block. 
*   However, catching parsing errors is crucial. If `VpnParser.parse` returns null, respond with `call.respond(HttpStatusCode.BadRequest, "Invalid Link")`. Do not throw unhandled exceptions from the routing block.

### 3. Fetching Local IP Address
*   Getting the accurate Wi-Fi/Ethernet IP address on Android can be tricky. Use `WifiManager` or iterate through `NetworkInterface.getNetworkInterfaces()` filtering out `isLoopback` and IPv6 addresses to find the true IPv4 LAN address to display on the TV screen.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 7.1 and 7.2**. Show me a snippet of the `embeddedServer` initialization block and explain how you will ensure the server is cleanly stopped when the TV app is closed. Do not write the full code until I approve the plan.