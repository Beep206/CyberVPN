# CyberVPN Mobile vs Happ: gap-analysis и пофазный план внедрения

## Цель

Подготовить реалистичный план развития `cybervpn_mobile`, чтобы подтянуть приложение к уровню Happ в части:

- VPN Settings
- Routing
- Per-app Proxy
- расширенных транспортных настроек
- подписок
- ping/диагностики

Документ основан на:

- текущем коде `cybervpn_mobile`
- внутреннем Android TV референсе из этого монорепозитория
- публичной документации Happ и карточке приложения в App Store, просмотренных 16 апреля 2026 года

## Что уже есть в `cybervpn_mobile`

### Подтверждено по коду

1. В приложении уже есть оформленный слой настроек:
   - `lib/features/settings/domain/entities/app_settings.dart`
   - `lib/features/settings/presentation/providers/settings_provider.dart`
   - `lib/features/settings/presentation/screens/settings_screen.dart`
   - `lib/features/settings/presentation/screens/vpn_settings_screen.dart`

2. Экран VPN Settings уже поддерживает:
   - preferred protocol
   - auto-connect on launch
   - auto-connect on untrusted Wi‑Fi
   - kill switch toggle
   - split tunneling toggle
   - DNS provider и custom DNS
   - MTU auto/manual

3. В приложении уже есть заметная подписочная база:
   - экран тарифов
   - заготовка purchase flow
   - payment history
   - парсинг subscription headers

4. Уже есть диагностический слой:
   - server ping service
   - diagnostics screen
   - speed test screen
   - debug screen

5. Текущий VPN runtime построен вокруг `flutter_v2ray_plus`:
   - `lib/features/vpn/data/datasources/vpn_engine_datasource.dart`
   - текущий connect flow использует `FlutterV2ray.parseFromURL(...)` и `startVless(...)`

6. Уже есть частичный scaffold под split tunnel:
   - `lib/features/vpn/data/datasources/split_tunnel_android.dart`
   - `lib/features/vpn/data/datasources/split_tunnel_ios.dart`

7. Внутри монорепо уже есть полезный Android TV референс под per-app bypass:
   - `apps/android-tv/app/src/main/java/com/cybervpn/tv/ui/screens/settings/PerAppScreen.kt`
   - `apps/android-tv/app/src/main/java/com/cybervpn/tv/ui/screens/settings/PerAppViewModel.kt`
   - `apps/android-tv/app/src/main/java/com/cybervpn/tv/data/RoutingRepository.kt`
   - `apps/android-tv/app/src/main/java/com/cybervpn/tv/core/system/AppManager.kt`

### Важная техническая реальность

Текущее mobile-приложение пока **не** имеет полноценного routing/profile engine уровня Happ.

Главное ограничение в архитектуре сейчас такое:

- конфиг строится вокруг proxy URL
- connect flow опирается на `startVless(...)`
- в runtime передается очень узкая поверхность настроек:
  - `blockedApps`
  - `bypassSubnets`
  - `proxyOnly`

Этого недостаточно для полноценного паритета с Happ по следующим направлениям:

- rule profiles с `Proxy` / `Direct` / `Block`
- переиспользуемые routing profiles с geo-правилами
- расширенные настройки fragmentation
- mux tuning
- preferred IP type
- предсказуемое cross-platform поведение advanced tunnel settings

## Happ: что удалось подтвердить публично

### Подтвержденные возможности Happ

1. Happ поддерживает routing profiles с `Direct`, `Proxy` и `Block`.
   - В публичном JSON-примере есть `DirectSites`, `DirectIp`, `ProxySites`, `ProxyIp`, `BlockSites`, `BlockIp`.

2. Happ умеет добавлять routing через:
   - deep link
   - QR
   - clipboard
   - HTTP headers
   - subscription body

3. Happ поддерживает app/settings management через параметры подписки.

4. В Happ публично задокументированы глобальные настройки:
   - fragmentation
   - ping behavior
   - mux
   - auto-ping
   - auto-connect

5. Happ отдельно документирует `App-specific Proxy (Android)`.

6. Happ документирует `Exclude routes`.

7. В публичном описании Happ заявляет:
   - rule-based proxy configuration
   - hidden subscriptions
   - encrypted subscriptions
   - multiple protocol types

### Важная оговорка по `Preferred IP type`

В публичной developer documentation Happ, просмотренной 16 апреля 2026 года, я подтвердил routing, per-app proxy, fragmentation, ping, mux и excluded routes, но **не нашел** отдельного публичного developer-doc раздела, где явно описан `Preferred IP type`.

Поэтому для дальнейшего планирования этот пункт нужно считать:

- валидным продуктовым требованием из вашего брифа
- но технически еще не до конца верифицированной целью относительно:
  - нашего target core
  - Android behavior
  - iOS behavior
  - точного UX-паритета с Happ

## Gap Matrix

| Возможность | Happ | `cybervpn_mobile` сейчас | Размер разрыва | Комментарий |
|---|---|---:|---:|---|
| Routing profiles с Proxy / Direct / Block | Да | Нет | High | Ключевой продуктовый gap |
| Импорт/обновление routing profiles | Да | Нет | High | Нет data model и UX |
| Per-app proxy mode: Off / On / Bypass | Да на Android | Частично | High | Есть только split-tunneling toggle и незавершенный scaffold |
| UI выбора приложений | Да | Нет | High | Можно адаптировать код из Android TV |
| Fragmentation toggle/settings | Да | Нет | High | Нет domain/settings/core wiring |
| Mux toggle/settings | Да | Нет | High | Нет domain/settings/core wiring |
| Preferred IP type | Нужен по benchmark brief | Нет | High | Требует capability decision |
| Excluded routes | Да | Нет | Medium/High | Нет user-facing модели и экрана |
| Настройки ping method | Да | Частично | Medium | Сейчас есть TCP latency service, но нет selectable ping modes |
| Subscription UX parity | Сильнее в Happ | Частично | Medium | База уже есть, но нет единой Happ-подобной control area |
| Информационная архитектура VPN Settings | Да | Частично | Medium | Текущий экран пока плоский и менее операционный |
| Runtime completeness kill switch | Да | Частично | Medium | Flutter facade есть, а native handler'ы в mobile native code не найдены |

## Архитектурный вывод

### Коротко

Если мы хотим реальный parity level с Happ, это нельзя решать как задачу вида “добавим несколько toggle в Flutter”.

Нужны два слоя:

1. **Product/settings layer**
   - новые domain models
   - persistence
   - экраны
   - state management
   - migrations

2. **Transport/core layer**
   - richer runtime config generation
   - Android platform integration для per-app behavior
   - route/rule application
   - advanced outbound tuning
   - capability-aware platform fallbacks

### Рекомендуемое направление

Для Happ-like parity безопаснее идти так:

- оставить `flutter_v2ray_plus` только если spike докажет, что он реально покрывает нужную config surface
- иначе вынести advanced VPN features за отдельный native bridge, который принимает полноценный generated config

Почему:

- текущий flow оптимизирован под простые proxy URL
- Happ-style routing и transport settings конфигурируются через config-driven model, а не через набор UI toggle
- попытка “натянуть” нынешний happy-path API почти гарантированно приведет к хрупкой реализации и повторной переделке

## Общий принцип поставки

Не надо сразу реализовывать весь UI уровня Happ.

Правильный порядок такой:

1. capability foundation
2. Android routing/per-app foundation
3. advanced settings UI, который уже реально что-то делает
4. iOS-compatible subset
5. parity polish и provider-managed extensions

Это позволяет не плодить “мертвые” настройки.

## Пофазный план

## Фаза 0. Capability Audit и архитектурное решение

### Цель

Понять, остается ли `flutter_v2ray_plus` базой runtime, либо его нужно уводить за более богатый native transport bridge.

### Работы

1. Собрать capability matrix для:
   - текущего `flutter_v2ray_plus`
   - Android platform APIs
   - iOS platform APIs
   - target core behavior для routing, mux, fragmentation, IP family preference

2. Через технический spike проверить, поддерживает ли текущий runtime:
   - полноценные routing rules
   - per-app include/exclude
   - outbound mux config
   - fragmentation/noise config
   - preferred IP family
   - excluded routes

3. Принять одно из двух решений:
   - `Path A`: расширяем текущий runtime и добавляем минимальные native pieces
   - `Path B`: вводим новый native core bridge под advanced settings

### Deliverables

- architecture decision record
- supported/unsupported matrix по платформам
- вердикт `must migrate / can stay` для VPN engine layer

### Exit criteria

- в следующих фазах не остается ни одной критичной фичи, зависящей от непроверенного предположения

## Фаза 1. Domain model и persistence foundation

### Цель

Добавить полноценную продуктовую модель Happ-like VPN settings до финального UI.

### Новые сущности

1. `RoutingMode`
   - `disabled`
   - `customProfile`
   - опционально `providerManaged`

2. `RoutingProfile`
   - id
   - name
   - direct domains / IPs
   - proxy domains / IPs
   - block domains / IPs
   - DNS strategy
   - geo file refs / version metadata
   - lastUpdated

3. `PerAppProxyMode`
   - `off`
   - `onlySelectedUseProxy`
   - `selectedBypassProxy`

4. `PerAppSelection`
   - package name / bundle id
   - display name
   - icon ref
   - installed state

5. `FragmentationSettings`
   - enabled
   - позже можно расширить параметрами length / interval / packets

6. `MuxSettings`
   - enabled
   - позже можно добавить concurrency tuning

7. `PreferredIpType`
   - `auto`
   - `ipv4`
   - `ipv6`

8. `PingSettings`
   - mode: `proxy`, `tcp`, `icmp`
   - optional proxy ping URL
   - display mode / appearance

9. `ExcludedRoutesSettings`
   - список CIDR/IP, которые исключаются из туннеля

### Основные файлы на изменение

- `lib/features/settings/domain/entities/app_settings.dart`
- `lib/features/settings/presentation/providers/settings_provider.dart`
- `lib/features/settings/data/repositories/settings_repository_impl.dart`

### Принцип persistence

Нужны явные schema-versioned migrations. Нельзя бесшумно переопределить текущий `splitTunneling` boolean новой семантикой.

### Exit criteria

- все новые настройки можно сохранить, прочитать, сбросить и безопасно мигрировать

## Фаза 2. Android routing и per-app foundation

### Цель

Сначала довести до рабочего состояния Android, потому что Happ сам документирует app-specific proxy именно как Android-функцию.

### Работы

1. Переиспользовать идеи из Android TV:
   - installed app discovery
   - package persistence
   - bypass/include repository

2. Реализовать mobile Android equivalents для:
   - installed-app enumeration
   - package label/icon resolution
   - selected app persistence
   - active VPN runtime mapping

3. Заменить текущий незавершенный split-tunnel scaffold на production flow:
   - `split_tunnel_android.dart` перестает быть thin stub
   - в Android появляются реальные native handlers
   - app selection начинает влиять на реальный VPN runtime

4. Добавить Android routing/excluded-routes support:
   - exclude route list
   - route application при старте туннеля
   - корректная очистка/переприменение при изменении настроек

### UX scope

Добавить Android-first экраны:

- `Per-App Proxy`
- `Excluded Routes`
- `Routing`

### Exit criteria

- Android build умеет:
  - показывать список установленных user apps
  - сохранять выбранные apps
  - реконнектиться с нужным mode
  - доказывать include/exclude behavior в traffic tests

## Фаза 3. Config generation и advanced tunnel settings

### Цель

Связать Flutter settings с реальным config/runtime layer, а не с декоративным UI.

### Работы

1. Ввести config builder abstraction:
   - input: app settings + server/profile + platform capability
   - output: runtime-ready VPN config payload

2. Добавить mapping для:
   - routing profile rules
   - excluded routes
   - mux
   - fragmentation
   - preferred IP type
   - sniffing policy, если позже захотим вынести и это

3. Сделать runtime capability-aware:
   - unsupported options явно отклоняются или downgrade’ятся
   - никаких silent no-op настроек

4. Добавить runtime validation/logging:
   - какие settings реально применились
   - какие были пропущены
   - почему были пропущены

### Почему эта фаза обязательна

Без config-generation layer UI быстро превратится в набор связных, но плохо контролируемых toggle с неочевидным runtime outcome.

### Exit criteria

- для каждого поддерживаемого platform/runtime scenario есть понятный generated config path
- advanced settings трассируются от storage до runtime

## Фаза 4. iOS-compatible стратегия

### Цель

Четко определить iOS subset, а не пытаться насильно уравнять Android и iOS по семантике.

### Базовое продуктовое правило

`App-specific Proxy` нужно считать **Android-first** фичей. Публичная документация Happ сама маркирует ее как Android-only.

### Работы

1. Для каждой advanced feature принять решение по iOS:
   - routing
   - excluded routes
   - fragmentation
   - mux
   - preferred IP type
   - ping modes

2. Пометить каждую как:
   - fully supported on iOS
   - supported with reduced semantics
   - unsupported and hidden

3. Спроектировать iOS-safe UX:
   - без мертвых toggle
   - с понятным help text о platform differences

### Наиболее вероятный результат

На iOS в первой parity-итерации, скорее всего, получится так:

- routing: да, если выбранный core/runtime path это поддержит
- excluded routes: вероятно да
- fragmentation: возможно да
- mux: вероятно да
- preferred IP type: требует отдельной проверки
- per-app proxy: вероятнее всего hidden на iOS в первом релизе

### Exit criteria

- platform support matrix зафиксирована и в продукте, и в коде

## Фаза 5. Новая информационная архитектура VPN Settings

### Цель

Перестроить VPN settings area в масштабируемую структуру, близкую по операционному удобству к Happ.

### Рекомендуемая структура

1. `VPN Settings`
   - auto-connect
   - kill switch
   - DNS
   - MTU

2. `Routing`
   - routing enable/disable
   - active routing profile
   - import/edit/delete routing profiles
   - excluded routes

3. `Per-App Proxy`
   - mode: Off / Use proxy only for selected / Bypass selected
   - app picker

4. `Advanced`
   - fragmentation
   - mux
   - preferred IP type
   - позже можно добавить sniffing, DNS-from-JSON, idle timeout и т.д.

5. `Subscriptions`
   - import by URL / QR / clipboard
   - update interval
   - encrypted/hidden profile state
   - support URL / profile page URL

6. `Ping`
   - ping mode
   - ping target URL для proxy ping
   - display mode

### Основные участки кода

- `lib/features/settings/presentation/screens/settings_screen.dart`
- `lib/features/settings/presentation/screens/vpn_settings_screen.dart`
- новые экраны в `lib/features/settings/presentation/screens/`

### Exit criteria

- настройки становятся модульными
- Happ-comparable features доступны без перегруза главного settings screen

## Фаза 6. Подписки и ping parity layer

### Цель

Превратить уже существующие subscription/ping наработки в единый операционный experience.

### Подписки

Сейчас база уже хорошая:

- планы
- payment history
- subscription status parsing
- support URL parsing
- profile title parsing
- update interval parsing

Что еще нужно для Happ-like parity:

1. объединить manual config import и subscription import UX
2. поднять provider metadata на более заметный уровень
3. добавить subscription-level controls в settings
4. при необходимости поддержать provider-managed options по модели Happ

### Ping

Сейчас приложение больше похоже на:

- TCP latency checker
- diagnostics utility

Чтобы приблизиться к Happ, нужно:

1. добавить explicit ping mode selection
2. добавить proxy-ping URL support
3. добавить ping display preferences
4. связать ping preferences с server list и diagnostics flows

### Exit criteria

- subscriptions и ping становятся first-class sections, а не разрозненными feature islands

## Фаза 7. QA, верификация и rollout

### Цель

Довести новые возможности до production без regressions по connectivity.

### Уровни тестирования

1. Unit tests
   - settings migrations
   - routing profile parsing
   - config generation
   - platform support matrix decisions

2. Widget tests
   - settings screens
   - app picker
   - routing profile editor

3. Integration tests
   - Android per-app mode
   - reconnect after settings changes
   - routing profile activation
   - subscription import with managed settings

4. Manual QA matrix
   - Android 13/14/15
   - iOS 17/18
   - IPv4-only / IPv6-only / dual-stack
   - Wi‑Fi / LTE / hotspot

### Observability

Нужно логировать:

- active routing profile id
- per-app mode
- app count в include/exclude set
- ping mode
- mux enabled state
- fragmentation enabled state
- preferred IP type
- unsupported-feature fallbacks

### Rollout strategy

Рекомендуется развертывание через feature flags:

1. `routing_profiles`
2. `per_app_proxy_android`
3. `advanced_transport_settings`
4. `ping_modes`

Это позволит выкатывать изменения поэтапно, а не big bang релизом.

## Рекомендуемый порядок релизов

### Release A

- Фаза 0
- Фаза 1
- Фаза 2 Android foundation

Результат:

- реальная Android per-app foundation
- полноценная routing data model
- без декоративных toggle

### Release B

- Фаза 3
- первая часть Фазы 5

Результат:

- routing UI
- excluded routes
- mux/fragmentation wiring

### Release C

- Фаза 4
- Фаза 6

Результат:

- iOS-safe advanced subset
- subscription/ping parity layer

### Release D

- Фаза 7 hardening

Результат:

- production rollout
- regression confidence

## Ключевые риски

1. **Runtime limitation risk**
   - Если `flutter_v2ray_plus` не поддерживает нужную config surface, любой UI, сделанный раньше Фазы 0, станет rework.

2. **Platform asymmetry risk**
   - Android и iOS не дадут одинаковый capability set; это нужно принять на ранней стадии.

3. **Fake-toggle risk**
   - В проекте уже есть настройки и platform facades, которые выглядят подготовленными, но не выглядят полностью доведенными до native runtime wiring. Этот паттерн нельзя масштабировать.

4. **Reconnect-state risk**
   - Advanced settings, влияющие на route/app/core behavior, должны либо форсировать reconnect, либо поддерживать прозрачную live reconfiguration с явным UX.

5. **Migration risk**
   - Нельзя бесшумно поменять смысл текущего `splitTunneling` boolean без схемы миграции и явной UX-логики.

## Самый правильный следующий шаг

Следующим шагом должен быть **не UI**.

Следующим шагом должен быть:

1. Phase 0 capability audit
2. runtime strategy decision
3. затем Phase 1
4. затем Android-first Phase 2

Если этот порядок пропустить, мы почти наверняка построим настройки быстрее, чем сможем сделать их рабочими.

## Источники

Внешние:

- Happ developer docs: App management
  - https://www.happ.su/main/dev-docs/app-management
- Happ developer docs: Routing
  - https://www.happ.su/main/dev-docs/routing
- Happ App Store page
  - https://apps.apple.com/tm/app/happ-proxy-utility/id6504287215
- Happ GitHub organization
  - https://github.com/Happ-proxy

Внутренние:

- `cybervpn_mobile/lib/features/settings/...`
- `cybervpn_mobile/lib/features/vpn/...`
- `cybervpn_mobile/lib/features/subscription/...`
- `cybervpn_mobile/lib/features/diagnostics/...`
- `apps/android-tv/app/src/main/java/com/cybervpn/tv/...`
