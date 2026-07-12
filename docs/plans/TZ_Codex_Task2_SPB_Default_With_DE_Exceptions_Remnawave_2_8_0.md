# Техническое задание для Codex App GPT-5.6 Sol
## Задача 2 — новый тариф: SPB по умолчанию, Antifilter/vendor/custom prefixes через Германию

**Статус:** implementation-ready
**Целевой репозиторий:** `https://github.com/Beep206/CyberVPN`
**Панель:** Remnawave `2.8.0`
**Рабочее имя продукта:** `CyberVPN Premium SPB + DE Exceptions`
**Рекомендуемый plan code:** `premium_spb_de_exceptions`
**Приоритет:** P0/P1 — новый production product

---

# 0. Режим работы Codex

Codex должен реализовать новый тариф как отдельный продуктовый и инфраструктурный контур. Нельзя изменять существующий `premium_smart_ru` так, чтобы пользователи двух тарифов делили неоднозначную routing policy.

Обязательные правила:

1. Сначала выполнить repo/preproduction audit и зафиксировать исходный `HEAD`.
2. Не использовать текущие числа префиксов как константы: Antifilter BGP-наборы меняются.
3. Не загружать десятки тысяч префиксов вручную в UI.
4. Не использовать Remnawave Node Plugin как route-steering engine: plugins могут фильтровать/drop traffic, но не заменяют Xray outbound selection.
5. Не допускать silent fallback matched traffic обратно в SPB, если DE bridge недоступен.
6. Не выполнять production route/profile replacement без backup, canary и rollback.
7. Не сохранять BGP session secrets, bridge passwords, Remnawave tokens или customer credentials в Git.
8. Доказать route selection Xray logs/telemetry, а не только фактом открытия сайта.
9. Не генерировать live Torrent/TOR traffic в тестах.
10. В финальном отчёте разделить local/staging/production evidence.

---

# 1. Бизнес-цель

Пользователь подключается к публичной ноде Санкт-Петербурга.

Далее:

```text
Destination входит в Antifilter/vendor/custom prefix union -> через DE bridge -> Germany egress
Destination не входит в union                         -> DIRECT из SPB -> Russia egress
Ads/Torrent/TOR/abuse policy                          -> BLOCK согласно тарифной policy
Private/management/self destinations                  -> BLOCK или явно утверждённая safe policy
```

Главное отличие от `Premium Smart RU`:

- здесь default route — SPB;
- исключения преимущественно IP/CIDR, а не только domain/geosite;
- решение должно работать server-side на SPB для любого совместимого VLESS-клиента;
- клиенту не нужен сложный multi-outbound full config для выполнения основного контракта.

---

# 2. Нормативные Antifilter communities

Pipeline должен принимать отдельные категории и строить их union.

Утверждённое владельцем продукта уточнение от 2026-07-12: production BGP
export для зарегистрированного collector IP считается полным без отдельной
community `65444:110`. Категория RKN строится из `65444:100`; остальные 12
выбранных service/custom communities остаются обязательными. Текущее число
примерно 29 451 IPv4-prefix не является константой acceptance: pipeline всё
равно проверяет непустые категории, freshness, checksums, safety thresholds и
delta относительно last-known-good.

| Категория | BGP community |
|---|---|
| RKN/blocked/summarized host prefixes | `65444:100` |
| Meta | `65444:700` |
| Twitter/X | `65444:710` |
| Netflix | `65444:720` |
| Amazon CloudFront | `65444:730` |
| Microsoft | `65444:740` |
| Amazon | `65444:750` |
| OpenAI | `65444:760` |
| YouTube | `65444:770` |
| Google | `65444:780` |
| Telegram | `65444:790` |
| Discord | `65444:800` |
| Custom networks | `65444:65444` |

Источник описания: `https://antifilter.network/bgp`.

Количество префиксов и адресов динамическое. Acceptance не должен сравнивать feed с навсегда зашитым числом. Вместо этого использовать:

- non-empty checks;
- per-category minimum/maximum safety thresholds;
- change delta thresholds;
- checksums;
- freshness;
- last-known-good comparison;
- spot membership fixtures.

---

# 3. Архитектурное решение

## 3.1. Authoritative server-side routing

Основной path:

```text
Customer
  -> SPB public VLESS RAW/XHTTP inbound
  -> SPB Xray routing
       -> matched compiled prefix -> dedicated DE bridge outbound
       -> unmatched TCP/UDP       -> DIRECT from SPB
       -> prohibited traffic      -> BLOCK
```

Это решение одинаково работает для:

- XRAY_BASE64 clients;
- INCY/HAPP с обычной VLESS link;
- Mihomo clients;
- других клиентов, способных использовать выданный SPB VLESS transport.

Клиентский full config может добавляться позже для UI/diagnostics, но не должен быть единственным способом выполнить тарифный контракт.

## 3.2. Dedicated bridge

Создать отдельный service bridge SPB -> DE, не переиспользовать customer credentials.

Рекомендуемые logical objects:

```text
Service user:      CYBERVPN_SPB_DE_EXCEPTIONS_BRIDGE_USER
Internal squad:   CYBERVPN_SPB_DE_EXCEPTIONS_BRIDGE
DE inbound tag:   DE_SPB_EXCEPTIONS_BRIDGE_9444
SPB outbound tag: DE_EXCEPTIONS_BRIDGE
```

Remnawave 2.8.0 physical internal-squad mapping:
`CYBERVPN_SPB_DE_BRIDGE`. The longer descriptive squad name exceeds the
database `varchar(30)` limit; the service username and inbound/outbound tags
remain as specified.

Порт `9444` приведён как пример. Codex должен проверить inventory и выбрать свободный, управляемый IaC порт. Нельзя молча конфликтовать с существующим `9443` bridge.

Bridge requirements:

- отдельный strong random secret из secret storage;
- modern AEAD method, совместимый с установленным Xray;
- TCP + UDP;
- inbound только на DE;
- no public Remnawave host;
- service user only in bridge squad;
- firewall allows only SPB source IPs/addresses;
- customer subscription never contains bridge outbound/inbound;
- rotation/rollback procedure;
- per-bridge metrics/log tags.

---

# 4. CIDR ingestion architecture

Система состоит из двух независимых слоёв.

## 4.1. Collector/importer

Collector получает authoritative routes по BGP communities.

Предпочтительный production method:

```text
BIRD2 или FRR sidecar
  -> eBGP session с Antifilter endpoint
  -> community filtering
  -> export selected RIB entries by category
  -> atomic canonical CIDR files
```

Codex должен выбрать BIRD2 или FRR в соответствии с существующей инфраструктурой проекта. Не внедрять оба без необходимости.

Если BGP session нельзя поднять в первом PR, обязательный MVP interface:

```text
importer читает externally supplied canonical CIDR files
compiler и deploy pipeline полностью работают
BGP collector оформлен отдельным deployable component с тем же output contract
```

HTTP scraping HTML-страницы `antifilter.network/bgp` не является authoritative production ingest. Страница может использоваться для metadata/sanity check, но не как единственный route feed.

## 4.2. Compiler

Compiler:

1. Читает per-community route files.
2. Валидирует IPv4/IPv6 CIDR.
3. Нормализует network addresses.
4. Удаляет exact duplicates.
5. Collapse/summarize только математически безопасные adjacent/contained networks.
6. Сохраняет category membership metadata.
7. Строит union `de-exceptions`.
8. Исключает forbidden/self/management networks.
9. Создаёт Xray-renderable artifact.
10. Создаёт manifest/checksums/stats.
11. Публикует только после всех safety checks.

## 4.3. Last-known-good

При feed/parser/validation failure:

- не публиковать пустой или подозрительно маленький список;
- сохранить предыдущий last-known-good;
- выставить DEGRADED metric/alert;
- записать reason и failed checksum;
- не менять production profile.

---

# 5. Рекомендуемая структура репозитория

```text
infra/antifilter/
  README.md
  bird/                 # либо frr/, выбрать один вариант
  systemd/
  examples/
scripts/remnawave/antifilter/
  __init__.py
  models.py
  parse_routes.py
  validate_routes.py
  compile_routes.py
  render_xray.py
  build_manifest.py
  publish.py
  cli.py
data/antifilter/
  README.md
  fixtures/
    communities/
  # production raw feed не коммитить, если он слишком большой/динамический
artifacts/antifilter/    # generated; решить Git/LFS/release storage policy
  manifest.json
  categories/
  de-exceptions.cidr
  xray/
backend/src/application/antifilter_routes/
backend/src/infrastructure/antifilter_routes/
services/task-worker/src/tasks/antifilter_routes/
docs/runbooks/ANTIFILTER_BGP_ROUTE_PIPELINE.md
docs/runbooks/SPB_DE_EXCEPTIONS_ROLLBACK.md
```

Адаптировать пути к фактической архитектуре проекта. Не создавать параллельный framework, если уже есть TaskIQ, metrics, release gates и VPN Tester.

---

# 6. Canonical data model

Рекомендуемый manifest:

```json
{
  "schemaVersion": 1,
  "product": "premium_spb_de_exceptions",
  "generatedAt": "2026-07-11T00:00:00Z",
  "source": {
    "type": "bgp",
    "provider": "antifilter.network",
    "collector": "bird2",
    "sessionIdHash": "redacted-hash"
  },
  "categories": {
    "rkn": {
      "communities": ["65444:100"],
      "prefixCountRaw": 0,
      "prefixCountCompiled": 0,
      "addressCount": "0",
      "sha256": "..."
    }
  },
  "union": {
    "prefixCount": 0,
    "addressCount": "0",
    "sha256": "..."
  },
  "exclusions": {
    "private": 0,
    "management": 0,
    "selfEndpoints": 0,
    "invalid": 0
  },
  "previousManifestSha256": "...",
  "change": {
    "added": 0,
    "removed": 0,
    "percent": 0.0
  }
}
```

Большие address counts хранить как string или arbitrary precision integer, не как JavaScript number.

---

# 7. CIDR validation and exclusions

## 7.1. Validate

Для каждого prefix:

- `ipaddress.ip_network(value, strict=False)` или эквивалент;
- canonical string output;
- correct family;
- no host bits after canonicalization;
- prefix length within allowed range;
- no malformed comments/attributes mixed into CIDR file.

## 7.2. Exclude by default

Нельзя отправлять в DE bridge:

```text
loopback
RFC1918/private
link-local
multicast
unspecified
CGNAT, если он нужен для локальной инфраструктуры
SPB node public/control IPs
DE node public/control IPs
Remnawave control-plane addresses
bridge peer addresses
DNS/relay management endpoints
monitoring and SSH management networks
Docker/Kubernetes internal networks
```

Точный allow/deny набор должен храниться в отдельном reviewed policy file.

## 7.3. Self-route protection

Compiler должен падать, если union после exclusions всё ещё содержит:

- SPB public endpoint, через который подключается клиент;
- DE bridge endpoint;
- Remnawave Node API endpoint;
- control plane;
- route collector peer.

Это предотвращает routing loop и потерю управления.

## 7.4. IPv6 policy

Если feed и bridge полноценно поддерживают IPv6, обрабатывать IPv4 и IPv6 раздельно и объединять в профиль.

Если эквивалентный IPv6 exception feed не доказан:

- либо отключить IPv6 для тарифа;
- либо явно маршрутизировать IPv6 по утверждённой fallback policy;
- не допускать silent IPv6 bypass исключений.

Acceptance должен содержать IPv6 leak/route test.

---

# 8. Формат Xray route artifact

Canonical source всегда остаётся набором CIDR + manifest. Renderer может выбрать один из двух доказанных способов.

## 8.1. Inline/chunked CIDR rules

Допустимо для canary/MVP, если измерения подтверждают:

- config size в допустимом диапазоне;
- startup/reload time;
- memory consumption;
- Node API transfer size;
- Remnawave DB/profile limits;
- route lookup performance.

Разбивать union на deterministic chunks, например по `500–2000` prefixes, не создавая rule без matcher.

Пример логики:

```json
{
  "type": "field",
  "inboundTag": ["SPB_EXCEPTIONS_REALITY_443", "SPB_EXCEPTIONS_XHTTP_8443"],
  "ip": ["203.0.113.0/24"],
  "outboundTag": "DE_EXCEPTIONS_BRIDGE"
}
```

## 8.2. External GeoIP/DAT artifact

Предпочтителен, если inline profile слишком велик или медленно загружается.

Требования:

- использовать формат и `ext:` syntax, реально поддерживаемые установленным Xray Core;
- compiler version pinned;
- artifact checksum pinned in manifest;
- atomic deployment рядом с Xray geodata;
- Xray config test после замены файла;
- rollback previous DAT;
- no restart window without valid artifact.

Codex не должен выбирать DAT только теоретически. Он обязан сделать маленький fixture, загрузить его в production-compatible Xray и доказать matcher.

## 8.3. Decision gate

В evidence сравнить inline и DAT по:

```text
artifact size
compile time
Xray validation/start time
RSS memory
route lookup smoke latency
operational update complexity
rollback complexity
```

Выбрать решение на основе измерений. До измерений использовать inline renderer для тестового fixture и не считать production format утверждённым.

---

# 9. SPB Xray server profile

Создать отдельный Config Profile, не менять base profile всех SPB пользователей.

Рабочее имя:

```text
S1 SPB DE Exceptions
```

## 9.1. Inbounds

Минимум:

```text
SPB_EXCEPTIONS_REALITY_443
SPB_EXCEPTIONS_XHTTP_REALITY_8443
```

Требования:

- VLESS Reality RAW/TCP 443;
- VLESS Reality XHTTP 8443;
- отдельные public Hosts;
- customer internal squad содержит оба inbound;
- sniffing настроен только в проверенном объёме;
- no bridge inbound exposed publicly.

## 9.2. Outbounds

```text
DIRECT               freedom from SPB
BLOCK                blackhole
DE_EXCEPTIONS_BRIDGE dedicated SPB -> DE bridge
```

Bridge должен поддерживать UDP, иначе часть QUIC/voice/application traffic из exception prefixes нарушит контракт.

## 9.3. Обязательный rule order

```text
1. management/private/self IPs -> BLOCK или approved safe path
2. bridge inbound isolation rules
3. bittorrent protocol -> BLOCK
4. torrent domains/process equivalents where server can inspect -> BLOCK
5. ads/trackers policy -> BLOCK, если входит в тариф
6. TOR best-effort policy -> BLOCK
7. SMTP abuse ports -> BLOCK/plugin policy
8. compiled de-exceptions IPv4 chunks/DAT -> DE_EXCEPTIONS_BRIDGE
9. compiled de-exceptions IPv6 chunks/DAT -> DE_EXCEPTIONS_BRIDGE
10. final inboundTag + network tcp,udp -> DIRECT
```

Финальное правило:

```json
{
  "type": "field",
  "inboundTag": [
    "SPB_EXCEPTIONS_REALITY_443",
    "SPB_EXCEPTIONS_XHTTP_REALITY_8443"
  ],
  "network": "tcp,udp",
  "outboundTag": "DIRECT"
}
```

Нельзя полагаться только на position of first outbound. Default route должен быть явным и ограниченным target inbounds.

## 9.4. Fail semantics

Для destination, совпавшего с exception union:

```text
DE bridge available   -> Germany egress
DE bridge unavailable -> connection fails / explicit fail-closed
```

Нельзя fallback matched traffic в `DIRECT` SPB: это нарушит заявленный смысл тарифа и может открыть заблокированный ресурс через РФ только частично/непредсказуемо.

Если владелец позже утвердит NL backup, он должен быть отдельным EU bridge и отдельной product policy revision. Для текущей задачи требуется именно Germany.

Unmatched traffic продолжает работать DIRECT через SPB даже при падении DE bridge.

---

# 10. Remnawave objects и тариф

## 10.1. Internal squad

```text
Name: CYBERVPN_PREMIUM_SPB_DE_EXCEPTIONS_NODES
Nodes/inbounds:
  - SPB RAW public inbound
  - SPB XHTTP public inbound
```

Implementation mapping for Remnawave 2.8.0: the physical database name is
`CYBERVPN_SPB_DE_NODES`. The normative descriptive name above exceeds the
actual `varchar(30)` limit of `internal_squads.name`; plan code and environment
setting names remain unchanged.

Не включать обычные DE customer inbounds: пользователь подключается к SPB, а DE используется server-side bridge.

## 10.2. External squad

```text
Name: CYBERVPN_PREMIUM_SPB_DE_EXCEPTIONS
Purpose: headers/template/branding for the new tariff
```

Implementation mapping for Remnawave 2.8.0: the physical database name is
`CYBERVPN_SPB_DE_EXCEPTIONS`. The normative descriptive name above exceeds the
actual `varchar(30)` limit of `external_squads.name`.

Для простых clients можно отдавать XRAY_BASE64 с двумя SPB transports. Mihomo/XRAY_JSON templates могут использоваться для UX, block policy и diagnostics, но должны направлять весь пользовательский proxy traffic на SPB public Host; authoritative exception routing остаётся на SPB server profile.

## 10.3. Plan code

Добавить отдельный plan:

```python
PREMIUM_SPB_DE_EXCEPTIONS = "premium_spb_de_exceptions"
```

Не переиспользовать `premium_smart_ru`.

Добавить settings по текущим conventions проекта:

```text
REMNAWAVE_SPB_DE_EXCEPTIONS_INTERNAL_SQUAD_UUID
REMNAWAVE_SPB_DE_EXCEPTIONS_EXTERNAL_SQUAD_UUID
REMNAWAVE_SPB_DE_EXCEPTIONS_PLAN_CODES
REMNAWAVE_SPB_DE_EXCEPTIONS_PROFILE_NAME
REMNAWAVE_SPB_DE_EXCEPTIONS_POLICY_VERSION
```

## 10.4. Provisioning

Проверить paid/manual/admin provisioning:

- new plan resolves correct internal squad;
- correct external squad assigned;
- no Premium Smart RU squads leaked;
- bridge service user cannot be provisioned as customer;
- traffic accounting remains enabled;
- Unlimited/fair-use display does not disable counters.

---

# 11. Feed update and deployment workflow

Целевой pipeline:

```text
BGP collector
  -> export per-community routes to staging directory
  -> compiler validate/normalize/collapse
  -> self/management exclusions
  -> category + union artifacts
  -> manifest + checksums + delta
  -> fixture Xray validation
  -> policy safety gate
  -> render candidate SPB profile/artifact
  -> staging runtime tests
  -> atomic publish
  -> Remnawave profile update/reload
  -> post-deploy smoke
  -> promote last-known-good
```

## 11.1. Atomicity

Запрещено обновлять active artifact in-place.

Использовать:

```text
write candidate to temp/versioned path
fsync/checksum
validate Xray config
atomic symlink/rename switch
reload/restart
post-check
rollback switch on failure
```

## 11.2. Schedule

Начальная рекомендация:

- collector каждые 15–60 минут, согласно feed policy;
- compile только при изменении RIB checksum;
- production publish не чаще установленного debounce interval;
- daily full verification;
- immediate alert on stale feed beyond threshold.

Точные интервалы вынести в settings.

## 11.3. Safety thresholds

Настраиваемые gates:

```text
min prefixes per required category
max prefixes per category
max removed percent without manual approval
max added percent without manual approval
max invalid prefixes
max self/management exclusions delta
max artifact age
```

Значения определить по observed history и fixtures, а не по одному snapshot.

---

# 12. Tests for collector/compiler

## 12.1. Unit tests

Проверить:

- community mapping;
- IPv4/IPv6 parse;
- host-bit normalization;
- duplicate removal;
- contained-network collapse;
- safe adjacent collapse;
- category attribution after collapse;
- deterministic sort;
- address count using arbitrary precision;
- manifest checksum;
- previous-manifest delta;
- empty feed rejection;
- suspicious shrink rejection;
- self endpoint rejection;
- private/management exclusion;
- last-known-good retention;
- no secret fields in manifest.

## 12.2. Property tests

Для random CIDR sets:

- compiled union covers every input address/network;
- compiler never expands beyond mathematically valid collapse;
- excluded networks never remain in output;
- second compile of compiled output is idempotent;
- ordering/checksum deterministic across runs.

## 12.3. Fixture tests

Создать small fixture для каждой community и overlapping cases.

Не коммитить полный production feed в обычный Git, если размер/обновляемость делают это неразумным. Для production artifact использовать release/object storage или отдельный controlled artifact mechanism.

---

# 13. Remnawave/Xray contract tests

Проверить:

```text
new Config Profile exists
SPB target node uses new profile only for new tariff inbounds
RAW and XHTTP inbounds exist
public Hosts map to correct inbounds
customer squad contains only customer inbounds
bridge inbound has no public Host
bridge user isolated
DE bridge outbound exists in SPB profile
DIRECT and BLOCK exist
exception rules precede final DIRECT
final DIRECT limited by inboundTag and network tcp,udp
no empty routing rule
no accidental geoip:ru catch-all before exceptions
profile size/startup within limits
Node reports healthy after profile update
```

Если profile assignment в Remnawave действует на всю node, а не на отдельный тариф/inbound, Codex обязан решить конфликт архитектурно:

- объединить old/new inbounds в одном node profile с routing scoped by `inboundTag`; либо
- выделить отдельную Remnawave node/runtime instance; либо
- документировать другой доказанный Remnawave 2.8.0 mechanism.

Нельзя заменить профиль SPB так, чтобы сломать существующих пользователей.

---

# 14. Runtime route test matrix

## 14.1. Test principle

Для каждой категории выбрать безопасный probe:

1. Resolve target to current IP.
2. Assert IP входит в compiled category/union.
3. Send safe HTTPS HEAD/GET through SPB customer transport.
4. Capture Xray route/outbound log.
5. Determine egress IP/country where possible.
6. Assert outbound `DE_EXCEPTIONS_BRIDGE` and Germany egress.

Не достаточно проверить domain name без подтверждения, что его текущий IP входит в feed.

## 14.2. Required categories

Минимум один устойчивый probe для:

```text
RKN/blocked list
Meta
Twitter/X
Netflix
CloudFront
Microsoft
Amazon
OpenAI
YouTube
Google
Telegram
Discord
Custom networks
```

Если сервис не предоставляет безопасный unauthenticated HTTP endpoint, использовать:

- controlled test prefix из custom community;
- DNS resolution + TCP/TLS handshake;
- route log evidence без авторизации.

## 14.3. Unmatched DIRECT probes

Выбрать несколько адресов, гарантированно не входящих в union:

```text
Russian public service outside union
controlled SPB-direct test endpoint
ordinary non-listed endpoint
```

Ожидается:

```text
outbound = DIRECT
egress = SPB/Russia
```

Перед тестом membership нужно проверять автоматически, иначе feed update может сделать fixture matched.

## 14.4. Block probes

Без live prohibited traffic:

```text
ad domain fixture -> BLOCK
torrent website/static fixture -> BLOCK
torproject/onion rule fixture -> BLOCK
SMTP port synthetic test target -> BLOCK according to policy
```

## 14.5. Transport matrix

Каждую route category достаточно полно прогнать хотя бы через primary transport, но отдельно обязательно проверить:

```text
SPB RAW -> matched -> DE
SPB RAW -> unmatched -> SPB
SPB XHTTP -> matched -> DE
SPB XHTTP -> unmatched -> SPB
UDP matched -> DE bridge
UDP unmatched -> SPB DIRECT
```

---

# 15. Degraded/failure tests

## 15.1. DE bridge down

Ожидается:

```text
matched destination -> fails closed
unmatched destination -> continues via SPB DIRECT
metric/alert -> DE_BRIDGE_UNAVAILABLE
no silent DIRECT fallback for matched prefix
```

## 15.2. Feed failure

Ожидается:

```text
last-known-good remains active
new empty/corrupt artifact rejected
alert includes safe reason/checksum
no production profile mutation
```

## 15.3. Suspicious route delta

Ожидается:

```text
candidate quarantined
manual approval required
last-known-good active
```

## 15.4. Xray candidate invalid

Ожидается:

```text
no reload of invalid config
active runtime remains healthy
candidate retained for evidence
```

## 15.5. SPB node down

Тариф недоступен, если не утверждён отдельный SPB backup. Не менять смысл продукта автоматическим подключением к DE customer node. Отразить outage в monitoring и customer status.

---

# 16. Observability

## 16.1. Logs

Structured fields:

```text
route_feed_version
manifest_sha256
category
community
prefix_count
change_added
change_removed
candidate_status
profile_checksum
selected_outbound
matched_rule_tag
bridge_health
test_run_id
```

Не логировать:

```text
BGP passwords/MD5 keys
bridge password
subscription URL/UUID
VLESS UUID
Reality private keys
Remnawave token
customer PII
```

## 16.2. Metrics

Минимум:

```text
cybervpn_antifilter_feed_prefixes{category,family}
cybervpn_antifilter_feed_age_seconds
cybervpn_antifilter_feed_invalid_prefixes_total{category}
cybervpn_antifilter_feed_change{category,type}
cybervpn_antifilter_publish_total{status}
cybervpn_spb_de_bridge_health
cybervpn_spb_de_route_smoke{category,expected,actual}
cybervpn_spb_de_matched_fail_closed_total
cybervpn_spb_de_profile_reload_total{status}
cybervpn_spb_de_last_known_good_age_seconds
```

## 16.3. Alerts

Blocker alerts:

```text
feed stale
required category empty
suspicious shrink/growth
self endpoint found in union
compile failure
Xray validation failure
DE bridge down
matched route exits SPB
unmatched route exits DE
profile reload failure
last-known-good too old
```

---

# 17. Security requirements

1. BGP session credentials in secret manager/Ansible Vault, not Git.
2. Bridge secret in secret manager and rollback manifest outside Git.
3. Firewall allowlist for bridge TCP/UDP.
4. Bridge inbound not published as Remnawave Host.
5. Dedicated service user cannot log in through customer flow.
6. Route feed artifacts are untrusted input until parsed/validated.
7. Protect against path traversal, oversized input and decompression bombs if importer accepts archives.
8. Run compiler without root.
9. Limit collector privileges/network access.
10. Sign or checksum released artifacts.
11. Audit manual override of suspicious feed delta.
12. Redact evidence.

---

# 18. Rollout plan

## Phase 1 — offline compiler

- implement fixtures, compiler, manifest, safety gates;
- no production changes;
- benchmark inline vs DAT.

## Phase 2 — staging bridge/profile

- dedicated staging service user/bridge;
- staging SPB profile/inbounds;
- runtime route matrix;
- failure injection.

## Phase 3 — canary tariff

- hidden/admin-only plan;
- one test customer;
- RAW/XHTTP tests;
- 24–72 hour synthetic monitoring;
- verify feed updates without traffic regression.

## Phase 4 — production

- backup Remnawave DB/profile/firewall/artifacts;
- deploy collector/compiler;
- publish last-known-good candidate;
- assign canary users;
- full acceptance;
- enable sale only after release gate green.

---

# 19. Rollback

Rollback artifacts:

```text
previous manifest
previous canonical CIDR union
previous Xray inline/DAT artifact
previous SPB Config Profile JSON
previous node-profile assignment
previous DE bridge config/firewall rules
Remnawave DB dump/checksum
```

Procedure:

1. Stop automatic publish.
2. Switch artifact symlink/version to previous last-known-good.
3. Restore previous SPB profile if renderer/profile changed.
4. Reload/restart Xray/Node via verified method.
5. Run matched/unmatched smoke.
6. If bridge itself caused failure, disable new tariff Hosts/squad assignment without touching existing SPB products.
7. Preserve failed candidate/evidence without secrets.

---

# 20. Acceptance Criteria

## Feed/compiler

```text
AC-FEED-001: All required communities have explicit category mapping.
AC-FEED-002: Prefix/address counts are derived, not hardcoded.
AC-FEED-003: Invalid/empty/suspicious feeds are rejected.
AC-FEED-004: Last-known-good remains active on failure.
AC-FEED-005: Compiler output is deterministic and idempotent.
AC-FEED-006: Private/management/self endpoints are excluded.
AC-FEED-007: IPv6 policy prevents bypass.
AC-FEED-008: Manifest contains checksums, freshness and deltas.
```

## Bridge/profile

```text
AC-BRIDGE-001: Dedicated SPB->DE bridge uses isolated service credentials.
AC-BRIDGE-002: Bridge inbound has no public Host.
AC-BRIDGE-003: Firewall accepts only SPB peer addresses for TCP/UDP.
AC-BRIDGE-004: Matched IPv4 traffic exits Germany.
AC-BRIDGE-005: Matched UDP works through bridge.
AC-PROFILE-001: New SPB RAW/XHTTP inbounds exist without breaking old inbounds.
AC-PROFILE-002: Exception rules precede final DIRECT.
AC-PROFILE-003: Final DIRECT is scoped by inboundTag + tcp,udp.
AC-PROFILE-004: Customer subscription contains no bridge credentials.
```

## Routing

```text
AC-ROUTE-001: RKN category -> DE.
AC-ROUTE-002: Meta -> DE.
AC-ROUTE-003: Twitter/X -> DE.
AC-ROUTE-004: Netflix -> DE.
AC-ROUTE-005: CloudFront -> DE.
AC-ROUTE-006: Microsoft -> DE.
AC-ROUTE-007: Amazon -> DE.
AC-ROUTE-008: OpenAI -> DE.
AC-ROUTE-009: YouTube -> DE.
AC-ROUTE-010: Google -> DE.
AC-ROUTE-011: Telegram -> DE.
AC-ROUTE-012: Discord -> DE.
AC-ROUTE-013: Custom networks -> DE.
AC-ROUTE-014: Non-listed controlled target -> SPB DIRECT.
AC-ROUTE-015: Route decision is proven by outbound log and egress, not availability alone.
```

## Failure semantics

```text
AC-FAIL-001: DE bridge down makes matched traffic fail closed.
AC-FAIL-002: DE bridge down does not break unmatched SPB DIRECT traffic.
AC-FAIL-003: Feed failure does not publish empty rules.
AC-FAIL-004: Invalid Xray candidate does not replace active config.
AC-FAIL-005: Suspicious delta requires manual approval.
AC-FAIL-006: Rollback restores previous route matrix.
```

## Product/provisioning

```text
AC-PLAN-001: New plan code exists separately from premium_smart_ru.
AC-PLAN-002: Paid/manual provisioning assigns correct squads.
AC-PLAN-003: New customer receives SPB RAW and XHTTP entries.
AC-PLAN-004: Existing Premium Smart RU users are unaffected.
AC-PLAN-005: Traffic accounting/subscription-userinfo remains correct.
AC-PLAN-006: Plan remains hidden/admin-only until all release gates pass.
```

## Security/operations

```text
AC-SEC-001: No secrets/PII in Git, logs or evidence.
AC-SEC-002: Artifacts are checksummed and atomically published.
AC-OBS-001: Feed, bridge, route and last-known-good metrics exist.
AC-OBS-002: Blocker alerts are actionable.
AC-DOC-001: Runbook, architecture and rollback docs exist.
```

---

# 21. Definition of Done

Codex может написать `COMPLETE` только если:

1. Новый отдельный plan/squad/profile contract реализован.
2. Collector interface и compiler реализованы.
3. Все communities поддерживаются.
4. Counts не hardcoded.
5. Last-known-good и safety delta gates работают.
6. Self/private/management exclusions покрыты тестами.
7. Dedicated SPB->DE bridge изолирован и поддерживает TCP/UDP.
8. SPB RAW и XHTTP работают.
9. Каждая обязательная category доказанно выбирает DE outbound.
10. Controlled non-listed targets доказанно выбирают SPB DIRECT.
11. DE bridge down даёт fail-closed только для matched traffic.
12. Existing products не сломаны.
13. Production-compatible Xray validation проходит.
14. Inline/DAT production choice обоснован benchmark evidence.
15. Feed update, publish и rollback атомарны.
16. Metrics/alerts/evidence реализованы.
17. Secret scan и `git diff --check` проходят.
18. Staging/canary runtime evidence приложена.
19. Production rollout не объявляется выполненным без фактической production verification.

При наличии хотя бы одного непроверенного blocker использовать `INCOMPLETE` и перечислить точные недостающие шаги.
