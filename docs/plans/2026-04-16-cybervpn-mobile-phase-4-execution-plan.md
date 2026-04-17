# CyberVPN Mobile: Phase 4 Execution Plan

Date: 2026-04-16  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

`Phase 4` в этой итерации трактуется как `iOS-safe UX / capability matrix phase`. Цель фазы: перестать показывать в `VPN Settings` dead toggles для iOS и зафиксировать честную platform matrix для advanced tunnel settings уровня Happ.

## Goal

Реализовать единый support matrix для advanced VPN settings, скрыть Android-only controls из стандартного iOS flow, оставить только реально применяемый subset с clear help text, и обновить дочерние экраны `Per-App Proxy` / `Excluded Routes` до capability-safe поведения.

## Estimate

- Оценка: `2-3 рабочих дня`
- Статус: `Completed`

## Tasks

### 1. Support matrix

- Добавить единый `VpnSettingsSupportMatrix`.
- Зафиксировать для каждой advanced feature один из статусов:
  - `supported`
  - `reduced`
  - `unsupportedHidden`
  - `unsupportedVisible`
- Привязать матрицу к current platform и runtime capabilities.

### 2. VPN Settings UX gating

- Перестроить `VPN Settings`, чтобы на iOS:
  - скрывались `Per-App Proxy`
  - скрывались `Excluded Routes`
  - скрывался `Manual MTU`
  - сохранялись `Fragmentation`, `Mux`, `Preferred IP Type` как `reduced semantics`
- Добавить platform notice в секцию advanced settings.

### 3. Child screen hardening

- Сделать `Per-App Proxy` read-only на unsupported platforms.
- Сделать `Excluded Routes` read-only на unsupported platforms.
- Обновить copy, чтобы не осталось старого Phase 2 утверждения про то, что Android runtime ещё не применяет excluded routes.

### 4. Test coverage

- Добавить unit tests на support matrix.
- Обновить widget tests для `VPN Settings`, `Per-App Proxy`, `Excluded Routes`.
- Покрыть iOS-mode rendering через provider overrides вместо platform-specific test harness hacks.

## Acceptance Criteria

### Functional

- На iOS в стандартном `VPN Settings` flow отсутствуют dead toggles для `Per-App Proxy`, `Excluded Routes` и `Manual MTU`.
- `Fragmentation`, `Mux` и `Preferred IP Type` остаются доступны на iOS, но сопровождаются честным help text про reduced semantics.
- `Per-App Proxy` и `Excluded Routes`, если открыть их напрямую на unsupported platform, работают как read-only informational screens.
- Android UX не теряет уже реализованный advanced settings flow.

### Safety / honesty

- UI больше не обещает iOS capabilities, которых нет в текущем plugin/runtime wiring.
- Copy на `Excluded Routes` отражает фактическое состояние после Phase 3: Android route bypass уже применяется.

### Quality

- Targeted `dart analyze` проходит без замечаний.
- Targeted settings test pack проходит полностью.

## Actual Result

`Phase 4` закрыта в полном объёме, запланированном для iOS-safe UX.

- Добавлен `VpnSettingsSupportMatrix` и provider wiring для settings-layer platform gating.
- `VpnSettingsScreen` теперь строит advanced section через support matrix:
  - Android сохраняет полный текущий набор advanced controls;
  - iOS показывает platform notice и скрывает `Per-App Proxy`, `Excluded Routes`, `Manual MTU`;
  - `Fragmentation`, `Mux`, `Preferred IP Type` остаются видимыми с reduced-semantics пояснениями.
- `PerAppProxyScreen` переведён в read-only informational mode на unsupported platforms.
- `ExcludedRoutesScreen` переведён в read-only informational mode на unsupported platforms и больше не содержит устаревший Phase 2 текст.
- Добавлены tests для support matrix и iOS-specific widget rendering.

## Acceptance Result

### Functional

- `PASS`: iOS standard settings flow больше не показывает Android-only controls.
- `PASS`: `Fragmentation`, `Mux`, `Preferred IP Type` на iOS сопровождаются platform-aware help text.
- `PASS`: direct access в `Per-App Proxy` / `Excluded Routes` на unsupported platforms теперь read-only и честно описывает runtime limitation.
- `PASS`: Android advanced settings flow сохранён.

### Safety / honesty

- `PASS`: iOS capability claims приведены в соответствие с текущим `flutter_v2ray_plus` wiring.
- `PASS`: copy для `Excluded Routes` отражает уже реализованный Android runtime path из Phase 3.

### Quality

- `PASS`: targeted `dart analyze` зелёный.
- `PASS`: targeted settings/widget regression pack зелёный.

## Validation Evidence

### Static

- `cd cybervpn_mobile && dart analyze lib/features/settings/domain/services/vpn_settings_support_matrix.dart lib/features/settings/presentation/providers/vpn_settings_support_provider.dart lib/features/settings/presentation/screens/vpn_settings_screen.dart lib/features/settings/presentation/screens/per_app_proxy_screen.dart lib/features/settings/presentation/screens/excluded_routes_screen.dart test/features/settings/domain/services/vpn_settings_support_matrix_test.dart test/features/settings/presentation/screens/vpn_settings_screen_test.dart test/features/settings/presentation/screens/per_app_proxy_screen_test.dart test/features/settings/presentation/screens/excluded_routes_screen_test.dart`
- Result: `No issues found!`

### Tests

- `cd cybervpn_mobile && flutter test test/features/settings/domain/services/vpn_settings_support_matrix_test.dart test/features/settings/presentation/screens/vpn_settings_screen_test.dart test/features/settings/presentation/screens/per_app_proxy_screen_test.dart test/features/settings/presentation/screens/excluded_routes_screen_test.dart`
- Result: `All tests passed!`

## Residuals

- iOS `Excluded Routes` скрыты не потому, что Apple platform этого не умеет в принципе, а потому что текущий локальный `flutter_v2ray_plus` iOS path не пробрасывает `NEIPv4Settings.excludedRoutes` / `NEIPv6Settings.excludedRoutes` из Flutter layer в `PacketTunnelProvider`.
- iOS `Manual MTU` скрыт по той же причине: текущий tunnel provider использует фиксированный `mtu = 9000` и не принимает runtime MTU из Flutter.
- `Per-App Proxy` остаётся Android-only до появления отдельного iOS design/runtime решения. Для Phase 4 это сознательное скрытие, а не частичная псевдоподдержка.

## Sources

- Happ App Management: https://www.happ.su/main/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/dev-docs/routing
- Apple NetworkExtension / `NEIPv4Settings.excludedRoutes`: https://developer.apple.com/documentation/networkextension/neipv4settings/excludedroutes
- Apple NetworkExtension / `NEIPv6Settings.excludedRoutes`: https://developer.apple.com/documentation/networkextension/neipv6settings/excludedroutes
- Riverpod Providers: https://riverpod.dev/docs/concepts2/providers
- Flutter `TextField` API: https://api.flutter.dev/flutter/material/TextField-class.html
