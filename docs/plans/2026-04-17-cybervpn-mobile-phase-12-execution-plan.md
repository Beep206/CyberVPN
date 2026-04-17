# CyberVPN Mobile Phase 12 Execution Plan

## Goal

Close Phase 12 from the Happ advanced-settings roadmap by turning `Other Settings > Statistics` and `Other Settings > Logs` into real operational surfaces instead of placeholder or diagnostics-only flows.

Phase 12 scope was intentionally limited to:

- an `Other Settings` hub inside mobile settings IA
- a truthful `Statistics` screen backed by real VPN runtime counters
- a hybrid `Logs` center that combines in-memory diagnostics logs with persistent files
- runtime log-level control that affects both app logging and generated Xray JSON
- persistent access, subscription, and Xray runtime log artifacts
- file viewing, sharing, export, and clear-log operations

## Planned Tasks

1. Add a file-backed logging service that can persist categorized application logs and runtime Xray snapshots.
2. Extend the shared logger so settings-controlled log level affects buffering and persistent output.
3. Apply log-level semantics to the VPN runtime builder so generated Xray configs reflect the selected verbosity.
4. Extend VPN statistics entities and repository mapping so live engine counters can drive a dedicated statistics surface.
5. Add `Other Settings`, `Statistics`, `Logs Center`, and log-file viewer screens plus router/search wiring.
6. Verify the phase with code generation, targeted analysis, and targeted tests.

## Status

Phase 12 is complete.

Completed implementation:

- extended shared logging in `cybervpn_mobile/lib/core/utils/app_logger.dart`
- added persistent file logging in `cybervpn_mobile/lib/core/services/log_file_store.dart`
- wired logger and file store into app lifecycle and DI in:
  - `cybervpn_mobile/lib/app/app.dart`
  - `cybervpn_mobile/lib/core/di/providers.dart`
- extended VPN settings projection with runtime `logLevel` in `cybervpn_mobile/lib/features/settings/presentation/providers/settings_provider.dart`
- applied runtime log settings in `cybervpn_mobile/lib/features/vpn/domain/services/vpn_runtime_config_builder.dart`
- persisted Xray runtime snapshots from connect flow in `cybervpn_mobile/lib/features/vpn/data/datasources/vpn_engine_datasource.dart`
- extended connection statistics models and live repository mapping in:
  - `cybervpn_mobile/lib/features/vpn/domain/entities/connection_stats_entity.dart`
  - `cybervpn_mobile/lib/features/vpn/data/models/connection_stats_model.dart`
  - `cybervpn_mobile/lib/features/vpn/data/repositories/vpn_repository_impl.dart`
  - `cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_stats_provider.dart`
- added `Other Settings` providers and screen flows in:
  - `cybervpn_mobile/lib/features/settings/presentation/providers/other_settings_providers.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/other_settings_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/statistics_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/logs_center_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/log_file_viewer_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/settings_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/widgets/settings_search.dart`
  - `cybervpn_mobile/lib/app/router/app_router.dart`
- added and updated targeted tests in:
  - `cybervpn_mobile/test/core/services/log_file_store_test.dart`
  - `cybervpn_mobile/test/features/vpn/data/repositories/vpn_repository_impl_test.dart`
  - `cybervpn_mobile/test/features/vpn/domain/services/vpn_runtime_config_builder_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/other_settings_screen_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/statistics_screen_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/logs_center_screen_test.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| `Settings > Other Settings` exists as a dedicated hub with `Statistics` and `Logs` entry points | Passed |
| `Statistics` uses real VPN runtime counters for session start, duration, aggregate speed, and aggregate traffic | Passed |
| Unsupported proxy/direct split traffic metrics are marked honestly instead of inferred from aggregate counters | Passed |
| `Logs Center` exposes log-level control, in-memory log viewing, export, persistent files, and clear-log actions | Passed |
| Persistent files include `access_log.txt`, `subscription_log.txt`, and Xray runtime snapshots | Passed |
| App log level affects both the shared logger threshold and generated Xray runtime JSON log level | Passed |
| Phase 12 passes targeted code generation, analysis, and tests | Passed |

## Implementation Details

### 1. Hybrid Logging Model

Phase 12 introduced a hybrid logging path instead of keeping logs only in memory.

`AppLogger` now supports:

- a runtime severity threshold
- optional persistence binding
- categorized entries
- full reset support for tests

`LogFileStore` now persists:

- access diagnostics into `access_log.txt`
- subscription diagnostics into `subscription_log.txt`
- generated runtime configs into `xray_runtime_<timestamp>_<remark>.json`

Important behavior:

- Xray snapshots redact sensitive fields before writing
- text logs are size-trimmed to prevent unbounded growth
- only a small rolling window of Xray snapshots is kept
- write failures are isolated so one failed append does not poison the full queue

### 2. Runtime Log-Level Application

Phase 12 made `LogLevel` operational instead of cosmetic.

App-side behavior:

- app lifecycle binds the logger to the current settings state
- changing the setting updates the minimum emitted severity without restart

VPN runtime behavior:

- `VpnRuntimeConfigBuilder` now mutates JSON `log.loglevel`
- `dnsLog` is only enabled for debug-level verbosity
- the applied log setting is recorded in runtime metadata/logging

This keeps app diagnostics and Xray verbosity aligned with a single settings source.

### 3. Statistics Surface

`VpnRepositoryImpl.connectionStatsStream` now maps the live engine status into richer app-side statistics, including:

- current session start time
- connection duration
- aggregate download and upload speed
- aggregate total download and upload traffic
- current active server identity and endpoint metadata

The `Statistics` screen intentionally stays truthful:

- aggregate counters are shown
- proxy/direct split counters are marked unsupported because current mobile runtime does not expose those buckets separately

This avoids inventing data just to mirror Happ visually.

### 4. Other Settings IA

Phase 12 also added a dedicated `Other Settings` area to keep the advanced-settings surface modular.

Implemented navigation:

- `Settings > Other Settings`
- `Settings > Other Settings > Statistics`
- `Settings > Other Settings > Logs`
- `Settings > Other Settings > Logs > File Viewer`

The settings search index now links directly into the new `Statistics` and `Logs` destinations.

## Verification

### Code Generation

- `flutter pub run build_runner build --delete-conflicting-outputs`
  - Result: success

### Static Analysis

- `dart analyze lib/core/utils/app_logger.dart lib/core/services/log_file_store.dart lib/core/di/providers.dart lib/app/app.dart lib/app/router/app_router.dart lib/features/vpn/domain/entities/connection_stats_entity.dart lib/features/vpn/data/models/connection_stats_model.dart lib/features/vpn/data/repositories/vpn_repository_impl.dart lib/features/vpn/data/datasources/vpn_engine_datasource.dart lib/features/vpn/domain/services/vpn_runtime_config_builder.dart lib/features/vpn/presentation/providers/vpn_stats_provider.dart lib/features/settings/presentation/providers/other_settings_providers.dart lib/features/settings/presentation/providers/settings_provider.dart lib/features/settings/presentation/screens/other_settings_screen.dart lib/features/settings/presentation/screens/statistics_screen.dart lib/features/settings/presentation/screens/logs_center_screen.dart lib/features/settings/presentation/screens/log_file_viewer_screen.dart lib/features/settings/presentation/screens/settings_screen.dart lib/features/settings/presentation/widgets/settings_search.dart test/core/services/log_file_store_test.dart test/features/vpn/data/repositories/vpn_repository_impl_test.dart test/features/vpn/domain/services/vpn_runtime_config_builder_test.dart test/features/settings/presentation/screens/other_settings_screen_test.dart test/features/settings/presentation/screens/statistics_screen_test.dart test/features/settings/presentation/screens/logs_center_screen_test.dart`
  - Result: `No issues found!`

### Tests

- `flutter test test/core/services/log_file_store_test.dart test/features/vpn/data/repositories/vpn_repository_impl_test.dart test/features/vpn/data/datasources/vpn_engine_datasource_test.dart test/features/vpn/domain/services/vpn_runtime_config_builder_test.dart test/features/settings/presentation/screens/other_settings_screen_test.dart test/features/settings/presentation/screens/statistics_screen_test.dart test/features/settings/presentation/screens/logs_center_screen_test.dart`
  - Result: `All tests passed!`

## Residuals

- current mobile runtime still exposes only aggregate Xray traffic counters; real proxy/direct split statistics are not available yet
- `Diagnostics > Logs` legacy widget coverage in `test/features/diagnostics/presentation/screens/log_viewer_screen_test.dart` still has a pre-existing share/action-button harness issue and was not rewritten as part of Phase 12
- full on-device E2E for Xray snapshot creation, persistent file viewing, and share flows was not run in this session

## References

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
