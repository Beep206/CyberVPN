# CyberVPN Flutter Mobile Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file explicitly before changing `cybervpn_mobile/`.

Use `pubspec.yaml`, generated sources, platform projects, and current code as
the source of truth. The application uses Riverpod, go_router, Dio,
Freezed/json_serializable, Drift, secure storage, and a local
`flutter_v2ray_plus` package; follow the established architecture instead of
adding a parallel one.

## Architecture and state ownership

- Keep presentation, application/state, data, and platform/VPN boundaries
  explicit.
- Use Riverpod providers according to existing lifecycle/ownership patterns.
  Do not introduce global singletons or duplicate provider state.
- Keep navigation in the established go_router configuration and preserve deep
  link/auth guard behavior.
- Generated Freezed, JSON, Drift, localization, and platform registration files
  are generated artifacts. Change their sources and regenerate; never patch
  generated output manually.
- Keep API models separate from persisted/domain state when their invariants or
  lifecycle differ.
- Avoid business, entitlement, subscription, or VPN policy in widgets.

## VPN and lifecycle state machines

Treat connect/disconnect, permission, configuration import, authentication,
foreground/background, reconnect, service restoration, and logout as explicit
state machines.

For changed flows, define and test:

- valid source and target states;
- repeated connect/disconnect requests;
- cancellation during transition;
- concurrent commands;
- permission denied/permanently denied;
- invalid or revoked configuration;
- network loss and restoration;
- app pause/resume and process/service restart;
- stale backend/entitlement state;
- platform exception and timeout;
- safe terminal and recoverable states.

Do not show `connected`, `subscribed`, `authenticated`, or `provisioned` before
the authoritative operation completed. Persist only the minimum state needed
for safe restoration and reconcile it with the platform/backend on startup.

## Networking and persistence

- Use the established Dio client/interceptors, typed models, cancellation, and
  timeout strategy. Do not create ad-hoc clients per request.
- Retry only safe operations and prevent duplicate purchases, provisioning,
  device registration, or state-changing requests.
- Treat connectivity signals as hints, not proof of internet/service
  reachability.
- Bound local history, logs, caches, retries, polling, and database queries.
- Drift migrations must preserve existing data and include upgrade tests.
- Store credentials, refresh material, device keys, and approved sensitive
  values only in secure storage.
- SharedPreferences is for non-sensitive preferences, not secrets.
- Never bundle `.env` or production secrets as assets. Use the established
  `--dart-define`/environment configuration flow.

## Platform channels and native code

- Validate every Dart/native message and return typed errors.
- Keep channel method names and payload schemas stable or version them.
- Never build shell commands from untrusted values.
- Clean up native listeners, services, VPN sessions, sockets, and resources on
  cancellation/shutdown.
- Respect Android foreground-service, notification, VPN permission, background,
  battery, and process-death behavior.
- Respect iOS Network Extension, Keychain, permission, lifecycle, and platform
  policy constraints.
- A mock platform channel is not proof of real platform behavior; add a
  deterministic harness and run the relevant device/emulator smoke.

## UI, localization, and accessibility

- Keep widgets small and driven by typed state. Do not perform I/O in `build`.
- Preserve state restoration and avoid calling state mutations after disposal.
- Handle loading, empty, offline, permission, degraded, error, retry, and
  success states explicitly.
- Do not hard-code user-visible strings. Update ARB/localization sources and
  regenerate localizations.
- Verify long translations, RTL, text scaling, small devices, landscape,
  keyboard/focus, screen-reader semantics, reduced motion, and touch targets
  when affected.
- Avoid expensive work and object allocation in high-frequency build/animation
  paths. Use const widgets and existing selectors appropriately.

## Security and privacy

- Never log or persist raw subscription links, VPN configurations, access or
  refresh tokens, private keys, device credentials, purchase receipts, raw
  Telegram data, or PII outside approved secure storage.
- Redact Sentry breadcrumbs/events and analytics.
- Validate deep links, QR codes, clipboard/imported configuration, files, and
  external URLs as untrusted input.
- Do not allow screenshots/clipboard/background previews to expose sensitive
  material where the product policy forbids it.
- Authentication, entitlement, device, and subscription decisions remain
  server-authoritative.

## Testing

Add relevant:

- pure unit tests for state machines, repositories, parsers, and policies;
- Riverpod/provider tests for transitions and cancellation;
- widget tests for user interaction, semantics, loading/error/permission states;
- Drift migration/persistence tests;
- platform-channel contract tests;
- integration tests for auth, deep links, purchase/provisioning, VPN lifecycle,
  secure storage, and process restoration;
- Android/iOS device or emulator smoke for changed native behavior.

Use fake clocks and deterministic platform/provider fakes. Do not use arbitrary
delays, real production services, or assertions that only check method calls.

## Required validation

From `cybervpn_mobile/`:

```bash
flutter pub get
dart run build_runner build --delete-conflicting-outputs
dart format --output=none --set-exit-if-changed .
flutter analyze --fatal-warnings
flutter test
```

Run code generation only when relevant, but always verify generated files are
synchronized. For platform-channel, VPN, permissions, background service, deep
link, secure storage, purchase, or release changes, add the relevant Android/iOS
build and integration/device smoke. Rerun final gates after the last relevant
change.
