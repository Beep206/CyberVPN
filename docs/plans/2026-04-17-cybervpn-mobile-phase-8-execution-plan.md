# CyberVPN Mobile Phase 8 Execution Plan

## Goal

Close Phase 8 from the Happ advanced settings parity roadmap by finishing the domain, persistence, and provider foundation for the next advanced settings wave without prematurely mixing product contracts with runtime-specific hacks.

Phase 8 scope was intentionally limited to:

- settings schema expansion
- migration-safe persistence
- explicit precedence rules
- derived provider contracts for future UI/runtime phases
- test coverage for serialization and provider flows

## Planned Tasks

1. Expand `AppSettings` with new Happ-like advanced settings fields and enums.
2. Add a typed excluded-routes model that supports IPv4/IPv6 address and CIDR inputs.
3. Extend `SettingsRepositoryImpl` to persist, migrate, normalize, and backfill the new settings safely.
4. Extend `SettingsNotifier` and derived providers so later phases can wire UI and runtime incrementally.
5. Lock precedence rules for DNS, ping, subscriptions, excluded routes, and reset semantics in writing.
6. Verify the schema with targeted unit and provider tests.

## Status

Phase 8 is complete.

Completed implementation:

- expanded `AppSettings` with new enums and fields for:
  - `useLocalDns`
  - `localDnsPort`
  - `useDnsFromJson`
  - `sniffingEnabled`
  - `vpnRunMode`
  - `serverAddressResolveEnabled`
  - `serverAddressResolveDohUrl`
  - `serverAddressResolveDnsIp`
  - `excludedRouteEntries`
  - `subscriptionAutoUpdateEnabled`
  - `subscriptionAutoUpdateIntervalHours`
  - `subscriptionUpdateNotificationsEnabled`
  - `subscriptionAutoUpdateOnOpen`
  - `subscriptionPingOnOpenEnabled`
  - `subscriptionConnectStrategy`
  - `preventDuplicateImports`
  - `collapseSubscriptions`
  - `subscriptionNoFilter`
  - `subscriptionUserAgentMode`
  - `subscriptionUserAgentValue`
  - `subscriptionSortMode`
  - `allowLanConnections`
  - `appAutoStart`
- expanded enums:
  - `LogLevel`: `auto`, `debug`, `info`, `warning`, `error`, `none`
  - `PingMode`: `tcp`, `realDelay`, `proxyGet`, `proxyHead`, `icmp`
  - `PingResultMode`: `time`, `icon`
- added typed excluded route parsing and storage normalization
- added migration-safe repository behavior for:
  - legacy `bypassSubnets`
  - legacy `pingDisplayMode`
- added new notifier mutation APIs and derived providers:
  - `vpnSettingsProvider`
  - `subscriptionSettingsProvider`
  - `pingSettingsPreferencesProvider`
- updated existing diagnostics and settings UI switch expressions so the expanded enums are safe to use before later UI/runtime phases land

Primary implementation files:

- `cybervpn_mobile/lib/features/settings/domain/entities/app_settings.dart`
- `cybervpn_mobile/lib/features/settings/domain/entities/excluded_route_entry.dart`
- `cybervpn_mobile/lib/features/settings/data/repositories/settings_repository_impl.dart`
- `cybervpn_mobile/lib/features/settings/presentation/providers/settings_provider.dart`

Compatibility shims added in:

- `cybervpn_mobile/lib/features/settings/presentation/screens/debug_screen.dart`
- `cybervpn_mobile/lib/features/settings/presentation/screens/vpn_settings_screen.dart`
- `cybervpn_mobile/lib/features/diagnostics/presentation/providers/diagnostics_provider.dart`
- `cybervpn_mobile/lib/features/diagnostics/presentation/screens/speed_test_screen.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| New settings schema serializes without dropping existing Phase 0-7 settings | Passed |
| Every new field has an explicit default | Passed |
| Typed excluded routes support IPv4/IPv6 address and CIDR forms in domain storage | Passed |
| Legacy `bypassSubnets` remains compatible with current runtime | Passed |
| Written precedence table exists for DNS, ping, subscriptions, and reset semantics | Passed |
| UI can remain hidden while domain/persistence is fully implemented | Passed |

## Implementation Details

### 1. Settings Schema

`AppSettings` is now the canonical storage contract for the next advanced settings batch. The additions were made without removing previous Phase 0-7 fields, so current installs remain readable.

Important defaults currently locked in code:

- `useLocalDns = false`
- `localDnsPort = 1053`
- `useDnsFromJson = false`
- `sniffingEnabled = false`
- `vpnRunMode = vpn`
- `serverAddressResolveEnabled = false`
- `pingMode = tcp`
- `pingTestUrl = https://google.com/generate_204`
- `pingResultMode = time`
- `subscriptionAutoUpdateEnabled = true`
- `subscriptionAutoUpdateIntervalHours = 24`
- `subscriptionAutoUpdateOnOpen = true`
- `subscriptionPingOnOpenEnabled = false`
- `preventDuplicateImports = true`
- `collapseSubscriptions = true`
- `subscriptionNoFilter = false`
- `subscriptionSortMode = none`
- `allowLanConnections = false`
- `appAutoStart = false`
- `logLevel = info`

### 2. Typed Excluded Routes

`ExcludedRouteEntry` was introduced as the new canonical domain model for excluded routes.

Supported target types:

- IPv4 address
- IPv4 CIDR
- IPv6 address
- IPv6 CIDR
- `unknown` fallback for invalid persisted values

Normalization rules:

- whitespace is trimmed
- duplicate values are removed
- storage is sorted by normalized textual value
- repository writes both `excludedRouteEntries` and legacy `bypassSubnets` so the current runtime path continues to work

### 3. Persistence and Migration

`SettingsRepositoryImpl` now persists every new field under dedicated `settings.*` keys.

Backward-compatible migration behavior:

- if `excludedRouteEntries` is absent, repository derives it from legacy `bypassSubnets`
- if `pingResultMode` is absent, repository derives it from legacy `pingDisplayMode`
- if typed excluded routes exist, they become the source of truth and backfill `bypassSubnets`

This keeps Phase 0-7 runtime behavior stable while establishing the richer Phase 8 contract.

## Precedence Table

### DNS Precedence

This table defines the intended contract for later runtime phases. Phase 8 stores and validates the inputs; full runtime enforcement is deferred to Phase 9.

| Order | Rule | Phase 8 Status |
|---|---|---|
| 1 | If `useDnsFromJson = true` and imported full JSON contains DNS config, runtime should preserve JSON DNS and ignore app-level DNS overrides | Contract documented, runtime pending |
| 2 | Else if `useLocalDns = true`, runtime should prefer the local DNS endpoint on `127.0.0.1:localDnsPort` once native support exists | Contract documented, runtime pending |
| 3 | Else if `dnsProvider = custom` and `customDns` is valid, runtime should use the custom DNS value | Existing app concept, precedence now documented |
| 4 | Else if `dnsProvider` is a preset provider, runtime should use that preset | Existing app concept |
| 5 | Else fallback to system/default DNS | Existing app concept |

### Excluded Routes Precedence

| Order | Rule | Phase 8 Status |
|---|---|---|
| 1 | `excludedRouteEntries` is the new canonical stored model | Implemented |
| 2 | `bypassSubnets` is maintained as a compatibility mirror for older runtime/UI paths | Implemented |
| 3 | If only `bypassSubnets` exists on disk, derive `excludedRouteEntries` from it during read | Implemented |

### Ping Precedence

| Order | Rule | Phase 8 Status |
|---|---|---|
| 1 | `pingMode` is the canonical strategy selector | Implemented |
| 2 | `pingTestUrl` is only relevant for URL-based strategies such as `realDelay`, `proxyGet`, and `proxyHead` | Contract documented |
| 3 | `pingResultMode` is the canonical Happ-style presentation preference | Implemented |
| 4 | If `pingResultMode` is absent, derive it from legacy `pingDisplayMode` (`quality -> icon`, otherwise `time`) | Implemented |
| 5 | Legacy `pingDisplayMode` remains compatibility-only until later UI cleanup | Implemented |

### Subscription Precedence

| Order | Rule | Phase 8 Status |
|---|---|---|
| 1 | Local app policy toggles are authoritative for automation and UI behavior | Implemented |
| 2 | Subscription metadata such as parsed update interval remains informational unless a later phase explicitly promotes it to scheduler input | Documented |
| 3 | `subscriptionUserAgentMode = custom` overrides the app default User-Agent for subscription fetches in future runtime/fetcher phases | Contract documented |
| 4 | `preventDuplicateImports`, `collapseSubscriptions`, `subscriptionNoFilter`, `subscriptionSortMode`, and `subscriptionConnectStrategy` are local product policies and are not overridden by remote headers | Documented |

### Reset Semantics

| Scope | Semantics | Phase 8 Status |
|---|---|---|
| Settings reset | Clears repository-managed `settings.*` keys and rehydrates `AppSettings()` defaults only | Existing and documented |
| Full app reset | Future destructive flow that should additionally clear logs, caches, subscription metadata, and product-defined local state after explicit confirmation | Documented, not implemented |

## Platform Scope

Phase 8 finishes the storage contract cross-platform, but not the runtime parity:

- Android:
  - settings schema is ready
  - runtime effect for most new flags still depends on later phases
- iOS:
  - schema is also ready
  - runtime support remains a reduced subset until later native and product decisions

Current intent:

- keep newly added settings available to domain/persistence layers now
- surface them progressively in later phases only where runtime behavior is real and supportable

## Open Product Questions

These questions remain unresolved and were intentionally not hardcoded as runtime behavior in Phase 8:

1. `Use local DNS`
   - should this mean a real local DNS listener inside the app, or just routing requests to a local endpoint?
2. `Use DNS from JSON`
   - should this disable every app-level DNS override, or only override `dnsProvider/customDns` while still allowing local DNS?
3. `VPN / proxy-only`
   - should mobile expose proxy-only publicly even though Happ docs describe related toggles as desktop-oriented?
4. `Subscription no filter`
   - what exact filtering pipeline is being bypassed in CyberVPN terms?
5. `Connect to random`
   - should random selection be uniform, seeded per session, or constrained by availability/ping freshness?
6. Full app reset
   - should it wipe imported profiles, logs, local databases, exported files, and secure storage tokens, or remain a softer cleanup flow?

## Verification

### Analyze

```bash
dart analyze \
  lib/features/settings/domain/entities/app_settings.dart \
  lib/features/settings/domain/entities/excluded_route_entry.dart \
  lib/features/settings/data/repositories/settings_repository_impl.dart \
  lib/features/settings/presentation/providers/settings_provider.dart \
  lib/features/settings/presentation/screens/debug_screen.dart \
  lib/features/settings/presentation/screens/vpn_settings_screen.dart \
  lib/features/diagnostics/presentation/providers/diagnostics_provider.dart \
  lib/features/diagnostics/presentation/screens/speed_test_screen.dart \
  test/features/settings/domain/entities/app_settings_test.dart \
  test/features/settings/domain/entities/excluded_route_entry_test.dart \
  test/features/settings/data/settings_repository_impl_test.dart \
  test/features/settings/presentation/providers/settings_provider_test.dart
```

Result: `No issues found!`

### Targeted Tests

```bash
flutter test \
  test/features/settings/domain/entities/excluded_route_entry_test.dart \
  test/features/settings/domain/entities/app_settings_test.dart \
  test/features/settings/data/settings_repository_impl_test.dart \
  test/features/settings/presentation/providers/settings_provider_test.dart \
  test/features/diagnostics/presentation/diagnostics_provider_test.dart \
  test/features/diagnostics/presentation/screens/speed_test_screen_test.dart
```

Result: `All tests passed!`

### Additional Smoke Check

```bash
flutter test \
  test/features/settings/presentation/screens/vpn_settings_screen_test.dart \
  test/features/settings/presentation/screens/debug_screen_test.dart
```

Result:

- `vpn_settings_screen_test.dart` smoke path started normally
- `debug_screen_test.dart` fails because the existing test harness does not provide the localization context expected by `DebugScreen`

This failure is treated as a pre-existing harness issue, not a Phase 8 regression.

## Residuals

1. Most new Phase 8 fields are stored and provider-accessible, but not yet applied to the VPN runtime.
2. `diagnostics_provider.dart` currently degrades unsupported new ping modes to existing strategies until the dedicated ping parity phase lands.
3. Full advanced UI exposure is intentionally deferred; Phase 8 completes the contracts first.
4. `debug_screen_test.dart` still needs a localization-aware test harness if that suite is to become part of the stable regression pack.

## Outcome

Phase 8 delivered the contract layer needed for the remaining Happ parity work:

- the settings model is now broad enough for advanced VPN, subscriptions, ping, LAN, and autostart options
- old installs remain readable
- legacy settings still bridge into the current runtime
- later phases can wire real behavior without reopening storage and migration design
