# Техническое задание: CyberVPN Premium Smart RU

**Версия ТЗ:** 1.0
**Дата:** 2026-06-28
**Цель:** внедрить premium smart-routing профиль CyberVPN на базе Remnawave/Mihomo для схемы DE/NL/RU, настроить Remnawave template, squads, тариф, серверы и node-level abuse protection.

---

## 1. Целевая серверная топология

### 1.1. VPN-ноды

| Локация | Роль | Пропускная способность | Рекомендуемый remark в Remnawave |
|---|---:|---:|---|
| Germany / DE | основной EU-контур | 25 Gbit/s | `🇩🇪 DE Frankfurt 01 25G` |
| Netherlands / NL | резервный/дополнительный EU-контур | 10 Gbit/s | `🇳🇱 NL Amsterdam 01 10G` |
| Russia / Moscow | RU-контур | 25 Gbit/s | `🇷🇺 RU Moscow 01 25G` |
| Russia / Saint Petersburg | RU-контур | 25 Gbit/s | `🇷🇺 RU SPB 01 25G` |

### 1.2. Логика маршрутизации

1. Обычный non-RU трафик идёт через EU-контур: DE/NL.
2. Российские сервисы идут через RU-контур: Москва/Санкт-Петербург.
3. Ресурсы, заблокированные или нестабильные из РФ, идут через EU-контур даже при `.ru` доменах.
4. YouTube, Discord, Telegram, AI, GitHub и Dev-сервисы имеют отдельные selectors.
5. Реклама, трекеры, Windows telemetry, Torrent и TOR блокируются на уровне клиентского шаблона.
6. Torrent/TOR дополнительно ограничиваются на уровне Remnawave Node Plugins / server egress policy.

---

## 2. Новый Mihomo template

### 2.1. Template metadata

| Поле | Значение |
|---|---|
| Template type | `MIHOMO` |
| Template name | `CyberVPN Premium Smart RU` |
| Source file | `scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml` |
| Назначение | Premium smart-routing профиль для DE/NL/RU инфраструктуры |

### 2.2. Требования к содержанию шаблона

Шаблон должен включать:

- TUN mode.
- DNS hijack.
- Fake-IP DNS.
- Sniffer HTTP/TLS/QUIC.
- EU selectors: `🌍 World / EU`, `⚡ EU Auto`, `🇩🇪 DE Auto`, `🇳🇱 NL Auto`.
- RU selectors: `🇷🇺 RU Sites`, `⚡ RU Auto`, `🇷🇺 Moscow Auto`, `🇷🇺 SPB Auto`.
- Service selectors: YouTube, Discord, Telegram, Messengers, AI, Dev Services, Games, Speedtest.
- Client-side adblock: `oisd_big`, `ads-all`, `win-spy`.
- Client-side torrent block: torrent clients/trackers/websites -> `🧲 Torrents`, где default = `REJECT`.
- Client-side TOR best-effort block: `.onion`, `torproject`, `tor2web`, process-name regex.
- Default rule: `MATCH,🌍 World / EU`.

### 2.3. Обязательное правило по именам нод

В Remnawave remarks должны содержать location keywords, которые используются в Mihomo `filter`:

```text
DE: 🇩🇪, DE, Germany, Deutschland, Frankfurt, FRA
NL: 🇳🇱, NL, Netherlands, Amsterdam, AMS
RU Moscow: 🇷🇺, RU, Russia, Moscow, Москва, MSK, MOW
RU SPB: 🇷🇺, RU, Russia, SPB, Санкт, Петербург, Saint Petersburg, LED
```

Если naming convention меняется, необходимо обновить `filter` и `exclude-filter` в `proxy-groups` шаблона.

### 2.4. Приёмочные критерии шаблона

После загрузки шаблона подписка Mihomo должна содержать:

```powershell
$SubUrl = "https://cyber-vpn.org/api/sub/<short_uuid>"
$Ua = "ClashMetaForAndroid/2.11.0"

curl.exe -A $Ua $SubUrl -o cybervpn-premium-smart-ru.yaml

Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "CyberVPN Premium Smart RU"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🌍 World / EU"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇩🇪 DE Auto"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇳🇱 NL Auto"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇷🇺 RU Sites"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇷🇺 Moscow Auto"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇷🇺 SPB Auto"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "oisd_big"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "ads-all"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "tor-inline"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "MATCH,🌍 World / EU"
```

---

## 3. Remnawave squads

### 3.1. Internal squad

Создать или обновить internal squad:

```text
Name: CYBERVPN_PREMIUM_SMART_RU_NODES
Purpose: ноды для Premium Smart RU подписок
Nodes:
  - 🇩🇪 DE Frankfurt 01 25G
  - 🇳🇱 NL Amsterdam 01 10G
  - 🇷🇺 RU Moscow 01 25G
  - 🇷🇺 RU SPB 01 25G
```

Все пользователи тарифа `CyberVPN Premium Smart RU` должны получать этот internal squad.

### 3.2. External squad

Создать external squad:

```text
Name: CYBERVPN_PREMIUM_SMART_RU
Purpose: template override для Premium Smart RU пользователей
Template override:
  MIHOMO -> CyberVPN Premium Smart RU
```

### 3.3. Backend settings

Добавить новые настройки в `backend/src/config/settings.py`:

```python
remnawave_smart_ru_external_squad_uuid: str = ""
remnawave_smart_ru_plan_codes: str = "premium_smart_ru"
remnawave_smart_ru_subscription_template_name: str = "CyberVPN Premium Smart RU"
```

Для обратной совместимости допускается временно использовать существующие настройки:

```text
REMNAWAVE_RU_BUNDLE_EXTERNAL_SQUAD_UUID
REMNAWAVE_RU_BUNDLE_PLAN_CODES
REMNAWAVE_RU_BUNDLE_SUBSCRIPTION_TEMPLATE_NAME
```

Но целевое состояние — переименование `ru_bundle` в `smart_ru`, чтобы код отражал реальную бизнес-логику.

### 3.4. Backend resolver

Создать новый модуль:

```text
backend/src/infrastructure/remnawave/smart_ru_bundle.py
```

Функции:

```python
def is_smart_ru_plan(plan_code: str | None) -> bool: ...
def resolve_smart_ru_external_squad_uuid(plan_code: str | None) -> str | None: ...
```

Заменить использование старого resolver в:

```text
backend/src/infrastructure/remnawave/stage1_paid_gateway.py
backend/src/infrastructure/remnawave/stage1_manual_subscription_gateway.py
```

---

## 4. Тариф CyberVPN Premium Smart RU

### 4.1. Новый plan code

Добавить в `PlanCode`:

```python
PREMIUM_SMART_RU = "premium_smart_ru"
```

### 4.2. Seed pricing catalog

В `backend/src/application/services/pricing_catalog_seed.py` добавить новую тарифную семью.

Рекомендуемый MVP-вариант:

```python
PlanCode.PREMIUM_SMART_RU.value: {
    "display_name": "Premium Smart RU",
    "catalog_visibility": CatalogVisibility.HIDDEN.value,
    "device_limit": 5,
    "sale_channels": ADMIN_ONLY_CHANNELS,
    "traffic_policy": {
        "mode": "fair_use",
        "display_label": "Unlimited",
        "enforcement_profile": "premium_smart_ru",
    },
    "connection_modes": ["standard", "stealth", "smart_routing"],
    "server_pool": ["premium_smart_ru"],
    "support_sla": SupportSLA.PRIORITY.value,
    "dedicated_ip": {"included": 0, "eligible": True},
    "features": {
        "marketing_badge": "Smart Routing",
        "audience": "premium_ru_users",
        "market": "RU/EU",
        "smart_routing": True,
        "adblock": True,
        "tracker_block": True,
        "tor_policy": "blocked",
        "torrent_policy": "blocked",
        "remnawave_external_squad": "CYBERVPN_PREMIUM_SMART_RU",
        "remnawave_subscription_template": "CyberVPN Premium Smart RU",
        "remnawave_subscription_template_scope": "mihomo_only",
    },
    "trial_eligible": False,
    "is_active": True,
}
```

Цены на 30/90/180/365 дней оставить как `TODO_OWNER_APPROVAL` до утверждения владельцем. До утверждения цен тариф держать `hidden` и `ADMIN_ONLY_CHANNELS`.

### 4.3. Тесты

Обновить:

```text
backend/tests/unit/pricing/test_pricing_catalog_seed.py
backend/tests/security/test_stage1_paid_provisioning.py
backend/tests/security/test_stage1_admin_manual_subscription_ops.py
```

Минимальные assertions:

- `premium_smart_ru` присутствует в preview seed.
- `premium_smart_ru` назначает external squad `CYBERVPN_PREMIUM_SMART_RU`.
- Paid provisioning передаёт `external_squad_uuid` для `premium_smart_ru`.
- Manual provisioning передаёт `external_squad_uuid` для `premium_smart_ru`.
- Existing RU plans `ru_start`, `ru_basic` не ломаются до миграции/решения владельца.

---

## 5. Remnawave Node Plugins и запрет abuse-трафика

### 5.1. Preflight на каждом VPN-сервере

На каждом из 4 серверов проверить:

```bash
uname -r
nft --version
docker --version
docker compose version
```

Требования:

- Linux kernel `>= 5.7`.
- `nftables` установлен и доступен.
- Remnawave Node `>= 2.7.0`.
- Xray-Core `>= 26.3.27` для Torrent Blocker.
- Docker compose service содержит `cap_add: [NET_ADMIN]`.

### 5.2. Ansible / Docker Compose

В текущей Ansible role уже должен быть `NET_ADMIN` для edge node. Проверить, что production inventory не переопределяет это пустым значением.

Для real edge nodes использовать:

```yaml
remnawave_edge_image: remnawave/node:2.7.4
remnawave_edge_cap_add:
  - NET_ADMIN
remnawave_edge_network_mode: host
remnawave_edge_ulimits_nofile_soft: 1048576
remnawave_edge_ulimits_nofile_hard: 1048576
```

Для local/lab compose profile `vpn-node-local` добавить `cap_add: [NET_ADMIN]`, если планируется тестировать Node Plugins локально.

### 5.3. Node Plugins config

Базовая конфигурация для каждой production-ноды:

```json
{
  "ingressFilter": {
    "enabled": false,
    "blockedIps": []
  },
  "egressFilter": {
    "enabled": true,
    "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"],
    "blockedPorts": []
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
    {
      "name": "ext:tor-exit-nodes",
      "type": "ipList",
      "items": []
    },
    {
      "name": "ext:tor-relays",
      "type": "ipList",
      "items": []
    }
  ]
}
```

### 5.4. Torrent policy

Torrent должен блокироваться в три слоя:

1. Mihomo-шаблон: torrent clients/trackers/websites -> `REJECT`.
2. Remnawave Node Plugin: `torrentBlocker.enabled = true`.
3. CyberVPN webhook policy: обработка `torrent_blocker.report`.

Важно: Torrent Blocker не является абсолютной DPI-блокировкой всего torrent-трафика. Он обнаруживает часть torrent-трафика через Xray-Core, отправляет report в Remnawave Node, после чего Node блокирует IP-адрес нарушителя через nftables на заданный период. Поэтому клиентский template block и abuse webhook policy обязательны как дополнительные слои.

### 5.5. TOR policy

В Remnawave Node Plugins нет отдельного native `Tor Blocker`. TOR блокировать так:

1. Mihomo-шаблон: `.onion`, `torproject`, `tor2web`, Tor process names -> `REJECT`.
2. Server-side egress policy: `egressFilter.blockedIps` через `ext:tor-exit-nodes` и `ext:tor-relays`.
3. Отдельная automation-задача CyberVPN должна регулярно обновлять `sharedLists.items` для Tor IP lists.

До реализации automation допускается запустить без Tor IP list, но тогда TOR запрет считается неполным.

### 5.6. Webhook abuse handling

Текущий endpoint `/webhooks/remnawave` должен быть расширен:

- Принимать и валидировать `torrent_blocker.report`.
- Сохранять abuse event в БД.
- Отправлять admin notification.
- Опционально отключать пользователя в Remnawave после N нарушений.

Рекомендуемый безопасный MVP:

```text
REMNAWAVE_ABUSE_AUTO_DISABLE_ENABLED=false
REMNAWAVE_ABUSE_TORRENT_DISABLE_AFTER=2
REMNAWAVE_ABUSE_TORRENT_WINDOW_HOURS=24
```

Пока auto-disable выключен, система только логирует и уведомляет администратора.

---

## 6. Серверные настройки производительности

### 6.1. Docker / ulimits

Для всех edge nodes:

```yaml
ulimits:
  nofile:
    soft: 1048576
    hard: 1048576
```

### 6.2. Sysctl baseline

Применять осторожно после staging-теста:

```bash
cat >/etc/sysctl.d/99-cybervpn-edge.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
net.core.somaxconn=65535
net.ipv4.tcp_fastopen=3
net.ipv4.ip_local_port_range=1024 65535
net.ipv4.tcp_tw_reuse=1
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 134217728
net.ipv4.tcp_wmem=4096 65536 134217728
EOF
sysctl --system
```

Не применять вслепую на production без сравнения latency/packet loss до и после.

---

## 7. Deployment plan

### 7.1. Подготовка

1. Добавить файл шаблона:

```text
scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml
```

2. Добавить seed/upsert script:

```text
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

3. Добавить backend settings для smart RU.
4. Добавить новую тарифную семью в pricing seed.
5. Обновить paid/manual provisioning resolver.
6. Обновить тесты.

### 7.2. Staging rollout

1. Загрузить template в Remnawave staging.
2. Создать internal squad с 4 staging/mock nodes или production-like nodes.
3. Создать external squad `CYBERVPN_PREMIUM_SMART_RU`.
4. Создать тестового пользователя с `premium_smart_ru`.
5. Проверить Mihomo subscription.
6. Проверить routing в клиенте.
7. Проверить Node Plugins preflight.
8. Проверить Torrent Blocker report webhook на тестовом controlled кейсе.

### 7.3. Production rollout

1. Обновить edge nodes через Ansible.
2. Проверить `NET_ADMIN`, `nftables`, kernel, node health.
3. Создать/обновить template в Remnawave production.
4. Создать/обновить squads.
5. Внести UUID external squad в secrets/env.
6. Пересоздать backend container.
7. Выполнить smoke-проверку подписки.
8. Включить тариф сначала как hidden/admin-only.
9. После QA открыть публичные sale channels.

---

## 8. Acceptance checklist

### 8.1. Template

- [ ] YAML парсится без ошибок.
- [ ] В подписке есть `CyberVPN Premium Smart RU`.
- [ ] В подписке есть DE/NL/RU selectors.
- [ ] `MATCH` отправляет default traffic в `🌍 World / EU`.
- [ ] RU domains/IP идут в `🇷🇺 RU Sites`.
- [ ] `ru-bundle`, `refilter`, `ru-inside` идут в `🌍 World / EU`.
- [ ] Torrent default = `REJECT`.
- [ ] TOR best-effort rules присутствуют.

### 8.2. Remnawave

- [ ] Internal squad содержит 4 production-ноды.
- [ ] External squad содержит template override `MIHOMO -> CyberVPN Premium Smart RU`.
- [ ] User с тарифом получает correct external squad UUID.
- [ ] User получает все 4 ноды в подписке.

### 8.3. Node Plugins

- [ ] На всех 4 серверах есть `cap_add: NET_ADMIN`.
- [ ] `nft --version` работает.
- [ ] Kernel `>= 5.7`.
- [ ] Torrent Blocker enabled.
- [ ] Egress Filter enabled для Tor lists.
- [ ] `torrent_blocker.report` приходит в backend webhook.

### 8.4. Tariff

- [ ] `premium_smart_ru` добавлен в PlanCode.
- [ ] `premium_smart_ru_30/90/180/365` появляются в pricing seed preview.
- [ ] Тариф hidden/admin-only до утверждения цен.
- [ ] Paid provisioning назначает `CYBERVPN_PREMIUM_SMART_RU`.
- [ ] Manual provisioning назначает `CYBERVPN_PREMIUM_SMART_RU`.

---

## 9. Команды проверки

### 9.1. Backend tests

```bash
cd backend
python -m pytest \
  tests/unit/pricing/test_pricing_catalog_seed.py \
  tests/security/test_stage1_paid_provisioning.py \
  tests/security/test_stage1_admin_manual_subscription_ops.py \
  tests/integration/api/v1/webhooks/test_remnawave_webhook.py
```

### 9.2. Pricing preview

```bash
cd backend
python scripts/seed_pricing_catalog.py --json
```

### 9.3. Mihomo subscription smoke на Windows

```powershell
$SubUrl = "https://cyber-vpn.org/api/sub/<short_uuid>"
$Ua = "ClashMetaForAndroid/2.11.0"

curl.exe -A $Ua $SubUrl -o cybervpn-premium-smart-ru.yaml

Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "CyberVPN Premium Smart RU"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇩🇪 DE Auto"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇳🇱 NL Auto"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "🇷🇺 RU Sites"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "tor-inline"
Select-String -Path cybervpn-premium-smart-ru.yaml -Pattern "MATCH,🌍 World / EU"
```

---

## 10. Важные ограничения

1. Mihomo smart-routing работает только в клиентах, которые реально используют Mihomo/Clash Meta profile.
2. Для XRAY_BASE64/Happ/Singbox нужны отдельные шаблоны или отдельная логика.
3. Remnawave Mihomo generator может не отдавать `xhttp`, если upstream generator помечает transport как unsupported. Не смешивать внедрение Smart RU и XHTTP в один релиз.
4. TOR запрет без регулярного обновления Tor IP lists неполный.
5. Torrent Blocker не является 100% DPI-защитой, нужен layered abuse policy.
