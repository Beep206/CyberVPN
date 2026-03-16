# Phase 5 Start: Data Layer & Subscription Sync

Brilliant work on Phase 4! The `AntiBurnInBackground` implementation is an incredible touch of senior engineering, and the strict adherence to `androidx.tv` composables sets us up for perfect D-Pad navigation.

We are now officially starting **Phase 5: Data Layer & Subscription Sync**. This phase connects our TV UI to actual persistent data and the network, enabling the storage of proxy nodes and the dynamic fetching of subscription URLs.

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 5.1: Local Database (Room) Setup
*   **Dependencies:** Add `androidx.room` dependencies (runtime, compiler/ksp, and ktx) to `build.gradle.kts`.
*   **Entities:** Define `@Entity` data classes for `ProxyNodeEntity` and `SubscriptionEntity`. (You may need to write mapping functions to convert between these Room entities and the domain models created in Phase 2).
*   **DAO:** Create `VpnDao` with `suspend` functions for basic CRUD operations (`insertNodes`, `getNodesBySubscription`, `getAllSubscriptions`, `deleteSubscription`).
*   **Database:** Create `CyberVpnDatabase` extending `RoomDatabase`. Provide it via Hilt in a new `DatabaseModule.kt`.

### Task 5.2: Subscription Fetcher (Ktor Client)
*   **Dependencies:** Add `io.ktor:ktor-client-core`, `ktor-client-android` (or `okhttp`), and `ktor-client-content-negotiation` to Gradle.
*   **Implementation:** Create `com.cybervpn.tv.core.network.SubscriptionClient.kt`.
    *   Implement a `suspend fun fetchSubscription(url: String): String?` using the Ktor client.
    *   Set strict timeouts (e.g., 10 seconds) so the TV doesn't hang if a provider is blocked.
    *   Once the raw string is fetched, use the `VpnParser` (from Phase 2) and robust Base64/YAML logic to extract a `List<ProxyNode>`.

### Task 5.3: Repository & Flow State Modeling
*   **Location:** Create `com.cybervpn.tv.data.repository.VpnRepository.kt`.
*   **Implementation:** 
    *   Inject the `VpnDao` and `SubscriptionClient`.
    *   Create a method `suspend fun syncSubscription(sub: Subscription)` that fetches the nodes, clears the old ones for that `sub.id` in the DB, and inserts the new ones within a `@Transaction`.
    *   Expose data to the UI using `Flow<List<ProxyNode>>`.
    *   Maintain the active connection state using the `UiState` interface we defined in Phase 1 (e.g., `StateFlow<UiState<ConnectionState>>`).

---

## ⚠️ STRICT KOTLIN SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `kotlin-specialist` and `android-compose` rules:

### 1. Database Threading & Dispatchers
*   Room DAOs with `suspend` functions automatically run on a background thread. However, when performing complex mapping lists of hundreds of nodes from entities to domain models, wrap the heavy mapping logic in `withContext(Dispatchers.Default) { ... }` to avoid frame drops (jank) on low-end TV processors.

### 2. Ktor Exception Handling
*   Ktor throws exceptions (like `HttpRequestTimeoutException` or `UnresolvedAddressException`) on failure. 
*   You MUST wrap your `client.get(url)` calls in `runCatching` or a `try/catch` block. Never let a network failure crash the app. Return a well-defined `UiState.Error` or a nullable result to the Repository.

### 3. Hilt Modules
*   Use `@Module` and `@InstallIn(SingletonComponent::class)` for your Room Database and Ktor Client providers. 
*   Keep the Ktor Client instance as a Singleton to reuse connection pools, conserving memory.

### 4. Code Quality
*   As always, run `./gradlew detekt ktlintCheck` before finalizing this phase to ensure strict code style adherence.

---

**Next Step:** Acknowledge these instructions. Provide a brief technical plan for **Task 5.1 and 5.2**. Detail exactly which Ktor engine you will use and how you plan to handle the Room Entity to Domain Model mapping. Do not write the full code until I approve the plan.