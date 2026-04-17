# CyberVPN Mobile vs Happ: advanced settings parity addendum

## Цель

Этот документ дополняет основной план [2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md](./2026-04-16-cybervpn-mobile-happ-gap-analysis-plan.md) и фиксирует следующий parity-scope относительно Happ:

- `Advanced Settings > VPN Settings`
- `Subscriptions`
- `Ping`
- `Allow LAN Connections`
- `App Auto Start`
- `Other Settings > Statistics`
- `Logs`
- `Reset`

Документ опирается на:

- текущее состояние `cybervpn_mobile` после ранее выполненных mobile phases
- публичную документацию Happ, проверенную 17 апреля 2026 года
- UI-benchmark из вашего описания Happ, если публичный dev-doc не покрывает пункт напрямую

## Evidence Model

Чтобы не смешивать подтвержденные API-контракты и продуктовые наблюдения, дальше используется три уровня доказательств:

1. `Confirmed by Happ docs`
   - параметр или поведение публично описаны в документации Happ
2. `Observed in Happ UI benchmark`
   - пункт подтвержден вашим описанием UI/UX Happ, но не найден как явный dev-doc параметр
3. `Confirmed in CyberVPN code`
   - текущее состояние проверено локально по коду `cybervpn_mobile`

## Happ Sources Checked

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/ru/dev-docs/routing
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
- Happ Local Network Connections FAQ: https://www.happ.su/main/ru/faq/local-network-connections

Подтвержденные публичные Happ параметры, релевантные этому addendum:

- `server-address-resolve-enable`
- `server-address-resolve-dns-domain`
- `server-address-resolve-dns-ip`
- `subscription-autoconnect`
- `subscription-autoconnect-type`
- `subscription-ping-onopen-enabled`
- `subscription-auto-update-enable`
- `subscription-auto-update-open-enable`
- `profile-update-interval`
- `ping-type`
- `check-url-via-proxy`
- `change-user-agent`
- `app-auto-start`
- `per-app-proxy-mode`
- `per-app-proxy-list`
- `sniffing-enable`
- `subscriptions-collapse`
- `subscriptions-expand-now`
- `ping-result`
- `mux-enable`
- `proxy-enable`
- `tun-enable`
- `exclude-routes`

Важно: часть пунктов из вашего Happ benchmark не найдена как явный публичный dev-doc параметр. Это не значит, что функции в Happ нет; это значит, что для CyberVPN их нельзя проектировать как полностью верифицированный wire-compatible contract без дополнительного product decision или ручной device-verification.

## Current CyberVPN Baseline

### Что уже реализовано

По коду уже существуют:

- `VPN Settings` hub и разбивка по экранам:
  - `lib/features/settings/presentation/screens/vpn_settings_screen.dart`
  - `vpn_general_settings_screen.dart`
  - `routing_settings_screen.dart`
  - `advanced_vpn_settings_screen.dart`
  - `subscription_settings_screen.dart`
  - `ping_settings_screen.dart`
- модель настроек:
  - `lib/features/settings/domain/entities/app_settings.dart`
- support matrix по Android/iOS:
  - `lib/features/settings/domain/services/vpn_settings_support_matrix.dart`
- runtime builder под advanced config:
  - `lib/features/vpn/domain/services/vpn_runtime_config_builder.dart`
- Android-first per-app proxy и excluded routes foundation
- текущий subscriptions hub и refresh flows
- diagnostics speed test и log viewer

### Что реально есть в settings model сейчас

В `app_settings.dart` уже есть:

- `routingProfiles`
- `activeRoutingProfileId`
- `bypassSubnets`
- `perAppProxyMode`
- `perAppProxyAppIds`
- `dnsProvider`
- `customDns`
- `fragmentationEnabled`
- `muxEnabled`
- `preferredIpType`
- `pingMode`
- `pingTestUrl`
- `pingDisplayMode`
- `mtuMode`
- `mtuValue`
- `logLevel`

Ограничения текущей модели:

- `PingMode` поддерживает только `tcp` и `realDelay`
- `PingDisplayMode` поддерживает только `latency` и `quality`
- `LogLevel` поддерживает только `debug`, `info`, `warning`, `error`
- отдельной модели под local DNS, sniffing, VPN/proxy-only mode, server-resolve, LAN, autostart, subscription policy engine, file-backed logs и full app reset пока нет

### Что уже умеет runtime

`vpn_runtime_config_builder.dart` уже умеет:

- применять DNS override
- применять `bypassSubnets`
- применять `fragmentation`
- применять `mux`
- применять `preferredIpType`
- собирать runtime metadata и skip reasons

Но сейчас:

- generated config содержит `sniffing: { enabled: false }` по умолчанию
- `vpn_engine_datasource.dart` всегда вызывает engine с `proxyOnly: false`
- `excluded_routes_screen.dart` принимает только IPv4 CIDR
- UI и persistence не покрывают `server-address-resolve-*`
- нет UI и orchestration под `local DNS` / `DNS from JSON`

### Subscriptions сейчас

Текущее состояние подписочного слоя:

- `subscription_settings_screen.dart` уже является operational hub
- `subscription_fetcher.dart` парсит:
  - `profile-update-interval`
  - `support-url`
  - `test-url`
- `profile_update_notifier.dart` уже умеет app-scoped refresh logic
- `config_import_repository_impl.dart` уже делает dedupe по `rawUri`

Но сейчас:

- нет пользовательских глобальных policy toggles
- нет настраиваемого `connect-to` policy
- нет настраиваемого `subscription sort` policy
- нет явного UI для duplicate policy
- нет explicit UI для collapse behavior
- `User-Agent` захардкожен как `CyberVPN/1.0`

### Ping сейчас

По коду уже есть:

- `Ping` settings screen
- TCP latency path
- proxy-delay path уровня `realDelay`
- configurable `pingTestUrl`
- отображение результата как `latency` или `quality`

Ограничения:

- нет полного Happ-набора `via Proxy GET / via Proxy HEAD / TCP / ICMP`
- текущее `quality` не равно Happ-поведеню `icon`
- server-list ping и diagnostics ping еще не являются единым policy-driven pipeline

### Statistics сейчас

`connection_stats_entity.dart` и `vpn_stats_provider.dart` дают только aggregate counters:

- `downloadSpeed`
- `uploadSpeed`
- `totalDownload`
- `totalUpload`
- `connectionDuration`
- `serverName`
- `protocol`
- `ipAddress`

Отсутствует Happ-like разбиение на:

- proxy in/out speed
- proxy in/out traffic
- direct in/out speed
- direct in/out traffic
- separate server start time / session start time semantics

### Logs и Reset сейчас

Сейчас в приложении есть:

- `log_viewer_screen.dart`
- `AppLogger` in-memory ring buffer
- export и clear logs
- `settingsProvider.resetAll()`
- debug screen с `clear cache` и `reset settings`

Но отсутствуют:

- file-backed logs
- `access_log.txt`
- `subscription_log.txt`
- Xray file browser / config viewer
- log level options `auto` и `none`
- full app reset как отдельная безопасная операция

## Gap Matrix

| Scope | Happ benchmark / docs | CyberVPN now | Gap | Priority |
|---|---|---|---|---|
| Use local DNS | Observed in Happ UI benchmark | Нет local DNS listener/settings model | Новый runtime + settings scope | High |
| Local DNS port | Observed in Happ UI benchmark | Нет | Новый runtime + native bridge scope | High |
| Use DNS from JSON | Observed in Happ UI benchmark | Есть только `dnsProvider/customDns`, без JSON precedence flag | Нужны precedence rules и builder changes | High |
| Packet analysis / sniffing | Confirmed by Happ docs (`sniffing-enable`) | Runtime hardcodes `sniffing=false` | UI + persistence + runtime patch | High |
| Mode: VPN / proxy-only | Happ docs подтверждают `proxy-enable/tun-enable`, но явно помечают как Desktop-only | Plugin already supports `proxyOnly`, app always sends `false` | Нужен mobile product decision и runtime wiring | High |
| Resolve server | Confirmed by Happ docs (`server-address-resolve-*`) | Нет UI/runtime layer | Нужен preconnect resolver + storage | High |
| Excluded routes IPv4/IPv6 IP/CIDR | Confirmed by Happ docs (`exclude-routes`) | Есть Android-first foundation, но UI принимает только IPv4 CIDR | Typed route parser + IPv6 support + UX update | High |
| Background settings shortcut | Observed in Happ UI benchmark | Есть только reusable `openAppSettings()` helper | Нужен explicit menu entry | Low |
| Subscription auto update toggle | Confirmed by Happ docs (`subscription-auto-update-enable`) | Есть implicit refresh foundation, но нет user toggle | Policy engine отсутствует | Medium |
| Auto update interval (hours) | Confirmed by Happ docs (`profile-update-interval`) | Interval only parsed from subscription metadata | Нет global UI + persistence | Medium |
| Update notifications | Observed in Happ UI benchmark | Нет | Нужен notification flow | Medium |
| Update on open | Confirmed by Happ docs (`subscription-auto-update-open-enable`) | Startup refresh exists, но не user-controlled | Policy/UI gap | Medium |
| Ping on open | Confirmed by Happ docs (`subscription-ping-onopen-enabled`) | Нет | Lifecycle + diagnostics orchestration | Medium |
| Connect to last / lowest / random | Docs confirm `lastused` and `lowestdelay`; `random` observed in UI benchmark | Нет policy layer | Нужен server selection policy | Medium |
| Prevent duplicates | Observed in Happ UI benchmark | Dedupe есть, но жёстко в repo logic и без toggle | Нужен explicit policy | Medium |
| Collapse subscriptions | Confirmed by Happ docs (`subscriptions-collapse`) | Нет user-facing collapse policy | UI/persistence gap | Low |
| No filter | Observed in Happ UI benchmark | Нет | Требует уточнения semantics | Medium |
| Show / override User-Agent | Confirmed by Happ docs (`change-user-agent`) | Hardcoded `CyberVPN/1.0`, скрыт от пользователя | UI + fetcher wiring | Medium |
| Sort servers in subscription | Observed in Happ UI benchmark | Нет explicit subscription sorting policy | Needs view-model + persistence | Medium |
| Ping type: via Proxy GET | Confirmed by Happ docs (`ping-type: proxy`) | Частично через `realDelay`, но semantics не зафиксированы как GET | Need explicit strategy | High |
| Ping type: via Proxy HEAD | Confirmed by Happ docs (`ping-type: proxy-head`) | Speed test uses HEAD internally, но нет user-facing mode | Need explicit strategy | High |
| Ping type: TCP | Confirmed by Happ docs | Уже есть | Только привести к unified policy engine | Medium |
| Ping type: ICMP | Confirmed by Happ docs | Нет | Native/platform risk | High |
| Ping test URL | Confirmed by Happ docs (`check-url-via-proxy`) | Уже есть `pingTestUrl` | Mostly naming/UX alignment | Low |
| Ping result: time / icon | Confirmed by Happ docs (`ping-result`) | `latency / quality` | UI semantics mismatch | Medium |
| Allow LAN connections | Confirmed by Happ FAQ | Нет feature surface | Core/runtime/native work | High |
| App autostart | Confirmed by Happ docs (`app-auto-start`, Android-only) | Нет boot integration | Android OS integration | High |
| Statistics screen | Observed in Happ UI benchmark | Только aggregate stats | New domain + UI + runtime data source | High |
| Logs center | Observed in Happ UI benchmark; docs only partially cover log-related app-management | In-memory viewer only | File storage + file browser + richer settings | High |
| Reset: full app reset | Observed in Happ UI benchmark | Нет | New destructive flow with guardrails | Medium |
| Reset: settings reset | Observed in Happ UI benchmark | Уже есть | Need move from debug-only flow into formal settings IA | Low |

## Architecture Conclusions

### 1. Это уже не просто "еще несколько toggle"

Оставшийся Happ scope делится на четыре разных класса работ:

- `Product/settings layer`
  - enums
  - persistence
  - defaults
  - migrations
  - settings IA
- `Runtime/core layer`
  - sniffing
  - proxy-only mode
  - server resolve
  - DNS precedence
  - IPv6 excluded routes
- `OS integration layer`
  - autostart
  - app settings shortcut
  - LAN exposure
  - ICMP ping
- `Operational tooling layer`
  - file-backed logs
  - reset flows
  - richer statistics
  - notifications

### 2. Несколько Happ пунктов требуют явного product decision

До начала реализации нужно зафиксировать семантику следующих пунктов:

- `Use local DNS`
- `Local DNS port`
- `Use DNS from JSON`
- `No filter`
- `Random` в `Connect to`
- `Statistics`: что именно считается direct traffic на mobile
- `Full app reset`: включает ли logout, secure storage, imported profiles и локальные логи

Без этих решений Phase 8 можно делать только как schema-prep, но не как финальный runtime contract.

### 3. Не все Happ параметры мобильные один-к-одному

`proxy-enable` и `tun-enable` публично описаны в Happ docs как Desktop-oriented параметры. В CyberVPN mobile есть `flutter_v2ray_plus` флаг `proxyOnly`, но это не гарантирует полный UX/behavior parity с Happ mobile. Для mobile product parity нужно отдельно определить:

- является ли proxy-only режим supported feature на Android
- нужен ли он на iOS
- должен ли он жить рядом с VPN Settings, LAN settings и diagnostics

### 4. Statistics и Logs нельзя обещать без capability audit

Текущие mobile stats — агрегированные. Happ-level разбиение на proxy/direct counters может потребовать:

- дополнительные counters из Xray runtime
- patch в `flutter_v2ray_plus`
- собственный bridge для runtime metrics

То же самое относится к log files и Xray file browsing.

## Supplemental Roadmap

Нумерация продолжается после уже выполненных прошлых phases.

## Phase 8. Settings Schema, Contracts, and Precedence Rules

### Цель

Подготовить устойчивую модель данных и UX contracts для нового Happ scope без немедленного смешивания с runtime hacks.

### Работы

1. Расширить `AppSettings` и persistence:
   - `useLocalDns`
   - `localDnsPort`
   - `useDnsFromJson`
   - `sniffingEnabled`
   - `vpnRunMode` (`vpn`, `proxyOnly`)
   - `serverAddressResolveEnabled`
   - `serverAddressResolveDohUrl`
   - `serverAddressResolveDnsIp`
   - `excludedRouteEntries` typed model для IPv4/IPv6 IP/CIDR
   - `subscriptionAutoUpdateEnabled`
   - `subscriptionAutoUpdateIntervalHours`
   - `subscriptionUpdateNotificationsEnabled`
   - `subscriptionAutoUpdateOnOpen`
   - `subscriptionPingOnOpenEnabled`
   - `subscriptionConnectStrategy`
   - `preventDuplicateImports`
   - `collapseSubscriptions`
   - `subscriptionNoFilter`
   - `subscriptionUserAgentMode`
   - `subscriptionUserAgentValue`
   - `subscriptionSortMode`
   - расширенный `PingMode`
   - `PingResultMode`
   - `allowLanConnections`
   - `appAutoStart`
   - расширенный `LogLevel` (`auto`, `none`)
2. Определить precedence rules:
   - subscription headers vs local settings
   - JSON config vs builder overrides
   - `useDnsFromJson` vs custom DNS vs local DNS
3. Зафиксировать platform support matrix:
   - Android
   - iOS reduced subset
   - unsupported hidden vs unsupported visible
4. Добавить миграции и defaults без breaking current installs.
5. Зафиксировать unresolved product questions отдельным section внутри execution doc.

### Acceptance Criteria

- новый settings schema сериализуется и мигрирует без потери существующих Phase 0-7 данных
- каждая новая настройка имеет зафиксированный default
- существует письменная precedence table для DNS, ping, subscriptions и reset semantics
- UI еще может быть скрытым, но domain/persistence слой должен быть завершен

## Phase 9. Advanced VPN Runtime and Android-First Native Wiring

### Цель

Довести `Advanced VPN Settings` до реально работающего runtime слоя, а не до декоративных toggle.

### Работы

1. Включить user-controlled `sniffingEnabled` в runtime builder.
2. Добавить mobile-facing `vpnRunMode` и перестать всегда форсить `proxyOnly: false`.
3. Реализовать `server-address-resolve-*`:
   - DoH resolve before connect
   - optional fixed DNS IP
   - fastest-IP selection policy
4. Реализовать DNS precedence:
   - `useDnsFromJson`
   - `customDns`
   - `useLocalDns`
   - fallback to system/default DNS
5. Перевести excluded routes на typed parser:
   - IPv4 IP
   - IPv4 CIDR
   - IPv6 IP
   - IPv6 CIDR
6. Добавить `Background Settings` shortcut в `VPN Settings`.
7. Провести plugin/native audit для `local DNS` и `local DNS port`:
   - если `flutter_v2ray_plus` не покрывает это безопасно, зафиксировать отдельный bridge patch как обязательное условие для release.

### Acceptance Criteria

- Android runtime применяет `sniffingEnabled`, `vpnRunMode`, `server resolve` и typed excluded routes
- settings screen не показывает unsupported features как fully working там, где capability отсутствует
- runtime logs явно отражают, какие advanced settings были применены и какие были пропущены
- IPv6 excluded routes проходят validation и persistence

## Phase 10. Subscription Policy Engine and UX

### Цель

Превратить текущий subscriptions hub в policy-driven Happ-like control center.

### Работы

1. Добавить UI и persistence для:
   - auto update on/off
   - auto update interval
   - update notifications
   - update on open
   - ping on open
   - connect strategy
   - prevent duplicates
   - collapse subscriptions
   - no filter
   - User-Agent display / override
   - subscription sorting mode
2. Расширить `subscription_fetcher.dart`:
   - effective User-Agent
   - policy-aware request headers
3. Расширить `profile_update_notifier.dart`:
   - startup policy checks
   - refresh gating
   - ping-on-open orchestration
4. Развязать current hardcoded dedupe behavior от explicit product setting.
5. Добавить effective settings summary на subscriptions screen:
   - current interval
   - current connect strategy
   - current UA
   - current sort mode
6. Отдельно определить semantics `No filter`, потому что этот пункт пока не подтвержден публичным Happ dev-doc contract.

### Acceptance Criteria

- subscriptions screen управляет всеми policy toggles без ухода в debug/developer surface
- startup/resume logic следует пользовательским settings, а не скрытым hardcoded правилам
- User-Agent виден пользователю и может быть overridden или возвращен к default
- dedupe, collapse и sort behavior ведут себя предсказуемо и тестируемо

## Phase 11. Ping Parity, LAN Access, and App Autostart

### Цель

Закрыть operational parity вокруг ping behavior и системных Android features.

### Работы

1. Расширить `PingMode` до:
   - `proxyGet`
   - `proxyHead`
   - `tcp`
   - `icmp`
2. Унифицировать server-list ping и diagnostics speed test вокруг одного policy engine.
3. Перевести `ping result` на Happ-like semantics:
   - `time`
   - `icon`
4. Оставить `pingTestUrl` как общую test URL настройку.
5. Реализовать `Allow LAN Connections` Android-first:
   - toggle
   - display current local IP
   - display SOCKS5 port
   - display HTTP port
   - user education for same-LAN usage
6. Реализовать `App Auto Start` Android-first:
   - boot/startup registration
   - OEM caveats
   - current state visibility
7. Если ICMP или LAN невозможно реализовать безопасно в текущем plugin stack, оформить это как runtime patch gate, а не как UI-only feature.

### Acceptance Criteria

- пользователь может выбрать конкретный ping mode и увидеть, что он реально используется
- `ping result` в server list соответствует выбранной `time/icon` semantics
- Android показывает operational LAN state только если capability реально доступна
- app autostart переживает cold start / reboot smoke test на Android

## Phase 12. Statistics and Logs Center

### Цель

Довести раздел `Other Settings` до уровня реального operational toolkit.

### Работы

1. Создать formal `Statistics` screen.
2. Расширить metrics model:
   - server session start time
   - VPN connection duration
   - proxy speed in/out
   - proxy traffic in/out
   - direct speed in/out
   - direct traffic in/out
3. Провести capability audit:
   - что реально доступно из current runtime
   - что требует native/plugin patch
4. Создать formal `Logs` center:
   - log level selector `auto/debug/info/warning/error/none`
   - view logs
   - file list
   - open file flow
5. Перевести logging с pure in-memory на hybrid model:
   - UI ring buffer
   - persistent files
   - retention policy
6. Добавить file-backed outputs:
   - `access_log.txt`
   - `subscription_log.txt`
   - Xray-related logs/config snapshots, если runtime это позволяет

### Acceptance Criteria

- logs screen показывает не только buffered entries, но и persistent files с датой и размером
- log level влияет на effective runtime/application logging
- statistics screen либо показывает supported counters, либо честно маркирует unsupported metrics
- нет ложной promise-UX там, где runtime пока не выдает direct/proxy split

## Phase 13. Reset Flows, QA Matrix, and Rollout

### Цель

Закрыть destructive flows и подготовить безопасный rollout нового advanced settings scope.

### Работы

1. Реализовать два reset flow:
   - `Reset Settings`
   - `Full App Reset`
2. Для `Full App Reset` определить scope:
   - settings
   - imported profiles
   - subscription metadata
   - logs
   - local caches
   - auth/session data
3. Вынести reset из debug-only surface в formal settings IA.
4. Подготовить manual QA matrix:
   - Android supported path
   - iOS reduced subset
   - upgrade migration path
   - rollback path
5. Подготовить observability checklist:
   - runtime logs
   - subscription actions
   - ping actions
   - reset audit logs

### Acceptance Criteria

- `Reset Settings` не трогает пользовательские данные вне настроек
- `Full App Reset` очищает только те области, которые явно описаны в product contract
- destructive actions защищены confirm dialog и не выполняются скрыто
- rollout plan отдельно фиксирует Android-first features и iOS subset

## Recommended Delivery Order

Рекомендуемый порядок поставки такой:

1. `Phase 8`
   - потому что сейчас слишком много нового scope завязано на отсутствующий settings contract
2. `Phase 9`
   - потому что без runtime wiring остальные VPN toggles останутся декоративными
3. `Phase 10`
   - потому что subscriptions уже имеют foundation и дадут быстрый visible product gain
4. `Phase 11`
   - потому что ping parity и Android OS integrations можно делать на уже готовом settings/runtime base
5. `Phase 12`
   - потому что statistics/logs требуют отдельного capability audit и не должны тормозить settings/runtime work
6. `Phase 13`
   - потому что reset flows и rollout safety логично делать в конце расширения scope

## Open Product Questions

Перед стартом Phase 8 желательно утвердить:

1. `Use local DNS`
   - это запуск локального DNS listener внутри приложения или просто использование локального DNS endpoint?
2. `Use DNS from JSON`
   - должно ли это отключать все app-level DNS overrides?
3. `VPN / proxy-only`
   - является ли режим обязательным и на Android, и на iOS, или Android-first?
4. `No filter`
   - что именно означает этот toggle в вашем benchmark: игнорировать server filters subscription provider-а, локальные search filters или routing filters?
5. `Connect to random`
   - это случайный сервер из выбранной подписки или случайный сервер из всего каталога?
6. `Statistics`
   - нужен ли строгий Happ-level direct/proxy split или допустим Android-only subset на первом релизе?
7. `Full app reset`
   - должен ли он делать logout и очищать secure storage?

## Final Recommendation

Практически правильный следующий шаг после этого addendum:

- открыть `Phase 8` как отдельный execution plan
- зафиксировать unresolved semantics из раздела `Open Product Questions`
- не начинать `LAN`, `ICMP`, `Full direct/proxy stats split`, `file-backed Xray logs` без capability spike

Если идти именно так, CyberVPN будет догонять Happ последовательно и без слоя "мертвых" настроек, которые есть в UI, но не гарантируют реального поведения в runtime.
