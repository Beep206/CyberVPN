# CyberVPN Mobile Phase 11 Execution Plan

## Goal

Close Phase 11 from the Happ advanced-settings roadmap by turning the remaining `Ping`, `Allow Connections from LAN`, and `App Auto Start` scope into honest runtime behavior instead of storage-only toggles.

Phase 11 scope was intentionally limited to:

- explicit ping transport policy resolution across settings, diagnostics, server list, and subscription refresh
- real `GET` / `HEAD` proxy-delay execution where a V2Ray config is available
- explicit fallback behavior where only TCP probing is possible
- Android-first `Allow Connections from LAN` runtime wiring
- Android-first `App Auto Start` system integration with OEM/background settings handoff
- `VPN Settings > General` and `VPN Settings > Ping` UX updates that reflect platform capability truthfully

## Planned Tasks

1. Add a shared ping-policy runtime that resolves Happ-like ping modes and result semantics from `AppSettings`.
2. Use the effective ping policy in diagnostics, provider-profile ping refresh, and server-list latency refresh paths.
3. Extend the local `flutter_v2ray_plus` bridge so proxy delay checks can choose `GET` or `HEAD`.
4. Add Android-first LAN access runtime support and wire it into VPN connect/reconnect flows.
5. Add Android system integration for app auto-start status, OEM auto-start settings, and battery-optimization settings.
6. Rework `VPN Settings > General` and `VPN Settings > Ping` so the new controls are visible and honest about fallbacks.
7. Verify the phase with targeted analyze, tests, and Android Kotlin compilation.

## Status

Phase 11 is complete.

Completed implementation:

- added shared ping runtime policy service in `cybervpn_mobile/lib/features/settings/domain/services/ping_policy_runtime.dart`
- wired ping policy DI in `cybervpn_mobile/lib/core/di/providers.dart`
- synchronized ping result/display semantics in `cybervpn_mobile/lib/features/settings/presentation/providers/settings_provider.dart`
- rebuilt `VPN Settings > Ping` in `cybervpn_mobile/lib/features/settings/presentation/screens/ping_settings_screen.dart`
- updated server-list ping rendering and latency execution in:
  - `cybervpn_mobile/lib/features/servers/presentation/widgets/ping_indicator.dart`
  - `cybervpn_mobile/lib/features/servers/presentation/providers/server_list_provider.dart`
  - `cybervpn_mobile/lib/features/diagnostics/data/services/speed_test_service.dart`
  - `cybervpn_mobile/lib/features/diagnostics/presentation/providers/diagnostics_provider.dart`
  - `cybervpn_mobile/lib/features/diagnostics/presentation/screens/speed_test_screen.dart`
  - `cybervpn_mobile/lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart`
- extended VPN runtime wiring for LAN access in:
  - `cybervpn_mobile/lib/features/vpn/domain/entities/vpn_config_entity.dart`
  - `cybervpn_mobile/lib/features/vpn/domain/services/vpn_runtime_capabilities.dart`
  - `cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_connection_notifier.dart`
  - `cybervpn_mobile/lib/features/vpn/data/datasources/vpn_engine_datasource.dart`
  - `cybervpn_mobile/lib/features/vpn/data/repositories/vpn_repository_impl.dart`
- patched local plugin support in:
  - `packages/flutter_v2ray_plus/lib/flutter_v2ray.dart`
  - `packages/flutter_v2ray_plus/lib/flutter_v2ray_platform_interface.dart`
  - `packages/flutter_v2ray_plus/lib/flutter_v2ray_method_channel.dart`
  - `packages/flutter_v2ray_plus/android/src/main/kotlin/com/wisecodex/flutter_v2ray/FlutterV2rayPlugin.kt`
  - `packages/flutter_v2ray_plus/android/src/main/kotlin/com/wisecodex/flutter_v2ray/xray/core/XrayCoreManager.kt`
  - `packages/flutter_v2ray_plus/android/src/main/kotlin/com/wisecodex/flutter_v2ray/xray/dto/XrayConfig.kt`
- added Android system integration service and providers in:
  - `cybervpn_mobile/lib/features/settings/data/datasources/android_system_integration_service.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/providers/android_system_integration_providers.dart`
- rebuilt `VPN Settings > General` for `Allow Connections from LAN` and `App Auto Start` in `cybervpn_mobile/lib/features/settings/presentation/screens/vpn_general_settings_screen.dart`
- added native Android support in:
  - `cybervpn_mobile/android/app/src/main/kotlin/com/cybervpn/cybervpn_mobile/MainActivity.kt`
  - `cybervpn_mobile/android/app/src/main/kotlin/com/cybervpn/cybervpn_mobile/AppAutoStartBootReceiver.kt`
  - `cybervpn_mobile/android/app/src/main/AndroidManifest.xml`
- added and updated targeted tests in:
  - `cybervpn_mobile/test/features/settings/domain/services/ping_policy_runtime_test.dart`
  - `cybervpn_mobile/test/features/settings/data/datasources/android_system_integration_service_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/ping_settings_screen_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/vpn_general_settings_screen_test.dart`
  - `cybervpn_mobile/test/features/diagnostics/presentation/diagnostics_provider_test.dart`
  - `cybervpn_mobile/test/features/diagnostics/presentation/screens/speed_test_screen_test.dart`
  - `cybervpn_mobile/test/features/diagnostics/data/services/speed_test_service_test.dart`
  - `cybervpn_mobile/test/features/vpn/data/datasources/vpn_engine_datasource_test.dart`
  - `cybervpn_mobile/test/features/vpn/data/repositories/vpn_repository_impl_test.dart`
  - `cybervpn_mobile/test/features/vpn_profiles/presentation/providers/profile_update_notifier_test.dart`
  - `cybervpn_mobile/test/features/servers/presentation/screens/server_list_screen_test.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| App settings resolve effective Happ-like ping modes for diagnostics, server list, and subscription refresh | Passed |
| `Via Proxy GET` and `Via Proxy HEAD` can execute as real proxy delay checks where a runtime config exists | Passed |
| Unsupported ICMP and metadata-only server-list cases fall back explicitly instead of pretending to use proxy ping | Passed |
| Ping result presentation supports `Time` and `Icon` modes in the UI | Passed |
| `Allow Connections from LAN` is a real Android runtime setting that changes local proxy bind behavior on reconnect | Passed |
| `App Auto Start` exposes real Android status plus OEM/battery settings entry points | Passed |
| `VPN Settings > General` and `VPN Settings > Ping` show the new Happ-like controls honestly on supported and unsupported platforms | Passed |
| Phase 11 passes targeted analysis, tests, and Android Kotlin compile validation | Passed |

## Implementation Details

### 1. Ping Policy Runtime

`PingPolicyRuntime` now centralizes ping semantics for the app.

It resolves:

- desired transport:
  - `TCP`
  - `Via Proxy GET`
  - `Via Proxy HEAD`
- diagnostics execution plan
- server-list execution plan
- provider-profile ping execution plan
- user-facing labels
- display/result mode normalization

Important behavior:

- legacy `PingMode.realDelay` is normalized to `Via Proxy HEAD`
- `ICMP` is preserved as a settings choice but marked unsupported in current runtime execution
- server-list latency refresh remains TCP-only when only server metadata is available, and this fallback is now logged instead of being hidden

### 2. Ping Runtime Execution

Phase 11 pushed the effective ping policy into all active latency surfaces.

Diagnostics:

- `DiagnosticsNotifier` now resolves the effective plan from settings
- runtime logs include requested mode, applied transport, and fallback reasons
- `SpeedTestService` supports `HEAD` and `GET` HTTP probe execution explicitly

Provider-profile refresh:

- `ProfileUpdateNotifier` can now use the stored V2Ray config for real proxy ping during `Ping on Open`
- `GET` vs `HEAD` is selected from policy
- per-server failures are handled per item and logged without aborting the full batch

Server list:

- `server_list_provider.dart` now resolves a ping plan before refresh
- when only plain host metadata exists, it falls back to TCP and records the reason
- `PingIndicator` now supports Happ-like `Time` or `Icon` display semantics

### 3. LAN Connections Runtime

`Allow Connections from LAN` is no longer just a stored toggle.

Runtime behavior:

- `VpnConnectionNotifier` derives `allowLanConnections` from settings plus platform capability
- the value is persisted into VPN config metadata and reconnect state
- Android runtime capabilities now expose `supportsLanProxyAccess`
- local `flutter_v2ray_plus` plugin wiring forwards `allow_lan_connections` into the native layer
- `XrayCoreManager` binds SOCKS and HTTP inbounds to:
  - `127.0.0.1` by default
  - `0.0.0.0` when LAN access is enabled

This gives the app a real Android-first LAN sharing foundation while keeping unsupported platforms truthful.

### 4. App Auto Start Integration

Phase 11 introduces a small Android integration layer instead of pretending the app can fully self-manage OEM background policies.

Implemented behavior:

- `AndroidSystemIntegrationService` reads:
  - LAN proxy status
  - app auto-start status
  - OEM auto-start settings availability
  - battery optimization settings availability
- `MainActivity` exposes a new method channel:
  - `getLanProxyStatus`
  - `getAppAutoStartStatus`
  - `setAppAutoStartEnabled`
  - `openAppAutoStartSettings`
  - `openBatteryOptimizationSettings`
- `AppAutoStartBootReceiver` listens for `BOOT_COMPLETED` and `MY_PACKAGE_REPLACED`
- the receiver checks the persisted Flutter setting and records that boot handling occurred

Important limitation:

- the receiver does not try to force-open the app UI after reboot
- instead, the app exposes status plus the correct OS/OEM settings handoff, which matches current Android platform reality more honestly

### 5. Settings UX

`VPN Settings > General` now includes:

- `Allow Connections from LAN`
- current local Wi-Fi IPv4 / IPv6 information where available
- effective SOCKS and HTTP ports
- app auto-start toggle
- auto-start status summary
- OEM auto-start settings entry point
- battery optimization settings entry point

`VPN Settings > Ping` now includes:

- `Via Proxy GET`
- `Via Proxy HEAD`
- `TCP`
- `ICMP`
- test URL editor
- `Time` / `Icon` result mode
- explicit info about current runtime fallbacks

This makes the settings surface much closer to Happ while staying aligned with what the current runtime can actually do.

## Verification

### Code Generation

- `flutter pub run build_runner build --delete-conflicting-outputs`
  - Result: success

### Static Analysis

- `dart analyze lib/core/di/providers.dart lib/features/settings/domain/services/ping_policy_runtime.dart lib/features/settings/data/datasources/android_system_integration_service.dart lib/features/settings/presentation/providers/android_system_integration_providers.dart lib/features/settings/presentation/providers/settings_provider.dart lib/features/settings/presentation/screens/ping_settings_screen.dart lib/features/settings/presentation/screens/vpn_general_settings_screen.dart lib/features/diagnostics/data/services/speed_test_service.dart lib/features/diagnostics/presentation/providers/diagnostics_provider.dart lib/features/diagnostics/presentation/screens/speed_test_screen.dart lib/features/servers/presentation/widgets/ping_indicator.dart lib/features/servers/presentation/providers/server_list_provider.dart lib/features/vpn/domain/entities/vpn_config_entity.dart lib/features/vpn/domain/services/vpn_runtime_capabilities.dart lib/features/vpn/data/datasources/vpn_engine_datasource.dart lib/features/vpn/data/repositories/vpn_repository_impl.dart lib/features/vpn/presentation/providers/vpn_connection_notifier.dart lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart`
  - Result: `No issues found!`

- `cd packages/flutter_v2ray_plus && flutter analyze`
  - Result: `No issues found!`

### Tests

- `flutter test test/features/settings/domain/services/ping_policy_runtime_test.dart test/features/settings/data/datasources/android_system_integration_service_test.dart test/features/settings/presentation/screens/ping_settings_screen_test.dart test/features/settings/presentation/screens/vpn_general_settings_screen_test.dart test/features/diagnostics/presentation/diagnostics_provider_test.dart test/features/diagnostics/presentation/screens/speed_test_screen_test.dart test/features/diagnostics/data/services/speed_test_service_test.dart`
  - Result: `All tests passed!`

- `flutter test test/features/vpn/data/datasources/vpn_engine_datasource_test.dart test/features/vpn/data/repositories/vpn_repository_impl_test.dart test/features/vpn_profiles/presentation/providers/profile_update_notifier_test.dart test/features/servers/presentation/screens/server_list_screen_test.dart`
  - Result: `All tests passed!`

### Android Compile

- `cd cybervpn_mobile/android && ./gradlew :app:compileDevDebugKotlin`
  - Result: `BUILD SUCCESSFUL`

## Residuals

- `ICMP` is now an explicit settings option and fallback path, but there is still no native ICMP probe implementation in the current mobile runtime.
- server-list refresh can only execute real proxy ping when a full runtime config is available; metadata-only flows still fall back to TCP by design.
- `Allow Connections from LAN` is Android-first and takes effect on the next VPN reconnect because it changes inbound bind behavior.
- `App Auto Start` is implemented as Android boot-receiver readiness plus OEM/background-settings guidance; it does not guarantee forced UI launch after reboot because modern Android background start rules are OEM and OS constrained.
- full on-device E2E for real reboot handling, LAN client access, and physical-device proxy ping was not run in this session.

## References

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
- Happ Local Network Connections FAQ: https://www.happ.su/main/ru/faq/local-network-connections
- `network_info_plus` package: https://pub.dev/packages/network_info_plus
- Android background-start restrictions: https://developer.android.com/guide/components/activities/background-starts
