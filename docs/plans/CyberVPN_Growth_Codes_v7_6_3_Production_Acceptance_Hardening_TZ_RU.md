# Техническое задание v7.6.3
# Production Acceptance Hardening: Remnawave 2.8.0, XHTTP, Node Metrics, Mini App WebView и RSC/CORS

**Проект:** CyberVPN
**Версия ТЗ:** v7.6.3
**Статус:** требуется к выполнению
**Основание:** после реализации v7.6.2 кодовая база существенно доработана, но production acceptance нельзя считать закрытым без фактических доказательств работы Remnawave 2.8.0, XHTTP на реальных нодах, node metrics в Prometheus/Grafana, Mini App WebView и отсутствия RSC/CORS redirect в личном кабинете.

---

## 1. Краткая цель

Закрыть оставшиеся недостатки после реализации v7.6.2:

1. Подтвердить, что production реально работает на Remnawave `2.8.0`.
2. Подтвердить, что XHTTP реально настроен и работает на выбранных Remnawave-нодаx.
3. Подтвердить, что node CPU load metrics `1m/5m/15m` реально приходят в Prometheus и видны в Grafana.
4. Исправить/подтвердить Mini App WebView, чтобы Telegram больше не показывал `Произошёл сбой WebView`.
5. Полностью закрыть RSC/CORS redirect в личном кабинете:
   ```text
   my.cyber-vpn.net/en-EN/rewards/*?_rsc=...
   → cyber-vpn.net/en-EN
   ```
6. Добавить production evidence, CI/tests и smoke-gates, чтобы задача была закрыта не только кодом, но и фактической проверкой.

---

## 2. Текущее состояние

### 2.1. Что уже сделано в коде

В репозитории уже есть:

- Remnawave image bump в Ansible default до `remnawave/backend:2.8.0`;
- Remnawave 2.8 contract fields;
- XHTTP feature flags;
- XHTTP filtering/rollback в `GenerateConfigUseCase`;
- XHTTP counters;
- Remnawave node diagnostics endpoint;
- Prometheus recording rules для node CPU load;
- alerts для node metrics;
- Grafana dashboard file;
- Mini App health route;
- Mini App diagnostics page;
- Mini App error boundary;
- Mini App client error telemetry endpoint;
- Mini App auth hardening;
- RSC route smoke script.

### 2.2. Что осталось недостаточно подтверждённым

Недостатки:

```text
1. Нет свежего production evidence после актуального commit.
2. Нет доказательства, что production container Remnawave реально запущен на 2.8.0.
3. Нет доказательства, что XHTTP host/inbound/node реально существует в Remnawave.
4. Нет доказательства, что test user получает XHTTP config + stable fallback.
5. Нет доказательства, что node CPU load metrics реально приходят в Prometheus.
6. Alert Stage1RemnawaveNodeCpuLoadHigh использует абсолютный threshold >0.90 без нормализации по CPU cores.
7. Нет явных Remnawave 2.8 integration/fixture tests.
8. Нет актуального CI status/checks для последнего commit.
9. Mini App health route был изменён для production build, но не подтверждено, что Telegram WebView больше не падает.
10. В production-логе всё ещё виден RSC/CORS redirect my.cyber-vpn.net → cyber-vpn.net.
```

---

## 3. P0. Закрыть RSC/CORS redirect в личном кабинете

### 3.1. Симптом

В браузере пользователь видит ошибки:

```text
Access to fetch at 'https://cyber-vpn.net/en-EN'
redirected from 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=...'
from origin 'https://my.cyber-vpn.net' has been blocked by CORS policy:
Redirect is not allowed for a preflight request.
```

Затронутые routes:

```text
/en-EN/rewards
/en-EN/rewards/referral
/en-EN/rewards/gifts
/en-EN/rewards/invites
/en-EN/rewards/codes
/en-EN/rewards/notifications
/en-EN/messages
```

### 3.2. Обязательное расследование

Нужно определить источник redirect:

```text
1. Next proxy runtime policy;
2. Caddy container-edge;
3. system Caddy;
4. Cloudflare rule/cache;
5. старый frontend bundle/chunk в браузере;
6. старый production origin;
7. stale capabilities/runtime config;
8. preloaded RSC request из старого JS chunk.
```

### 3.3. Диагностические команды

Выполнить с внешней машины, не с production host:

```bash
curl -I 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component' \
  -H 'Next-Router-State-Tree: []' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Dest: empty'

curl -I 'https://my.cyber-vpn.net/en-EN/messages?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component' \
  -H 'Next-Router-State-Tree: []' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Dest: empty'
```

Проверить OPTIONS:

```bash
curl -I -X OPTIONS 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=probe' \
  -H 'Origin: https://my.cyber-vpn.net' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: rsc,next-router-state-tree'
```

Fail condition:

```text
HTTP 30x
Location: https://cyber-vpn.net/...
Location: https://www.cyber-vpn.net/...
```

Accept:

```text
200
204
400
404
```

Главное: **не должно быть redirect на другой origin**.

### 3.4. Runtime fingerprint

Проверить, что браузер и curl попадают в актуальный frontend/backend:

```bash
curl -s https://cyber-vpn.net/runtime/fingerprint | jq
curl -s https://my.cyber-vpn.net/runtime/fingerprint | jq
curl -s https://api.cyber-vpn.net/api/v1/runtime/fingerprint | jq
```

Все fingerprints должны совпадать по:

```text
release
git_sha
origin_marker
container_image
```

### 3.5. Cloudflare/cache purge

Перед повторной проверкой обязательно:

```text
Purge:
- cyber-vpn.net/*
- my.cyber-vpn.net/*
- api.cyber-vpn.net/*
- cyber-vpn.net/_next/static/*
- my.cyber-vpn.net/_next/static/*
```

После purge:

```text
1. открыть incognito;
2. проверить Network panel;
3. убедиться, что JS chunks имеют новый build id;
4. повторить клики по rewards/invites/messages;
5. сохранить screenshot Network с отсутствием redirect.
```

### 3.6. Code hardening

Если после purge redirect сохраняется:

1. Добавить в frontend proxy финальный guard:
   ```ts
   if (isCabinetHost && isNextInternalNavigationRequest(request)) {
     return new NextResponse(null, { status: 404 });
   }
   ```
   Он должен срабатывать **до любого redirect на public host**.

2. Для cabinet route segments:
   ```ts
   if (isCabinetHost && isCabinetRouteSegment(routeSegment)) {
     return NextResponse.next();
   }
   ```

3. В Caddy добавить explicit no-redirect handle для cabinet routes:
   ```caddy
   @cabinet_routes path_regexp cabinet_routes ^/(?:(?:[a-z]{2}-[A-Z]{2}|zh-Hant)/)?(?:dashboard|subscriptions|payment-history|referral|rewards|messages|wallet|settings|support|servers|onboarding|monitoring|analytics|users|partner)(?:/.*)?$
   handle @cabinet_routes {
     reverse_proxy cybervpn-frontend:3000
   }
   ```

### 3.7. Acceptance

- [ ] RSC GET на `/rewards/invites` не redirect.
- [ ] RSC GET на `/messages` не redirect.
- [ ] OPTIONS preflight не redirect.
- [ ] Browser Network panel не показывает redirect `my → cyber`.
- [ ] Старые chunks очищены.
- [ ] Evidence приложен к релизу.

---

## 4. P0. Production evidence для Remnawave 2.8.0

### 4.1. Цель

Подтвердить, что production реально обновлён:

```text
Remnawave 2.7.4 → 2.8.0
```

### 4.2. Команды

На production:

```bash
docker inspect remnawave --format '{{.Config.Image}} {{.Image}}'
docker image inspect remnawave/backend:2.8.0 --format '{{index .RepoDigests 0}}'
docker logs --tail=200 remnawave
curl -fsS http://127.0.0.1:3001/health
curl -fsS http://127.0.0.1:3005/api/system/health || curl -fsS http://127.0.0.1:3005/health
```

Через Remnawave API:

```bash
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/users?start=0\&size=1

curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/nodes

curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/hosts

curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/inbounds
```

### 4.3. Evidence файл

Создать файл:

```text
docs/evidence/releases/<release>/remnawave-2-8-production-evidence.md
```

Содержимое:

```text
- release tag;
- commit sha;
- старый image/tag/digest;
- новый image/tag/digest;
- дата/время обновления;
- health output;
- API smoke output;
- backup path;
- rollback image;
- результат Premium Smart RU smoke;
- результат XHTTP smoke;
- результат Mini App smoke;
- результат RSC smoke.
```

### 4.4. Acceptance

- [ ] Evidence содержит image `2.8.0`.
- [ ] Evidence содержит digest.
- [ ] Health зелёный.
- [ ] API users/nodes/hosts/inbounds зелёные.
- [ ] Нет migration errors в логах.
- [ ] Backup создан перед обновлением.

---

## 5. P0. XHTTP должен реально работать на нодаx

### 5.1. Проблема

CyberVPN уже умеет:

```text
- распознавать XHTTP links;
- фильтровать их feature flag;
- возвращать xhttp_enabled/xhttp_links;
- считать XHTTP counters.
```

Но нужно подтвердить, что **Remnawave реально отдаёт XHTTP links**, а не просто CyberVPN готов их принять.

### 5.2. Проверить Remnawave node/host/inbound

Команды:

```bash
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/hosts | jq '.'

curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/inbounds | jq '.'

curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/nodes | jq '.'
```

Нужно найти:

```text
- минимум 1 node с tag xhttp или equivalent;
- минимум 1 host с tag xhttp;
- минимум 1 inbound/transport, где есть xhttp;
- host не disabled;
- node connected;
- host относится к правильной ноде;
- Premium Smart RU может получить этот host.
```

### 5.3. Если XHTTP host/inbound отсутствует

В Remnawave admin создать/настроить:

```text
1. XHTTP-capable inbound.
2. Host с XHTTP transport.
3. Tags:
   - xhttp
   - premium_smart_ru
   - canary
   - stable_fallback=false или отдельный tag
4. Response rule, который отдаёт XHTTP только canary/premium_smart_ru.
5. Stable fallback host без XHTTP.
```

### 5.4. Проверка subscription config

Создать тестового пользователя:

```text
plan = premium_smart_ru
segment = premium_smart_ru_canary
device_limit = 5
traffic = unlimited/fair_use
```

Получить config через CyberVPN:

```bash
curl -fsS https://api.cyber-vpn.net/api/v1/customer/onboarding/connection/bootstrap \
  -H "Authorization: Bearer <test_user_token>"
```

Или напрямую через backend internal tool/use-case.

Проверить:

```text
xhttp_enabled = true
xhttp_links.length > 0
links contains XHTTP
stable fallback link exists
subscription_url exists
config import works
```

### 5.5. Client QA

Проверить импорт:

```text
Mihomo Desktop
Mihomo Party
Android Mihomo-compatible client
iOS Mihomo-compatible client
Windows client
macOS client
Linux client
```

Для каждого:

```text
- subscription imports;
- XHTTP outbound/proxy appears;
- stable fallback appears;
- connection works;
- DNS works;
- fallback works if XHTTP node disabled.
```

### 5.6. Acceptance

- [ ] Remnawave has real XHTTP node/host/inbound.
- [ ] XHTTP host has tags.
- [ ] Test user receives XHTTP config.
- [ ] Stable fallback remains.
- [ ] Mihomo import works.
- [ ] At least Android/Desktop QA done.
- [ ] XHTTP can be disabled by `REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true`.
- [ ] Evidence contains sample sanitized config proof.

---

## 6. P0/P1. Node metrics должны быть фактически подключены

### 6.1. Проверить Remnawave `/metrics`

На production:

```bash
curl -fsS http://127.0.0.1:3001/metrics | grep -Ei 'node|cpu|load|traffic|online|xray|remnawave' | head -100
```

Нужно найти реальные имена метрик для:

```text
node CPU load 1m
node CPU load 5m
node CPU load 15m
node status
node online users
node traffic
```

### 6.2. Prometheus target

Проверить, что Prometheus видит target:

```text
job="remnawave"
up == 1
```

Если есть доступ к Prometheus API:

```bash
curl -G http://<prometheus>/api/v1/query \
  --data-urlencode 'query=up{job="remnawave"}'
```

### 6.3. Recording rules

Проверить:

```promql
stage1:remnawave_node_cpu_load_1m:current
stage1:remnawave_node_cpu_load_5m:current
stage1:remnawave_node_cpu_load_15m:current
stage1:remnawave_node_metrics_available:current
```

### 6.4. CPU core normalization

Текущий alert с абсолютным threshold `> 0.90` нужно улучшить.

Вариант A: если есть metric CPU cores:

```promql
node_load_5m / node_cpu_cores > 0.80
```

Вариант B: если CPU cores нет, добавить статическую карту per node:

```yaml
remnawave_node_cpu_cores:
  node-a: 2
  node-b: 4
```

Вариант C: временно оставить absolute threshold, но явно прописать в evidence:

```text
CPU load threshold absolute, not core-normalized.
Requires follow-up.
```

### 6.5. Grafana dashboard

Проверить dashboard:

```text
CyberVPN / Remnawave Nodes
```

Он должен показывать:

```text
- CPU load 1m;
- CPU load 5m;
- CPU load 15m;
- node status;
- online users;
- traffic;
- xray version;
- node version;
- XHTTP-capable nodes;
- Premium Smart RU users per node, если возможно.
```

### 6.6. Alerts

Проверить alerts loaded:

```text
Stage1RemnawaveNodeMetricsUnavailable
Stage1RemnawaveNodeCpuLoadHigh
Stage1RemnawaveUnavailable
Stage1NoHealthyRemnawaveNodes
```

### 6.7. Acceptance

- [ ] `/metrics` содержит node CPU load.
- [ ] Prometheus target `remnawave` UP.
- [ ] Recording rules возвращают значения.
- [ ] Dashboard показывает реальные значения.
- [ ] Alerts загружены.
- [ ] CPU threshold нормализован или явно documented.
- [ ] Evidence приложен.

---

## 7. P0. Mini App WebView: закрыть «Произошёл сбой WebView»

### 7.1. Проверить route health

```bash
curl -I https://cyber-vpn.net/ru-RU/miniapp
curl -I https://cyber-vpn.net/ru-RU/miniapp/home
curl -I https://cyber-vpn.net/ru-RU/miniapp/health
curl -I https://cyber-vpn.net/ru-RU/miniapp/diagnostics
```

Fail:

```text
redirect to /register
redirect to /login
redirect to /dashboard
redirect to my.cyber-vpn.net
HTML Cloudflare challenge
5xx
```

### 7.2. Telegram WebView QA

Проверить вручную:

```text
Android Telegram stable
iOS Telegram stable
Telegram Desktop
```

Steps:

```text
/start
кнопка Mini App
menu button Mini App
/miniapp/health
/miniapp/diagnostics
/miniapp/home
/miniapp/onboarding/code
```

Expected:

```text
no WebView crash
no blank screen
no register page
no dashboard redirect
diagnostics visible
auth restore works
```

### 7.3. Client error telemetry

Проверить, что ошибки попадают в backend:

```bash
grep miniapp_client_error_ingested backend logs
```

Payload не должен содержать:

```text
raw initData
tokens
cookies
invite code
subscription URL
VPN links
```

### 7.4. Health route decision

`/miniapp/health` сейчас отдаёт `generated_at`, но route может быть статически оптимизирован после удаления `force-dynamic`.

Решить:

```text
Option A: оставить как availability check, не использовать как runtime proof;
Option B: вернуть dynamic безопасным способом;
Option C: использовать только /runtime/fingerprint для runtime proof.
```

Рекомендация:

```text
/miniapp/health = lightweight availability
/runtime/fingerprint = runtime proof
```

### 7.5. Acceptance

- [ ] Telegram Android opens Mini App.
- [ ] Telegram iOS opens Mini App.
- [ ] Telegram Desktop opens Mini App.
- [ ] No `Произошёл сбой WebView`.
- [ ] Diagnostics page works inside Telegram.
- [ ] Error telemetry sanitized.
- [ ] Evidence attached.

---

## 8. P1. Remnawave 2.8 tests

### 8.1. Backend tests

Добавить:

```text
backend/tests/integration/remnawave/test_remnawave_2_8_contracts.py
backend/tests/integration/remnawave/test_remnawave_xhttp_subscription.py
backend/tests/integration/remnawave/test_remnawave_node_metrics.py
backend/tests/integration/remnawave/test_remnawave_hwid_2_8.py
backend/tests/integration/remnawave/test_remnawave_cursor_users.py
```

### 8.2. Fixtures

Добавить fixtures:

```text
Remnawave 2.8 user response
Remnawave 2.8 node response with cpuLoad1m/5m/15m
Remnawave 2.8 host response with tags/xhttpExtraParams
Remnawave 2.8 subscription response with xhttpLinks
Remnawave 2.8 cursor users response
```

### 8.3. Acceptance

- [ ] Tests validate Remnawave 2.8 fixtures.
- [ ] XHTTP response parsing tested.
- [ ] Cursor user sync tested.
- [ ] HWID active header compatibility tested.
- [ ] CI runs these tests.

---

## 9. P1. CI/checks

### 9.1. Required checks

Для PR/merge в `main` должны запускаться:

```text
backend unit tests
backend integration tests selected
frontend tests
admin tests
telegram-bot tests
lint/typecheck
OpenAPI generation check
```

### 9.2. GitHub status

Для последнего commit должны быть видны checks. Если GitHub status пустой, это должно считаться release risk.

Acceptance:

- [ ] `main` имеет видимый CI status.
- [ ] failures блокируют release.
- [ ] release evidence ссылается на CI run.

---

## 10. P1. Production release evidence template

Создать новый evidence файл после выполнения:

```text
docs/evidence/releases/<release>/v7-6-3-production-acceptance.md
```

Шаблон:

```md
# v7.6.3 Production Acceptance Evidence

## Release
- commit:
- release tag:
- deployed at:
- deploy operator:
- production target:
- Cloudflare purge: yes/no

## Runtime fingerprints
...

## Remnawave 2.8
- image:
- digest:
- health:
- API smoke:

## Backup
- dump path:
- compose backup:
- env backup:
- rollback image:

## XHTTP
- node:
- host:
- inbound:
- tags:
- test user:
- xhttp links present:
- stable fallback present:
- client QA:

## Node metrics
- /metrics grep output:
- Prometheus target:
- recording rules:
- dashboard:
- alerts:

## Mini App
- Android:
- iOS:
- Desktop:
- health:
- diagnostics:
- WebView crash absent:

## RSC/CORS
- rewards/invites RSC:
- messages RSC:
- OPTIONS:
- browser Network screenshot:

## Multi-use invite smoke
- root code:
- user A:
- user B:
- child invites:
- sorting:

## Final decision
- accepted / rejected:
- remaining risks:
```

Acceptance:

- [ ] Evidence file exists.
- [ ] Evidence is committed.
- [ ] Evidence includes actual command outputs.
- [ ] Evidence includes failures if any.

---

## 11. Итоговые acceptance criteria

Работа считается завершённой только если:

```text
1. Production Remnawave image = 2.8.0.
2. Production Remnawave digest зафиксирован.
3. Backup перед обновлением существует.
4. Remnawave API health зелёный.
5. CyberVPN Remnawave contract smoke зелёный.
6. XHTTP host/inbound/node реально существует.
7. Test user получает XHTTP config + stable fallback.
8. Node CPU load metrics реально видны в Prometheus.
9. Grafana dashboard показывает реальные node metrics.
10. Alerts загружены.
11. Mini App открывается в Telegram WebView.
12. Mini App diagnostics работает.
13. Нет WebView crash.
14. RSC/CORS redirect в cabinet отсутствует.
15. Browser Network panel подтверждает отсутствие redirect.
16. Multi-use invite smoke проходит.
17. Клиентская сортировка invite-кодов работает.
18. CI/checks видны.
19. Production evidence committed.
```

---

## 12. Rollback

Если Remnawave 2.8.0 ломает provisioning:

```text
1. Stop worker/scheduler.
2. Disable XHTTP:
   REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true
3. If Remnawave API broken:
   rollback image to previous digest.
4. If DB migration incompatible:
   restore backup.
5. Verify health.
6. Re-enable stable provisioning only.
```

Если XHTTP ломает клиентов:

```text
1. Set REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true.
2. Restart backend/frontend if needed.
3. Clear subscription cache if any.
4. Verify stable fallback config.
5. Keep Remnawave 2.8.0 running if base provisioning works.
```

Если Mini App ломается:

```text
1. Keep bot /start working.
2. Route users to bot fallback.
3. Disable Mini App menu button if needed.
4. Keep /miniapp/diagnostics accessible.
5. Fix WebView issue before re-enabling.
```

Если RSC/CORS persists:

```text
1. Purge Cloudflare.
2. Verify active JS build id.
3. Temporarily force full browser navigation for cabinet menu links.
4. Temporarily set customer_site_mode=full_site only if needed.
5. Re-run RSC smoke.
```
