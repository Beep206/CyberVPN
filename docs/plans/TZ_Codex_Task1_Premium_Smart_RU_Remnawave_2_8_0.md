# Техническое задание для Codex App GPT-5.6 Sol
## Задача 1 — довести CyberVPN Premium Smart RU до единого и доказуемого поведения на Remnawave 2.8.0

**Статус:** implementation-ready
**Целевой репозиторий:** `https://github.com/Beep206/CyberVPN`
**Основная ветка:** определить из репозитория; не предполагать имя ветки
**Панель:** Remnawave `2.8.0`
**Продукт:** `CyberVPN Premium Smart RU`
**Целевой plan code:** `premium_smart_ru`
**Приоритет:** P0 / production correctness

---

# 0. Режим работы Codex

Codex должен выполнить задачу как инженерный remediation-проект, а не как косметическое редактирование шаблона.

Обязательный порядок:

1. Открыть репозиторий и зафиксировать исходный `HEAD`, активную ветку и состояние worktree.
2. Прочитать перечисленные ниже документы и реальные исходники, прежде чем менять код.
3. Сопоставить Git-состояние с production snapshot. Не считать production DB автоматически эквивалентной Git.
4. Создать focused implementation plan с файлами, миграциями, тестами и rollback.
5. Реализовать изменения небольшими логически завершёнными шагами.
6. Запустить статические, unit, contract, integration и runtime-проверки.
7. Не выполнять разрушительные production-действия без явного разрешения владельца.
8. Не печатать и не сохранять в Git subscription URL, VLESS UUID, Reality keys, short IDs, bridge passwords, API tokens, SSH keys, пользовательские email и другие PII.
9. Не объявлять задачу завершённой, пока не собрана доказательная матрица маршрутов для каждого поддерживаемого формата подписки.
10. В финальном отчёте явно разделить: `implemented`, `tested locally`, `tested on staging`, `tested on production`, `not verified`.

При обнаружении расхождения между этим ТЗ и текущим репозиторием Codex обязан:

- показать расхождение;
- выбрать решение, сохраняющее продуктовый контракт;
- покрыть решение тестом;
- отразить решение в release evidence.

---

# 1. Обязательные источники контекста

Сначала изучить:

```text
docs/plans/CyberVPN_Premium_Smart_RU_Workflow_Architecture.md
docs/architecture/CYBERVPN_PREMIUM_SMART_RU_CURRENT_PRODUCTION_ARCHITECTURE.md
scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
scripts/remnawave/generate-premium-smart-ru-incy-xray.py
scripts/remnawave/templates/cybervpn-premium-smart-ru-incy-xray.json
scripts/remnawave/seed-cybervpn-premium-smart-ru-incy-xray.sql
scripts/remnawave/apply-premium-smart-ru-server-routing.py
backend/tests/contract/remnawave/
backend/tests/integration/remnawave/
backend/src/application/vpn_testing/
docs/evidence/releases/
infra/ansible/inventories/production/hosts.yml
infra/systemd/README.md
```

Если путь отличается, найти соответствующий файл по содержимому, не создавать дубликат только из-за переименования.

Также сверить официальные материалы:

- `https://docs.rw/learn/xray-json-advanced/`
- `https://docs.rw/learn-en/routing-rules/`
- `https://github.com/remnawave/backend`
- `https://github.com/remnawave/node`
- `https://xtls.github.io/en/config/routing.html`
- документацию INCY full Xray config и routing, указанную в production architecture.

Особенно проверить поведение именно Remnawave `2.8.0`:

- порядок Response Rules и принцип first match;
- `subscriptionTemplate` override;
- `excludeHostsByTags`;
- массив `tags[]` у host;
- advanced `XRAY_JSON` с `remnawave.injectHosts`;
- virtual host и hidden injection hosts;
- исключение recipient-host из кандидатов инжектора;
- кеширование Subscription Settings/Response Rules;
- совместимую версию Xray Core для Node `2.8.0`.

Не использовать старую версию Xray Core для финального доказательства только потому, что она есть локально. Версию нужно определить из реально закреплённых production image/tag/digest и официальной compatibility matrix.

---

# 2. Бизнес-цель

Пользователь импортирует одну подписку `CyberVPN Premium Smart RU`, включает VPN один раз и получает следующее поведение:

```text
Обычный мировой трафик              -> Германия
Германия недоступна                 -> Нидерланды
Российские сервисы                  -> Москва или Санкт-Петербург
Ресурсы blocked/unstable из РФ      -> Германия/Нидерланды
Реклама и известные трекеры         -> BLOCK/REJECT
Torrent                             -> BLOCK/REJECT + server abuse layer
TOR                                 -> best-effort BLOCK
Локальные/частные сети              -> DIRECT на client-side full config
```

Пользователь не должен вручную переключать DE/RU при одновременном открытии, например, YouTube, Ozon, Госуслуг, GitHub и ChatGPT.

---

# 3. Нормативный маршрутный контракт

## 3.1. Глобальный трафик

Через DE должны идти как минимум:

```text
Google
YouTube
Discord
GitHub
OpenAI/ChatGPT
Telegram и международные мессенджеры
стриминговые и международные сервисы
обычный unmatched TCP/UDP traffic
```

Проверка внешнего IP по умолчанию должна показывать DE egress.

## 3.2. Российский трафик

Через RU-контур должны идти как минимум:

```text
Ozon
Wildberries
Яндекс и Яндекс Маркет
Госуслуги
ФНС/налоговые сервисы
Сбер
T-Bank
ВТБ
Альфа-Банк
VK
Rutube
другие явно заданные RU services
geoip:ru / geosite RU только после EU exceptions
```

## 3.3. EU exceptions до широких RU rules

Ресурсы, которые нельзя отправлять через РФ, обязаны проверяться до `category-ru`, `.ru`-подобных правил и `geoip:ru`.

Примеры:

```text
Habr
4PDA
Meduza
The Insider
Mediazona
Proton
Archive.org
ru-bundle / ru-inside / refilter / rkn-related exceptions
```

## 3.4. Блокировки

Порядок блокировок должен быть выше route-to-region правил:

```text
private/direct exceptions where applicable
bittorrent protocol
known torrent processes
known torrent domains/trackers
ads/trackers
TOR domains/processes
QUIC/DoQ policy, если она утверждена продуктом
EU exceptions
RU services
final default -> EU
```

Нельзя обещать абсолютную блокировку YouTube in-stream ads, всех TOR bridges или всех encrypted/WebTorrent сценариев. В документации и UI использовать корректную формулировку `best effort` там, где она технически необходима.

---

# 4. Почему текущая реализация может вести себя неправильно

Codex должен подтвердить или опровергнуть каждый пункт реальным кодом и тестом.

## 4.1. Один продукт фактически выдаётся в трёх разных моделях

Сейчас существуют:

1. `INCY full Xray JSON` — client-side split routing.
2. `Mihomo YAML` — client-side split routing с TUN/Fake-IP/DNS policy.
3. `XRAY_BASE64` — отдельные VLESS links, без общего клиентского routing engine.

Успешный тест одного формата не доказывает корректность двух остальных.

## 4.2. Response Rule для INCY может быть слишком широким

UA-only правило вида `contains incy` применяется глобально. Remnawave Response Rules сопоставляют HTTP-заголовки, а не тариф как внутреннюю сущность. Пользователь другого тарифа с тем же UA потенциально может получить template, для которого у него нет нужных injected hosts.

## 4.3. Drift между источниками правил

Могут расходиться:

```text
Mihomo template
INCY full Xray JSON
legacy routing header
DE server-side profile
Moscow server-side profile
XRAY_BASE64 compatibility path
Node Plugin lists
```

Известный пример — разные наборы torrent domains.

## 4.4. Неправильная health-модель RU

Если RU outbound проверяется non-RU URL, а server profile для non-RU traffic отправляет probe через DE bridge, измеряется цепочка `client -> RU -> DE -> probe`, а не здоровье RU path. Это создаёт false unhealthy и ошибочный fallback.

## 4.5. Base64 links не эквивалентны full config

Отдельные NL/SPB links могут подключаться, но не давать Smart RU поведение. Нельзя рекламировать такой path как полностью эквивалентный `Premium Smart RU` без отдельного server-side контракта.

## 4.6. Cache/restart effect

При прямом изменении DB Remnawave может продолжать отдавать старый response до restart/reload соответствующего процесса. Проверка только DB является недостаточной.

## 4.7. Device runtime отличается от чистого Xray

INCY/HAPP могут патчить inbounds, TUN, DNS и хранить subscription в memory/SecureStorage cache. Успех generated JSON в standalone Xray не заменяет device-side acceptance.

---

# 5. Обязательное архитектурное решение

## 5.1. Authoritative path

Для `Premium Smart RU` authoritative модель:

```text
Mihomo clients -> MIHOMO full config
INCY clients   -> XRAY_JSON full config
HAPP clients   -> XRAY_JSON full config, если подтверждена поддержка
```

Решение о маршруте принимается на клиентском устройстве. Клиент открывает отдельные соединения непосредственно к DE/NL и Moscow/SPB. Нельзя превращать весь трафик в постоянную цепочку `user -> RU -> DE -> Internet`.

## 5.2. Compatibility path

`XRAY_BASE64` разрешён только как явно обозначенный compatibility mode.

Codex должен выбрать и реализовать один из вариантов:

- довести server-side поведение всех выдаваемых Base64 links до задокументированного контракта; либо
- переименовать/маркировать compatibility path так, чтобы он не обещал полный Smart RU; либо
- ограничить список поддерживаемых клиентов для данного тарифа и возвращать понятную ошибку/инструкцию неподдерживаемому клиенту.

Нельзя оставлять скрытое неэквивалентное поведение под тем же продуктовым обещанием.

## 5.3. Product-scoped delivery

Не полагаться только на пользовательский `User-Agent`.

Целевая схема:

```text
public subscription request
        -> trusted CyberVPN subscription gateway / plan-specific host
        -> gateway определяет продукт по authoritative backend data
        -> gateway удаляет client-supplied x-cybervpn-* headers
        -> gateway добавляет доверенный internal header
        -> Remnawave Response Rule выбирает формат по trusted product header + UA
```

Пример внутреннего контракта:

```text
x-cybervpn-product: premium_smart_ru
x-cybervpn-client-family: incy | happ | mihomo | browser | generic
```

Заголовок должен перезаписываться reverse proxy/backend, а не доверяться клиенту.

Если проект не имеет gateway, допустим отдельный plan-specific subscription hostname/path, но он всё равно обязан проверять принадлежность пользователя тарифу до проксирования в Remnawave.

---

# 6. Единый source of truth для routing policy

Создать typed policy source, из которого генерируются все производные конфиги.

Рекомендуемая структура:

```text
scripts/remnawave/policies/premium_smart_ru.yaml
scripts/remnawave/policy_compiler/
  __init__.py
  models.py
  loader.py
  validate.py
  render_mihomo.py
  render_xray_client.py
  render_xray_server.py
  render_legacy_header.py
  cli.py
```

Минимальная модель policy:

```yaml
version: 1
product: premium_smart_ru
routes:
  private: direct
  default: eu
  ru_services: ru
  eu_exceptions: eu
blocks:
  ads: true
  trackers: true
  torrent: true
  tor: best_effort
  smtp_abuse_ports: [25, 465, 587]
regions:
  eu:
    primary: de
    fallback: nl
  ru:
    primary: moscow
    fallback: spb
sources:
  eu_exceptions: []
  ru_services: []
  ads: []
  torrent: []
  tor: []
```

Точный формат можно адаптировать к архитектуре проекта, но обязательны:

- Pydantic/dataclass validation;
- schema/version field;
- deterministic output;
- pinned upstream revisions/checksums;
- отсутствие секретов;
- reproducible generation;
- semantic validation порядка правил;
- manifest с counts/checksums/source revisions.

Запрещено поддерживать одинаковые списки вручную в четырёх независимых файлах.

---

# 7. Требуемые изменения в Remnawave objects

## 7.1. XRAY_JSON template

Сохранить модель одного visible virtual host и hidden injection hosts.

Обязательные свойства:

- visible virtual host не hidden;
- injection hosts hidden;
- injection hosts входят в доступные пользователю inbounds/squad;
- `tags[]` используются по модели Remnawave 2.8.0;
- `injectHosts` выбирает хосты по стабильным tags, а не по локализованному remark;
- recipient host не должен инжектироваться сам в себя;
- hidden hosts исключены из неподходящих subscription types;
- итоговый response содержит ровно один full Xray config для INCY/HAPP;
- `remnawave`-служебный объект отсутствует в generated output.

Рекомендуемые стабильные tags:

```text
premium-smart-ru
premium-smart-ru-eu-de
premium-smart-ru-eu-nl
premium-smart-ru-ru-msk
premium-smart-ru-ru-spb
transport-raw
transport-xhttp
client-inject-only
```

## 7.2. Response Rules

Правила должны быть ordered и тестируемыми.

Целевая логика:

```text
Browser HTML
Mihomo/Clash Meta + product=premium_smart_ru -> MIHOMO template
HAPP + product=premium_smart_ru             -> XRAY_JSON template
INCY + product=premium_smart_ru             -> XRAY_JSON template
Explicit supported fallback                  -> documented response
Generic unsupported client                   -> compatibility response or clear block
```

Добавить contract tests на:

- first-match semantics;
- регистр UA;
- реальные UA strings из request history;
- отсутствие trusted product header;
- spoofed client header;
- другой тариф с INCY UA;
- placement before unconditional fallback;
- `subscriptionTemplate` override;
- `excludeHostsByTags` при необходимости.

После изменения выполнить предусмотренный проектом cache reload/restart и проверить HTTP body, а не только DB row.

## 7.3. Squads

Проверить и закрепить:

```text
CYBERVPN_PREMIUM_SMART_RU_NODES
CYBERVPN_PREMIUM_SMART_RU
CYBERVPN_SMART_RU_BRIDGE
CYBERVPN_SMART_GLOBAL_BRIDGE
```

Требования:

- customer users состоят только в customer squads;
- bridge service users состоят только в bridge squads;
- bridge inbounds не имеют public hosts;
- customer subscription не содержит bridge credentials;
- injected host set соответствует customer internal squad;
- другой тариф не получает Premium Smart RU full template.

---

# 8. Xray client routing contract

## 8.1. Outbounds

Generated full config должен содержать:

```text
eu-de RAW
eu-de XHTTP
eu-nl RAW
eu-nl XHTTP
ru-msk RAW
ru-msk XHTTP
ru-spb RAW
ru-spb XHTTP
direct
block
```

Точные endpoints, Reality parameters и user IDs инжектируются Remnawave и не хранятся в шаблоне как секреты.

## 8.2. Rule order

Обязательный порядок:

```text
1. private/local networks -> direct
2. approved service processes that must bypass -> direct
3. bittorrent protocol -> block
4. torrent processes -> block
5. torrent domains/trackers -> block
6. ads/trackers -> block
7. TOR domains/processes -> block
8. approved QUIC/DoQ policy
9. EU exceptions -> eu route
10. explicit RU services -> ru route
11. broad RU geosite/geoip -> ru route
12. final network tcp,udp -> eu route
```

Финальное правило обязано иметь эффективный matcher, например:

```json
{
  "type": "field",
  "network": "tcp,udp",
  "balancerTag": "eu-auto"
}
```

Пустое field rule без matcher запрещено.

## 8.3. DNS

Для Mihomo сохранить:

- TUN;
- DNS hijack;
- Fake-IP;
- split DNS RU/EU;
- rule-provider DNS через EU;
- ad/tracker NXDOMAIN policy.

Для Xray full config:

- не заявлять FakeDNS/split DNS, если клиент не поддерживает их доказанно;
- проверить runtime patching INCY/HAPP;
- исключить DNS routing loops;
- обеспечить bootstrap DNS;
- покрыть DNS leakage и route correctness тестами;
- документировать различия между Mihomo и Xray, если полная эквивалентность невозможна.

---

# 9. Health, balancing и failover

## 9.1. EU

Целевой контракт:

```text
DE primary
NL fallback
```

Проверять RAW и XHTTP отдельно. NL XHTTP не должен существовать только декоративно: либо участвует в fallback, либо явно маркируется как manual/diagnostic transport.

## 9.2. RU

На первом production-safe этапе использовать deterministic regional priority:

```text
Moscow primary
SPB fallback
```

или обратный порядок, если владелец утвердит его документом. Нельзя выбирать порядок случайно по одному non-RU probe.

Если применяется observatory/leastPing:

- probe должен отражать здоровье требуемого regional path;
- RU probe не должен уходить через DE bridge;
- transport health и regional egress health должны различаться;
- probe URL должен быть доступен и стабилен из RU;
- false-unhealthy regression test обязателен.

## 9.3. Degraded semantics

Определить и реализовать явно:

```text
DE unavailable -> NL
Moscow unavailable -> SPB
SPB unavailable -> Moscow
both RU unavailable -> explicit degraded state
```

RU traffic не должен незаметно переходить в DE без события/метрики. Если продукт допускает EU fallback, это должно быть явно отражено в UI, метрике и evidence.

---

# 10. Server-side compatibility layer

Server-side profiles нужны для Base64/legacy clients и как defense-in-depth, но не должны становиться authoritative source для full clients.

Обязательные требования:

- DE profile: RU destinations -> RU bridge, EU exceptions/default -> DE direct;
- Moscow/SPB compatibility profiles: логика соответствует документированному продукту;
- lists генерируются тем же policy compiler;
- private destinations имеют явно утверждённую policy;
- torrent/ads/TOR lists синхронизированы;
- bridge credentials не попадают в customer subscription;
- bridge ingress firewall разрешает только peer node IPs;
- TCP и UDP bridge paths тестируются;
- stale server profile считается release blocker.

---

# 11. Реализация по этапам

## Этап A — аудит и воспроизводимость

1. Снять Git metadata и перечислить dirty files.
2. Сравнить source templates с production generated response.
3. Найти все копии RU/EU/torrent/ads/TOR lists.
4. Построить machine-readable drift report.
5. Добавить regression tests, которые сначала воспроизводят текущие расхождения.

## Этап B — policy compiler

1. Создать canonical policy model.
2. Перенести списки без потери entries.
3. Добавить deterministic rendering.
4. Добавить manifests/checksums.
5. Добавить `--check` mode, который падает при незакоммиченном generated drift.

Пример CLI:

```powershell
python .\scripts\remnawave\policy_compiler\cli.py generate `
  --policy .\scripts\remnawave\policies\premium_smart_ru.yaml

python .\scripts\remnawave\policy_compiler\cli.py check `
  --policy .\scripts\remnawave\policies\premium_smart_ru.yaml
```

## Этап C — product-scoped subscription delivery

1. Добавить trusted plan routing в subscription gateway/reverse proxy.
2. Sanitise/overwrite client-supplied internal headers.
3. Обновить Response Rules idempotently.
4. Добавить HAPP Android/iOS и INCY UA tests.
5. Проверить Browser/Mihomo/generic fallback.

## Этап D — Xray/Mihomo outputs

1. Сгенерировать оба client formats из policy.
2. Проверить 8 transports.
3. Проверить rule order.
4. Проверить final catch-all.
5. Проверить headers и `subscription-userinfo`.

## Этап E — server compatibility

1. Перегенерировать server profiles.
2. Синхронизировать torrent/ads/TOR.
3. Проверить bridges и firewall.
4. Не менять production до прохождения staging/canary.

## Этап F — health/failover

1. Устранить non-regional RU probe artifact.
2. Ввести deterministic primary/fallback или корректные региональные probes.
3. Добавить degraded metrics/events.

## Этап G — rollout

1. Backup DB/configs.
2. Staging rollout.
3. Canary user.
4. Device verification.
5. Production rollout.
6. Evidence + rollback validation.

---

# 12. Автоматические тесты

## 12.1. Unit tests policy compiler

Проверить:

- schema validation;
- invalid route target;
- duplicate entries;
- normalized domains/CIDRs;
- deterministic ordering;
- pinned source checksums;
- generated manifest;
- same torrent set in all renderers;
- EU exceptions strictly before broad RU;
- final catch-all exists;
- no secrets in outputs.

## 12.2. Remnawave contract tests

Проверить:

- template exists and type is correct;
- internal/external squads exist;
- hosts use `tags[]`;
- injection host visibility/exclusions;
- visible virtual host count = 1;
- generated outbounds = expected set;
- bridge users isolated;
- Response Rule order;
- trusted product header requirement;
- unconditional fallback is last;
- restart/cache reload procedure documented and testable.

## 12.3. Generated subscription tests

Матрица:

| Client/UA | Ожидаемый тип | Ожидаемое содержимое |
|---|---|---|
| Browser Accept HTML | BROWSER | subscription page |
| Mihomo/Clash Meta | MIHOMO | one YAML, Smart groups |
| INCY Android actual UA | XRAY_JSON | one full config |
| INCY legacy actual UA | XRAY_JSON | one full config |
| HAPP Android actual UA | XRAY_JSON или documented unsupported | доказанный contract |
| HAPP iOS actual UA | XRAY_JSON или documented unsupported | доказанный contract |
| v2rayNG/v2rayN | compatibility response | не выдавать ложное full-equivalence |
| another plan + INCY UA | не Premium template | isolation pass |

Не логировать body целиком. Тест должен извлекать только redacted structural summary.

## 12.4. Xray static validation

Для generated config:

```text
JSON parse
schema/semantic lint
Xray test/run with production-compatible core
2 inbounds or documented client runtime shape
10 outbounds
expected tags
expected balancers/selectors
no empty routing rules
no duplicate outbound tags
no unresolved injected references
```

## 12.5. Runtime route matrix

Проверять через локальный SOCKS/HTTP endpoint diagnostic Xray/Mihomo instance и по route logs.

| Категория | Probe | Ожидаемый маршрут |
|---|---|---|
| default world | safe IP-check + ordinary global site | DE |
| YouTube | safe 204/static endpoint | DE |
| OpenAI | safe public endpoint/domain resolution | DE |
| GitHub | public raw/static endpoint | DE |
| Ozon | HTTPS HEAD/GET without auth | RU |
| Госуслуги | safe public page | RU |
| Яндекс | safe public page | RU |
| EU exception | selected stable domain | DE |
| ad | synthetic/known ad domain | BLOCK |
| torrent | static torrent-domain fixture only | BLOCK |
| TOR | torproject/static domain fixture only | BLOCK |
| LAN | local test HTTP server | DIRECT |

Запрещено генерировать реальный BitTorrent traffic или подключаться к TOR network.

Доказательство маршрута должно включать:

```text
matched rule id/tag
selected outbound/balancer
egress country/IP, когда безопасно
HTTP result
latency
timestamp
config checksum
```

## 12.6. Transport matrix

Отдельно проверить:

```text
DE RAW
DE XHTTP
NL RAW
NL XHTTP
Moscow RAW
Moscow XHTTP
SPB RAW
SPB XHTTP
```

Рабочий XHTTP не маскирует сломанный RAW и наоборот.

## 12.7. Failover tests

На staging/isolated canary:

```text
DE RAW down, DE XHTTP up
DE both transports down -> NL
NL RAW down, NL XHTTP up
Moscow down -> SPB
SPB down -> Moscow
both RU down -> explicit degraded behavior
probe endpoint unavailable -> no false regional reroute
Remnawave restarted/reloaded -> response remains correct
```

## 12.8. Device tests

Минимум:

- Android INCY;
- HAPP platform, если заявлена поддержка;
- один Mihomo/Clash Meta client;
- Windows client для compatibility path, если он продаётся пользователю.

Для INCY после rollout:

```text
manual refresh
remove/re-add subscription when cache suspected
one visible profile
TUN connected
DE default
RU service route
block checks
LAN access
```

---

# 13. Логирование, метрики и evidence

## 13.1. Structured logs

Добавить безопасные поля:

```text
product_code
client_family
response_type
template_name
config_checksum
route_policy_version
selected_route_group
selected_outbound_tag
degraded_reason
test_run_id
```

Запрещённые поля:

```text
subscription short UUID
full subscription URL
VLESS UUID
Reality keys/short IDs
bridge password
Remnawave token
raw headers with secrets
user email/PII
```

## 13.2. Метрики

Минимум:

```text
cybervpn_subscription_response_total{product,client,response_type}
cybervpn_subscription_generation_failures_total{product,client}
cybervpn_route_smoke_result{product,route,expected,actual}
cybervpn_transport_health{region,transport}
cybervpn_route_degraded_total{product,reason}
cybervpn_policy_drift{artifact}
cybervpn_policy_age_seconds{product}
```

## 13.3. Evidence artifact

Создать:

```text
docs/evidence/releases/YYYY-MM-DD-premium-smart-ru-unified-routing.md
```

Включить:

- commit SHA;
- Remnawave image/tag/digest;
- Node image/tag/digest;
- Xray version;
- policy version/checksum;
- generated artifact checksums;
- redacted Response Rule matrix;
- transport matrix;
- route matrix;
- failover matrix;
- device verification;
- known limitations;
- rollback pointer.

---

# 14. Rollout и rollback

## 14.1. Pre-deploy backup

До изменений:

- Remnawave PostgreSQL dump + checksum;
- export current templates, Response Rules, hosts, squads and profiles;
- copy current generated subscription structural summary;
- save current node profile IDs/checksums;
- save firewall/bridge state;
- do not store secrets in Git evidence.

## 14.2. Rollout gates

Продвижение разрешено только если:

```text
policy compiler check PASS
unit tests PASS
Remnawave contract PASS
generated subscription matrix PASS
Xray/Mihomo static validation PASS
8 transport checks PASS
route matrix PASS
failover matrix PASS
secret scan PASS
rollback rehearsal PASS
```

## 14.3. Rollback

Rollback должен быть атомарным:

1. Остановить rollout.
2. Сохранить failed evidence.
3. Вернуть Response Rules/template/hosts одним согласованным набором.
4. Restore server profiles при изменении compatibility layer.
5. Reload/restart Remnawave согласно проверенной процедуре.
6. Повторить response matrix.
7. Проверить, что customer subscription снова пригодна к импорту.

Запрещён частичный `DELETE` связанных template/virtual host/injection host objects без транзакции и reference check.

---

# 15. Acceptance Criteria

## Subscription delivery

```text
AC-SUB-001: Premium Smart RU определяется authoritative product context, а не только UA.
AC-SUB-002: Client-supplied internal product headers удаляются/перезаписываются.
AC-SUB-003: INCY Premium user получает ровно один full XRAY_JSON config.
AC-SUB-004: Mihomo Premium user получает один hardened MIHOMO config.
AC-SUB-005: Another-plan INCY user не получает Premium Smart RU template.
AC-SUB-006: HAPP Android/iOS имеют доказанный response contract.
AC-SUB-007: Browser и generic fallback не ломаются.
AC-SUB-008: subscription-userinfo сохраняет accounting/expiry contract.
```

## Routing

```text
AC-ROUTE-001: Default world traffic выходит через DE.
AC-ROUTE-002: Ozon/Госуслуги/Яндекс/банки выходят через RU.
AC-ROUTE-003: EU exceptions применяются до broad RU rules.
AC-ROUTE-004: YouTube/OpenAI/GitHub/Discord идут через EU.
AC-ROUTE-005: LAN/private client destinations идут DIRECT согласно policy.
AC-ROUTE-006: Final Xray rule имеет network tcp,udp matcher.
AC-ROUTE-007: Route decision подтверждён логом, а не только доступностью сайта.
```

## Blocking

```text
AC-BLOCK-001: Ads/tracker fixtures блокируются.
AC-BLOCK-002: Torrent domain/process/protocol policy синхронизирована.
AC-BLOCK-003: Torrent group REJECT-only для Mihomo.
AC-BLOCK-004: TOR block маркирован best-effort и тестируется безопасными fixtures.
AC-BLOCK-005: Node Torrent Blocker и SMTP restrictions проверены на целевых nodes.
AC-BLOCK-006: Пустые TOR shared lists дают DEGRADED, а не ложный PASS.
```

## Transport/failover

```text
AC-TRANS-001..008: Каждый из 8 RAW/XHTTP transports проверен отдельно.
AC-FAIL-001: DE unavailable -> NL согласно контракту.
AC-FAIL-002: Moscow unavailable -> SPB.
AC-FAIL-003: SPB unavailable -> Moscow.
AC-FAIL-004: Both RU unavailable создаёт explicit degraded state.
AC-FAIL-005: Non-RU health endpoint не делает RU path false-unhealthy.
AC-FAIL-006: NL XHTTP имеет реальную роль или явно не считается automatic fallback.
```

## Reproducibility/security

```text
AC-SOT-001: Один typed policy source генерирует client/server/header outputs.
AC-SOT-002: Generated drift ловится CI check-ом.
AC-SOT-003: Source revisions/checksums pinned.
AC-SEC-001: Bridge/customer squads изолированы.
AC-SEC-002: Evidence/logs не содержат secrets/PII.
AC-SEC-003: Rollback проверен.
AC-DOC-001: Production architecture обновлена после rollout.
```

---

# 16. Definition of Done

Codex имеет право завершить задачу только когда:

1. Реальная причина текущего неправильного поведения задокументирована и подтверждена тестом.
2. Product-scoped subscription delivery реализована.
3. Canonical policy source внедрён.
4. Mihomo, XRAY_JSON, legacy header и server compatibility больше не расходятся по критическим спискам.
5. INCY, Mihomo и заявленный HAPP path протестированы отдельно.
6. Все восемь transports проверены отдельно.
7. Default DE, RU services, EU exceptions, block и LAN matrix проходят.
8. DE/NL и Moscow/SPB failover доказаны.
9. False-unhealthy RU regression закрыт.
10. Production-compatible Xray version использована в validation.
11. Staging/canary evidence создана.
12. Rollback готов и проверен.
13. Нет секретов в Git/logs/evidence.
14. Изменения закоммичены focused commits и `git diff --check` проходит.
15. Финальный отчёт содержит точные команды, результаты и список того, что не проверено.

Финальная строка `COMPLETE` разрешена только при выполнении всех blocker criteria. Иначе использовать `INCOMPLETE` с конкретным перечнем оставшихся проверок.
