# Phase 2 Start: The Kotlin Parsing Engine (Porting Logic)

Excellent work on Phase 1! The project architecture is rock-solid. `UiState` is perfectly idiomatic, and Hilt/Detekt are correctly configured.

We are now moving to **Phase 2: The Kotlin Parsing Engine**. This is a critical phase where we port the heart of our VPN logic (parsing proxy links and generating configurations) from our desktop Rust implementation to 100% pure Kotlin.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 2.1: Data Models Definition
*   **Location:** Create `com.cybervpn.tv.core.model.ProxyNode.kt`.
*   **Structure:** Create a `data class ProxyNode` heavily utilizing `@Serializable` from `kotlinx.serialization`. 
*   **Fields:** Include all the fields we established in the desktop app (e.g., `id`, `name`, `server`, `port`, `protocol`, `uuid`, `password`, `tls`, `sni`, `obfs`, etc.).
*   *Requirement:* Ensure strict null-safety. Use `String?`, `Int?` where appropriate. Default them to `null`.

### Task 2.2: The URI Parser (`Parser.kt`)
*   **Location:** Create `com.cybervpn.tv.core.parser.VpnParser.kt`.
*   **Implementation:** Implement URL parsing to decode standard share links (`vless://`, `trojan://`, `ss://`, `hysteria2://`).
*   **Tooling:** Use `java.net.URI` or Android's `android.net.Uri` to parse the host, port, user info, and query parameters.
*   **VMess / SS Decoding:** For `vmess://` and `ss://` (legacy), the payload is Base64 encoded. Implement a robust Base64 decoding mechanism using `android.util.Base64`.

### Task 2.3: Configuration Generator (`ConfigGenerator.kt`)
*   **Location:** Create `com.cybervpn.tv.core.config.ConfigGenerator.kt`.
*   **Implementation:** Create a class (or an `object` / top-level function) that takes a `ProxyNode` and returns the massive JSON string required by Sing-box.
*   **Tooling:** Use `kotlinx.serialization.json.buildJsonObject` and `buildJsonArray` to construct the JSON programmatically and safely. Map properties like `server` and `port` to the specific Sing-box `outbounds` format based on the `protocol`.

---

## ⚠️ STRICT KOTLIN SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following Senior Kotlin patterns:

### 1. Zero-Crash Base64 & URI Parsing
*   **NEVER use the `!!` operator.**
*   When parsing URLs or Base64 strings, inputs from the user/clipboard are fundamentally untrusted.
*   Use `runCatching { ... }.getOrNull()` for operations that might throw exceptions (like `Base64.decode` or `URI.create`).
*   Use Kotlin scope functions (`let`, `run`) idiomatically to process non-null results.
    ```kotlin
    val decoded = runCatching { 
        Base64.decode(payload, Base64.URL_SAFE or Base64.NO_PADDING) 
    }.getOrNull()?.let { String(it) } ?: return null
    ```

### 2. Immutable Data Classes
*   Your `ProxyNode` must be a `data class` with `val` properties exclusively. No `var`.
*   If a node needs to be modified (e.g., adding a subscription ID later), use the `.copy()` method provided automatically by Kotlin data classes.

### 3. Idiomatic JSON Building
*   Do not construct JSON strings via manual string concatenation or multi-line `"""` strings where variables are injected. This leads to malformed JSON.
*   Use the Kotlinx Serialization JSON builder DSL:
    ```kotlin
    val outbound = buildJsonObject {
        put("type", node.protocol)
        put("server", node.server)
        put("server_port", node.port)
        node.uuid?.let { put("uuid", it) }
    }
    ```

### 4. Code Quality
*   Run `./gradlew detekt ktlintCheck` before finalizing this phase. Your code must not trigger any warnings regarding cyclomatic complexity or formatting.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 2.2 (The URI Parser)**. Show me a snippet of how you will safely parse a `vless://` link using `runCatching` and `java.net.URI`. Do not write the full code until I approve the plan.