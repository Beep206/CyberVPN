# CyberVPN Mobile: Phase 7 Execution Plan

Date: 2026-04-17  
Product: `cybervpn_mobile`  
Reference: [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md)

## Scope

`Phase 7` в этой итерации трактуется как `QA / hardening / observability / rollout readiness` для уже внедрённых Happ-like VPN settings. Цель фазы: убрать нестабильность в `vpnConnectionNotifier` и широких provider-suite, закрыть runtime blind spots и зафиксировать rollout strategy перед дальнейшим parity work.

## Goal

Закрыть четыре направления:

- `Notifier hardening`
  - убрать fragile зависимость от eager warm-up активного профиля
  - сделать on-demand lookup `activeVpnProfileProvider` безопасным без внешнего watcher-а
- `Regression stabilization`
  - восстановить зелёный status у широкого `vpn provider` regression pack
  - синхронизировать устаревшие ожидания тестов с текущим notifier contract
- `Observability`
  - довести runtime logging до уровня acceptance из master plan
  - явно логировать unsupported fallback-ы и runtime-applied settings
- `Rollout readiness`
  - описать QA matrix и rollout strategy
  - честно зафиксировать, что feature-flag automation в app пока отсутствует

## Estimate

- Оценка: `2-3 рабочих дня`
- Статус: `Completed`

## Tasks

### 1. Harden active profile lookup

- Проверить runtime-path после удаления eager warm-up `activeVpnProfileProvider`.
- Убрать race, при которой `StreamProvider` мог быть disposed в `loading` при on-demand config lookup.
- Сохранить lazy behavior, но сделать lookup безопасным через временную container-level subscription.

### 2. Stabilize provider regression suites

- Привести `vpn_connection_provider_test.dart`, `vpn_state_machine_test.dart`, `vpn_lifecycle_reconciliation_test.dart`, `vpn_websocket_test.dart` к единому harness pattern.
- Подложить controlled `activeVpnProfileProvider` overrides в suite-ах, где profile storage не является предметом теста.
- Убрать flaky ожидания на `Future.delayed(...)` там, где нужен predicate-based wait.

### 3. Align tests with current runtime contract

- Зафиксировать текущую semantics для `force_disconnect` как `VpnForceDisconnected`, а не `VpnError`.
- Зафиксировать текущую semantics lifecycle reconciliation:
  - reconnect при resume-mismatch идёт по availability текущего сервера
  - поведение не опирается на старое тестовое допущение про `autoConnectOnLaunch`

### 4. Expand runtime observability

- Логировать runtime-prepared config с ключевыми operational fields:
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
- Логировать отдельное warning-событие для unsupported fallback subset.
- Логировать failures active profile resolution без обвала connect flow.

### 5. Final QA pass and rollout doc

- Прогнать расширенный notifier/provider regression pack.
- Зафиксировать acceptance result, QA matrix и rollout residuals в отдельном execution-doc.

## Acceptance Criteria

### Functional

- `vpnConnectionNotifier.connect()` безопасно работает без предварительного warm-up `activeVpnProfileProvider`.
- Config lookup из active profile подхватывает `configData` для profile-backed servers.
- `force_disconnect` обрабатывается предсказуемо и даёт стабильный terminal state.
- Lifecycle reconciliation при resume соответствует текущей notifier semantics и не ломает reconnect path.

### Observability

- Runtime log содержит ключевые fields из Phase 7 master plan.
- Unsupported runtime fallbacks логируются отдельным warning событием.
- Ошибки active profile lookup не приводят к silent crash и видны в логах.

### Quality

- Targeted `flutter analyze` проходит без ошибок.
- Расширенный notifier/provider regression pack проходит полностью.
- Residual `path_provider/Drift` failure в provider-suite больше не воспроизводится в Phase 7 coverage set.

## Actual Result

`Phase 7` закрыта в planned объёме для hardening/QA слоя.

- В [vpn_connection_notifier.dart](../cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_connection_notifier.dart) убран fragile dependency-path, при котором on-demand lookup `activeVpnProfileProvider.future` мог стартовать `StreamProvider` без живой подписки и получать dispose в `loading`.
- Lookup активного профиля теперь удерживает provider на время резолва через `ref.container.listen(...)`, после чего корректно закрывает временную подписку.
- В том же notifier добавлены runtime warning/info logs для:
  - prepare phase runtime config
  - unsupported fallback subset
  - failure active profile resolution
  - unsupported per-app proxy with selection count
- Runtime observability теперь покрывает поля, ожидаемые в master plan:
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
- В [vpn_connection_provider_test.dart](../cybervpn_mobile/test/features/vpn/presentation/providers/vpn_connection_provider_test.dart), [vpn_state_machine_test.dart](../cybervpn_mobile/test/features/vpn/presentation/providers/vpn_state_machine_test.dart), [vpn_lifecycle_reconciliation_test.dart](../cybervpn_mobile/test/features/vpn/presentation/providers/vpn_lifecycle_reconciliation_test.dart) и [vpn_websocket_test.dart](../cybervpn_mobile/test/features/vpn/presentation/providers/vpn_websocket_test.dart) выровнен harness:
  - mock `SharedPreferences`
  - null-profile override для `activeVpnProfileProvider`
  - predicate-based waits вместо `Future.delayed(...)` там, где state machine асинхронна
- В [vpn_connection_dedup_test.dart](../cybervpn_mobile/test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart) восстановлена реальная проверка profile-backed `configData`, и теперь suite подтверждает, что active profile lookup действительно подхватывает `configData` для обычного connect-flow.
- `vpn_websocket_test.dart` и `vpn_state_machine_test.dart` приведены к текущему контракту notifier: `force_disconnect` завершает flow в `VpnForceDisconnected`, а не в старом `VpnError`.
- `vpn_lifecycle_reconciliation_test.dart` выровнен под фактическую contract-semantics resume reconciliation: reconnect делается при available server, а disconnect path покрыт unavailable branch.

## Acceptance Result

### Functional

- `PASS`: `connect()` больше не зависит от внешнего warm-up активного профиля.
- `PASS`: profile-backed server connect подхватывает `configData` из active profile.
- `PASS`: `force_disconnect` стабильно завершает flow через `VpnForceDisconnected`.
- `PASS`: lifecycle reconciliation и reconnect path покрыты актуальными ожиданиями.

### Observability

- `PASS`: runtime logging содержит ключевые Phase 7 operational fields.
- `PASS`: unsupported fallback subset логируется отдельно warning-событием.
- `PASS`: failure active profile lookup логируется и не ломает provider initialization.

### Quality

- `PASS`: targeted `flutter analyze` зелёный.
- `PASS`: расширенный notifier/provider regression pack зелёный.
- `PASS`: residual Phase 6 provider failures с `path_provider/Drift` в Phase 7 coverage set больше не воспроизводятся.

## Validation Evidence

### Static

- `cd cybervpn_mobile && flutter analyze lib/features/vpn/presentation/providers/vpn_connection_notifier.dart test/features/vpn/presentation/providers/vpn_connection_provider_test.dart test/features/vpn/presentation/providers/vpn_state_machine_test.dart test/features/vpn/presentation/providers/vpn_lifecycle_reconciliation_test.dart test/features/vpn/presentation/providers/vpn_websocket_test.dart test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart`
- Result: `No issues found!`

### Tests

- `cd cybervpn_mobile && flutter test test/features/vpn/presentation/providers/vpn_connection_provider_test.dart test/features/vpn/presentation/providers/vpn_state_machine_test.dart test/features/vpn/presentation/providers/vpn_lifecycle_reconciliation_test.dart`
- Result: `All tests passed!`

- `cd cybervpn_mobile && flutter test test/features/vpn/presentation/providers/vpn_websocket_test.dart`
- Result: `All tests passed!`

- `cd cybervpn_mobile && flutter test test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart --plain-name "connect() resolves configData from the active profile server"`
- Result: `All tests passed!`

- `cd cybervpn_mobile && flutter test test/features/vpn/presentation/providers/vpn_connection_dedup_test.dart test/features/vpn/presentation/providers/vpn_connection_provider_test.dart test/features/vpn/presentation/providers/vpn_state_machine_test.dart test/features/vpn/presentation/providers/vpn_lifecycle_reconciliation_test.dart test/features/vpn/presentation/providers/vpn_websocket_test.dart`
- Result: `All tests passed!`

## QA Matrix

- `PASS`: notifier initialization without eager active-profile warm-up
- `PASS`: profile-backed config resolution for standard connect flow
- `PASS`: auto-connect and recommended-server fallback scenarios
- `PASS`: disconnect and force-disconnect terminal states
- `PASS`: lifecycle resume reconciliation on connected/disconnected/mismatch branches
- `PASS`: provider-side side effects for kill switch, persistence, auto-reconnect
- `PASS`: per-app blocked-app mapping in connect flow

## Rollout Strategy

- Рекомендованный rollout для этой фазы: ship как `hardening + observability` patch, без UI gating.
- Runtime behavior изменений здесь не добавляет нового user-facing surface; фаза стабилизирует уже shipped settings/runtime paths.
- Логически rollout стоит сопровождать:
  - manual Android smoke pass на connect / disconnect / force_disconnect / resume mismatch
  - log inspection по новым `vpn.runtime` и `vpn.connect` событиям
  - monitoring regression rate по connect failures после релиза

## Residuals

- В приложении по-прежнему нет полноценной feature-flag infrastructure для staged rollout advanced VPN settings; в этой фазе rollout strategy документирована, но не автоматизирована в коде.
- `Phase 7` закрывает QA/hardening именно для provider/notifier слоя. Полный on-device E2E проход с реальным `VpnService` и real network forcing нужно делать отдельным manual device pass.
- Observability улучшена на app-side, но централизованный remote log ingestion / dashboarding в рамках mobile app этой фазой не внедрялся.

## Sources

- Happ App Management: https://www.happ.su/main/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/dev-docs/routing
- Riverpod provider overrides: https://riverpod.dev/docs/concepts2/overrides
- Riverpod testing: https://riverpod.dev/docs/how_to/testing
- Riverpod reading providers: https://docs-v2.riverpod.dev/docs/concepts/reading
