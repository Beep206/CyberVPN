# CyberVPN Mobile Release Readiness Checklist

Date: 2026-04-17  
Product: `cybervpn_mobile`  
Type: `Post-Phase-7 operational runbook`  
References:
- [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)
- [2026-04-16-cybervpn-mobile-phase-5-execution-plan.md](./2026-04-16-cybervpn-mobile-phase-5-execution-plan.md)
- [2026-04-16-cybervpn-mobile-phase-6-execution-plan.md](./2026-04-16-cybervpn-mobile-phase-6-execution-plan.md)
- [2026-04-17-cybervpn-mobile-phase-7-execution-plan.md](./2026-04-17-cybervpn-mobile-phase-7-execution-plan.md)

## Purpose

Этот документ нужен для выпуска Happ-like VPN settings после завершения `Phase 7`. Это не ещё одна implementation phase, а operational handoff для QA, release owner и mobile team.

Документ покрывает:

- release gates перед кандидатом в релиз
- manual QA script для Android и iOS
- observability checks
- go / no-go rules
- rollback triggers

## Release Scope

В текущий release scope входят:

- `Settings > VPN` как hub
- `VPN Settings / General`
- `Routing`
- `Per-App Proxy`
- `Advanced`
- `Subscriptions`
- `Ping`
- `Diagnostics > Speed Test`
- runtime wiring и observability для:
  - routing profiles
  - per-app proxy
  - excluded routes
  - fragmentation
  - mux
  - preferred IP type
  - ping mode / target URL

Основные маршруты приложения:

- `/settings/vpn`
- `/settings/vpn/general`
- `/settings/vpn/routing`
- `/settings/vpn/per-app-proxy`
- `/settings/vpn/advanced`
- `/settings/vpn/subscriptions`
- `/settings/vpn/ping`
- `/diagnostics`
- `/diagnostics/speed-test`
- `/diagnostics/logs`

## Platform Support Matrix

### Android

- `General`: supported
- `Routing`: supported
- `Excluded Routes`: supported in UX/runtime foundation, Android-first path
- `Per-App Proxy`: supported
- `Fragmentation`: supported when runtime capability exists
- `Mux`: supported when runtime capability exists
- `Preferred IP Type`: supported when runtime capability exists
- `Manual MTU`: supported when runtime capability exists
- `Subscriptions`: supported
- `Ping`: supported

### iOS

- `General`: supported
- `Routing`: supported as stored/runtime-config layer
- `Per-App Proxy`: hidden / unsupported in this release
- `Excluded Routes`: hidden / unsupported in this release
- `Fragmentation`: reduced semantics
- `Mux`: reduced semantics
- `Preferred IP Type`: reduced semantics
- `Manual MTU`: hidden / unsupported in this release
- `Subscriptions`: supported
- `Ping`: supported

## Release Inputs

Перед началом manual QA должны быть готовы:

- релизная ветка или кандидат commit SHA
- Android build artifact
- iOS build artifact
- changelog по Phase 5-7
- список известных residuals из Phase 6-7

## Test Data Prerequisites

Подготовить заранее:

- минимум `1` рабочий VPN сервер
- минимум `1` imported config
- минимум `1` remote subscription profile
- минимум `2` обычных Android-приложения для `Per-App Proxy`
- тестовый routing profile с минимум `3` rules:
  - `domainSuffix = google.com -> direct`
  - `domainKeyword = ads -> block`
  - `ipCidr = 1.1.1.0/24 -> proxy`
- тестовые excluded routes:
  - `192.168.1.0/24`
  - `10.0.0.0/8`
- ping target URL:
  - `https://google.com/generate_204`

## Device Matrix

Минимальный device coverage:

- Android: `1` stock-like device и `1` OEM device
- iOS: `1` iPhone на текущей поддерживаемой версии iOS

Если есть время на расширение:

- Android tablet / foldable
- iPhone с другой major iOS version

## Pre-Release Gates

### Engineering Gates

- [ ] `flutter analyze` по затронутым settings / vpn / diagnostics / test files зелёный
- [ ] расширенный VPN notifier/provider regression pack зелёный
- [ ] Android compile gate зелёный
- [ ] нет новых unresolved crash / blocker issues после merge

Рекомендуемый regression pack:

```bash
cd cybervpn_mobile
flutter test \
  test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart \
  test/features/vpn/presentation/providers/vpn_connection_provider_test.dart \
  test/features/vpn/presentation/providers/vpn_state_machine_test.dart \
  test/features/vpn/presentation/providers/vpn_lifecycle_reconciliation_test.dart \
  test/features/vpn/presentation/providers/vpn_websocket_test.dart
```

### Product Gates

- [ ] Android manual QA completed
- [ ] iOS manual QA completed
- [ ] support matrix behavior подтверждён на обеих платформах
- [ ] `Settings > VPN` hub не содержит dead navigation paths

### Observability Gates

- [ ] `vpn.runtime` logs появляются на connect flow
- [ ] `vpn.connect` warning появляется только при ожидаемом fallback scenario
- [ ] нет silent connect crash при active-profile lookup

## Manual QA Script

### 1. Common Smoke

Выполнить на обеих платформах:

1. Открыть `/settings/vpn`.
2. Проверить, что видны секции `Connection` и `Operations`.
3. Зайти в `VPN Settings`, `Routing`, `Advanced`, `Subscriptions`, `Ping`.
4. Проверить, что возврат назад работает без потери состояния экрана.
5. Запустить обычное подключение к VPN из основного connection flow.
6. Отключиться от VPN.

Ожидаемо:

- экраны открываются без ошибок
- hub summary отражает текущие значения settings
- connect / disconnect работают без regressions

### 2. Android: General

Проверить:

1. `Preferred Protocol`
2. `Auto-connect on launch`
3. `Auto-connect on untrusted Wi-Fi`
4. `Kill Switch`
5. `DNS Provider`
6. `Custom DNS`
7. `MTU Auto / Manual`

Ожидаемо:

- изменения сохраняются после возврата на `/settings/vpn`
- summary на hub обновляется
- custom DNS и manual MTU переживают re-open экрана

### 3. Android: Routing

Проверить:

1. Включить `Enable routing rules`.
2. Создать routing profile.
3. Добавить минимум `3` rules с разными `matchType` / `action`.
4. Сделать профиль активным.
5. Открыть `Excluded Routes`.
6. Добавить `192.168.1.0/24` и `10.0.0.0/8`.
7. Удалить один route.
8. Вернуться на hub.
9. Подключиться к VPN.

Ожидаемо:

- profile сохраняется
- active profile отображается на routing экране и в hub summary
- excluded routes сохраняются
- connect проходит без UI error
- в логах есть `activeRoutingProfileId` и `bypassSubnetCount`

### 4. Android: Per-App Proxy

Проверить:

1. Открыть `/settings/vpn/per-app-proxy`.
2. Выставить `Off`.
3. Выставить `Selected apps use proxy`.
4. Отметить минимум `2` приложения.
5. Выставить `Selected apps bypass proxy`.
6. Снова сохранить выбор.
7. Подключиться к VPN после каждого режима.

Ожидаемо:

- mode сохраняется
- selected apps сохраняются
- connect проходит
- в логах видны `perAppProxyMode`, `perAppSelectionCount`, `blockedAppCount`

### 5. Android: Advanced

Проверить:

1. Открыть `/settings/vpn/advanced`.
2. Включить `Use Fragmentation`.
3. Включить `Use Mux`.
4. Переключить `Preferred IP Type`:
   - `Auto`
   - `IPv4 only`
   - `IPv6 only`
5. Подключиться к VPN после изменения.

Ожидаемо:

- toggles сохраняются
- connect проходит
- в логах отражаются:
  - `fragmentationEnabled`
  - `muxEnabled`
  - `preferredIpType`
- если capability недоступен, это видно в help text или warning log, но не приводит к crash

### 6. iOS: Support Matrix Behavior

Проверить:

1. Открыть `/settings/vpn`.
2. Убедиться, что `Per-App Proxy` скрыт.
3. Открыть `Routing`.
4. Проверить, что `Excluded Routes` не предлагаются как editable Android-style flow.
5. Открыть `Advanced`.
6. Проверить наличие iOS notice про reduced subset.
7. Переключить `Fragmentation`, `Mux`, `Preferred IP Type`.
8. Подключиться к VPN.

Ожидаемо:

- iOS не показывает dead Android-only controls
- reduced-semantics текст присутствует
- connect проходит
- нет misleading UX, где control виден, но не имеет объяснения

### 7. Subscriptions

Проверить на обеих платформах:

1. Открыть `/settings/vpn/subscriptions`.
2. Перейти в `Imported Configurations`.
3. Вернуться назад.
4. Перейти в `Add Subscription URL`.
5. Вернуться назад.
6. Перейти в `Scan QR Code`.
7. Вернуться назад.
8. Нажать `Refresh All`.
9. Для существующего remote profile нажать refresh.
10. Если есть `supportUrl`, открыть support link.
11. Если есть `testUrl`, открыть provider page.
12. Проверить `Plans & Upgrades`.
13. Проверить `Payment History`.

Ожидаемо:

- navigation работает из одного operational hub
- refresh action показывает корректный snackbar
- remote profiles отображают metadata
- external links открываются без падения приложения

### 8. Ping and Diagnostics

Проверить на обеих платформах:

1. Открыть `/settings/vpn/ping`.
2. Переключить `TCP connect`.
3. Переключить `Real delay`.
4. Переключить display mode:
   - `Latency (ms)`
   - `Quality labels`
5. Задать `https://google.com/generate_204`.
6. Открыть `/diagnostics/speed-test`.
7. Проверить summary над кнопкой запуска.
8. Запустить speed test.
9. Вернуться в список серверов и проверить ping chip presentation.

Ожидаемо:

- `Speed Test` summary показывает текущие `pingMode` и target host
- ping mode сохраняется
- display mode реально меняет server-list presentation
- приложение не теряет settings после перезахода

### 9. Force Disconnect and Resume Mismatch

Проверить минимум на Android:

1. Подключиться к VPN.
2. Вызвать `force_disconnect` через тестовый backend или dev scenario.
3. Проверить terminal state.
4. Повторно подключиться.
5. Сымитировать resume mismatch scenario:
   - приложение считает себя connected
   - runtime disconnect случился в фоне
6. Вернуть приложение на foreground.

Ожидаемо:

- `force_disconnect` приводит к `VpnForceDisconnected`
- UI не зависает в ложном connected-state
- reconnect или disconnect path соответствует доступности текущего сервера

## Observability Checklist

После connect flow проверить, что в логах доступны:

- `serverId`
- `activeRoutingProfileId`
- `perAppProxyMode`
- `perAppSelectionCount`
- `blockedAppCount`
- `pingMode`
- `muxEnabled`
- `fragmentationEnabled`
- `preferredIpType`
- `bypassSubnetCount`
- `dnsServerCount`
- `applied`
- `skipped`

Если есть fallback:

- должен появиться warning `VPN runtime settings fell back to supported subset`

Если active profile resolution ломается:

- должен появиться warning `Failed to resolve active VPN profile during config lookup`
- connect flow не должен silently crash

Для ручной проверки логов использовать:

- `/diagnostics/logs`

## Go / No-Go Rules

### Go

Релиз можно выпускать, если:

- все engineering gates зелёные
- Android manual QA зелёный
- iOS manual QA зелёный
- нет blocker regressions в connect / disconnect / settings persistence
- observability события появляются штатно

### No-Go

Релиз останавливается, если найден хотя бы один из пунктов:

- connect flow падает после изменения advanced settings
- `Settings > VPN` содержит dead navigation route
- `Per-App Proxy` ломает обычный connect flow на Android
- iOS показывает Android-only control без корректного notice
- ping settings не доходят до `Speed Test`
- lifecycle mismatch оставляет UI в ложном connected-state

## Rollback Triggers

Немедленный rollback или hotfix обязателен, если после релиза наблюдается:

- рост connect failure rate
- массовый crash при открытии `Settings > VPN`
- повреждение persisted settings после обновления
- некорректное поведение `Per-App Proxy` на Android
- полный разрыв diagnostics / speed test flow

## Release Notes Input

В user-facing release notes достаточно отметить:

- reorganized `VPN Settings`
- new `Routing`, `Per-App Proxy`, `Advanced`, `Subscriptions`, `Ping` sections
- better diagnostics alignment
- Android-first support for advanced tunnel controls
- improved runtime stability and logging

## Residuals to Keep Visible

- feature-flag infrastructure для staged rollout всё ещё отсутствует
- iOS advanced support остаётся частично reduced
- полный device-level E2E с реальным сетевым forcing остаётся обязательным manual step

## Recommended Ownership

- `Release owner`: финальный go / no-go
- `Android QA`: Android full pass
- `iOS QA`: iOS reduced-semantics pass
- `Mobile engineer`: triage логов и hotfix if needed
