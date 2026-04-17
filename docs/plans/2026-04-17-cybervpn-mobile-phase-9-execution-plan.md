# CyberVPN Mobile Phase 9 Execution Plan

## Goal

Close Phase 9 from the Happ advanced-settings roadmap by wiring the new runtime-sensitive VPN settings into the actual connection flow instead of keeping them as storage-only flags.

Phase 9 scope was intentionally limited to:

- runtime DNS precedence
- sniffing and proxy-only mode injection
- server-address resolve before connect
- full typed excluded-routes application for Android where the platform bridge allows it
- UI wiring for the new controls
- explicit audit of unsupported local DNS behavior

## Planned Tasks

1. Extend runtime capabilities so the app can distinguish between full, reduced, and unsupported settings.
2. Add a server-address resolver that can resolve hostnames before connect and patch the runtime config safely.
3. Extend `VpnRuntimeConfigBuilder` with:
   - `useDnsFromJson`
   - `sniffingEnabled`
   - `vpnRunMode`
   - typed IPv4/IPv6 excluded routes
4. Pass `proxyOnly` through repository and engine layers instead of forcing `false`.
5. Patch Android VPN routing so API 33+ can exclude typed IPv4/IPv6 routes with `excludeRoute(IpPrefix)`.
6. Expose the new controls in `VPN Settings > General` and `VPN Settings > Advanced`.
7. Audit `useLocalDns` and `localDnsPort` against the current `flutter_v2ray_plus` bridge and document the gap.
8. Verify the phase with targeted analyze, tests, and Android Kotlin compile.

## Status

Phase 9 is complete.

Completed implementation:

- added pre-connect resolver service in `cybervpn_mobile/lib/features/vpn/domain/services/vpn_server_address_resolver.dart`
- expanded runtime capability matrix in `cybervpn_mobile/lib/features/vpn/domain/services/vpn_runtime_capabilities.dart`
- extended runtime builder in `cybervpn_mobile/lib/features/vpn/domain/services/vpn_runtime_config_builder.dart`
- propagated `proxyOnly` through:
  - `cybervpn_mobile/lib/features/vpn/domain/entities/vpn_config_entity.dart`
  - `cybervpn_mobile/lib/features/vpn/data/datasources/vpn_engine_datasource.dart`
  - `cybervpn_mobile/lib/features/vpn/data/repositories/vpn_repository_impl.dart`
- updated connect flow and runtime logging in `cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_connection_notifier.dart`
- added DI wiring in `cybervpn_mobile/lib/core/di/providers.dart`
- expanded support-matrix semantics in:
  - `cybervpn_mobile/lib/features/settings/domain/services/vpn_settings_support_matrix.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/providers/vpn_settings_support_provider.dart`
- extended UI in:
  - `cybervpn_mobile/lib/features/settings/presentation/screens/vpn_general_settings_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/advanced_vpn_settings_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/excluded_routes_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/screens/vpn_settings_screen.dart`
- patched Android route application in `packages/flutter_v2ray_plus/android/src/main/kotlin/com/wisecodex/flutter_v2ray/xray/service/XrayVPNService.kt`
- fixed Android app-settings shortcut recursion bug in `cybervpn_mobile/lib/core/network/wifi_monitor_service.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| `sniffingEnabled` mutates runtime JSON and is logged in connect flow | Passed |
| `vpnRunMode = proxyOnly` reaches repository, datasource, plugin start call, and reconnect flow | Passed |
| `useDnsFromJson` preserves imported JSON DNS when present | Passed |
| app-level DNS precedence still applies when JSON DNS is not authoritative | Passed |
| server hostname can be resolved before connect using DoH or system lookup | Passed |
| typed excluded routes accept IPv4/IPv6 address and CIDR values and reach runtime config | Passed |
| Android API 33+ applies typed excluded routes through `excludeRoute(IpPrefix)` | Passed |
| `useLocalDns` / `localDnsPort` are either implemented safely or explicitly marked unsupported | Passed |
| new settings are surfaced in General/Advanced settings UX with platform-aware messaging | Passed |

## Implementation Details

### 1. Server Address Resolve

`VpnServerAddressResolver` now runs before `VpnRuntimeConfigBuilder`.

Implemented behavior:

- skips resolve when the server address is already numeric
- supports DoH lookup when `serverAddressResolveDohUrl` is configured
- supports optional fixed DNS IP for the DoH request path
- falls back to `InternetAddress.lookup` when DoH is absent or fails
- respects `PreferredIpType`
- probes candidate IPs with TCP connect timing and selects the fastest reachable candidate
- patches both:
  - `VpnConfigEntity.serverAddress`
  - `configData` by mutating full JSON or rebuilding URI-based configs into full JSON first

`vpnConnectionNotifier` now logs:

- `serverAddressResolveEnabled`
- `resolvedServerAddress`
- `resolvedCandidateCount`
- `resolvedCandidates`

### 2. Runtime DNS Precedence

`VpnRuntimeConfigBuilder` now applies the written Phase 8 precedence instead of treating everything as a flat override.

Current runtime order:

1. If `useDnsFromJson = true` and full JSON contains DNS servers, preserve JSON DNS.
2. Else if `useLocalDns = true`, log explicit skip when the bridge does not support a managed local DNS listener.
3. Else apply app-level DNS override from preset/custom provider.
4. Else fall back to default runtime behavior.

This phase also preserves `dnsServers` in `VpnConfigEntity` and reconnect flow so the live engine contract matches the built config.

### 3. Sniffing and Proxy-only

Runtime builder now:

- injects Xray sniffing on non-API inbounds when `sniffingEnabled = true`
- disables sniffing explicitly when the JSON already has a sniffing block and the setting is off
- resolves `vpnRunMode`
- marks `proxyOnly = true` only when the platform capability allows it

`VpnEngineDatasource.connect()` now accepts `proxyOnly`, stores it for reconnects, and forwards it to `FlutterV2ray.startVless(...)`.

### 4. Typed Excluded Routes

`VpnRuntimeConfigBuilder` now prefers `excludedRouteEntries` over legacy `bypassSubnets` and normalizes:

- IPv4 address to `/32`
- IPv6 address to `/128`
- CIDR values as-is

Android runtime behavior:

- API 33+:
  - adds default IPv4 and IPv6 routes
  - excludes server IP as a precise prefix
  - excludes typed user routes with `VpnService.Builder.excludeRoute(IpPrefix)`
- API < 33:
  - keeps the existing IPv4 subtraction path
  - ignores IPv6 exclusions with explicit logging because the older builder API cannot represent them safely

### 5. Settings UX

`VPN Settings > General` now includes:

- `Use DNS from JSON`
- informational DNS precedence tile
- `Use Local DNS` capability messaging
- `Local DNS Port` input when the feature is available
- `Enable server address resolve`
- DoH URL input
- fixed DNS IP input
- `Background Settings` shortcut that opens app settings on Android

`VPN Settings > Advanced` now includes:

- `Packet analysis`
- `Mode`
  - `VPN`
  - `Proxy only`

`Excluded Routes` now accepts both IPv4 and IPv6 address/CIDR values in the editor UI.

### 6. Local DNS Audit

The Phase 9 audit result is explicit:

- current `flutter_v2ray_plus` bridge exposes DNS server lists, not an app-managed local DNS listener
- there is no current bridge contract for:
  - starting a local DNS service
  - binding it to `127.0.0.1:<localDnsPort>`
  - managing its lifecycle alongside the VPN engine
- because of that, enabling `useLocalDns` cannot be made truthful in this phase

Final Phase 9 behavior:

- setting is stored
- support matrix shows it as unavailable
- runtime builder logs a skipped reason instead of pretending the feature works

## Verification

### Static Analysis

- `dart analyze ...` on the Phase 9 app files and tests
  - Result: `No issues found!`
- `cd packages/flutter_v2ray_plus && flutter analyze`
  - Result: `No issues found!`

### Tests

- `flutter test test/features/vpn/domain/services/vpn_server_address_resolver_test.dart test/features/vpn/domain/services/vpn_runtime_config_builder_test.dart test/features/vpn/data/datasources/vpn_engine_datasource_test.dart test/features/vpn/data/repositories/vpn_repository_impl_test.dart test/features/settings/domain/services/vpn_settings_support_matrix_test.dart test/features/settings/presentation/screens/advanced_vpn_settings_screen_test.dart test/features/settings/presentation/screens/vpn_general_settings_screen_test.dart test/features/settings/presentation/screens/excluded_routes_screen_test.dart`
  - Result: `All tests passed!`

### Android Compile

- `cd cybervpn_mobile/android && ./gradlew :app:compileDevDebugKotlin`
  - Result: `BUILD SUCCESSFUL`

### Codegen

- `flutter pub run build_runner build --delete-conflicting-outputs`
  - Result: completed successfully after the new runtime and settings-model changes

## Residuals

- `useLocalDns` and `localDnsPort` remain storage- and UX-level only until the mobile bridge gains a real managed local DNS contract.
- Android API 33+ has full typed route exclusion support, but API < 33 still falls back to the older IPv4-only subtraction strategy.
- iOS remains a reduced-semantics platform for this phase:
  - runtime JSON mutation for DNS/sniffing is available
  - proxy-only mode is still not advertised as supported
  - excluded routes and local DNS are still constrained by the mobile bridge
- full on-device E2E with a real tunnel session and manual Happ-style acceptance pass was not run in this session.

## References

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/ru/dev-docs/routing
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
- Android `VpnService.Builder.excludeRoute`: https://developer.android.com/reference/android/net/VpnService.Builder#excludeRoute(android.net.IpPrefix)
- Dart `HttpClient`: https://api.dart.dev/stable/dart-io/HttpClient-class.html
- Dart `Socket.connect`: https://api.dart.dev/stable/dart-io/Socket/connect.html
- `permission_handler` app settings API: https://pub.dev/packages/permission_handler
