# Phase 30 Start: Bandwidth Analytics & Global Stats

Congratulations on completing the Stealth Lab! With the core security and diagnostics finalized, we now move to **Phase 30: Bandwidth Analytics & Global Stats**. 

The goal is to provide users with a beautiful, high-tech overview of their data consumption and global network footprint. We want to transform raw numbers into meaningful insights using interactive visualizations that feel like a "Command Center."

---

## 🎯 Task Breakdown (Execute sequentially, ask for approval after planning)

### Task 30.1: The Stats Historian (Rust Backend)
Currently, we only track live session speeds. We need a persistent history of usage.
*   **Implementation:** Create `engine::sys::stats.rs`.
*   **Storage:** Use a lightweight SQLite database (via `sqlx`) or a simple binary file to store daily usage records: `{ date: String, bytes_up: u64, bytes_down: u64, protocol: String, country_code: String }`.
*   **Logic:** Every hour (or upon disconnect), the app should flush accumulated session stats into the persistent store.
*   **Command:** `get_usage_history(period: String) -> Result<Vec<UsageRecord>, AppError>`.

### Task 30.2: Geo-IP Mapper (Rust Backend)
To build a global map, we need to know where the servers are located.
*   **Implementation:** Enhance the `provision` module.
*   **Logic:** Use the locally stored `geoip.db` (from Phase 18) to resolve the `ProxyNode.server` IP into a Country Code (ISO 3166-1).
*   **Command:** `get_global_footprint() -> Result<HashMap<String, u64>, AppError>` (Returns a map of Country -> Total Bytes).

### Task 30.3: "Command Center" Analytics UI (React Frontend)
Create a visually stunning analytics dashboard.
*   **Location:** New "Analytics" tab.
*   **Features:**
    *   **Interactive Traffic Map:** A sleek SVG world map. Countries where the user has connected should glow in `NeonCyan`. 
    *   **Consumption Charts:** Use `recharts` or `visx` to show a "Data Usage Over Time" bar chart (Daily/Weekly/Monthly).
    *   **Protocol Breakdown:** A donut chart showing which protocol (VLESS, Hysteria2, etc.) is used the most.
    *   **Milestones:** "You've saved 500MB of data this month with Privacy Shield."
    *   **Visual Style:** Use "Dark Industrial" aesthetics with high-contrast glowing elements.

---

## ⚠️ STRICT RUST SKILL REQUIREMENTS FOR THIS PHASE

As you implement this phase, you **MUST** strictly adhere to the following `rust-engineer`, `rust-best-practices`, and `rust-async-patterns` rules:

### 1. Batch Database Writes (`rust-best-practices`)
*   **Rule:** Do not perform a disk write for every single kilobyte transferred. This will destroy SSD life and cause UI micro-stutters.
*   **Implementation:** Accumulate traffic stats in an atomic in-memory buffer (`Arc<AtomicU64>`) and only perform a database flush every 5 minutes or when the app is closing.

### 2. Zero-Copy Visualization Data (`rust-engineer`)
*   When the UI requests 30 days of history, do not return a giant JSON of 100,000 data points. 
*   **Optimization:** Aggregation must happen in Rust. Return pre-calculated daily totals to the frontend to keep the IPC payload small and fast.

### 3. Non-Blocking IO for History (`rust-async-patterns`)
*   Reading 30 days of history from a file/DB can take 50-100ms. 
*   **Rule:** Always use `tokio::task::spawn_blocking` for database queries to ensure the main Tauri loop never hitches.

### 4. Semantic Error Handling
*   If the usage database is corrupted, do not panic. 
*   **Rule:** Implement a "Soft Reset" variant in `AppError`. If the stats file fails to load, rename it to `.corrupted` and start a fresh one, notifying the user: "Usage history was reset due to data corruption."

---

**Next Step:** Acknowledge these instructions and provide a brief technical plan for **Task 30.1 (Stats Historian)**. Will you use SQLite or a flat binary file? How will you handle the periodic flushing of stats from memory to disk safely? Do not write the full code until I approve the plan.