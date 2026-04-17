# CyberVPN Mobile: Phase 6 Execution Plan

Date: 2026-04-16  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

`Phase 6` в этой итерации трактуется как `Subscriptions and ping parity layer`. Цель фазы: перестать держать subscriptions и ping как разрозненные utility-features и сделать из них единый operational layer, ближе к Happ.

## Goal

Закрыть два основных направления:

- `Subscriptions`
  - объединить import entry points и provider-managed subscription flows
  - поднять provider metadata на уровень отдельного settings experience
  - дать refresh/support/provider-page controls прямо из `Settings > VPN > Subscriptions`
- `Ping`
  - довести `pingMode`, `pingTestUrl` и `ping display mode` до runtime/use-case уровня
  - связать ping settings с `Diagnostics > Speed Test` и server list display

## Estimate

- Оценка: `3-4 рабочих дня`
- Статус: `Completed`

## Tasks

### 1. Ping domain and persistence

- Добавить `pingDisplayMode` в settings domain.
- Протащить новый флаг через repository + SharedPreferences persistence.
- Обновить settings notifier API.

### 2. Ping UX and runtime wiring

- Доработать `PingSettingsScreen`, чтобы отдельно настраивались:
  - latency mode
  - display mode
  - ping test URL
- Связать эти настройки с `DiagnosticsNotifier.runSpeedTest(...)`.
- Добавить runtime mapping в `SpeedTestService`:
  - `TCP connect`
  - `Real delay`
- Поднять ping summary в `SpeedTestScreen`.
- Применить display preference в server list ping chips.

### 3. Subscription provider metadata parity

- Расширить `SubscriptionInfo` provider metadata новыми полями.
- На уровне fetch/import извлекать `support-url` и `test-url`.
- Довести эти поля до `RemoteVpnProfile`.

### 4. Subscription operational screen

- Перестроить `SubscriptionSettingsScreen` в practical operational screen.
- Свести в один экран:
  - imported configs
  - add subscription URL
  - QR scan entry
  - provider-managed remote profiles
  - bulk refresh
  - support/provider links
  - imported subscription snapshots
  - billing entry points

### 5. Refresh controls

- Добавить explicit refresh API для provider-managed profiles.
- Развести refresh imported subscription sources и remote provider profiles в одном UX action.

### 6. Test coverage

- Обновить settings / diagnostics / server list tests под новую phase behavior.
- Добавить service/provider/widget coverage для ping parity и provider metadata.

## Acceptance Criteria

### Functional

- `Ping` settings управляют не только storage, но и реальным diagnostics flow.
- `Speed Test` использует текущий `pingMode` и `pingTestUrl`.
- Server list умеет показывать ping по display preference, а не только в raw milliseconds.
- `Subscription Settings` становится единым местом для import/provider/billing actions.
- Provider-managed profiles показывают support/provider metadata и умеют refresh из settings.

### UX / product

- Ping и subscriptions перестают быть feature islands и становятся first-class sections.
- Пользователь может понять, какой ping strategy сейчас активен, прямо в speed test screen.
- Provider-managed subscriptions видны и управляемы без переходов по несвязанным экранам.

### Quality

- Targeted `flutter analyze` проходит без ошибок.
- Targeted regression pack по settings / diagnostics / profiles / server list проходит.

## Actual Result

`Phase 6` закрыта в planned объёме для app-side parity layer.

- В settings domain добавлен `PingDisplayMode`, доведённый до persistence и notifier API:
  - [app_settings.dart](../cybervpn_mobile/lib/features/settings/domain/entities/app_settings.dart)
  - [settings_repository_impl.dart](../cybervpn_mobile/lib/features/settings/data/repositories/settings_repository_impl.dart)
  - [settings_provider.dart](../cybervpn_mobile/lib/features/settings/presentation/providers/settings_provider.dart)
- `PingSettingsScreen` теперь даёт отдельные controls для:
  - latency mode
  - display mode
  - ping target URL
  - diagnostics entry
  - [ping_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/ping_settings_screen.dart)
- Server list ping display привязан к settings и умеет показывать `Fast / Okay / Slow` вместо raw `ms`:
  - [ping_indicator.dart](../cybervpn_mobile/lib/features/servers/presentation/widgets/ping_indicator.dart)
- Diagnostics runtime теперь принимает ping preferences:
  - [diagnostics_provider.dart](../cybervpn_mobile/lib/features/diagnostics/presentation/providers/diagnostics_provider.dart)
  - [speed_test_service.dart](../cybervpn_mobile/lib/features/diagnostics/data/services/speed_test_service.dart)
  - [speed_test_screen.dart](../cybervpn_mobile/lib/features/diagnostics/presentation/screens/speed_test_screen.dart)
- `SpeedTestService` получил явный latency strategy layer:
  - `SpeedTestLatencyMode.tcpConnect`
  - `SpeedTestLatencyMode.realDelay`
- Provider metadata для subscriptions расширена и доведена до profile storage:
  - [subscription_info.dart](../cybervpn_mobile/lib/features/vpn_profiles/domain/entities/subscription_info.dart)
  - [subscription_fetcher.dart](../cybervpn_mobile/lib/features/vpn_profiles/data/datasources/subscription_fetcher.dart)
  - [profile_repository_impl.dart](../cybervpn_mobile/lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart)
- Добавлен bulk refresh API для provider-managed profiles:
  - [profile_update_notifier.dart](../cybervpn_mobile/lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart)
- `SubscriptionSettingsScreen` перестроен в operational hub для imports, provider profiles, snapshots и billing:
  - [subscription_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/subscription_settings_screen.dart)

## Acceptance Result

### Functional

- `PASS`: `PingSettings` теперь влияют на `Diagnostics > Speed Test` runtime path.
- `PASS`: `Speed Test` использует текущие `pingMode` и `pingTestUrl`.
- `PASS`: server list поддерживает `pingDisplayMode` и показывает semantic labels.
- `PASS`: `Subscription Settings` агрегирует import/provider/billing controls.
- `PASS`: provider-managed profiles показывают `supportUrl` / `testUrl` и умеют refresh из settings.

### UX / product

- `PASS`: ping и subscriptions стали first-class operational sections.
- `PASS`: в `Speed Test` есть явный summary текущего latency mode и target host.
- `PASS`: provider-managed subscriptions теперь видны и управляемы прямо из settings.

### Quality

- `PASS`: targeted `flutter analyze` зелёный.
- `PASS`: full targeted Phase 6 regression pack зелёный.

## Validation Evidence

### Static

- `cd cybervpn_mobile && flutter analyze lib/features/settings/domain/entities/app_settings.dart lib/features/settings/data/repositories/settings_repository_impl.dart lib/features/settings/presentation/providers/settings_provider.dart lib/features/servers/presentation/widgets/ping_indicator.dart lib/features/diagnostics/data/services/speed_test_service.dart lib/features/diagnostics/presentation/providers/diagnostics_provider.dart lib/features/diagnostics/presentation/screens/speed_test_screen.dart lib/features/settings/presentation/screens/ping_settings_screen.dart lib/features/vpn_profiles/domain/entities/subscription_info.dart lib/features/vpn_profiles/data/datasources/subscription_fetcher.dart lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart lib/features/settings/presentation/screens/subscription_settings_screen.dart test/features/settings/data/settings_repository_impl_test.dart test/features/settings/presentation/screens/ping_settings_screen_test.dart test/features/settings/presentation/screens/subscription_settings_screen_test.dart test/features/vpn_profiles/domain/entities/subscription_info_test.dart test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart test/features/diagnostics/presentation/diagnostics_provider_test.dart test/features/diagnostics/presentation/screens/speed_test_screen_test.dart test/features/diagnostics/data/services/speed_test_service_test.dart test/features/servers/presentation/screens/server_list_screen_test.dart`
- Result: `No issues found!`

### Tests

- `cd cybervpn_mobile && flutter test test/features/settings/data/settings_repository_impl_test.dart test/features/settings/presentation/screens/ping_settings_screen_test.dart test/features/settings/presentation/screens/subscription_settings_screen_test.dart test/features/vpn_profiles/domain/entities/subscription_info_test.dart test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart test/features/diagnostics/presentation/diagnostics_provider_test.dart test/features/diagnostics/presentation/screens/speed_test_screen_test.dart test/features/diagnostics/data/services/speed_test_service_test.dart test/features/servers/presentation/screens/server_list_screen_test.dart`
- Result: `All tests passed!`

## Residuals

- `Ping mode` сейчас доведён до `Diagnostics > Speed Test`, но не до всего server discovery/sweep pipeline; server list пока использует display preference, а не full proxy-ping runtime mode.
- Provider profile page action сейчас использует `testUrl` как provider-facing external page fallback; если провайдер не отдаёт metadata, action корректно не показывается.
- `Subscription Settings` в этой фазе стали operational hub, но это ещё не full Happ-level subscription management console с provider-specific options, plan comparison и deeper account controls.

## Sources

- Happ App Management: https://www.happ.su/main/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/dev-docs/routing
- url_launcher package docs: https://pub.dev/packages/url_launcher
