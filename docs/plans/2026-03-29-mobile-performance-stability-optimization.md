# Mobile Performance and Stability Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `cybervpn_mobile` feel fast on cold start, reduce runtime jank, eliminate auth/network race conditions, and raise confidence with stronger tests and profiling guardrails.

**Architecture:** Optimize the app in layers instead of one big rewrite. First establish a clean baseline and safety net, then remove startup blockers, then reduce rebuild/render cost in the heaviest screens, then harden networking/auth coordination and stale cache behavior, and finally lock gains in with tests and performance budgets.

**Tech Stack:** Flutter, Dart, Riverpod, GoRouter, Dio, Drift, Flutter Secure Storage, Firebase, WebSocket, flutter_test, integration_test

---

## Baseline Findings

- Cold start is front-loaded by `EnvironmentConfig.init()`, `SharedPreferences.getInstance()`, `buildProviderOverrides()`, secure-storage prewarm, and optional `SentryFlutter.init()` before `runApp` in `cybervpn_mobile/lib/main.dart`.
- Splash routing is currently blocked by auth, onboarding, quick setup, and profile migration state in `cybervpn_mobile/lib/app/router/app_router.dart`, with a global timeout that can force users to `/login`.
- Router redirect performs side effects and auth work in `cybervpn_mobile/lib/app/router/app_router.dart`, which makes navigation less predictable and increases duplicate work risk.
- Root app lifecycle wiring eagerly watches many services in `cybervpn_mobile/lib/app/app.dart`, likely pulling heavy providers into startup too early.
- The heaviest UI hotspots are `cybervpn_mobile/lib/features/servers/presentation/screens/server_list_screen.dart`, `cybervpn_mobile/lib/features/vpn/presentation/screens/connection_screen.dart`, `cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart`, and `cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart`.
- Token refresh is split between `cybervpn_mobile/lib/core/network/auth_interceptor.dart` and `cybervpn_mobile/lib/core/auth/token_refresh_scheduler.dart`, which risks duplicate refreshes and unstable auth behavior.
- WebSocket ticket fallback and deep-link logging still expose sensitive auth material in risky ways via `cybervpn_mobile/lib/core/network/websocket_provider.dart`, `cybervpn_mobile/lib/core/routing/deep_link_handler.dart`, and `cybervpn_mobile/lib/core/utils/app_logger.dart`.
- Subscription cache strategy in `cybervpn_mobile/lib/features/subscription/data/repositories/subscription_repository_impl.dart` has no TTL/versioning, so stale data can persist too long.
- Full static analysis is not clean: `flutter analyze` reports an invalid lint rule and unused integration-test imports.
- Full `flutter test` is not green; current failures show test drift in biometric and auth repository coverage, which weakens optimization safety.

---

### Task 1: Establish performance baseline and CI safety net

**Files:**
- Modify: `cybervpn_mobile/analysis_options.yaml`
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: `cybervpn_mobile/lib/main.dart`
- Modify: `cybervpn_mobile/lib/core/utils/app_logger.dart`
- Create: `cybervpn_mobile/test/perf/startup_smoke_test.dart`
- Create: `cybervpn_mobile/test/perf/navigation_smoke_test.dart`
- Modify: `cybervpn_mobile/integration_test/e2e_auth_flow_test.dart`

**Step 1: Clean the baseline checks**

- Remove invalid lint configuration from `cybervpn_mobile/analysis_options.yaml`.
- Remove or fix obviously stale unused imports and broken test assumptions found by `flutter analyze`.

Run:

```bash
flutter analyze
```

Expected: no analyzer warnings or infos that hide real regressions.

**Step 2: Add repeatable startup instrumentation**

- Expand startup logging in `cybervpn_mobile/lib/main.dart` with a structured summary for pre-`runApp`, first frame, and deferred-init milestones.
- Add reusable timing helpers to `cybervpn_mobile/lib/core/utils/app_logger.dart` or a dedicated perf helper.

**Step 3: Add smoke benchmarks**

- Add a startup smoke test and one navigation smoke test that assert the app can bootstrap and navigate without timing out.
- Keep them light enough for CI, not device-lab benchmarks.

**Step 4: Verify the guardrails**

Run:

```bash
flutter analyze
flutter test test/perf/startup_smoke_test.dart test/perf/navigation_smoke_test.dart
```

Expected: the project has a clean baseline and repeatable performance signals before refactors begin.

---

### Task 2: Cut cold-start latency and splash instability

**Files:**
- Modify: `cybervpn_mobile/lib/main.dart`
- Modify: `cybervpn_mobile/lib/app/app.dart`
- Modify: `cybervpn_mobile/lib/app/router/app_router.dart`
- Modify: `cybervpn_mobile/lib/core/di/providers.dart`
- Modify: `cybervpn_mobile/lib/core/storage/secure_storage.dart`
- Modify: `cybervpn_mobile/lib/features/vpn_profiles/di/profile_providers.dart`
- Modify: `cybervpn_mobile/lib/features/vpn_profiles/data/services/legacy_profile_migration.dart`
- Test: `cybervpn_mobile/test/app/router/app_router_test.dart`

**Step 1: Move non-critical initialization out of the critical path**

- Minimize pre-`runApp` bootstrap in `cybervpn_mobile/lib/main.dart`.
- Reduce secure-storage prewarm to only the keys truly required for routing/auth restoration.
- Defer diagnostics and non-essential platform services until after the first frame.

**Step 2: Introduce explicit startup phases**

- Separate startup work into `critical`, `post_first_frame`, and `authenticated_only` phases.
- Ensure FCM, widgets, quick actions, and non-blocking observers are not needed to render the first usable screen.

**Step 3: Simplify splash gating**

- Remove profile migration and other non-critical tasks from splash blocking in `cybervpn_mobile/lib/app/router/app_router.dart`.
- Replace the current global splash timeout fallback to `/login` with task-aware fallbacks that preserve authenticated users.

**Step 4: Verify router behavior**

Run:

```bash
flutter test test/app/router/app_router_test.dart
flutter analyze
```

Expected: splash resolves faster and startup no longer sends authenticated users to the wrong route under slow initialization.

---

### Task 3: Make routing and deep-link handling pure and deterministic

**Files:**
- Modify: `cybervpn_mobile/lib/app/router/app_router.dart`
- Modify: `cybervpn_mobile/lib/core/routing/deep_link_handler.dart`
- Modify: `cybervpn_mobile/lib/core/routing/deep_link_parser.dart`
- Modify: `cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart`
- Modify: `cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart`
- Test: `cybervpn_mobile/test/core/routing/deep_link_handler_test.dart`
- Test: `cybervpn_mobile/test/core/routing/deep_link_parser_test.dart`
- Test: `cybervpn_mobile/test/integration/deep_link_integration_test.dart`

**Step 1: Remove side effects from GoRouter redirect**

- Ensure `redirect` only decides the next route string.
- Move provider mutations, auth callbacks, and token exchanges out of the redirect path.

**Step 2: Add a deep-link coordinator**

- Create a dedicated startup/deep-link coordinator that performs async side effects once, outside routing.
- Make pending deep links durable enough for app resume/cold start if needed.

**Step 3: Remove build-triggered post-frame auth work**

- Eliminate repeated `addPostFrameCallback` scheduling from auth screen `build()` paths.
- Keep auth callbacks one-shot and idempotent.

**Step 4: Verify auth/deep-link paths**

Run:

```bash
flutter test test/core/routing/deep_link_handler_test.dart test/core/routing/deep_link_parser_test.dart test/integration/deep_link_integration_test.dart
```

Expected: deep links and OAuth callbacks are handled exactly once, without redirect loops or duplicate auth work.

---

### Task 4: Reduce rebuild scope and render cost in the heaviest screens

**Files:**
- Modify: `cybervpn_mobile/lib/features/servers/presentation/screens/server_list_screen.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/presentation/screens/connection_screen.dart`
- Modify: `cybervpn_mobile/lib/features/navigation/presentation/screens/main_shell_screen.dart`
- Modify: `cybervpn_mobile/lib/shared/widgets/glitch_text.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/presentation/widgets/connect_button.dart`
- Modify: `cybervpn_mobile/lib/features/servers/presentation/providers/server_list_provider.dart`
- Test: `cybervpn_mobile/test/features/servers/...`
- Test: `cybervpn_mobile/test/features/vpn/...`

**Step 1: Make server list rendering lazy**

- Replace grouped `Column` trees inside slivers with lazy sliver delegates.
- Precompute filtered/grouped view-models in providers instead of recomputing them in `build()`.
- Debounce search input and avoid full-screen rebuilds on every keypress.

**Step 2: Split connection screen into narrow consumers**

- Isolate ticking session stats from the rest of the connection screen.
- Keep Lottie and transition logic outside the broadest rebuild scope.

**Step 3: Move shell notifications out of scaffold build**

- Replace `ref.listen` in `build()` with dedicated listener widgets/effects or `ConsumerState` lifecycle-safe hooks.

**Step 4: Tone down always-on animation cost**

- Reduce glitch redraw frequency or switch to lower-cost effects.
- Profile and narrow animated glow/shadow work in the connect button.

**Step 5: Verify no behavior regressions**

Run:

```bash
flutter analyze
flutter test
```

Expected: typing, scrolling, server browsing, and active connection screens feel smoother and rebuild less often.

---

### Task 5: Unify auth refresh, harden networking, and remove token leakage risks

**Files:**
- Modify: `cybervpn_mobile/lib/core/network/auth_interceptor.dart`
- Modify: `cybervpn_mobile/lib/core/auth/token_refresh_scheduler.dart`
- Modify: `cybervpn_mobile/lib/features/auth/data/repositories/auth_repository_impl.dart`
- Modify: `cybervpn_mobile/lib/core/network/websocket_provider.dart`
- Modify: `cybervpn_mobile/lib/core/network/websocket_client.dart`
- Modify: `cybervpn_mobile/lib/core/utils/app_logger.dart`
- Modify: `cybervpn_mobile/lib/core/routing/deep_link_handler.dart`
- Test: `cybervpn_mobile/test/core/network/...`
- Test: `cybervpn_mobile/test/features/auth/data/repositories/auth_repository_impl_test.dart`

**Step 1: Create a single token-refresh coordinator**

- Ensure proactive and reactive refresh go through one serialized refresh path.
- Prevent duplicate refresh requests, token rotation races, and 401 storms.

**Step 2: Harden WebSocket authentication**

- Remove fallback to raw access token in WebSocket URLs.
- Fail closed or use a safer temporary auth mechanism if ticket issuance fails.

**Step 3: Expand log redaction**

- Redact OAuth codes, magic-link tokens, Telegram auth payloads, WebSocket ticket params, and similar secrets.
- Avoid logging raw deep-link URIs if they contain one-time auth values.

**Step 4: Stabilize background session validation**

- Make `getCurrentUser()` background validation testable and less error-prone.
- Ensure tests fully stub all async branches so validation helpers do not create hidden failures.

**Step 5: Verify high-risk auth/network flows**

Run:

```bash
flutter test test/core/network test/features/auth/data/repositories/auth_repository_impl_test.dart test/features/auth/domain/usecases/biometric_service_test.dart
```

Expected: refresh logic is deterministic, logs are sanitized, and network/auth regressions are caught by tests.

---

### Task 6: Add cache TTLs, stale-while-revalidate, and resilient data refresh

**Files:**
- Modify: `cybervpn_mobile/lib/features/subscription/data/repositories/subscription_repository_impl.dart`
- Modify: `cybervpn_mobile/lib/features/subscription/data/datasources/subscription_local_ds.dart`
- Modify: `cybervpn_mobile/lib/core/data/cache_strategy.dart`
- Modify: `cybervpn_mobile/lib/features/referral/data/datasources/referral_remote_ds.dart`
- Test: `cybervpn_mobile/test/features/subscription/...`
- Test: `cybervpn_mobile/test/features/referral/...`

**Step 1: Add TTL/versioning for cached subscription data**

- Do not keep plans/subscription cache forever.
- Prefer explicit freshness windows plus stale-while-revalidate where it improves UX.

**Step 2: Fix incorrect cache/error behavior**

- Audit datasource type mismatches and sticky “unavailable” cache flags.
- Ensure network recovery is not masked by stale failure cache state.

**Step 3: Verify cache correctness**

Run:

```bash
flutter test test/features/subscription test/features/referral
```

Expected: user-visible data stays fresh and cache behavior becomes predictable under flaky network conditions.

---

### Task 7: Dependency and platform hardening pass

**Files:**
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: platform-specific files only when required by dependency upgrades
- Test: smoke test affected auth/map/notification/platform flows

**Step 1: Upgrade safe low-risk packages first**

- Prioritize patch/minor upgrades for `dio`, `firebase_core`, `firebase_messaging`, `flutter_riverpod`, `shared_preferences`, `google_fonts`, `flutter_svg`, and similar runtime libraries.

**Step 2: Evaluate major-version upgrades separately**

- Review breaking changes for `flutter_map`, `google_sign_in`, `sign_in_with_apple`, and local notification packages before adoption.

**Step 3: Re-run the full safety suite**

Run:

```bash
flutter pub outdated --no-dev-dependencies
flutter analyze
flutter test
```

Expected: dependency drift shrinks without destabilizing core flows.

---

## Execution Order

1. Baseline and guardrails
2. Startup and splash path
3. Router/deep-link purity
4. Render and rebuild optimization
5. Auth/network hardening
6. Cache/data freshness
7. Dependency hardening

## Success Criteria

- Cold start visibly improves and first useful screen appears sooner.
- Splash no longer blocks on non-critical work or falls back incorrectly.
- Server list search/scroll and connection screen updates stay smooth.
- Full `flutter analyze` is clean.
- Full `flutter test` is green.
- No raw auth secrets appear in logs, breadcrumbs, or WebSocket URLs.
