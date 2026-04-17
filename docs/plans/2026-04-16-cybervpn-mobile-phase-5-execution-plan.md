# CyberVPN Mobile: Phase 5 Execution Plan

Date: 2026-04-16  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

`Phase 5` в этой итерации трактуется как `VPN Settings information architecture phase`. Цель фазы: перестроить плоский `VPN Settings` screen в модульную операционную структуру, близкую к Happ, не ломая foundation, сделанный в Phases 0-4.

## Goal

Сделать `VPN Settings` hub с отдельными экранами для:

- `General`
- `Routing`
- `Per-App Proxy`
- `Advanced`
- `Subscriptions`
- `Ping`

и связать это с app router, settings search и уже существующими diagnostics/config-import flows.

## Estimate

- Оценка: `3-4 рабочих дня`
- Статус: `Completed`

## Tasks

### 1. VPN Settings hub

- Превратить `/settings/vpn` в hub screen.
- Добавить summary tiles для modular areas.
- Учесть iOS support matrix из Phase 4, чтобы Android-only entries не возвращались в стандартный iOS flow.

### 2. Dedicated settings screens

- Вынести `General` в отдельный screen:
  - protocol
  - auto-connect
  - kill switch
  - DNS
  - MTU
- Вынести `Routing` в отдельный screen:
  - routing enable/disable
  - active routing profile
  - basic routing profile CRUD
  - excluded routes entry
- Вынести `Advanced`, `Subscriptions`, `Ping` в отдельные screens.

### 3. Navigation and search wiring

- Добавить child routes под `/settings/vpn/*`.
- Обновить `SettingsSearchDelegate`, чтобы он вёл в соответствующие modular screens.

### 4. Test coverage

- Переписать old `vpn_settings_screen_test` под hub-model.
- Добавить screen tests для:
  - `VpnGeneralSettingsScreen`
  - `RoutingSettingsScreen`
  - `AdvancedVpnSettingsScreen`
  - `SubscriptionSettingsScreen`
  - `PingSettingsScreen`

## Acceptance Criteria

### Functional

- `/settings/vpn` больше не перегружен low-level toggles и работает как hub.
- `General`, `Routing`, `Advanced`, `Subscriptions`, `Ping` доступны как отдельные operational screens.
- `Routing` screen умеет хотя бы базовый create/edit/delete/select flow для routing profiles.
- `Subscriptions` screen поднимает import/billing entry points на видимый уровень.
- `Ping` screen даёт отдельный control plane для `pingMode` и `pingTestUrl`.

### UX / architecture

- Новая IA делает VPN settings area модульной и ближе к Happ по операционному удобству.
- iOS-safe gating из Phase 4 сохраняется и не ломается новой структурой.
- Search routes ведут в правильные modular screens, а не в старый перегруженный page.

### Quality

- Targeted `dart analyze` проходит без ошибок.
- Targeted widget regression pack по новым settings screens проходит.

## Actual Result

`Phase 5` закрыта в полном planned объёме для IA refactor.

- `/settings/vpn` переведён в hub screen: [vpn_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/vpn_settings_screen.dart)
- Добавлены новые modular screens:
  - [vpn_general_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/vpn_general_settings_screen.dart)
  - [routing_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/routing_settings_screen.dart)
  - [advanced_vpn_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/advanced_vpn_settings_screen.dart)
  - [subscription_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/subscription_settings_screen.dart)
  - [ping_settings_screen.dart](../cybervpn_mobile/lib/features/settings/presentation/screens/ping_settings_screen.dart)
- Router расширен child routes под `/settings/vpn/*` в [app_router.dart](../cybervpn_mobile/lib/app/router/app_router.dart).
- `SettingsSearchDelegate` теперь ведёт в новые modular destinations.
- `RoutingSettingsScreen` даёт базовый CRUD для routing profiles с simple rule editor.
- `SubscriptionSettingsScreen` связывает config import sources и billing entry points.
- `PingSettingsScreen` выносит `pingMode` / `pingTestUrl` из общего VPN экрана в отдельный control surface.

## Acceptance Result

### Functional

- `PASS`: `/settings/vpn` стал hub screen.
- `PASS`: `General`, `Routing`, `Per-App Proxy`, `Advanced`, `Subscriptions`, `Ping` доступны отдельно.
- `PASS`: basic routing profile create/select/delete flow появился.
- `PASS`: subscription import/billing controls подняты в отдельный settings area.
- `PASS`: ping mode и test URL выделены в самостоятельный screen.

### UX / architecture

- `PASS`: новая IA стала модульной и ближе к Happ operational flow.
- `PASS`: iOS gating из Phase 4 сохранён; `Per-App Proxy` не возвращён в standard iOS hub flow.
- `PASS`: settings search маршрутизирует в новые modular screens.

### Quality

- `PASS`: targeted `dart analyze` зелёный.
- `PASS`: targeted widget tests по новым screens зелёные.

## Validation Evidence

### Static

- `cd cybervpn_mobile && dart analyze lib/app/router/app_router.dart lib/features/settings/presentation/screens/vpn_settings_screen.dart lib/features/settings/presentation/screens/vpn_general_settings_screen.dart lib/features/settings/presentation/screens/routing_settings_screen.dart lib/features/settings/presentation/screens/advanced_vpn_settings_screen.dart lib/features/settings/presentation/screens/subscription_settings_screen.dart lib/features/settings/presentation/screens/ping_settings_screen.dart lib/features/settings/presentation/widgets/settings_search.dart test/features/settings/presentation/screens/vpn_settings_screen_test.dart test/features/settings/presentation/screens/vpn_general_settings_screen_test.dart test/features/settings/presentation/screens/advanced_vpn_settings_screen_test.dart test/features/settings/presentation/screens/routing_settings_screen_test.dart test/features/settings/presentation/screens/subscription_settings_screen_test.dart test/features/settings/presentation/screens/ping_settings_screen_test.dart`
- Result: `No issues found!`

### Tests

- `cd cybervpn_mobile && flutter test test/features/settings/presentation/screens/vpn_settings_screen_test.dart test/features/settings/presentation/screens/vpn_general_settings_screen_test.dart test/features/settings/presentation/screens/advanced_vpn_settings_screen_test.dart test/features/settings/presentation/screens/routing_settings_screen_test.dart test/features/settings/presentation/screens/subscription_settings_screen_test.dart test/features/settings/presentation/screens/ping_settings_screen_test.dart`
- Result: `All tests passed!`

## Residuals

- `RoutingSettingsScreen` даёт базовый practical CRUD для routing profiles, но это ещё не полноценный Happ-level routing rule workbench с import/export и bulk editing.
- `Subscriptions` screen в этой фазе агрегирует уже существующие import/billing flows, но не вводит полноценный provider-managed parity layer; это остаётся задачей следующей фазы.
- `Ping` screen пока хранит `pingMode` и `pingTestUrl`, а deeper diagnostics/runtime integration остаётся Phase 6 work.

## Sources

- Happ App Management: https://www.happ.su/main/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/dev-docs/routing
- Flutter `showDialog`: https://api.flutter.dev/flutter/material/showDialog.html
- Flutter `TextFormField`: https://api.flutter.dev/flutter/material/TextFormField-class.html
- Flutter navigation docs: https://docs.flutter.dev/ui/navigation
- go_router package docs: https://pub.dev/packages/go_router
