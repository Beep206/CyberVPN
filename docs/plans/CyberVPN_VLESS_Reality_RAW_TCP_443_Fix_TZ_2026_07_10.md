# Техническое задание для Codex App
# Диагностика и исправление VLESS Reality RAW/TCP 443 в CyberVPN Premium Smart RU

**Проект:** `Beep206/CyberVPN`
**Remnawave:** `2.8.0`
**Целевой тариф:** `premium_smart_ru`
**Целевой шаблон:** `CyberVPN Premium Smart RU`
**Canonical Mihomo YAML:** `scripts/remnawave/templates/cybervpn-premium-smart-ru.yaml`
**Hardened YAML:** `scripts/remnawave/templates/cybervpn-premium-smart-ru-de-primary-hardened.yaml`
**Дата ТЗ:** `2026-07-10`

---

## 1. Симптом

В production работают подключения:

```text
VLESS + XHTTP + REALITY + 8443
```

но не работают подключения:

```text
VLESS + RAW/TCP + REALITY + 443
```

Важно: оба варианта используют протокол `VLESS`. Отличается транспорт:

```text
XHTTP-профиль       -> VLESS / xhttp / reality / 8443
Обычный VLESS       -> VLESS / raw|tcp / reality / 443 / xtls-rprx-vision
```

Нельзя считать задачу решённой только потому, что XHTTP подключается.

---

## 2. Цель

Нужно:

1. точно определить, на каком слое ломается `VLESS_REALITY_443`;
2. исправить серверный Remnawave Config Profile/inbound, Hosts или delivery logic;
3. сохранить рабочий XHTTP;
4. доказать, что все четыре RAW/TCP Reality-профиля реально подключаются;
5. усилить VPN Tester, чтобы он больше не давал `pass`, когда XHTTP есть, а обычный VLESS сломан;
6. зафиксировать безопасное evidence без UUID пользователей, private keys, subscription URLs и других секретов.

---

## 3. Текущая целевая топология

| Локация | Node remark в Remnawave | Public host | Public IP | RAW/TCP | XHTTP |
|---|---|---|---:|---:|---:|
| Германия | `🇩🇪 DE Frankfurt 01 25G` | `de-3.cyber-vpn.org` | `138.124.115.206` | `443/tcp` | `8443/tcp` |
| Нидерланды | `🇳🇱 NL Amsterdam 01 10G` | `nl-4.cyber-vpn.org` | `138.16.140.44` | `443/tcp` | `8443/tcp` |
| Москва | `🇷🇺 RU Moscow 01 25G` | `ru-msk-3.cyber-vpn.org` | `178.159.94.225` | `443/tcp` | `8443/tcp` |
| Санкт-Петербург | `🇷🇺 RU SPB 01 25G` | `ru-spb-3.cyber-vpn.org` | `193.233.91.99` | `443/tcp` | `8443/tcp` |

Целевые inbounds:

```text
VLESS_REALITY_443
VLESS_XHTTP_REALITY_8443
```

Целевой internal squad:

```text
CYBERVPN_PREMIUM_SMART_RU_NODES
```

Целевой external squad:

```text
CYBERVPN_PREMIUM_SMART_RU
```

---

## 4. Важное архитектурное ограничение

Hardened Mihomo template отвечает за клиентскую маршрутизацию:

```text
обычный интернет -> DE
RU-сервисы       -> RU
NL                -> резерв
```

Он **не создаёт серверный Xray inbound** и не задаёт Reality private key.

Не изменять smart-routing YAML без доказательства, что ошибка находится именно в нём.

Текущий seed:

```text
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

находит уже существующие inbounds по тегам и привязывает их к nodes/squad/hosts. Поэтому существование строки `VLESS_REALITY_443` в БД ещё не доказывает корректность:

```text
network
security
port
target
serverNames
privateKey
shortIds
flow
```

---

## 5. Правила безопасности

Codex обязан:

- не выводить в консоль и evidence:
  - VLESS UUID;
  - Reality private key;
  - полный Reality public key;
  - raw subscription URL;
  - short UUID пользователя;
  - API tokens;
  - invite secrets;
- не коммитить production secrets;
- перед изменением Remnawave DB сделать backup;
- не генерировать новый Reality key pair без явной необходимости;
- не перезаписывать рабочий XHTTP inbound;
- не отключать XHTTP feature flags;
- не выполнять массовое перепровиживание пользователей до canary smoke;
- не использовать старого пользователя как единственное доказательство после изменения inbound.

---

# P0. Диагностика до изменений

## 6. Снять безопасный baseline

Создать evidence-файл:

```text
docs/evidence/releases/<date>-premium-smart-ru-vless-reality-443-fix.md
```

Зафиксировать:

```text
git commit SHA
Remnawave image/version
Remnawave Node image/version
Xray version каждой ноды
список node names без secrets
connected/disabled state
активные inbound tags
количество Hosts RAW и XHTTP
доступность 443/8443
результат generated subscription inspection
```

Не сохранять полные connection links.

---

## 7. Определить: RAW/TCP отсутствует или не подключается

Создать скрипт:

```text
scripts/testing/diagnose-premium-smart-ru-generated-sub.py
```

Скрипт принимает путь к generated Mihomo YAML и печатает только безопасные поля.

Пример реализации:

```python
#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: diagnose-premium-smart-ru-generated-sub.py <generated.yaml>")
        return 2

    path = Path(sys.argv[1])
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise SystemExit("generated config root is not an object")

    proxies = config.get("proxies") or []
    raw_count = 0
    xhttp_count = 0
    invalid_raw: list[str] = []
    invalid_xhttp: list[str] = []

    for item in proxies:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() != "vless":
            continue

        name = str(item.get("name") or "")
        network = str(item.get("network") or "tcp").lower()
        port = int(item.get("port") or 0)
        reality = item.get("reality-opts")
        reality = reality if isinstance(reality, dict) else {}

        safe = {
            "name": name,
            "server": item.get("server"),
            "port": port,
            "network": network,
            "tls": item.get("tls"),
            "flow": item.get("flow"),
            "has_servername": bool(item.get("servername") or item.get("sni")),
            "has_public_key": bool(reality.get("public-key")),
            "has_short_id_field": "short-id" in reality,
        }
        print(safe)

        if network in {"", "tcp", "raw"}:
            raw_count += 1
            valid = (
                port == 443
                and item.get("tls") is True
                and item.get("flow") == "xtls-rprx-vision"
                and safe["has_servername"]
                and safe["has_public_key"]
                and safe["has_short_id_field"]
            )
            if not valid:
                invalid_raw.append(name)
        elif network == "xhttp":
            xhttp_count += 1
            valid = (
                port == 8443
                and item.get("tls") is True
                and safe["has_servername"]
                and safe["has_public_key"]
                and safe["has_short_id_field"]
            )
            if not valid:
                invalid_xhttp.append(name)

    summary = {
        "vless_reality_raw_tcp_count": raw_count,
        "vless_reality_xhttp_count": xhttp_count,
        "invalid_raw_tcp": invalid_raw,
        "invalid_xhttp": invalid_xhttp,
    }
    print(summary)

    if raw_count != 4:
        return 10
    if xhttp_count != 4:
        return 11
    if invalid_raw:
        return 12
    if invalid_xhttp:
        return 13
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Скачать реальную подписку canary-пользователя:

```bash
curl -fsSL \
  -A 'ClashMetaForAndroid/2.11.0' \
  "$SUB_URL" \
  -o /tmp/cybervpn-premium-smart-ru.generated.yaml

python3 scripts/testing/diagnose-premium-smart-ru-generated-sub.py \
  /tmp/cybervpn-premium-smart-ru.generated.yaml
```

Ожидаемо:

```text
vless_reality_raw_tcp_count = 4
vless_reality_xhttp_count   = 4
invalid_raw_tcp             = []
invalid_xhttp               = []
```

### Интерпретация

Если:

```text
RAW/TCP = 0
XHTTP = 4
```

проверять:

```text
Hosts
Host exclusions
Internal Squad
Node inbound links
subscription response rules
exclude_from_subscription_types
```

Если:

```text
RAW/TCP = 4
XHTTP = 4
```

но RAW не подключается, проверять:

```text
Reality inbound
SNI
target
Reality key pair
shortId
flow
443/tcp
DNS/Cloudflare
синхронизацию пользователя
```

---

# P0. Проверка и исправление Remnawave Config Profile

## 8. Добавить безопасную SQL-диагностику inbound

Создать:

```text
scripts/remnawave/diagnose-premium-smart-ru-inbounds.sql
```

Содержимое:

```sql
select
    cpi.tag,
    cpi.type,
    cpi.network,
    cpi.security,
    cpi.port,
    cpi.profile_uuid,

    cpi.raw_inbound -> 'settings' ->> 'decryption'
        as decryption,

    cpi.raw_inbound -> 'settings' ->> 'flow'
        as explicit_flow,

    cpi.raw_inbound -> 'streamSettings' ->> 'network'
        as stream_network,

    cpi.raw_inbound -> 'streamSettings' ->> 'security'
        as stream_security,

    jsonb_array_length(
        coalesce(
            cpi.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                -> 'serverNames',
            '[]'::jsonb
        )
    ) as server_names_count,

    jsonb_array_length(
        coalesce(
            cpi.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                -> 'shortIds',
            '[]'::jsonb
        )
    ) as short_ids_count,

    case
        when coalesce(
            cpi.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                ->> 'target',
            cpi.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                ->> 'dest',
            ''
        ) <> ''
        then true
        else false
    end as reality_target_present,

    case
        when length(
            coalesce(
                cpi.raw_inbound
                    -> 'streamSettings'
                    -> 'realitySettings'
                    ->> 'privateKey',
                ''
            )
        ) > 0
        then true
        else false
    end as reality_private_key_present

from config_profile_inbounds cpi
where cpi.tag in (
    'VLESS_REALITY_443',
    'VLESS_XHTTP_REALITY_8443'
)
order by cpi.tag;
```

Скрипт не должен печатать private key, public key или shortIds.

---

## 9. Целевой контракт `VLESS_REALITY_443`

Inbound должен удовлетворять:

```text
tag              = VLESS_REALITY_443
protocol/type    = vless
port             = 443
network          = raw или tcp
security         = reality
decryption       = none
flow             = xtls-rprx-vision
serverNames      = непустой массив
shortIds         = непустой массив
target/dest      = непустое значение с :443
privateKey       = присутствует
sniffing         = enabled
destOverride     содержит http,tls,quic
```

Рекомендуемая форма:

```json
{
  "tag": "VLESS_REALITY_443",
  "listen": "0.0.0.0",
  "port": 443,
  "protocol": "vless",
  "settings": {
    "clients": [],
    "decryption": "none",
    "flow": "xtls-rprx-vision"
  },
  "streamSettings": {
    "network": "raw",
    "security": "reality",
    "realitySettings": {
      "show": false,
      "target": "<REALITY_TARGET>:443",
      "xver": 0,
      "serverNames": [
        "<REALITY_TARGET>"
      ],
      "privateKey": "<EXISTING_OR_ROTATED_PRIVATE_KEY>",
      "shortIds": [
        "<VALID_HEX_SHORT_ID>"
      ]
    }
  },
  "sniffing": {
    "enabled": true,
    "destOverride": [
      "http",
      "tls",
      "quic"
    ],
    "routeOnly": true
  }
}
```

Не помещать реальные key values в Git.

---

## 10. Reality SNI contract

Текущие Smart RU Hosts используют:

```text
sni = null
security_layer = DEFAULT
override_sni_from_address = false
```

Поэтому Remnawave должен получить SNI из:

```text
VLESS_REALITY_443.streamSettings.realitySettings.serverNames[0]
```

Требования:

- `serverNames[0]` не пустой;
- он соответствует Reality target;
- он не должен автоматически заменяться на:
  - `de-3.cyber-vpn.org`;
  - `nl-4.cyber-vpn.org`;
  - `ru-msk-3.cyber-vpn.org`;
  - `ru-spb-3.cyber-vpn.org`;
- Host-level SNI не задавать без причины;
- если Host-level SNI используется, он обязан входить в inbound `serverNames`.

---

## 11. Добавить fail-fast validation в seed

Обновить:

```text
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

Перед созданием links/hosts добавить validation block:

```sql
do $premium_smart_ru_inbound_validation$
declare
    v_raw record;
    v_xhttp record;
begin
    select *
    into v_raw
    from config_profile_inbounds
    where tag = 'VLESS_REALITY_443';

    if v_raw.uuid is null then
        raise exception 'VLESS_REALITY_443 inbound is missing';
    end if;

    if v_raw.type <> 'vless' then
        raise exception 'VLESS_REALITY_443 must use type=vless';
    end if;

    if coalesce(v_raw.network, '') not in ('raw', 'tcp') then
        raise exception 'VLESS_REALITY_443 must use raw/tcp network';
    end if;

    if coalesce(v_raw.security, '') <> 'reality' then
        raise exception 'VLESS_REALITY_443 must use reality security';
    end if;

    if v_raw.port <> 443 then
        raise exception 'VLESS_REALITY_443 must use port 443';
    end if;

    if coalesce(
        v_raw.raw_inbound -> 'settings' ->> 'decryption',
        ''
    ) <> 'none' then
        raise exception 'VLESS_REALITY_443 must use decryption=none';
    end if;

    if jsonb_array_length(
        coalesce(
            v_raw.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                -> 'serverNames',
            '[]'::jsonb
        )
    ) = 0 then
        raise exception 'VLESS_REALITY_443 serverNames is empty';
    end if;

    if jsonb_array_length(
        coalesce(
            v_raw.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                -> 'shortIds',
            '[]'::jsonb
        )
    ) = 0 then
        raise exception 'VLESS_REALITY_443 shortIds is empty';
    end if;

    if length(
        coalesce(
            v_raw.raw_inbound
                -> 'streamSettings'
                -> 'realitySettings'
                ->> 'privateKey',
            ''
        )
    ) = 0 then
        raise exception 'VLESS_REALITY_443 privateKey is empty';
    end if;

    if coalesce(
        v_raw.raw_inbound
            -> 'streamSettings'
            -> 'realitySettings'
            ->> 'target',
        v_raw.raw_inbound
            -> 'streamSettings'
            -> 'realitySettings'
            ->> 'dest',
        ''
    ) = '' then
        raise exception 'VLESS_REALITY_443 Reality target is empty';
    end if;

    select *
    into v_xhttp
    from config_profile_inbounds
    where tag = 'VLESS_XHTTP_REALITY_8443';

    if v_xhttp.uuid is null then
        raise exception 'VLESS_XHTTP_REALITY_8443 inbound is missing';
    end if;

    if v_xhttp.type <> 'vless'
       or coalesce(v_xhttp.network, '') <> 'xhttp'
       or coalesce(v_xhttp.security, '') <> 'reality'
       or v_xhttp.port <> 8443 then
        raise exception 'VLESS_XHTTP_REALITY_8443 contract is invalid';
    end if;
end
$premium_smart_ru_inbound_validation$;
```

Validation должна работать до любых destructive changes.

---

# P0. DNS и сеть

## 12. Проверить public DNS

Проверить:

```bash
dig +short A de-3.cyber-vpn.org
dig +short A nl-4.cyber-vpn.org
dig +short A ru-msk-3.cyber-vpn.org
dig +short A ru-spb-3.cyber-vpn.org

dig +short AAAA de-3.cyber-vpn.org
dig +short AAAA nl-4.cyber-vpn.org
dig +short AAAA ru-msk-3.cyber-vpn.org
dig +short AAAA ru-spb-3.cyber-vpn.org
```

Ожидаемые A records:

```text
de-3.cyber-vpn.org      -> 138.124.115.206
nl-4.cyber-vpn.org      -> 138.16.140.44
ru-msk-3.cyber-vpn.org  -> 178.159.94.225
ru-spb-3.cyber-vpn.org  -> 193.233.91.99
```

Требования:

- node records должны быть `DNS only`;
- не проксировать VLESS Reality через Cloudflare HTTP proxy;
- удалить ошибочный `AAAA`, если на ноде нет рабочего IPv6;
- TTL на время исправления можно временно уменьшить;
- после стабилизации вернуть нормальный TTL.

---

## 13. Проверить внешний доступ к портам

Проверка должна выполняться с внешней машины, не с самой ноды:

```bash
for endpoint in \
  138.124.115.206:443 \
  138.124.115.206:8443 \
  138.16.140.44:443 \
  138.16.140.44:8443 \
  178.159.94.225:443 \
  178.159.94.225:8443 \
  193.233.91.99:443 \
  193.233.91.99:8443
do
  host="${endpoint%:*}"
  port="${endpoint#*:}"
  nc -vz -w 5 "$host" "$port"
done
```

На каждой ноде:

```bash
ss -lntp | grep -E ':(443|8443)\b'
ufw status verbose
nft list ruleset
docker logs --since 10m remnanode
```

Ожидаемо:

```text
443/tcp  LISTEN
8443/tcp LISTEN
```

---

# P0. Применение Config Profile и синхронизация

## 14. Повторно применить Config Profile

После исправления inbound:

1. открыть Remnawave `Config Profiles`;
2. сохранить профиль через штатный editor/API;
3. убедиться, что Xray validation проходит;
4. на каждой из четырёх нод:
   - выбрать правильный Config Profile;
   - включить `VLESS_REALITY_443`;
   - включить `VLESS_XHTTP_REALITY_8443`;
5. применить изменения;
6. перезапустить ноды штатным Remnawave action;
7. проверить, что Xray запущен без ошибок;
8. проверить listeners `443` и `8443`.

Нельзя считать SQL links достаточным доказательством. Нода должна реально получить обновлённый Xray config.

---

## 15. Создать нового canary-пользователя

После изменения inbound:

- создать нового disposable пользователя;
- назначить:
  - internal squad `CYBERVPN_PREMIUM_SMART_RU_NODES`;
  - external squad `CYBERVPN_PREMIUM_SMART_RU`;
- убедиться, что пользователь активен;
- скачать subscription;
- после теста удалить disposable user.

Дополнительно обновить или перепровижить один существующий `premium_smart_ru` user через штатный application/API path.

Не использовать только старую cached subscription.

---

# P0. Исправление VPN Tester

## 16. Проблема текущего VPN Tester

Сейчас tester считает:

```text
proxy_count
xhttp_proxy_count
```

но не доказывает наличие корректных:

```text
VLESS Reality RAW/TCP 443
```

Следовательно, тест может пройти, когда:

```text
XHTTP = 4
RAW/TCP = 0 или RAW/TCP сломан
```

---

## 17. Усилить generated subscription summary

Файл:

```text
backend/src/application/vpn_testing/generated_subscription_checker.py
```

Добавить helpers:

```python
def _is_xhttp_reality_vless(proxy: Mapping[str, Any]) -> bool:
    reality = proxy.get("reality-opts")
    reality = reality if isinstance(reality, Mapping) else {}
    return (
        str(proxy.get("type") or "").lower() == "vless"
        and str(proxy.get("network") or "").lower() == "xhttp"
        and int(proxy.get("port") or 0) == 8443
        and proxy.get("tls") is True
        and bool(proxy.get("servername") or proxy.get("sni"))
        and bool(reality.get("public-key"))
        and "short-id" in reality
    )


def _is_raw_tcp_reality_vless(proxy: Mapping[str, Any]) -> bool:
    reality = proxy.get("reality-opts")
    reality = reality if isinstance(reality, Mapping) else {}
    network = str(proxy.get("network") or "tcp").lower()
    return (
        str(proxy.get("type") or "").lower() == "vless"
        and network in {"", "tcp", "raw"}
        and int(proxy.get("port") or 0) == 443
        and proxy.get("tls") is True
        and str(proxy.get("flow") or "") == "xtls-rprx-vision"
        and bool(proxy.get("servername") or proxy.get("sni"))
        and bool(reality.get("public-key"))
        and "short-id" in reality
    )
```

В summary считать:

```python
xhttp_proxy_count = sum(
    1 for proxy in proxies
    if _is_xhttp_reality_vless(proxy)
)

vless_reality_tcp_proxy_count = sum(
    1 for proxy in proxies
    if _is_raw_tcp_reality_vless(proxy)
)
```

Возвращать:

```python
{
    ...
    "xhttp_proxy_count": xhttp_proxy_count,
    "vless_reality_tcp_proxy_count": vless_reality_tcp_proxy_count,
}
```

---

## 18. Добавить обязательные checks

Для `premium_smart_ru`:

```python
raw_vless_ok = (
    artifact_summary["vless_reality_tcp_proxy_count"] == 4
)

checks.append(
    {
        "check_key": "generated_subscription.vless_reality_raw_tcp",
        "check_name": "Generated VLESS Reality RAW/TCP profiles",
        "category": "generated_subscription",
        "status": "pass" if raw_vless_ok else "fail",
        "severity": "error",
        "target": target,
        "safe_summary": (
            "Generated subscription contains four valid VLESS Reality RAW/TCP profiles"
            if raw_vless_ok
            else "Generated subscription does not contain four valid VLESS Reality RAW/TCP profiles"
        ),
        "details": {
            "expected_count": 4,
            "actual_count": artifact_summary[
                "vless_reality_tcp_proxy_count"
            ],
            "links_redacted": True,
        },
        "duration_ms": 0,
    }
)
```

Усилить XHTTP check:

```python
xhttp_ok = artifact_summary["xhttp_proxy_count"] == 4
```

а не:

```python
xhttp_proxy_count > 0
```

---

## 19. Добавить node/inbound contract checks

VPN Tester должен проверять через Remnawave API/DB-safe adapter:

```text
4 connected enabled nodes
каждая нода имеет VLESS_REALITY_443
каждая нода имеет VLESS_XHTTP_REALITY_8443
4 RAW/TCP Hosts enabled
4 XHTTP Hosts enabled
RAW/TCP Hosts не excluded from MIHOMO/XRAY_BASE64
XHTTP Hosts не excluded from требуемых форматов
```

Не возвращать raw inbound secrets в API response/evidence.

Добавить check keys:

```text
remnawave.inbounds.vless_reality_raw_tcp
remnawave.inbounds.vless_reality_xhttp
remnawave.hosts.transport_matrix
```

---

## 20. Runtime checks

Contract check не доказывает handshake.

Runtime Agent должен тестировать отдельно восемь профилей:

```text
DE Reality 443
DE XHTTP 8443

NL Reality 443
NL XHTTP 8443

RU Moscow Reality 443
RU Moscow XHTTP 8443

RU SPB Reality 443
RU SPB XHTTP 8443
```

Для каждого сохранить безопасный результат:

```text
node/location
transport
dns_ok
tcp_connect_ok
proxy_handshake_ok
http_probe_ok
exit_country
latency_ms
safe_error_class
```

Не сохранять raw links.

Test mode:

```text
proxy-only
```

Можно не включать TUN для первого P0.

Release Gate должен блокировать rollout, если любой обязательный transport отсутствует или не подключается.

---

# P0. Тесты

## 21. Unit tests

Обновить/добавить:

```text
backend/tests/unit/application/vpn_testing/test_generated_subscription_checker.py
```

Cases:

```text
4 RAW + 4 XHTTP -> pass
0 RAW + 4 XHTTP -> fail RAW check
3 RAW + 4 XHTTP -> fail RAW check
4 RAW + 3 XHTTP -> fail XHTTP check
RAW без flow -> fail
RAW без servername -> fail
RAW без public-key -> fail
RAW без short-id field -> fail
RAW на неправильном port -> fail
XHTTP на неправильном port -> fail
```

---

## 22. Seed contract tests

Обновить:

```text
backend/tests/contract/remnawave/test_premium_smart_ru_hardened_rollout_seed.py
```

Проверить, что seed содержит fail-fast assertions для:

```text
VLESS_REALITY_443 type=vless
network raw/tcp
security=reality
port=443
decryption=none
serverNames non-empty
shortIds non-empty
privateKey present
target/dest present

VLESS_XHTTP_REALITY_8443:
type=vless
network=xhttp
security=reality
port=8443
```

---

## 23. Integration tests

Прогнать:

```bash
cd backend

python -m pytest \
  tests/integration/remnawave/test_remnawave_2_8_contracts.py \
  tests/integration/remnawave/test_remnawave_xhttp_subscription.py \
  tests/contract/remnawave/test_premium_smart_ru_hardened_rollout_seed.py \
  tests/unit/application/vpn_testing/test_generated_subscription_checker.py \
  tests/unit/application/vpn_testing/test_vpn_tester_service.py \
  -q --no-cov
```

Также:

```bash
python -m ruff check \
  src/application/vpn_testing \
  tests/unit/application/vpn_testing \
  tests/contract/remnawave
```

---

# P0. Проверка Mihomo

## 24. Проверить generated YAML core-ом

```bash
mihomo -t -f /tmp/cybervpn-premium-smart-ru.generated.yaml
```

Ожидаемо:

```text
exit code = 0
```

Проверять нужно именно generated subscription, а не только template fixture.

---

# P0. Реальный клиентский smoke

## 25. Проверить каждый профиль вручную

В Mihomo/Clash Meta клиенте временно выбирать конкретные proxy nodes, а не только Auto-группы.

Проверить:

```text
🇩🇪 DE ... Reality 443
🇩🇪 DE ... XHTTP Reality 8443

🇳🇱 NL ... Reality 443
🇳🇱 NL ... XHTTP Reality 8443

🇷🇺 RU Moscow ... Reality 443
🇷🇺 RU Moscow ... XHTTP Reality 8443

🇷🇺 RU SPB ... Reality 443
🇷🇺 RU SPB ... XHTTP Reality 8443
```

Почему: Auto selector может выбрать рабочий XHTTP и скрыть, что RAW/TCP сломан.

Для каждого профиля проверить:

```text
подключение устанавливается
открывается HTTPS сайт
exit IP соответствует локации
DNS работает
нет immediate disconnect
```

---

## 26. Проверить smart routing после transport fix

После доказательства 8/8 transport profiles:

```text
ipwho.is              -> DE
google.com            -> DE
youtube.com           -> DE
github.com            -> DE
openai.com            -> DE

gosuslugi.ru          -> RU
nalog.gov.ru          -> RU
market.yandex.ru      -> RU
ozon.ru               -> RU
wildberries.ru        -> RU
sber.ru               -> RU
tbank.ru              -> RU
```

Исправление VLESS не должно менять routing behavior hardened template.

---

# P1. Улучшение автоматизации

## 27. Canonical Config Profile representation

После P0 рекомендуется добавить безопасный canonical source Config Profile без secrets:

```text
scripts/remnawave/config-profiles/premium-smart-ru-profile.template.json
```

Вместо секретов использовать placeholders:

```text
${REALITY_PRIVATE_KEY}
${REALITY_SHORT_ID}
${REALITY_TARGET}
```

Создать render/apply tool, который:

- получает secrets только из runtime secret store;
- валидирует JSON;
- делает backup текущего Config Profile;
- применяет через Remnawave API;
- не пишет rendered config в Git;
- выводит только redacted summary.

Это P1, не блокирует срочный P0 fix.

---

# 28. Rollback

Перед изменениями сохранить:

```text
Remnawave PostgreSQL dump
config_profiles row
config_profile_inbounds rows
hosts rows
internal_squad_inbounds rows
config_profile_inbounds_to_nodes rows
hosts_to_nodes rows
node state
```

Rollback:

1. восстановить предыдущий Config Profile;
2. повторно применить его к нодам;
3. перезапустить ноды;
4. восстановить previous seed/template только при необходимости;
5. проверить XHTTP;
6. проверить старого canary user;
7. не откатывать unrelated backend changes.

---

# 29. Acceptance criteria

Задача закрыта только если выполнено всё:

## Generated subscription

- [ ] Generated Mihomo YAML парсится.
- [ ] `mihomo -t` завершён с code `0`.
- [ ] В generated subscription есть ровно 4 valid RAW/TCP Reality profiles.
- [ ] В generated subscription есть ровно 4 valid XHTTP Reality profiles.
- [ ] Каждый RAW/TCP proxy использует `443`.
- [ ] Каждый RAW/TCP proxy использует `flow=xtls-rprx-vision`.
- [ ] Каждый RAW/TCP proxy содержит non-empty `servername`.
- [ ] Каждый RAW/TCP proxy содержит `reality-opts.public-key`.
- [ ] Каждый RAW/TCP proxy содержит `reality-opts.short-id`.
- [ ] Каждый XHTTP proxy использует `8443`.

## Remnawave

- [ ] `VLESS_REALITY_443` валиден.
- [ ] `VLESS_XHTTP_REALITY_8443` валиден.
- [ ] Оба inbounds активны на всех четырёх нодах.
- [ ] Оба inbounds входят в `CYBERVPN_PREMIUM_SMART_RU_NODES`.
- [ ] Созданы и enabled 8 Hosts.
- [ ] 4 RAW Hosts привязаны к правильным nodes.
- [ ] 4 XHTTP Hosts привязаны к правильным nodes.
- [ ] Новый canary user получает оба транспорта.

## Network

- [ ] A records указывают на правильные public IP.
- [ ] Node DNS records работают в режиме DNS-only.
- [ ] Нет ошибочных AAAA.
- [ ] `443/tcp` доступен на всех четырёх нодах.
- [ ] `8443/tcp` доступен на всех четырёх нодах.
- [ ] На каждой ноде Xray слушает оба порта.

## Real connectivity

- [ ] DE RAW/TCP работает.
- [ ] NL RAW/TCP работает.
- [ ] Moscow RAW/TCP работает.
- [ ] SPB RAW/TCP работает.
- [ ] DE XHTTP продолжает работать.
- [ ] NL XHTTP продолжает работать.
- [ ] Moscow XHTTP продолжает работать.
- [ ] SPB XHTTP продолжает работать.

## VPN Tester

- [ ] Tester считает RAW/TCP отдельно от XHTTP.
- [ ] `RAW/TCP count != 4` даёт `fail`.
- [ ] `XHTTP count != 4` даёт `fail`.
- [ ] Release Gate блокируется при missing transport.
- [ ] Contract run проходит.
- [ ] Runtime run доказывает handshake каждого обязательного профиля.
- [ ] Evidence не содержит secrets.

## Smart routing

- [ ] Default traffic остаётся через DE.
- [ ] RU services идут через RU.
- [ ] NL остаётся резервом.
- [ ] Hardened adblock/torrent/TOR policies не сломаны.

---

# 30. Итоговые deliverables от Codex

Codex должен предоставить:

1. список найденных root causes;
2. список изменённых файлов;
3. diff без secrets;
4. результаты тестов;
5. redacted generated subscription summary;
6. redacted Remnawave inbound summary;
7. результаты 443/8443 reachability;
8. результаты 8 transport smokes;
9. VPN Tester run IDs и statuses;
10. evidence-файл;
11. rollback instructions;
12. явный итог:

```text
VLESS Reality RAW/TCP 443: PASS/FAIL
VLESS Reality XHTTP 8443: PASS/FAIL
Premium Smart RU routing: PASS/FAIL
Release Gate: OPEN/BLOCKED
```

---

# 31. No-go

Codex не должен объявлять задачу выполненной, если:

```text
XHTTP работает, но RAW/TCP не проверен;
в YAML есть 4 RAW profiles, но реальный handshake не проверен;
443 открыт, но Reality handshake не доказан;
тестер проверил Auto group, но не конкретные transports;
проверен только один сервер из четырёх;
использовался только старый cached user;
в evidence попали connection links или secrets.
```
