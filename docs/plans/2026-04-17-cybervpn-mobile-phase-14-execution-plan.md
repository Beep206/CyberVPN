# CyberVPN Mobile Phase 14 Execution Plan

## Goal

Close the remaining `Connect To` orchestration gap from the Happ advanced-settings roadmap by wiring subscription connect strategy into real auto-connect entrypoints instead of leaving it as settings-only UI.

Phase 14 scope was intentionally limited to:

- policy-driven auto-connect target resolution for:
  - launch auto-connect
  - untrusted WiFi auto-connect
  - Android quick action `Quick Connect`
- runtime support for:
  - `Last used`
  - `Lowest latency`
  - `Random`
- deterministic fallback semantics when server inventory is unavailable at app start
- targeted tests for runtime selection and notifier wiring

## Planned Tasks

1. Extend `SubscriptionPolicyRuntime` with a concrete server-selection contract for auto-connect entrypoints.
2. Wire `VpnConnectionNotifier` to resolve subscription connect strategy before auto-connect.
3. Remove duplicated quick-connect selection logic from `QuickActionsHandler` and reuse the notifier contract.
4. Route untrusted WiFi auto-connect through the same policy-driven resolver.
5. Add targeted unit/integration coverage and run targeted analyze/tests.

## Status

Phase 14 is complete.

Completed implementation:

- extended runtime selection logic in `cybervpn_mobile/lib/features/vpn_profiles/domain/services/subscription_policy_runtime.dart`
- wired policy-driven auto-connect in `cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_connection_notifier.dart`
- simplified quick action connect orchestration in `cybervpn_mobile/lib/features/quick_actions/domain/services/quick_actions_handler.dart`
- switched untrusted WiFi auto-connect to shared resolver in `cybervpn_mobile/lib/features/vpn/domain/usecases/untrusted_wifi_handler.dart`
- added targeted tests in:
  - `cybervpn_mobile/test/features/vpn_profiles/domain/services/subscription_policy_runtime_test.dart`
  - `cybervpn_mobile/test/features/vpn/presentation/providers/vpn_connection_provider_test.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| `Subscription Connect Strategy` is no longer settings-only and affects runtime auto-connect behavior | Passed |
| launch auto-connect honors `Lowest latency` when server candidates are available | Passed |
| quick action `Quick Connect` uses the same strategy resolver as VPN launch/untrusted WiFi flows | Passed |
| untrusted WiFi auto-connect uses the shared strategy resolver instead of hard-coded last-used/recommended logic | Passed |
| `Random` strategy is deterministic under seeded test runtime and covered by tests | Passed |
| fallback behavior remains safe when server inventory is not loaded yet | Passed |
| Phase 14 passes targeted analysis and tests | Passed |

## Implementation Details

### 1. Subscription Connect Runtime

`SubscriptionPolicyRuntime` now exposes a concrete auto-connect selector instead of only resolving metadata and sort order.

The new runtime contract returns:

- selected server
- requested strategy
- actually applied strategy
- candidate count
- fallback note

This lets the app distinguish between:

- direct `Last used`
- direct `Lowest latency`
- direct `Random`
- fallback from `Last used` to `Lowest latency`
- fallback from `Lowest latency` or `Random` to recommended/last-used when the candidate list is not ready yet

### 2. Single Source of Truth for Auto-Connect

Before Phase 14, connection entrypoints were inconsistent:

- launch auto-connect only tried saved last server
- untrusted WiFi called `connectToLastOrRecommended()`
- quick actions reimplemented their own storage/server-fetch logic

Phase 14 consolidates those flows under `VpnConnectionNotifier.connectBySubscriptionPolicy(...)`.

That means the same target resolution now drives:

- launch
- untrusted WiFi
- quick connect shortcut

and all of them now produce the same runtime logs for requested/applied strategy and fallback semantics.

### 3. Safe Fallback Semantics

The tricky case was app startup, because `allServersWithPingProvider` may still be empty while the user already expects auto-connect to happen.

Phase 14 handles this explicitly:

- `Last used`
  - use saved server if still available
  - otherwise fall back to recommended/lowest-delay candidate
- `Lowest latency`
  - use ranked candidates when present
  - otherwise fall back to recommended or last used
- `Random`
  - choose from available candidate pool
  - otherwise fall back to recommended or last used

This keeps startup behavior robust without pretending the full server list is always ready.

### 4. Quick Action Cleanup

`QuickActionsHandler` no longer:

- reads secure storage directly for last server
- fetches raw server lists on its own
- maintains a separate “best server” contract

It now delegates to the notifier and inherits the same Happ-like semantics as the rest of the app.

That removes duplicated connection-target logic and closes a real drift risk.

## Verification

### Static Analysis

- `dart analyze lib/features/vpn/presentation/providers/vpn_connection_notifier.dart lib/features/quick_actions/domain/services/quick_actions_handler.dart lib/features/vpn/domain/usecases/untrusted_wifi_handler.dart lib/features/vpn_profiles/domain/services/subscription_policy_runtime.dart test/features/vpn/presentation/providers/vpn_connection_provider_test.dart test/features/vpn_profiles/domain/services/subscription_policy_runtime_test.dart`
  - Result: `No issues found!`

### Tests

- `flutter test test/features/vpn_profiles/domain/services/subscription_policy_runtime_test.dart test/features/vpn/presentation/providers/vpn_connection_provider_test.dart`
  - Result: `All tests passed!`

## Rollout Notes

- This phase does not change the tunnel engine or protocol/runtime payload. It only changes how the app selects the server to connect to.
- Android benefits the most because quick actions and untrusted WiFi are Android-first operational surfaces.
- iOS still benefits from launch-time strategy resolution where the setting is exposed and supported by current reduced semantics.

## Residuals

- `No Filter` remains a settings/policy flag, not a full runtime subscription filter-engine contract.
- `Use Local DNS`, real `ICMP ping`, and proxy/direct split statistics remain constrained by deeper runtime/plugin capability gaps.
- full on-device E2E for launcher shortcuts, untrusted WiFi transitions, and cold-start auto-connect was not run in this session.

## References

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/ru/dev-docs/routing
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
