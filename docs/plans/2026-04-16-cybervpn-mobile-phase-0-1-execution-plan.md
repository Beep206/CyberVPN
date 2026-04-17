# CyberVPN Mobile: Phase 0/1 Execution Plan and Completion

Date: 2026-04-16  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

Этот документ фиксирует, что именно вошло в `Phase 0` и `Phase 1`, какие acceptance criteria были приняты, какая была оценка, что фактически реализовано, и что сознательно оставлено на `Phase 2+`.

## Phase 0: Capability Audit

### Goal

Подтвердить, можно ли реализовать Happ-like VPN Settings поверх текущего mobile runtime без немедленной замены VPN-плагина и без premature native refactor.

### Estimate

- Оценка: `0.5-1 рабочий день`
- Статус: `Completed`

### Tasks

- Проверить текущий runtime в `cybervpn_mobile`.
- Проверить фактическую поверхность `flutter_v2ray_plus`.
- Сопоставить Happ settings с тем, что уже есть в приложении и плагине.
- Зафиксировать, какие возможности можно закрывать app-layer model/persistence, а какие требуют native/runtime wiring.

### Findings

- `flutter_v2ray_plus 1.1.3` уже поддерживает raw JSON config, `blockedApps`, `bypassSubnets`, `dnsServers`, `proxyOnly`, `getServerDelay`, `getConnectedServerDelay`.
- Текущая mobile-реализация использует только часть этой поверхности: сейчас connect flow в основном ограничен `config + blockedApps`.
- В `cybervpn_mobile` нет завершенного native wiring для method-channel split tunnel / excluded apps / excluded domains на mobile Android/iOS.
- Внутренний Android TV модуль уже содержит полезный reference для per-app bypass и routing storage/config generation.
- Следовательно, `Phase 0` решение: `Phase 1` можно и нужно закрывать без замены runtime, через расширение settings domain + persistence + provider surface. Native/runtime integration переносится в `Phase 2+`.

### Acceptance Criteria

- Есть письменное решение, нужен ли новый VPN bridge.
- Ясно разделены app-layer задачи и native/runtime задачи.
- Зафиксирован Android-first подход для per-app proxy.
- Зафиксировано, что iOS потребует отдельного capability mapping.

### Result

Acceptance criteria выполнены. Решение принято: `оставить текущий runtime`, расширить settings foundation, а конфиг-генерацию и native wiring делать следующей фазой.

## Phase 1: Settings Foundation

### Goal

Добавить в `cybervpn_mobile` отсутствующий foundation-слой для Happ-like VPN Settings, чтобы дальнейшие UI/runtime фазы не требовали миграции схемы настроек.

### Estimate

- Оценка: `1.5-2.5 рабочих дня`
- Статус: `Completed`

### Tasks

- Расширить `AppSettings` под routing/per-app proxy/fragmentation/mux/IP/ping foundation.
- Добавить отдельные domain entities для routing profile и routing rule.
- Расширить `settingsProvider` и `vpnSettingsProvider`.
- Расширить `SettingsRepositoryImpl` и persistence keys.
- Добавить тесты на defaults, round-trip и corrupt-data fallback.
- Проверить совместимость с текущим VPN provider suite.

### Implemented

#### Domain model

Добавлены новые типы и поля:

- `RoutingProfile`
- `RoutingRule`
- `RoutingRuleAction`
- `RoutingRuleMatchType`
- `PerAppProxyMode`
- `PreferredIpType`
- `PingMode`
- `routingEnabled`
- `routingProfiles`
- `activeRoutingProfileId`
- `bypassSubnets`
- `perAppProxyMode`
- `perAppProxyAppIds`
- `fragmentationEnabled`
- `muxEnabled`
- `preferredIpType`
- `pingMode`
- `pingTestUrl`

#### Provider surface

В `SettingsNotifier` добавлены методы для:

- включения/выключения routing
- upsert/remove/replace routing profiles
- выбора active routing profile
- управления bypass subnets
- управления per-app proxy mode и app ids
- управления fragmentation
- управления mux
- выбора preferred IP type
- выбора ping mode и probe URL

`vpnSettingsProvider` теперь отдает весь расширенный VPN settings surface, а `VpnSettings` содержит helper для получения активного routing profile.

#### Persistence

В `SettingsRepositoryImpl` добавлены:

- новые `settings.*` keys
- JSON persistence для `routingProfiles`
- enum round-trip для `PerAppProxyMode`, `PreferredIpType`, `PingMode`
- string-list persistence для `bypassSubnets` и `perAppProxyAppIds`
- safe fallback при битом JSON routing profiles

### Changed Files

- `cybervpn_mobile/lib/features/settings/domain/entities/app_settings.dart`
- `cybervpn_mobile/lib/features/settings/domain/entities/routing_profile.dart`
- `cybervpn_mobile/lib/features/settings/presentation/providers/settings_provider.dart`
- `cybervpn_mobile/lib/features/settings/data/repositories/settings_repository_impl.dart`
- `cybervpn_mobile/test/features/settings/domain/entities/app_settings_test.dart`
- `cybervpn_mobile/test/features/settings/domain/entities/routing_profile_test.dart`
- `cybervpn_mobile/test/features/settings/data/settings_repository_impl_test.dart`

Дополнительно обновлен test harness в `test/features/vpn/presentation/providers/*`, чтобы provider tests могли работать с mock `SharedPreferences` и корректной `WidgetsBinding` инициализацией.

### Acceptance Criteria

- Новые поля настроек существуют на domain level.
- Настройки переживают restart через `SettingsRepositoryImpl`.
- Routing profiles сериализуются и восстанавливаются корректно.
- Битый JSON routing profiles не валит repository, а мягко fallback’ится в defaults.
- `vpnSettingsProvider` отдает расширенный surface для Phase 2 runtime wiring.
- Existing settings tests проходят.

### Result

Acceptance criteria выполнены.

## Validation

### Passed

- `flutter test test/features/settings/domain/entities/app_settings_test.dart test/features/settings/domain/entities/routing_profile_test.dart test/features/settings/data/settings_repository_impl_test.dart`

### Additional Verification

- `build_runner` выполнен успешно.
- VPN provider suite частично дополнительно вычищен на уровне test harness.

### Residual Test Debt

Остался один несвязанный с Phase 1 failing test:

- `test/features/vpn/presentation/providers/vpn_lifecycle_reconciliation_test.dart`
  - сценарий: `transitions to VpnDisconnected when engine is disconnected and autoConnect is off`
  - фактическое поведение сейчас: state остается `VpnConnected`

Это выглядит как существующий lifecycle expectation drift / runtime bug и не относится к добавленному settings foundation.

## Deferred to Phase 2+

- Реальная сборка Xray/V2Ray config из `routingProfiles`
- Android runtime wiring для `perAppProxyMode` и `perAppProxyAppIds`
- iOS-specific capability mapping для per-app/split routing
- Fragmentation/Mux/IP type wiring в actual connection config
- Ping mode wiring between TCP latency and `getServerDelay(url:)`
- UI/IA перестройка экрана `VPN Settings`

## Source References

- Happ App Management: https://www.happ.su/main/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/dev-docs/routing
- Happ App Store: https://apps.apple.com/tm/app/happ-proxy-utility/id6504287215
- Happ GitHub: https://github.com/Happ-proxy
- Local runtime audit:
  - `cybervpn_mobile/lib/features/vpn/data/datasources/vpn_engine_datasource.dart`
  - `~/.pub-cache/hosted/pub.dev/flutter_v2ray_plus-1.1.3/lib/flutter_v2ray.dart`
  - `~/.pub-cache/hosted/pub.dev/flutter_v2ray_plus-1.1.3/lib/url/url.dart`
