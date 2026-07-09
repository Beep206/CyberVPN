# ТЗ: внедрение `cybervpn-premium-smart-ru-de-primary-hardened.yaml`

Проект: `Beep206/CyberVPN`
Remnawave: `2.8.0`
Целевой тариф/кампания: `premium_smart_ru_lifetime_multi_root_2026_06_30`
Root invite-code: `LU7QQTQZHG`
Целевой шаблон: `cybervpn-premium-smart-ru-de-primary-hardened.yaml`
Цель: быстро внедрить hardened smart-routing профиль, применить его к существующему Premium Smart RU lifetime invite, сохранить XHTTP, корректно отображать полезную информацию в HAPP/INCY и закрыть abuse-риск по Torrent/TOR.

---

## 0. Коротко: что должно получиться

Пользователь активирует invite `LU7QQTQZHG`, получает существующий `Premium Smart RU lifetime` доступ и импортирует одну подписку.

Маршрутизация в Mihomo/Clash Meta:

```text
Обычный интернет          -> 🇩🇪 DE 25G primary
EU резерв / ручной выбор  -> 🇳🇱 NL fallback
Госуслуги / Яндекс / банки / маркетплейсы РФ -> 🇷🇺 RU Moscow/SPB 25G
YouTube / Discord / AI / GitHub / global dev  -> 🇩🇪 DE / 🇳🇱 NL
Реклама / трекеры / Windows telemetry          -> REJECT
Torrent                                          -> REJECT на клиенте + Torrent Blocker на нодах
TOR                                              -> client best-effort block + server egress lists после наполнения
```

XHTTP:

```text
HAPP / INCY / Xray-compatible clients должны получать рабочий XHTTP/VLESS Reality профиль.
Mihomo-клиенты должны получать hardened smart-routing YAML.
```

Информация в приложениях:

```text
profile-title
support-url
profile-web-page-url
profile-update-interval
subscription-userinfo: upload/download/total/expire
announce для HAPP/совместимых клиентов
HWID/device limit headers, если включен HWID
```

Даже если тариф Unlimited, потребленный трафик должен считаться и отображаться через `download=<usedTrafficBytes>`.

---

## 1. Серверы и Remnawave node naming

### 1.1. Целевые VPN-ноды

| Провайдерское имя | Inventory host | Локация | IP | ОС | CPU/RAM/Disk | Канал | Remnawave node remark |
|---|---|---|---|---|---|---:|---|
| `gigantic-violet` | `s1-ru-msk-3` | Москва | `178.159.94.225` | Ubuntu 24.04 | 4 cores / 8 GB / 120 GB NVMe | до 25 Gbit/s | `🇷🇺 RU Moscow 01 25G` |
| `watery-azure` | `s1-ru-spb-3` | Санкт-Петербург | `193.233.91.99` | Ubuntu 24.04 | 4 cores / 8 GB / 120 GB NVMe | до 25 Gbit/s | `🇷🇺 RU SPB 01 25G` |
| `combative-sapphi` | `s1-de-3` | Германия | `138.124.115.206` | Ubuntu 24.04 | 4 cores / 8 GB / 120 GB NVMe | до 25 Gbit/s | `🇩🇪 DE Frankfurt 01 25G` |
| NL node | `s1-nl-4` | Нидерланды | `138.16.140.44` | Ubuntu 24.04 | 4 cores / 8192 MB / 1100 GB | ниже DE/RU | `🇳🇱 NL Amsterdam 01 10G` |

### 1.2. Inventory уже должен совпадать

Проверить и при необходимости привести к такому виду:

```yaml
remnawave_edge_production:
  hosts:
    s1-ru-msk-3:
      ansible_host: 178.159.94.225
      remnawave_node_remark: "🇷🇺 RU Moscow 01 25G"
    s1-ru-spb-3:
      ansible_host: 193.233.91.99
      remnawave_node_remark: "🇷🇺 RU SPB 01 25G"
    s1-nl-4:
      ansible_host: 138.16.140.44
      remnawave_node_remark: "🇳🇱 NL Amsterdam 01 10G"
    s1-de-3:
      ansible_host: 138.124.115.206
      remnawave_node_remark: "🇩🇪 DE Frankfurt 01 25G"
```

Почему это важно: hardened YAML использует `include-all + filter`. Если remark не содержит `DE/NL/RU/Moscow/SPB`, нода не попадет в правильную группу.

### 1.3. DNS/hostname

Если уже есть hostname — оставить существующие. Если нет, завести DNS A-records:

```text
ru-msk-3.cyber-vpn.org -> 178.159.94.225
ru-spb-3.cyber-vpn.org -> 193.233.91.99
de-3.cyber-vpn.org     -> 138.124.115.206
nl-4.cyber-vpn.org     -> 138.16.140.44
```

Для Reality/XHTTP не использовать IP как публичный адрес профиля, если уже применяется доменная SNI/Reality схема.

---

## 2. Edge node deployment baseline

### 2.1. Обязательные настройки Remnawave Node

Для всех 4 нод:

```yaml
remnawave_edge_image: remnawave/node:2.8.0
remnawave_edge_network_mode: host
remnawave_edge_node_port: 22230
remnawave_edge_cap_add:
  - NET_ADMIN
remnawave_edge_ulimits_nofile_soft: 1048576
remnawave_edge_ulimits_nofile_hard: 1048576
```

`NET_ADMIN` обязателен для Node Plugins.

### 2.2. Preflight на каждой ноде

Выполнить на `s1-de-3`, `s1-nl-4`, `s1-ru-msk-3`, `s1-ru-spb-3`:

```bash
hostnamectl
uname -r
nft --version
docker --version
docker compose version
ss -lntup | grep -E '22230|443|8443' || true
```

Acceptance:

```text
Ubuntu 24.04
kernel >= 5.7
nftables установлен
Docker работает
Remnawave Node container healthy
Node connected=true в Remnawave Panel
```

### 2.3. Deploy через Ansible

```bash
ansible-playbook \
  -i infra/ansible/inventories/production/hosts.yml \
  infra/ansible/playbooks/remnawave-edge.yml \
  --limit remnawave_edge_production
```

После deploy:

```bash
ansible -i infra/ansible/inventories/production/hosts.yml remnawave_edge_production -m shell -a 'docker ps --format "{{.Names}} {{.Image}} {{.Status}}" | grep remnanode'
ansible -i infra/ansible/inventories/production/hosts.yml remnawave_edge_production -m shell -a 'nft list tables | grep remnanode || true'
```

---

## 3. Hardened Mihomo template

### 3.1. Файл в repo

Добавить приложенный файл без переименования содержимого:

```text
scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml
```

Для обратной совместимости также заменить текущий canonical файл:

```text
scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml
```

на содержимое hardened-версии.

Template name в Remnawave оставить прежним:

```text
CyberVPN Premium Smart RU
```

Это важно, потому что backend settings уже ожидают это имя.

### 3.2. Что должно быть в hardened-шаблоне

Обязательно проверить наличие:

```text
bind-address: 127.0.0.1
🧲 Torrents -> только REJECT
DNS adblock -> rcode://name_error
🌍 World / EU -> 🇩🇪 DE Auto первым
🇷🇺 RU Sites -> ⚡ RU Auto первым
MATCH,🌍 World / EU
remnawave.include-proxies: false в auto/filter groups
include-all: true + filter/exclude-filter для DE/NL/RU groups
```

### 3.3. Локальная проверка YAML

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
p = Path('scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml')
data = yaml.safe_load(p.read_text(encoding='utf-8'))
print('groups=', len(data.get('proxy-groups', [])))
print('rule_providers=', len(data.get('rule-providers', {})))
print('rules=', len(data.get('rules', [])))
assert len(data.get('proxy-groups', [])) == 20
assert len(data.get('rule-providers', {})) == 39
assert len(data.get('rules', [])) == 59
PY
```

Если установлен Mihomo binary:

```bash
mihomo -t -f scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml
```

`mihomo -t` — обязательный gate перед production upload.

---

## 4. Remnawave template seed

### 4.1. Обновить seed SQL

Файл:

```text
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

Задача:

1. Заменить inline YAML block внутри `$cybervpn_premium_smart_ru_yaml$ ... $cybervpn_premium_smart_ru_yaml$` на содержимое `cybervpn-premium-smart-ru-de-primary-hardened.yaml`.
2. Оставить template metadata:

```sql
template_type = 'MIHOMO'
name = 'CyberVPN Premium Smart RU'
view_position = 202
```

3. Оставить external squad:

```text
CYBERVPN_PREMIUM_SMART_RU
MIHOMO -> CyberVPN Premium Smart RU
```

4. Оставить internal squad:

```text
CYBERVPN_PREMIUM_SMART_RU_NODES
```

5. Обновить node names в seed строго под новые remarks:

```sql
('🇩🇪 DE Frankfurt 01 25G'),
('🇳🇱 NL Amsterdam 01 10G'),
('🇷🇺 RU Moscow 01 25G'),
('🇷🇺 RU SPB 01 25G')
```

### 4.2. Запуск seed

```bash
psql "$REMNAWAVE_DATABASE_URL" -f scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

Ожидаемый итоговый SELECT:

```text
external_squad_name = CYBERVPN_PREMIUM_SMART_RU
template_name = CyberVPN Premium Smart RU
internal_squad_name = CYBERVPN_PREMIUM_SMART_RU_NODES
plugin_assigned_node_count = 4
internal_squad_inbound_count >= 2
linked_node_inbounds >= 8
```

Если `plugin_assigned_node_count != 4`, остановить rollout и проверить node names в Remnawave.

---

## 5. Internal / External Squad

### 5.1. Internal squad

Internal squad должен давать пользователю доступ к нужным inbounds на 4 нодах:

```text
CYBERVPN_PREMIUM_SMART_RU_NODES
  - VLESS_REALITY_443
  - VLESS_XHTTP_REALITY_8443
```

Если в Remnawave используются другие inbound tags, заменить в seed:

```sql
where tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
```

на актуальные tags из production config profiles.

### 5.2. External squad

External squad:

```text
CYBERVPN_PREMIUM_SMART_RU
```

Должен переопределять:

```text
MIHOMO -> CyberVPN Premium Smart RU
```

Не добавлять SRR rule, который случайно override-ит этот template для Mihomo клиентов. Если добавляются Response Rules для HAPP/INCY, они должны быть явными и протестированными.

---

## 6. Привязка к существующему тарифу и invite `LU7QQTQZHG`

### 6.1. Campaign / invite

Существующая campaign:

```text
campaign_key = premium_smart_ru_lifetime_multi_root_2026_06_30
root invite-code = LU7QQTQZHG
```

Должна выдавать:

```text
grant_plan_code = premium_smart_ru
grant_duration_mode = lifetime
grant_duration_days = null
grant_device_limit_override = 5
traffic policy = Unlimited / fair_use / NO_RESET
```

Важно: не создавать новый тариф, если текущий invite уже выдаёт `premium_smart_ru`. Нужно применить новый Remnawave template/squad к `premium_smart_ru`.

### 6.2. Backend env

Production env должен содержать:

```env
REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID=<uuid CYBERVPN_PREMIUM_SMART_RU>
REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID=<uuid CYBERVPN_PREMIUM_SMART_RU_NODES>
REMNAWAVE_SMART_RU_PLAN_CODES=premium_smart_ru
REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME=CyberVPN Premium Smart RU
```

Если переменная фактически называется `REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME` или `REMNAWAVE_SMART_RU_TEMPLATE_NAME` в deployment tooling — привести к имени из `backend/src/config/settings.py`.

### 6.3. Backend behavior

Для любого provisioning с `plan_code=premium_smart_ru` backend должен отправлять в Remnawave user payload:

```json
{
  "external_squad_uuid": "<CYBERVPN_PREMIUM_SMART_RU>",
  "active_internal_squads": ["<CYBERVPN_PREMIUM_SMART_RU_NODES>"]
}
```

Затрагиваемые файлы:

```text
backend/src/config/settings.py
backend/src/infrastructure/remnawave/smart_ru_bundle.py
backend/src/infrastructure/remnawave/stage1_paid_gateway.py
backend/src/infrastructure/remnawave/stage1_manual_subscription_gateway.py
backend/src/application/use_cases/customer_subscriptions/service_access.py
```

---

## 7. XHTTP: обязательное условие

### 7.1. Feature flags

Production env:

```env
REMNAWAVE_FEATURE_XHTTP_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_MIHOMO_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=false
REMNAWAVE_FEATURE_XHTTP_ALLOWED_PLAN_CODES=premium_smart_ru
REMNAWAVE_FEATURE_XHTTP_ALLOWED_USER_SEGMENTS=internal,beta,premium_smart_ru_canary
```

`REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE` выбрать один из двух вариантов:

```text
premium_smart_ru   # если хотим включить XHTTP всем пользователям premium_smart_ru
canary             # если сначала тестируем только выбранных пользователей/сегмент
```

Для этого ТЗ целевой режим:

```env
REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=premium_smart_ru
```

### 7.2. Remnawave config profile

В Remnawave production должен быть config profile с inbound:

```text
VLESS_XHTTP_REALITY_8443
transport = xhttp
security = reality
port = 8443 или текущий production port
sniffing.destOverride = http,tls,quic
```

Этот inbound должен быть включен для:

```text
CYBERVPN_PREMIUM_SMART_RU_NODES
```

Если сейчас XHTTP есть только на DE, P0 acceptance: XHTTP работает минимум на DE primary. P1 после smoke: добавить XHTTP host/inbound для RU/NL, если это требуется продуктово.

### 7.3. XHTTP smoke

Создать временного пользователя `premium_smart_ru`, скачать subscription под Xray/HAPP-compatible UA:

```bash
curl -i -A "Happ/2.0" "https://cyber-vpn.org/api/sub/<short_uuid>" -o /tmp/happ-sub.txt
curl -i -A "v2rayNG/1.9" "https://cyber-vpn.org/api/sub/<short_uuid>" -o /tmp/xray-sub.txt
```

Проверить:

```bash
grep -Ei 'xhttp|VLESS_XHTTP|Reality|8443' /tmp/happ-sub.txt /tmp/xray-sub.txt
```

Acceptance:

```text
xhttp link/config присутствует
Reality параметры присутствуют
DE XHTTP подключается в HAPP/INCY
stable fallback Reality TCP тоже присутствует
```

Если Mihomo subscription не содержит XHTTP, но HAPP/INCY Xray subscription содержит XHTTP — это допустимо для P0. Нельзя ломать Mihomo smart-routing ради XHTTP.

---

## 8. HAPP / INCY: полезная информация в приложениях

### 8.1. Что должны видеть приложения

В HTTP response подписки должны быть headers:

```http
profile-title: base64:<CyberVPN Premium Smart RU>
profile-update-interval: 24
support-url: https://cyber-vpn.org/support или актуальный support URL
profile-web-page-url: https://cyber-vpn.org/api/sub/<short_uuid>
subscription-userinfo: upload=0; download=<used_bytes>; total=<traffic_limit_bytes_or_0>; expire=<unix_or_0>
announce: base64:<короткое сообщение>
```

Для HAPP дополнительно, если используется `happRouting`:

```http
routing: <HAPP routing payload из Remnawave subscription settings>
```

### 8.2. Unlimited, но трафик считаем

Не отключать учет трафика. Проверка должна смотреть не на лимит, а на used counter:

```text
subscription-userinfo.download увеличивается после тестового трафика
subscription-userinfo.total корректно отображается как Unlimited/0 или согласованный высокий display-limit
expire=0 для lifetime
```

Если HAPP/INCY некрасиво показывают `total=0`, выбрать один из вариантов после теста:

```text
Вариант A: оставить total=0 как Unlimited, если приложения отображают нормально.
Вариант B: поставить большой soft display total, например 10 TiB, но только если Remnawave не будет жестко отключать пользователя по достижении этого значения.
```

Не использовать огромные числа выше JS safe integer для `total`, чтобы не ломать клиенты.

### 8.3. Subscription settings / External Squad headers

В Remnawave Subscription Settings или External Squad settings настроить:

```json
{
  "profileTitle": "CyberVPN Premium Smart RU",
  "supportLink": "https://cyber-vpn.org/support",
  "profileUpdateInterval": 24,
  "isProfileWebpageUrlEnabled": true,
  "happAnnounce": "CyberVPN Premium Smart RU: DE 25G + RU 25G smart routing. RU-сервисы работают без отключения VPN. Torrent запрещён.",
  "customResponseHeaders": {
    "x-cybervpn-plan": "premium_smart_ru",
    "x-cybervpn-routing": "de-primary-ru-smart",
    "x-cybervpn-unlimited": "true"
  }
}
```

Если эти поля задаются через External Squad `response_headers`, учитывать, что Remnawave применяет их как `customResponseHeaders`.

### 8.4. HAPP / INCY Response Rules

P0: не добавлять агрессивные SRR, пока не сняты реальные User-Agent из приложений.

Сначала снять headers:

```bash
curl -i -A "Happ/2.0" "https://cyber-vpn.org/api/sub/<short_uuid>" | sed -n '1,40p'
curl -i -A "INCY/1.0" "https://cyber-vpn.org/api/sub/<short_uuid>" | sed -n '1,40p'
```

Потом на реальных устройствах снять actual UA из Remnawave logs / backend access logs.

После этого допускаются SRR:

```json
{
  "name": "HAPP Premium Smart RU Xray JSON",
  "enabled": true,
  "operator": "AND",
  "conditions": [
    {"headerName":"user-agent","operator":"CONTAINS","value":"Happ","caseSensitive":false}
  ],
  "responseType": "XRAY_JSON",
  "responseModifications": {
    "subscriptionTemplate": "Default Xray JSON",
    "applyHeadersToEnd": true,
    "headers": [
      {"key":"x-cybervpn-client","value":"happ"}
    ]
  }
}
```

Для INCY аналогично, но только после подтверждения UA:

```json
{
  "name": "INCY Premium Smart RU Xray JSON",
  "enabled": true,
  "operator": "AND",
  "conditions": [
    {"headerName":"user-agent","operator":"CONTAINS","value":"INCY","caseSensitive":false}
  ],
  "responseType": "XRAY_JSON",
  "responseModifications": {
    "subscriptionTemplate": "Default Xray JSON",
    "applyHeadersToEnd": true,
    "headers": [
      {"key":"x-cybervpn-client","value":"incy"}
    ]
  }
}
```

Важно: SRR идут сверху вниз и могут override-ить External Squad. Поэтому не создавать SRR для Mihomo User-Agent, если они ломают `CyberVPN Premium Smart RU` MIHOMO template.

---

## 9. Node Plugins: Torrent/TOR/SMTP abuse

### 9.1. Plugin config

Обновить `CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION`:

```json
{
  "ingressFilter": {
    "enabled": false,
    "blockedIps": []
  },
  "egressFilter": {
    "enabled": true,
    "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"],
    "blockedPorts": [25, 465, 587]
  },
  "torrentBlocker": {
    "enabled": true,
    "ignoreLists": {
      "ip": [],
      "userId": []
    },
    "blockDuration": 86400
  },
  "connectionDrop": {
    "enabled": false,
    "whitelistIps": []
  },
  "sharedLists": [
    {"name": "ext:tor-exit-nodes", "type": "ipList", "items": []},
    {"name": "ext:tor-relays", "type": "ipList", "items": []}
  ]
}
```

P0: Torrent Blocker + SMTP ports.
P1: наполнить TOR lists через updater. До наполнения TOR egress block считается placeholder.

### 9.2. Torrent Blocker requirements

Во всех inbound, доступных Premium Smart RU, должен быть включен sniffing:

```json
"sniffing": {
  "enabled": true,
  "destOverride": ["http", "tls", "quic"]
}
```

Без этого Torrent Blocker не сможет определять bittorrent.

### 9.3. Abuse webhook

Проверить `/webhooks/remnawave`:

```text
scope = torrent_blocker
event = torrent_blocker.report
```

MVP-политика:

```env
REMNAWAVE_ABUSE_AUTO_DISABLE_ENABLED=false
REMNAWAVE_ABUSE_TORRENT_DISABLE_AFTER=2
REMNAWAVE_ABUSE_TORRENT_WINDOW_HOURS=24
```

На P0 только логируем и уведомляем админа. Auto-disable включать после 3-5 дней наблюдения.

---

## 10. Применение к invite `LU7QQTQZHG`

### 10.1. Тест активации

Создать disposable test user и активировать:

```text
Invite code: LU7QQTQZHG
```

Проверить в CyberVPN DB:

```sql
select
  s.subscription_key,
  s.status,
  p.plan_code,
  s.expires_at,
  s.device_limit,
  s.traffic_limit_bytes,
  s.traffic_limit_strategy
from customer_subscriptions s
join subscription_plans p on p.id = s.plan_id
where p.plan_code = 'premium_smart_ru'
order by s.created_at desc
limit 5;
```

Ожидаемо:

```text
plan_code = premium_smart_ru
status = active
expires_at = lifetime sentinel / configured lifetime mode
device_limit = 5
traffic_limit_strategy = NO_RESET / fair_use
```

Проверить Remnawave user:

```text
external_squad_uuid = CYBERVPN_PREMIUM_SMART_RU
active_internal_squads contains CYBERVPN_PREMIUM_SMART_RU_NODES
status = ACTIVE
hwid_device_limit = 5
```

### 10.2. Не ломать существующую campaign

Не менять:

```text
campaign_key
root invite-code
child invite policy
multi_use policy
lifetime grant logic
```

Меняем только VPN delivery/Remnawave assignment/template/squad/plugin/XHTTP behavior для `premium_smart_ru`.

---

## 11. Subscription smoke tests

### 11.1. Mihomo / Clash Meta

```bash
SUB_URL="https://cyber-vpn.org/api/sub/<short_uuid>"
curl -sS -A "ClashMetaForAndroid/2.11.0" "$SUB_URL" -o /tmp/cybervpn-smart.yaml

grep -F "CyberVPN Premium Smart RU" /tmp/cybervpn-smart.yaml
grep -F "bind-address: 127.0.0.1" /tmp/cybervpn-smart.yaml
grep -F "🇩🇪 DE Auto" /tmp/cybervpn-smart.yaml
grep -F "🇳🇱 NL Auto" /tmp/cybervpn-smart.yaml
grep -F "🇷🇺 RU Sites" /tmp/cybervpn-smart.yaml
grep -F "🇷🇺 Moscow Auto" /tmp/cybervpn-smart.yaml
grep -F "🇷🇺 SPB Auto" /tmp/cybervpn-smart.yaml
grep -F "MATCH,🌍 World / EU" /tmp/cybervpn-smart.yaml
```

Ожидаемые route checks в клиенте:

| Сервис | Ожидаемый маршрут |
|---|---|
| `2ip.io`, `ipwho.is` | `🌍 World / EU -> 🇩🇪 DE Auto` |
| `google.com` | `🌍 World / EU -> 🇩🇪 DE Auto` |
| `youtube.com` | `📺 YouTube -> 🌍 World / EU -> 🇩🇪 DE Auto` |
| `discord.com` | `💬 Discord -> 🌍 World / EU -> 🇩🇪 DE Auto` |
| `github.com` | `👨‍💻 Dev Services -> 🌍 World / EU` |
| `openai.com`, `chatgpt.com` | `🤖 AI -> 🌍 World / EU` |
| `gosuslugi.ru` | `🇷🇺 RU Sites -> ⚡ RU Auto` |
| `nalog.gov.ru` | `🇷🇺 RU Sites -> ⚡ RU Auto` |
| `yandex.ru`, `market.yandex.ru` | `🇷🇺 RU Sites -> ⚡ RU Auto` |
| `ozon.ru`, `wildberries.ru` | `🇷🇺 RU Sites -> ⚡ RU Auto` |
| torrent process / tracker | `🧲 Torrents -> REJECT` |
| `.onion`, `torproject.org` | `⛔ BLOCK -> REJECT` |

### 11.2. HAPP headers

```bash
curl -i -A "Happ/2.0" "$SUB_URL" -o /tmp/happ-response.txt
sed -n '1,80p' /tmp/happ-response.txt
```

Проверить headers:

```bash
grep -Ei '^profile-title:|^profile-update-interval:|^support-url:|^profile-web-page-url:|^subscription-userinfo:|^announce:|^routing:' /tmp/happ-response.txt
```

Acceptance:

```text
subscription-userinfo есть
profile-title есть
support-url есть
announce есть, если настроен happAnnounce
xhttp присутствует в body, если responseType XRAY_JSON/Xray-compatible
```

### 11.3. INCY headers

Сначала снять реальный UA из приложения. Пока smoke:

```bash
curl -i -A "INCY/1.0" "$SUB_URL" -o /tmp/incy-response.txt
sed -n '1,80p' /tmp/incy-response.txt
```

Проверить:

```bash
grep -Ei '^profile-title:|^profile-update-interval:|^support-url:|^profile-web-page-url:|^subscription-userinfo:' /tmp/incy-response.txt
grep -Ei 'xhttp|reality|vless|8443' /tmp/incy-response.txt
```

---

## 12. Production rollout sequence

### Шаг 1. Commit файлов

```text
scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml
scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
docs/plans/CyberVPN_Premium_Smart_RU_Hardened_Rollout_TZ_2026_07_09.md
```

### Шаг 2. Backend/env

Обновить secrets/env:

```env
REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID=<from seed>
REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID=<from seed>
REMNAWAVE_SMART_RU_PLAN_CODES=premium_smart_ru
REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME=CyberVPN Premium Smart RU
REMNAWAVE_FEATURE_XHTTP_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_MIHOMO_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=premium_smart_ru
REMNAWAVE_FEATURE_XHTTP_ALLOWED_PLAN_CODES=premium_smart_ru
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=false
```

### Шаг 3. Deploy nodes

```bash
ansible-playbook -i infra/ansible/inventories/production/hosts.yml infra/ansible/playbooks/remnawave-edge.yml --limit remnawave_edge_production
```

### Шаг 4. Apply Remnawave seed

```bash
psql "$REMNAWAVE_DATABASE_URL" -f scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

### Шаг 5. Restart backend

```bash
docker compose up -d cybervpn-backend
```

или текущим production deploy script.

### Шаг 6. Smoke disposable user

1. Создать disposable user через invite `LU7QQTQZHG`.
2. Проверить backend subscription/access state.
3. Скачать Mihomo subscription.
4. Скачать HAPP/INCY subscription.
5. Проверить XHTTP.
6. Удалить/disable disposable user после теста.

---

## 13. Тесты в repo

Запустить минимум:

```bash
cd backend
python -m pytest \
  tests/security/test_stage1_paid_provisioning.py \
  tests/security/test_stage1_admin_manual_subscription_ops.py \
  tests/unit/application/use_cases/customer_subscriptions/test_service_access.py \
  tests/integration/test_growth_code_registry.py
```

Если включен VPN tester:

```bash
python -m pytest backend/tests -k "vpn_testing or premium_smart_ru or remnawave_assignment"
```

Проверить dry-run suite:

```text
backend/src/application/vpn_testing/suites/premium_smart_ru_v1.yaml
backend/src/application/vpn_testing/generated_subscription_checker.py
```

Добавить новые assertions:

```text
- expected groups include: 🇩🇪 DE Auto, 🇳🇱 NL Auto, 🇷🇺 RU Sites, 🧲 Torrents
- requires_xhttp=true для premium_smart_ru
- external/internal squad UUID present
- subscription-userinfo header present in raw subscription smoke
```

---

## 14. Acceptance checklist

### Template

- [ ] `cybervpn-premium-smart-ru-de-primary-hardened.yaml` добавлен в repo.
- [ ] Canonical `cybervpn-premium-smart-ru.yaml` заменен hardened-содержимым.
- [ ] YAML parse OK.
- [ ] `mihomo -t` OK.
- [ ] В generated Mihomo есть `🌍 World / EU`, `🇩🇪 DE Auto`, `🇳🇱 NL Auto`, `🇷🇺 RU Sites`, `🇷🇺 Moscow Auto`, `🇷🇺 SPB Auto`.
- [ ] Default route `MATCH,🌍 World / EU`.
- [ ] `🧲 Torrents` содержит только `REJECT`.

### Servers

- [ ] 4 production hosts в inventory соответствуют IP и remarks.
- [ ] На всех нодах `remnawave/node:2.8.0`.
- [ ] На всех нодах `NET_ADMIN`.
- [ ] `nft --version` OK.
- [ ] Remnawave Panel видит все 4 ноды connected/enabled.

### Squads / Remnawave

- [ ] `CYBERVPN_PREMIUM_SMART_RU_NODES` содержит нужные inbounds.
- [ ] `CYBERVPN_PREMIUM_SMART_RU` override-ит `MIHOMO -> CyberVPN Premium Smart RU`.
- [ ] Seed возвращает `plugin_assigned_node_count=4`.
- [ ] User `premium_smart_ru` получает external squad и internal squad.

### Existing invite/tariff

- [ ] `LU7QQTQZHG` активирует `premium_smart_ru`.
- [ ] `premium_smart_ru_lifetime_multi_root_2026_06_30` не пересоздана и не сломана.
- [ ] Lifetime/device limit/child invite logic сохранились.
- [ ] Новый пользователь после invite получает hardened Remnawave delivery.

### XHTTP

- [ ] `REMNAWAVE_FEATURE_XHTTP_ENABLED=true`.
- [ ] `REMNAWAVE_FEATURE_XHTTP_MIHOMO_ENABLED=true`.
- [ ] `VLESS_XHTTP_REALITY_8443` доступен Premium Smart RU internal squad.
- [ ] HAPP/INCY/Xray-compatible subscription содержит xhttp.
- [ ] Реальное подключение через XHTTP проходит.
- [ ] Stable fallback Reality TCP остаётся.

### HAPP / INCY info

- [ ] `subscription-userinfo` есть.
- [ ] `download` увеличивается после тестового трафика.
- [ ] `expire=0` для lifetime или корректный lifetime sentinel.
- [ ] `profile-title` отображает `CyberVPN Premium Smart RU`.
- [ ] `support-url` есть.
- [ ] `profile-web-page-url` есть.
- [ ] `announce` есть для HAPP/совместимых клиентов.
- [ ] Реальные UA HAPP/INCY зафиксированы в evidence.

### Abuse

- [ ] Torrent client-side -> `REJECT`.
- [ ] Torrent Blocker enabled на всех 4 нодах.
- [ ] SMTP ports `[25,465,587]` заблокированы через Egress Filter.
- [ ] TOR lists placeholder не выдаётся за полноценную TOR-блокировку.
- [ ] План TOR updater вынесен в P1.

---

## 15. Rollback

### Rollback template

1. Вернуть предыдущий `scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml`.
2. Перезапустить `seed-cybervpn-premium-smart-ru.sql` со старым YAML.
3. Обновить подписку в клиенте.

### Rollback XHTTP

```env
REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=canary
# или
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true
```

Перезапустить backend, проверить fallback Reality TCP.

### Rollback plugins

В Remnawave Node Plugin временно:

```json
{
  "torrentBlocker": {"enabled": false},
  "egressFilter": {"enabled": false}
}
```

Если nftables table зависла:

```bash
nft list tables | grep remnanode
# reset только по runbook/через Remnawave Executor, не вручную вслепую
```

---

## 16. Evidence, который нужно сохранить после внедрения

Создать файл:

```text
docs/evidence/releases/<date>-premium-smart-ru-hardened-rollout.md
```

Вставить туда:

```text
- git commit hash
- Remnawave version /api/system/metadata
- Remnawave Node image per host
- node connected=true table
- template uuid/name/type
- external_squad_uuid
- internal_squad_uuid
- plugin uuid/name/config redacted
- plugin_assigned_node_count
- disposable user uuid redacted
- generated Mihomo group grep output
- HAPP/INCY response headers redacted
- xhttp link fingerprint, не raw link
- route smoke table
- rollback target
```

---

## 17. Что НЕ делать в этом релизе

- Не создавать новый публичный тариф.
- Не менять root invite-code `LU7QQTQZHG`.
- Не ломать existing campaign/child invite policy.
- Не включать auto-disable abuse без canary-наблюдения.
- Не обещать полную TOR-блокировку, пока нет updater для TOR IP lists.
- Не добавлять широкие SRR для всех User-Agent, которые могут переопределить Mihomo template.
- Не выключать учет трафика на Unlimited тарифе.

---

## 18. Быстрый финальный порядок выполнения

```text
1. Commit hardened YAML.
2. Replace canonical Smart RU YAML.
3. Update seed SQL inline YAML + plugin blockedPorts [25,465,587].
4. Deploy/verify 4 edge nodes.
5. Run Remnawave seed.
6. Put external/internal squad UUIDs into production env.
7. Enable XHTTP flags for premium_smart_ru.
8. Restart backend.
9. Activate disposable user via LU7QQTQZHG.
10. Check Remnawave user squads.
11. Fetch Mihomo subscription and test routes.
12. Fetch HAPP/INCY subscription and check headers/XHTTP.
13. Check Torrent Blocker plugin assigned to all nodes.
14. Save evidence.
15. Only after smoke: allow real users to refresh subscription.
```
