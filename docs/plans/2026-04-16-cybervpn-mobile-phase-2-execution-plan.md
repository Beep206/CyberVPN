# CyberVPN Mobile: Phase 2 Execution Plan

Date: 2026-04-16  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

`Phase 2` в этой итерации трактуется как `Android-first runtime foundation`, а не как full Happ parity. Цель фазы: довести до production-ready состояния те части Happ-like VPN Settings, которые реально можно закрыть поверх текущего mobile stack уже сейчас, и явно зафиксировать то, что упирается в ограничения `flutter_v2ray_plus`.

## Goal

Реализовать рабочий `Per-App Proxy` на Android, довести его до connect runtime, расширить `VPN Settings` под новые Happ-like controls и закрыть базовый routing/excluded-routes UX без ложного обещания unsupported Android behavior.

## Estimate

- Оценка: `2-4 рабочих дня`
- Статус: `Completed`

## Tasks

### 1. Android app discovery

- Добавить native Android method channel для получения списка установленных приложений.
- Возвращать package name, display name и признаки системного приложения.
- Сохранить совместимость с iOS через explicit unsupported/empty behavior.

### 2. Per-app runtime resolution

- Добавить app-layer resolver, который переводит:
  - `PerAppProxyMode.off`
  - `PerAppProxyMode.proxySelected`
  - `PerAppProxyMode.bypassSelected`
  в конкретный `blockedApps` список для `flutter_v2ray_plus`.
- Подключить его в VPN connect flow.

### 3. VPN runtime wiring

- Расширить runtime config surface так, чтобы connect flow мог передавать:
  - `blockedApps`
  - `bypassSubnets`
  - transport toggles foundation
- По возможности восстановить `configData` из active profile перед connect, чтобы не терять raw config там, где она уже есть в Drift profiles.

### 4. VPN Settings IA

- Заменить текущий placeholder split-tunneling UX на Happ-like Android-first navigation:
  - `Per-App Proxy`
  - `Excluded Routes`
  - transport toggles (`Fragmentation`, `Mux`, `Preferred IP type`)
- Сделать экраны управляемыми через `settingsProvider`.

### 5. Capability guard

- Явно ограничить route bypass behavior там, где current plugin не обеспечивает real Android route exclusion.
- Не создавать UI, который визуально обещает production routing, если он не может быть применен runtime.

## Acceptance Criteria

### Functional

- На Android приложение умеет получить список приложений для выбора в `Per-App Proxy`.
- `Per-App Proxy` режимы корректно сохраняются в settings и используются при VPN connect.
- `proxySelected` приводит к тому, что в VPN идут только выбранные приложения, а остальные попадают в `blockedApps`.
- `bypassSelected` приводит к тому, что выбранные приложения обходят VPN через `blockedApps`.
- В `VPN Settings` доступны новые экраны/пункты для `Per-App Proxy`, `Excluded Routes`, `Fragmentation`, `Mux`, `Preferred IP type`.

### Safety / honesty

- Если Android runtime не умеет применить route bypass поверх текущего plugin surface, UI/документация не маскируют это как fully shipped feature.
- Unsupported platform behavior для per-app настроек не ломает connect flow.

### Quality

- Добавлены unit/widget tests для:
  - per-app mode resolution
  - Android app discovery Dart layer
  - VPN settings Phase 2 UI
  - connect runtime mapping where feasible
- `build_runner` и таргетные тесты проходят.

## Known Constraint Before Implementation

Во время Phase 2 capability audit подтверждено следующее:

- `flutter_v2ray_plus` реально поддерживает Android `blockedApps`, и эта возможность уже применена внутри plugin service через `VpnService.Builder.addDisallowedApplication(...)`.
- `flutter_v2ray_plus` принимает `bypassSubnets`, но текущая Android реализация их не применяет в `configureRoutes(...)`.

Следствие:

- `Per-App Proxy` можно закрыть полноценно уже в этой фазе.
- `Excluded Routes` в stock plugin нельзя считать полноценно shipped runtime feature без отдельного plugin/native patch.

## Planned Result

После завершения фазы приложение должно иметь:

- реальный Android per-app proxy flow;
- расширенный `VPN Settings` UX под Happ-like controls;
- capability-safe foundation для дальнейшей `Phase 3`, где уже можно делать deeper routing/runtime patching, mux/fragmentation/IP-type injection в actual config generation и iOS parity work.

## Actual Result

`Phase 2` закрыта в Android-first объёме.

- Добавлен Android method channel для получения списка launchable apps и current package name.
- Добавлен Dart platform service и runtime resolver для `Per-App Proxy`.
- Connect flow теперь передаёт в VPN runtime:
  - `blockedApps`
  - `bypassSubnets`
  - `configData`, восстановленный из active VPN profile там, где он доступен.
- `VPN Settings` получили новые Android-first пункты и экраны:
  - `Per-App Proxy`
  - `Excluded Routes`
  - `Use Fragmentation`
  - `Use Mux`
  - `Preferred IP Type`
- В `VpnConnectionNotifier` добавлены guards для безопасной работы после async gaps и prewarm active profile stream, чтобы connect flow не зависел от race между profile stream и UI action.

## Acceptance Result

### Functional

- `PASS`: Android app discovery реализован и доступен из Flutter через platform channel.
- `PASS`: `Per-App Proxy` режимы сохраняются в settings и участвуют в connect runtime mapping.
- `PASS`: `proxySelected` маппится в `blockedApps` как список всех невыбранных приложений.
- `PASS`: `bypassSelected` маппится в `blockedApps` как список выбранных приложений.
- `PASS`: `VPN Settings` содержит новые экраны и transport controls из Phase 2 scope.

### Safety / honesty

- `PASS`: `Excluded Routes` явно помечены как capability-safe foundation; поведение не маскируется под fully shipped Android routing bypass.
- `PASS`: unsupported platform behavior для per-app proxy не ломает connect flow и корректно деградирует.

### Quality

- `PASS`: добавлены/обновлены unit, widget и provider integration tests.
- `PASS`: таргетный `dart analyze` по изменённым файлам проходит без issues.
- `PASS`: таргетный Phase 2 regression pack проходит полностью.

## Validation Evidence

### Static

- `dart analyze lib/features/vpn/presentation/providers/vpn_connection_notifier.dart lib/features/settings/presentation/screens/vpn_settings_screen.dart lib/features/settings/presentation/screens/per_app_proxy_screen.dart lib/features/settings/presentation/screens/excluded_routes_screen.dart lib/features/settings/data/datasources/per_app_proxy_platform_service.dart lib/features/settings/presentation/providers/per_app_proxy_providers.dart lib/features/settings/domain/services/per_app_proxy_runtime_resolver.dart lib/features/vpn/data/repositories/vpn_repository_impl.dart lib/features/vpn/data/datasources/vpn_engine_datasource.dart lib/features/vpn/domain/entities/vpn_config_entity.dart`
- Result: `No issues found!`

### Tests

- `flutter test test/features/settings/domain/services/per_app_proxy_runtime_resolver_test.dart test/features/settings/data/datasources/per_app_proxy_platform_service_test.dart test/features/settings/presentation/screens/vpn_settings_screen_test.dart test/features/settings/presentation/screens/per_app_proxy_screen_test.dart test/features/settings/presentation/screens/excluded_routes_screen_test.dart test/features/vpn/data/repositories/vpn_repository_impl_test.dart test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart`
- Result: `All tests passed!`

## Remaining Limitation For Phase 3

- Stock `flutter_v2ray_plus` по-прежнему не применяет `bypassSubnets` в Android route builder, поэтому `Excluded Routes` сейчас являются persisted UX/runtime foundation, но не full native route bypass implementation.
- `Fragmentation`, `Mux` и `Preferred IP Type` уже вынесены в settings UX/domain foundation, но их полная инъекция в actual config generation требует следующей фазы runtime patching.
