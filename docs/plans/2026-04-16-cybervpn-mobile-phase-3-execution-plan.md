# CyberVPN Mobile: Phase 3 Execution Plan

Date: 2026-04-16  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

`Phase 3` в этой итерации трактуется как `runtime/config patch phase`. Цель фазы: перестать хранить advanced VPN settings как декоративный UI-only state и довести их до реального runtime path от `settings` до `Xray/Android VPN`.

## Goal

Реализовать runtime-ready config generation для Happ-like advanced settings, добавить capability-aware downgrades, пропатчить Android plugin под реальные `Excluded Routes` и `MTU`, и связать всё это с текущим connect flow.

## Estimate

- Оценка: `3-5 рабочих дней`
- Статус: `Completed`

## Tasks

### 1. Runtime config builder

- Добавить `VpnRuntimeConfigBuilder` как единый слой сборки runtime payload.
- Поддержать три входных сценария:
  - raw URI
  - полный Xray JSON
  - partial profile metadata JSON из subscription/profile storage

### 2. Capability-aware mapping

- Довести до runtime mapping для:
  - `Routing`
  - `Excluded Routes`
  - `Mux`
  - `Fragmentation`
  - `Preferred IP Type`
  - `DNS override`
  - `Manual MTU`
- Явно собирать `appliedSettings` и `skippedSettings`.

### 3. Connect flow integration

- Подключить builder в `VpnConnectionNotifier`.
- Передавать в runtime config не только `blockedApps`, но и:
  - generated JSON config
  - `dnsServers`
  - `bypassSubnets`
  - `mtu`

### 4. VPN engine hardening

- Перестроить `VpnEngineDatasource`, чтобы он принимал как raw URI, так и уже собранный JSON runtime config.
- Сохранять `dnsServers` и `mtu` для reconnect path.

### 5. Android native patch

- Пропатчить локальный `flutter_v2ray_plus`:
  - добавить `mtu` в Dart/native bridge
  - реально применять `bypassSubnets` в Android route builder
  - восстановить исключение server IP из VPN routes

## Acceptance Criteria

### Functional

- `VPN Settings` advanced toggles реально доходят до runtime, а не остаются только persisted state.
- Connect flow умеет генерировать runtime-ready config для raw URI, full JSON и partial profile metadata.
- Android runtime умеет применять `Excluded Routes` через `VpnService.Builder.addRoute(...)` с route subtraction.
- `Mux`, `Fragmentation`, `Preferred IP Type` и `Routing` реально отражаются в generated Xray JSON.
- `Manual MTU` пробрасывается в Android VPN builder и `tun2socks`.

### Safety / honesty

- Unsupported settings не теряются silently; они попадают в `skippedSettings` с причиной.
- Connect flow логирует, какие runtime settings реально применились.

### Quality

- `build_runner` проходит после расширения `VpnConfigEntity`.
- Таргетный analyze проходит для app и локального plugin.
- Таргетный regression pack по builder / datasource / repository / provider flow проходит.
- Android Kotlin compile проходит на debug variant.

## Actual Result

`Phase 3` закрыта в полном runtime объёме, запланированном для этой стадии.

- Добавлен `VpnRuntimeConfigBuilder`, который:
  - сохраняет raw URI path там, где JSON mutation не нужна;
  - собирает full Xray JSON при advanced runtime mapping;
  - умеет реконструировать full config из partial profile metadata.
- Добавлен `VpnRuntimeCapabilities` и provider wiring в DI.
- `VpnConnectionNotifier` теперь использует builder и пишет structured runtime log по `applied` / `skipped` settings.
- `VpnEngineDatasource` теперь:
  - нормализует raw URI в JSON только когда это нужно;
  - принимает и пробрасывает `dnsServers` и `mtu`;
  - сохраняет их для reconnect.
- `VpnRepositoryImpl` пробрасывает `dnsServers` / `mtu` в engine и сохраняет расширенную config metadata.
- Локальный `flutter_v2ray_plus` пропатчен:
  - Dart bridge поддерживает `mtu`;
  - Android plugin достаёт server endpoint из JSON config;
  - `XrayVPNService` применяет `bypassSubnets` как реальное исключение IPv4 CIDR из VPN route set;
  - `MTU` применяется и к `VpnService.Builder`, и к `tun2socks`.

## Acceptance Result

### Functional

- `PASS`: advanced settings трассируются от `settingsProvider` до runtime connect path.
- `PASS`: runtime builder покрывает raw URI, full JSON и partial profile metadata.
- `PASS`: `Routing`, `Mux`, `Fragmentation`, `Preferred IP Type`, `DNS override`, `Manual MTU` реально отражаются в generated config/runtime payload.
- `PASS`: Android `Excluded Routes` теперь не только сохраняются, но и реально участвуют в route calculation.
- `PASS`: reconnect path повторно использует `dnsServers` и `mtu`.

### Safety / honesty

- `PASS`: unsupported options попадают в `skippedSettings` с явной причиной.
- `PASS`: `VpnConnectionNotifier` логирует runtime application outcome.

### Quality

- `PASS`: `build_runner` прошёл.
- `PASS`: app-side targeted `dart analyze` зелёный.
- `PASS`: локальный `flutter_v2ray_plus` проходит `flutter analyze`.
- `PASS`: targeted Phase 3 tests зелёные.
- `PASS`: `:app:compileDevDebugKotlin` проходит успешно.

## Validation Evidence

### Codegen

- `cd cybervpn_mobile && flutter pub run build_runner build --delete-conflicting-outputs`
- Result: `Success`

### Static

- `cd cybervpn_mobile && dart analyze lib/core/di/providers.dart lib/core/di/vpn_providers.dart lib/features/vpn/domain/entities/vpn_config_entity.dart lib/features/vpn/domain/services/vpn_runtime_capabilities.dart lib/features/vpn/domain/services/vpn_runtime_config_builder.dart lib/features/vpn/presentation/providers/vpn_connection_notifier.dart lib/features/vpn/data/datasources/vpn_engine_datasource.dart lib/features/vpn/data/repositories/vpn_repository_impl.dart`
- Result: `No issues found!`

- `cd packages/flutter_v2ray_plus && flutter analyze`
- Result: `No issues found!`

### Tests

- `cd cybervpn_mobile && flutter test test/features/vpn/domain/services/vpn_runtime_config_builder_test.dart test/features/vpn/data/datasources/vpn_engine_datasource_test.dart test/features/vpn/data/repositories/vpn_repository_impl_test.dart test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart`
- Result: `All tests passed!`

### Android compile

- `cd cybervpn_mobile/android && ./gradlew :app:compileDevDebugKotlin`
- Result: `BUILD SUCCESSFUL`

## Residuals

- Более широкий provider regression suite (`vpn_connection_provider_test.dart`, `vpn_state_machine_test.dart`) по-прежнему упирается в старую test-harness проблему: часть тестов не override'ит `activeVpnProfileProvider`, из-за чего Drift пытается открыть DB через `path_provider` и падает с `MissingPluginException`. Это не было внесено Phase 3 и не связано с новым runtime/config patching.
- Android route subtraction в этой фазе реализован для IPv4 CIDR, что соответствует текущему `Excluded Routes` UX. IPv6 route bypass можно рассматривать отдельной задачей позже.

## Sources

- Happ App Management: https://www.happ.su/main/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/dev-docs/routing
- Xray Freedom outbound / Fragment: https://xtls.github.io/en/config/outbounds/freedom.html
- Xray Routing: https://xtls.github.io/en/config/routing.html
- Xray Outbound / Mux: https://xtls.github.io/en/config/outbound.html
- Xray Transport / `dialerProxy`: https://xtls.github.io/en/config/transport.html
