-- Seed CyberVPN Premium Smart RU Remnawave Mihomo template, squads, and abuse plugin.
--
-- Usage:
--   psql "$REMNAWAVE_DATABASE_URL" -f scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
--
-- Configure backend with the returned external_squad_uuid:
--   REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID=<external_squad_uuid>

begin;

with template_upsert as (
    insert into subscription_templates (
        template_type,
        name,
        template_yaml,
        template_json,
        view_position
    )
    values (
        'MIHOMO',
        'CyberVPN Premium Smart RU',
        $cybervpn_premium_smart_ru_yaml$
# ==================================================================================================
# CyberVPN Premium Smart RU
# Hardened review build for Remnawave 2.8.0 / Mihomo
# Гибридный Mihomo / Clash Meta шаблон для Remnawave
# --------------------------------------------------------------------------------------------------
# Топология под этот шаблон:
#   - 🇩🇪 DE Frankfurt / Germany: 25 Gbit/s — основной быстрый EU-контур
#   - 🇳🇱 NL Amsterdam / Netherlands: 10 Gbit/s — резервный/дополнительный EU-контур
#   - 🇷🇺 RU Moscow: 25 Gbit/s — российский контур для RU-сервисов
#   - 🇷🇺 RU Saint Petersburg: 25 Gbit/s — российский контур для RU-сервисов
#
# Идея:
#   - весь обычный non-RU трафик по умолчанию идет через DE 25G; NL 10G — резерв/ручной выбор;
#   - российские сервисы, банки, маркетплейсы, Яндекс, Госуслуги и RU IP идут через РФ-ноды;
#   - ресурсы, заблокированные/недоступные из РФ, идут через DE/NL, даже если домен .ru;
#   - Torrent/TOR режутся на уровне клиентского профиля, а также должны дублироваться Node Plugins на сервере;
#   - реклама, трекеры и Windows telemetry блокируются;
#   - YouTube / Discord / Telegram / AI / Dev вынесены в отдельные селекторы.
#
# ВАЖНО ПО ИМЕНАМ НОД В REMNAWAVE:
#   Чтобы фильтры групп работали стабильно, называй ноды примерно так:
#     🇩🇪 DE Frankfurt 01 25G
#     🇳🇱 NL Amsterdam 01 10G
#     🇷🇺 RU Moscow 01 25G
#     🇷🇺 RU SPB 01 25G
#
# Если названия другие — поправь filter/exclude-filter в proxy-groups.
# ==================================================================================================

remnawave:
  includeHiddenHosts: false

mixed-port: 7890
allow-lan: false
bind-address: 127.0.0.1
mode: rule
log-level: info
ipv6: false
tcp-concurrent: true
unified-delay: true
keep-alive-interval: 30
global-client-fingerprint: chrome
enable-process: true
find-process-mode: always
external-controller: 127.0.0.1:9090

profile:
  store-selected: true
  store-fake-ip: true

sniffer:
  enable: true
  force-dns-mapping: true
  parse-pure-ip: true
  override-destination: false
  sniff:
    HTTP:
      ports:
        - 80
        - 8080-8880
    TLS:
      ports:
        - 443
        - 8443
    QUIC:
      ports:
        - 443
  skip-dst-address:
    - 0.0.0.0/8
    - 10.0.0.0/8
    - 100.64.0.0/10
    - 127.0.0.0/8
    - 169.254.0.0/16
    - 172.16.0.0/12
    - 192.0.0.0/24
    - 192.0.2.0/24
    - 192.88.99.0/24
    - 192.168.0.0/16
    - 198.51.100.0/24
    - 203.0.113.0/24
    - 224.0.0.0/3
    - ::/127
    - fc00::/7
    - fe80::/10
    - ff00::/8

tun:
  enable: true
  # gvisor — максимально совместимый вариант. Для отдельных десктоп-клиентов можно тестировать stack: system/mixed.
  stack: gvisor
  auto-route: true
  auto-detect-interface: true
  strict-route: true
  dns-hijack:
    - any:53
    - tcp://any:53
  route-exclude-address:
    # Служебные/локальные сети не загоняем в TUN.
    # 198.18.0.0/15 НЕ добавляем сюда, потому что это fake-ip диапазон Mihomo.
    - 0.0.0.0/8
    - 10.0.0.0/8
    - 100.64.0.0/10
    - 127.0.0.0/8
    - 169.254.0.0/16
    - 172.16.0.0/12
    - 192.0.0.0/24
    - 192.0.2.0/24
    - 192.88.99.0/24
    - 192.168.0.0/16
    - 198.51.100.0/24
    - 203.0.113.0/24
    - 224.0.0.0/3
    - ::/127
    - fc00::/7
    - fe80::/10
    - ff00::/8

dns:
  enable: true
  cache-algorithm: arc
  prefer-h3: false
  use-hosts: true
  use-system-hosts: true
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - rule-set:geosite-private
    - "+.lan"
    - "+.local"
    - "+.localhost"
    - "+.msftconnecttest.com"
    - "+.msftncsi.com"
    - "stun.*.*"
    - "stun.*.*.*"
    - "time.windows.com"
    - "time.nist.gov"
    - "time.apple.com"
    - "time1.apple.com"
    - "time2.apple.com"
    - "time3.apple.com"
    - "time4.apple.com"
    - "time5.apple.com"
    - "time6.apple.com"
    - "time7.apple.com"
    - "time.google.com"
    - "time1.google.com"
    - "time2.google.com"
    - "time3.google.com"
    - "time4.google.com"
    - "pool.ntp.org"
    - "ntp.ubuntu.com"
    - "+.xboxlive.com"
    - "*.*.stun.playstation.net"
    - "xbox.*.*.microsoft.com"
    - "speedtest.cros.wr.pvp.net"
  default-nameserver:
    # DNS для резолва самих DNS-серверов.
    - https://77.88.8.8/dns-query
    - https://8.8.8.8/dns-query
    - https://1.1.1.1/dns-query
  proxy-server-nameserver:
    # DNS для доменов самих прокси-нод Remnawave.
    - https://8.8.8.8/dns-query#🌍 World / EU
    - https://1.1.1.1/dns-query#🌍 World / EU
    - https://77.88.8.8/dns-query#🇷🇺 RU Sites
  direct-nameserver:
    - system
    - https://77.88.8.8/dns-query
    - https://8.8.8.8/dns-query
  nameserver:
    # Default DNS идет через быстрый EU контур, потому что default routing тоже EU.
    - https://8.8.8.8/dns-query#🌍 World / EU
    - https://1.1.1.1/dns-query#🌍 World / EU
    - https://94.140.14.14/dns-query#🌍 World / EU
  nameserver-policy:
    "rule-set:geosite-private":
      - system
    # DNS-level adblock: домены рекламы/tor получают NXDOMAIN.
    # Если у редкого приложения ломается аналитика/логин — можно удалить этот policy-блок, rules ниже всё равно REJECT-ят рекламу.
    "rule-set:oisd_big,ads-all,win-spy,tor-inline":
      - rcode://name_error
    # Rule-set файлы и GitHub всегда через EU, иначе в РФ часто ловятся проблемы с доступом.
    "raw.githubusercontent.com,objects.githubusercontent.com,github.com,githubusercontent.com,cdn.jsdelivr.net":
      - https://8.8.8.8/dns-query#🌍 World / EU
      - https://1.1.1.1/dns-query#🌍 World / EU
    # Российские сервисы резолвим через RU-контур.
    "rule-set:ru-services-inline,geosite-ru":
      - https://77.88.8.8/dns-query#🇷🇺 RU Sites
      - https://8.8.8.8/dns-query#🇷🇺 RU Sites
    # Заблокированное из РФ и глобальные сервисы резолвим через EU.
    "rule-set:ru-eu-exceptions,manual-eu-inline,ru-inside,ru-bundle,refilter_domains,youtube,discord_domains,telegram-domains,additional-telegram-domains,whatsapp,ai,google-deepmind,github,speedtest-net":
      - https://8.8.8.8/dns-query#🌍 World / EU
      - https://1.1.1.1/dns-query#🌍 World / EU

proxies:
  # DNS-OUT используется правилом DST-PORT,53,DNS-OUT.
  - name: DNS-OUT
    type: dns

proxy-groups:
  - name: 🌍 World / EU
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Global.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      # DE — основной маршрут по умолчанию; NL — резерв/ручной выбор.
      - 🇩🇪 DE Auto
      - ⚡ EU Auto
      - 🇳🇱 NL Auto
      - 🇷🇺 RU Sites
      - DIRECT

  - name: 🇷🇺 RU Sites
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Russia.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - ⚡ RU Auto
      - 🇷🇺 Moscow Auto
      - 🇷🇺 SPB Auto
      - 🌍 World / EU
      - DIRECT

  - name: 📺 YouTube
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/YouTube.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇩🇪 DE Auto
      - 🇳🇱 NL Auto
      - 🇷🇺 RU Sites

  - name: 💬 Discord
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Discord.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇩🇪 DE Auto
      - 🇳🇱 NL Auto
      - DIRECT

  - name: ➤ Telegram
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Telegram.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇷🇺 RU Sites
      - DIRECT

  - name: 💬 Messengers
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Message.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇷🇺 RU Sites
      - DIRECT

  - name: 🤖 AI
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/AI.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇩🇪 DE Auto
      - 🇳🇱 NL Auto

  - name: 👨‍💻 Dev Services
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/GitHub.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇩🇪 DE Auto
      - 🇳🇱 NL Auto
      - DIRECT

  - name: 🎮 Games
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Game.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - DIRECT
      - 🌍 World / EU
      - 🇷🇺 RU Sites

  - name: 🧲 Torrents
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Download.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      # По умолчанию запрещено на клиенте; серверно дублируется Remnawave Torrent Blocker.
      - REJECT

  - name: 🧪 Speedtest
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Speedtest.png
    type: select
    remnawave:
      include-proxies: false
    proxies:
      - 🌍 World / EU
      - 🇷🇺 RU Sites
      - DIRECT

  - name: ⚡ EU Auto
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Auto.png
    type: url-test
    remnawave:
      include-proxies: false
    include-all: true
    filter: '(?i)(🇩🇪|🇳🇱|\bDE\b|\bNL\b|Germany|Deutschland|Германия|Frankfurt|FRA|Berlin|Берлин|Netherlands|Nederland|Нидерланд|Amsterdam|AMS)'
    exclude-filter: '(?i)(🇷🇺|\bRU\b|Russia|Россия|Москва|Moscow|Санкт|Петербург|Питер|SPB|DNS-OUT|DIRECT|Direct|REJECT|REJECT-DROP|COMPATIBLE)'
    url: https://www.gstatic.com/generate_204
    expected-status: 204
    interval: 300
    tolerance: 80
    lazy: true
    hidden: true

  - name: 🇳🇱 NL Auto
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Netherlands.png
    type: url-test
    remnawave:
      include-proxies: false
    include-all: true
    filter: '(?i)(🇳🇱|\bNL\b|Netherlands|Nederland|Нидерланд|Amsterdam|AMS)'
    exclude-filter: '(?i)(DNS-OUT|DIRECT|Direct|REJECT|REJECT-DROP|COMPATIBLE)'
    url: https://www.gstatic.com/generate_204
    expected-status: 204
    interval: 300
    tolerance: 80
    lazy: true
    hidden: true

  - name: 🇩🇪 DE Auto
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Germany.png
    type: url-test
    remnawave:
      include-proxies: false
    include-all: true
    filter: '(?i)(🇩🇪|\bDE\b|Germany|Deutschland|Германия|Frankfurt|FRA|Berlin|Берлин)'
    exclude-filter: '(?i)(DNS-OUT|DIRECT|Direct|REJECT|REJECT-DROP|COMPATIBLE)'
    url: https://www.gstatic.com/generate_204
    expected-status: 204
    interval: 300
    tolerance: 80
    lazy: true
    hidden: true

  - name: ⚡ RU Auto
    icon: https://cdn.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Auto.png
    type: url-test
    remnawave:
      include-proxies: false
    include-all: true
    filter: '(?i)(🇷🇺|\bRU\b|Russia|Россия|Москва|Moscow|MSK|MOW|Санкт|Петербург|Питер|SPB|LED|Saint.?Petersburg|St.?Petersburg)'
    exclude-filter: '(?i)(DNS-OUT|DIRECT|Direct|REJECT|REJECT-DROP|COMPATIBLE)'
    # Проверяем доступность RU-ноды. Для строгих клиентов можно заменить на https://www.gstatic.com/generate_204.
    url: https://ya.ru
    interval: 300
    tolerance: 120
    lazy: true
    hidden: true

  - name: 🇷🇺 Moscow Auto
    type: url-test
    remnawave:
      include-proxies: false
    include-all: true
    filter: '(?i)(Москва|Moscow|MSK|MOW)'
    exclude-filter: '(?i)(DNS-OUT|DIRECT|Direct|REJECT|REJECT-DROP|COMPATIBLE)'
    url: https://ya.ru
    interval: 300
    tolerance: 120
    lazy: true
    hidden: true

  - name: 🇷🇺 SPB Auto
    type: url-test
    remnawave:
      include-proxies: false
    include-all: true
    filter: '(?i)(Санкт|Петербург|Питер|Saint.?Petersburg|St.?Petersburg|SPB|LED)'
    exclude-filter: '(?i)(DNS-OUT|DIRECT|Direct|REJECT|REJECT-DROP|COMPATIBLE)'
    url: https://ya.ru
    interval: 300
    tolerance: 120
    lazy: true
    hidden: true


  - name: ♻️ DIRECT
    type: select
    remnawave:
      include-proxies: false
    hidden: true
    proxies:
      - DIRECT

  - name: ⛔ BLOCK
    type: select
    remnawave:
      include-proxies: false
    hidden: true
    proxies:
      - REJECT
      - REJECT-DROP

  - name: PROXY
    type: select
    remnawave:
      include-proxies: false
    hidden: true
    proxies:
      - 🌍 World / EU

rule-providers:
  geosite-private:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/private.mrs
    path: ./rule-sets/geosite-private.mrs

  private-ips:
    type: inline
    behavior: classical
    payload:
      # Не включаем 198.18.0.0/15, потому что это fake-ip диапазон Mihomo.
      - IP-CIDR,0.0.0.0/8
      - IP-CIDR,10.0.0.0/8
      - IP-CIDR,100.64.0.0/10
      - IP-CIDR,127.0.0.0/8
      - IP-CIDR,169.254.0.0/16
      - IP-CIDR,172.16.0.0/12
      - IP-CIDR,192.0.0.0/24
      - IP-CIDR,192.0.2.0/24
      - IP-CIDR,192.88.99.0/24
      - IP-CIDR,192.168.0.0/16
      - IP-CIDR,198.51.100.0/24
      - IP-CIDR,203.0.113.0/24
      - IP-CIDR,224.0.0.0/3
      - IP-CIDR,::/127
      - IP-CIDR,fc00::/7
      - IP-CIDR,fe80::/10
      - IP-CIDR,ff00::/8

  tor-inline:
    type: inline
    behavior: classical
    payload:
      - DOMAIN-SUFFIX,onion
      - DOMAIN-SUFFIX,torproject.org
      - DOMAIN-SUFFIX,torproject.net
      - DOMAIN-KEYWORD,torproject
      - DOMAIN-KEYWORD,tor2web

  quic:
    type: inline
    behavior: classical
    payload:
      # Блокируем QUIC/HTTP3 и DoQ, чтобы браузеры уходили в TCP/TLS и корректнее работали через Reality/TLS.
      - AND,((NETWORK,udp),(DST-PORT,443))
      - AND,((NETWORK,udp),(DST-PORT,853))

  oisd_big:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/oisd/big.mrs
    path: ./rule-sets/oisd_big.mrs

  ads-all:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-ads-all.mrs
    path: ./rule-sets/ads-all.mrs

  win-spy:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://cdn.jsdelivr.net/gh/hydraponique/roscomvpn-geosite/release/mihomo/win-spy.mrs
    path: ./rule-sets/win-spy.mrs

  twitch-ads:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://cdn.jsdelivr.net/gh/hydraponique/roscomvpn-geosite/release/mihomo/twitch-ads.mrs
    path: ./rule-sets/twitch-ads.mrs

  youtube:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/youtube.mrs
    path: ./rule-sets/youtube.mrs

  discord_domains:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/discord.mrs
    path: ./rule-sets/discord_domains.mrs

  discord_voiceips:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/discord-voice-ip-list.mrs
    path: ./rule-sets/discord_voiceips.mrs

  cloudflare-ips:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/cloudflare.mrs
    path: ./rule-sets/cloudflare-ips.mrs

  telegram-domains:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/telegram.mrs
    path: ./rule-sets/telegram-domains.mrs

  telegram-ips:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/telegram.mrs
    path: ./rule-sets/telegram-ips.mrs

  additional-telegram-domains:
    type: http
    behavior: classical
    format: yaml
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/Davoyan/mihomo-rule-sets/main/domains/additional-telegram-domains.yaml
    path: ./rule-sets/additional-telegram-domains.yaml

  additional-telegram-ips:
    type: http
    behavior: classical
    format: yaml
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/Davoyan/mihomo-rule-sets/main/domains/additional-telegram-ips.yaml
    path: ./rule-sets/additional-telegram-ips.yaml

  whatsapp:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/whatsapp.mrs
    path: ./rule-sets/whatsapp.mrs

  meta-ips:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/facebook.mrs
    path: ./rule-sets/meta-ips.mrs

  ai:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-ai-!cn.mrs
    path: ./rule-sets/ai.mrs

  google-deepmind:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/google-deepmind.mrs
    path: ./rule-sets/google-deepmind.mrs

  github:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://cdn.jsdelivr.net/gh/hydraponique/roscomvpn-geosite/release/mihomo/github.mrs
    path: ./rule-sets/github.mrs

  speedtest-net:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/speedtest.mrs
    path: ./rule-sets/speedtest-net.mrs

  remote-control:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-remote-control.mrs
    path: ./rule-sets/remote-control.mrs

  torrent-trackers:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/torrent-trackers.mrs
    path: ./rule-sets/torrent-trackers.mrs

  torrent-websites:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/torrent-websites.mrs
    path: ./rule-sets/torrent-websites.mrs

  torrent-clients:
    type: http
    behavior: classical
    format: yaml
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/torrent-clients.yaml
    path: ./rule-sets/torrent-clients.yaml

  games-direct:
    type: http
    behavior: classical
    format: yaml
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/games-direct.yaml
    path: ./rule-sets/games-direct.yaml

  ru-apps:
    type: http
    behavior: classical
    format: yaml
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/other/ru-app-list.yaml
    path: ./rule-sets/ru-apps.yaml

  geosite-ru:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/Davoyan/mihomo-rule-sets/main/rules/category-ru.mrs
    path: ./rule-sets/geosite-ru.mrs

  geoip-for-ru:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/Davoyan/mihomo-rule-sets/main/ip-for-ru/lists/ips-for-ru.mrs
    path: ./rule-sets/geoip-for-ru.mrs

  ru-bundle:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://cdn.jsdelivr.net/gh/legiz-ru/mihomo-rule-sets@main/ru-bundle/rule.mrs
    path: ./rule-sets/ru-bundle.mrs

  rknasnblock:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://cdn.jsdelivr.net/gh/legiz-ru/mihomo-rule-sets@main/ru-bundle/rknasnblock.mrs
    path: ./rule-sets/rknasnblock.mrs

  ru-inside:
    type: http
    behavior: classical
    format: text
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/itdoginfo/allow-domains/main/Russia/inside-clashx.lst
    path: ./rule-sets/ru-inside.lst

  refilter_domains:
    type: http
    behavior: domain
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/re-filter/domain-rule.mrs
    path: ./rule-sets/refilter_domains.mrs

  refilter_ipsum:
    type: http
    behavior: ipcidr
    format: mrs
    proxy: "🌍 World / EU"
    interval: 86400
    url: https://raw.githubusercontent.com/legiz-ru/mihomo-rule-sets/main/re-filter/ip-rule.mrs
    path: ./rule-sets/refilter_ipsum.mrs

  apps_ipcheck:
    type: inline
    behavior: classical
    payload:
      - DOMAIN,ipwho.is
      - DOMAIN,api.ip.sb
      - DOMAIN,ipapi.co
      - DOMAIN,ipinfo.io
      - DOMAIN,ip-api.com
      - DOMAIN,ident.me
      - DOMAIN,api.myip.com
      - DOMAIN,2ip.io
      - DOMAIN,2ipcore.com
      - DOMAIN,flclashx.app

  ru-eu-exceptions:
    type: inline
    behavior: classical
    payload:
      # .ru/.com ресурсы, которые часто должны идти НЕ через РФ, а через EU.
      # Список можно расширять по обращениям пользователей.
      - DOMAIN-SUFFIX,habr.com
      - DOMAIN-SUFFIX,meduza.io
      - DOMAIN-SUFFIX,theins.ru
      - DOMAIN-SUFFIX,tvrain.ru
      - DOMAIN-SUFFIX,dozhd.tv
      - DOMAIN-SUFFIX,novayagazeta.ru
      - DOMAIN-SUFFIX,moscowtimes.ru
      - DOMAIN-SUFFIX,echo.msk.ru
      - DOMAIN-SUFFIX,svoboda.org
      - DOMAIN-SUFFIX,currenttime.tv
      - DOMAIN-SUFFIX,holod.media
      - DOMAIN-SUFFIX,zona.media
      - DOMAIN-SUFFIX,ovd.info
      - DOMAIN-SUFFIX,navalny.com
      - DOMAIN-SUFFIX,bellingcat.com
      - DOMAIN-SUFFIX,proekt.media
      - DOMAIN-SUFFIX,istories.media
      - DOMAIN-SUFFIX,agents.media
      - DOMAIN-SUFFIX,verstka.media
      - DOMAIN-SUFFIX,mediazona.ca
      - DOMAIN-SUFFIX,change.org
      - DOMAIN-SUFFIX,archive.org
      - DOMAIN-SUFFIX,archive.ph
      - DOMAIN-SUFFIX,archive.is
      - DOMAIN-SUFFIX,4pda.to
      - DOMAIN-SUFFIX,4pda.ws
      - DOMAIN-SUFFIX,nnmclub.to
      - DOMAIN-SUFFIX,rutracker.org
      - DOMAIN-SUFFIX,rutor.info
      - DOMAIN-SUFFIX,kinozal.tv
      - DOMAIN-SUFFIX,libgen.is
      - DOMAIN-SUFFIX,annas-archive.org
      - DOMAIN-KEYWORD,anilibria
      - DOMAIN-KEYWORD,anidub
      - DOMAIN-KEYWORD,animego
      - DOMAIN-KEYWORD,yummyanime

  manual-eu-inline:
    type: inline
    behavior: classical
    payload:
      # Ручные global/EU исключения поверх внешних списков.
      - DOMAIN-SUFFIX,openai.com
      - DOMAIN-SUFFIX,chatgpt.com
      - DOMAIN-SUFFIX,oaistatic.com
      - DOMAIN-SUFFIX,oaiusercontent.com
      - DOMAIN-SUFFIX,anthropic.com
      - DOMAIN-SUFFIX,claude.ai
      - DOMAIN-SUFFIX,perplexity.ai
      - DOMAIN-SUFFIX,poe.com
      - DOMAIN-SUFFIX,notion.so
      - DOMAIN-SUFFIX,figma.com
      - DOMAIN-SUFFIX,canva.com
      - DOMAIN-SUFFIX,spotify.com
      - DOMAIN-SUFFIX,netflix.com
      - DOMAIN-SUFFIX,discord.com
      - DOMAIN-SUFFIX,discordapp.com
      - DOMAIN-SUFFIX,discord.gg
      - DOMAIN-SUFFIX,github.com
      - DOMAIN-SUFFIX,githubusercontent.com
      - DOMAIN-SUFFIX,githubassets.com

  ru-services-inline:
    type: inline
    behavior: classical
    payload:
      # Общие российские зоны и сервисы.
      # Исключения, которые должны идти через EU, стоят выше в rules: ru-eu-exceptions / ru-bundle / refilter.
      - DOMAIN-SUFFIX,ru
      - DOMAIN-SUFFIX,рф
      - DOMAIN-SUFFIX,xn--p1ai
      - DOMAIN-SUFFIX,su
      - DOMAIN-SUFFIX,ru.com
      - DOMAIN-SUFFIX,ru.net
      - DOMAIN-SUFFIX,mos.ru
      - DOMAIN-SUFFIX,mosreg.ru
      - DOMAIN-SUFFIX,gosuslugi.ru
      - DOMAIN-SUFFIX,gosekspertiza.ru
      - DOMAIN-SUFFIX,nalog.gov.ru
      - DOMAIN-SUFFIX,fns.ru
      - DOMAIN-SUFFIX,pfr.gov.ru
      - DOMAIN-SUFFIX,sfr.gov.ru
      - DOMAIN-SUFFIX,gibdd.ru
      - DOMAIN-SUFFIX,zakupki.gov.ru
      - DOMAIN-SUFFIX,dom.gosuslugi.ru
      - DOMAIN-SUFFIX,esia.gosuslugi.ru
      - DOMAIN-SUFFIX,yandex.ru
      - DOMAIN-SUFFIX,yandex.net
      - DOMAIN-SUFFIX,yandex.com
      - DOMAIN-SUFFIX,yastatic.net
      - DOMAIN-SUFFIX,yadi.sk
      - DOMAIN-SUFFIX,ya.ru
      - DOMAIN-SUFFIX,kinopoisk.ru
      - DOMAIN-SUFFIX,kinopoiskhd.ru
      - DOMAIN-SUFFIX,plus.yandex.ru
      - DOMAIN-SUFFIX,avito.ru
      - DOMAIN-SUFFIX,avito.st
      - DOMAIN-SUFFIX,ozon.ru
      - DOMAIN-SUFFIX,ozonusercontent.com
      - DOMAIN-SUFFIX,wildberries.ru
      - DOMAIN-SUFFIX,wb.ru
      - DOMAIN-SUFFIX,wbbasket.ru
      - DOMAIN-SUFFIX,wbstatic.net
      - DOMAIN-SUFFIX,market.yandex.ru
      - DOMAIN-SUFFIX,sbermarket.ru
      - DOMAIN-SUFFIX,megamarket.ru
      - DOMAIN-SUFFIX,lamoda.ru
      - DOMAIN-SUFFIX,detmir.ru
      - DOMAIN-SUFFIX,citilink.ru
      - DOMAIN-SUFFIX,dns-shop.ru
      - DOMAIN-SUFFIX,mvideo.ru
      - DOMAIN-SUFFIX,eldorado.ru
      - DOMAIN-SUFFIX,sberbank.ru
      - DOMAIN-SUFFIX,sber.ru
      - DOMAIN-SUFFIX,online.sberbank.ru
      - DOMAIN-SUFFIX,tinkoff.ru
      - DOMAIN-SUFFIX,tbank.ru
      - DOMAIN-SUFFIX,vtb.ru
      - DOMAIN-SUFFIX,alfabank.ru
      - DOMAIN-SUFFIX,gazprombank.ru
      - DOMAIN-SUFFIX,raiffeisen.ru
      - DOMAIN-SUFFIX,open.ru
      - DOMAIN-SUFFIX,pochtabank.ru
      - DOMAIN-SUFFIX,psbank.ru
      - DOMAIN-SUFFIX,rshb.ru
      - DOMAIN-SUFFIX,akbars.ru
      - DOMAIN-SUFFIX,moex.com
      - DOMAIN-SUFFIX,moex.ru
      - DOMAIN-SUFFIX,vk.com
      - DOMAIN-SUFFIX,vk.ru
      - DOMAIN-SUFFIX,vkvideo.ru
      - DOMAIN-SUFFIX,userapi.com
      - DOMAIN-SUFFIX,mycdn.me
      - DOMAIN-SUFFIX,ok.ru
      - DOMAIN-SUFFIX,mail.ru
      - DOMAIN-SUFFIX,imgsmail.ru
      - DOMAIN-SUFFIX,dzen.ru
      - DOMAIN-SUFFIX,zen.yandex.ru
      - DOMAIN-SUFFIX,rutube.ru
      - DOMAIN-SUFFIX,premier.one
      - DOMAIN-SUFFIX,start.ru
      - DOMAIN-SUFFIX,more.tv
      - DOMAIN-SUFFIX,ivi.ru
      - DOMAIN-SUFFIX,okko.tv
      - DOMAIN-SUFFIX,wink.ru
      - DOMAIN-SUFFIX,kion.ru
      - DOMAIN-SUFFIX,2gis.ru
      - DOMAIN-SUFFIX,2gis.com
      - DOMAIN-SUFFIX,dublgis.ru
      - DOMAIN-SUFFIX,rzd.ru
      - DOMAIN-SUFFIX,tutu.ru
      - DOMAIN-SUFFIX,aviasales.ru
      - DOMAIN-SUFFIX,cdek.ru
      - DOMAIN-SUFFIX,pochta.ru
      - DOMAIN-SUFFIX,russianpost.ru
      - DOMAIN-SUFFIX,lenta.com
      - DOMAIN-SUFFIX,lenta.ru
      - DOMAIN-SUFFIX,magnit.ru
      - DOMAIN-SUFFIX,pyaterochka.ru
      - DOMAIN-SUFFIX,perekrestok.ru
      - DOMAIN-SUFFIX,vkusvill.ru
      - DOMAIN-SUFFIX,samokat.ru
      - DOMAIN-SUFFIX,eda.yandex.ru
      - DOMAIN-SUFFIX,lavka.yandex.ru
      - DOMAIN-SUFFIX,delivery-club.ru
      - DOMAIN-SUFFIX,hh.ru
      - DOMAIN-SUFFIX,superjob.ru
      - DOMAIN-SUFFIX,banki.ru
      - DOMAIN-SUFFIX,sravni.ru
      - DOMAIN-SUFFIX,championat.com
      - DOMAIN-SUFFIX,sportbox.ru
      - DOMAIN-SUFFIX,pikabu.ru
      - DOMAIN-SUFFIX,vc.ru
      - DOMAIN-SUFFIX,dtf.ru
      - DOMAIN-SUFFIX,tjournal.ru
      - DOMAIN-SUFFIX,kaspersky.ru
      - DOMAIN-SUFFIX,kaspersky.com
      - DOMAIN-KEYWORD,yandex
      - DOMAIN-KEYWORD,avito
      - DOMAIN-KEYWORD,ozon
      - DOMAIN-KEYWORD,wildberries
      - DOMAIN-KEYWORD,gazprom
      - DOMAIN-KEYWORD,sber
      - DOMAIN-KEYWORD,tinkoff
      - DOMAIN-KEYWORD,gosslugi
      - DOMAIN-KEYWORD,gosuslugi

rules:
  # DNS hijack
  - DST-PORT,53,DNS-OUT

  # Локальные и служебные сети — всегда напрямую.
  - RULE-SET,private-ips,DIRECT,no-resolve
  - RULE-SET,geosite-private,DIRECT

  # IPv6 выключен, чтобы не было обхода/утечек мимо IPv4 routing.
  - IP-CIDR6,::/0,REJECT,no-resolve

  # VPN/mesh/remote-control приложения не должны зацикливаться через TUN.
  - PROCESS-NAME-REGEX,(?i).*tailscale.*,DIRECT
  - PROCESS-NAME-REGEX,(?i).*wireguard.*,DIRECT
  - PROCESS-NAME-REGEX,(?i).*netbird.*,DIRECT
  - PROCESS-NAME-REGEX,(?i).*zerotier.*,DIRECT
  - PROCESS-NAME-REGEX,(?i).*anydesk.*,DIRECT
  - PROCESS-NAME-REGEX,(?i).*rustdesk.*,DIRECT
  - PROCESS-NAME-REGEX,(?i).*teamviewer.*,DIRECT
  - RULE-SET,remote-control,DIRECT

  # Блокировки: реклама, трекеры, Windows telemetry.
  # Если у пользователя ломается редкий сайт/приложение — первым делом временно отключить ads-all.
  - RULE-SET,oisd_big,REJECT
  - RULE-SET,ads-all,REJECT
  - RULE-SET,win-spy,REJECT

  # QUIC / HTTP3 / DoQ block. Часто улучшает стабильность и заставляет браузеры уйти в TCP/TLS.
  - RULE-SET,quic,REJECT

  # IP-check сайты всегда через EU, чтобы пользователь видел основной VPN IP.
  - RULE-SET,apps_ipcheck,🌍 World / EU

  # Торренты: по умолчанию REJECT через селектор 🧲 Torrents, чтобы не создавать abuse-нагрузку.
  - RULE-SET,torrent-clients,🧲 Torrents
  - RULE-SET,torrent-trackers,🧲 Torrents
  - PROCESS-NAME-REGEX,(?i).*torrent.*,🧲 Torrents
  - RULE-SET,torrent-websites,🧲 Torrents

  # TOR: клиентский best-effort блок. Серверный запрет должен дублироваться Node Plugins / egress policy.
  - RULE-SET,tor-inline,⛔ BLOCK
  - PROCESS-NAME-REGEX,(?i).*(tor|torbrowser|obfs4proxy|snowflake-client).*,⛔ BLOCK

  # Игры обычно лучше напрямую, но пользователь может переключить 🎮 Games на EU/RU.
  - RULE-SET,games-direct,🎮 Games

  # Основные global-сервисы.
  - RULE-SET,youtube,📺 YouTube
  - PROCESS-NAME-REGEX,(?i).*youtube.*,📺 YouTube

  # Discord: домены + voice UDP ranges.
  - AND,((RULE-SET,cloudflare-ips),(NETWORK,udp),(DST-PORT,19200-19500)),💬 Discord
  - AND,((RULE-SET,cloudflare-ips),(NETWORK,udp),(DST-PORT,50000-50100)),💬 Discord
  - AND,((RULE-SET,discord_voiceips),(NETWORK,udp),(DST-PORT,50000-50100)),💬 Discord
  - RULE-SET,discord_domains,💬 Discord
  - PROCESS-NAME-REGEX,(?i).*discord.*,💬 Discord
  - PROCESS-NAME-REGEX,(?i).*vesktop.*,💬 Discord

  # Telegram / WhatsApp / Meta.
  - RULE-SET,telegram-domains,➤ Telegram
  - RULE-SET,telegram-ips,➤ Telegram
  - RULE-SET,additional-telegram-domains,➤ Telegram
  - RULE-SET,additional-telegram-ips,➤ Telegram
  - PROCESS-NAME-REGEX,(?i).*telegram.*,➤ Telegram
  - PROCESS-NAME-REGEX,(?i).*ayugram.*,➤ Telegram
  - PROCESS-NAME-REGEX,(?i).*nekogram.*,➤ Telegram
  - RULE-SET,whatsapp,💬 Messengers
  - RULE-SET,meta-ips,💬 Messengers
  - PROCESS-NAME-REGEX,(?i).*whatsapp.*,💬 Messengers

  # AI / Dev.
  - RULE-SET,manual-eu-inline,🌍 World / EU
  - RULE-SET,ai,🤖 AI
  - RULE-SET,google-deepmind,🤖 AI
  - RULE-SET,github,👨‍💻 Dev Services

  # Twitch ads лучше не резать жестко: иногда ломает проигрывание. По умолчанию через EU.
  - RULE-SET,twitch-ads,🌍 World / EU

  # Speedtest — отдельный selector, удобно диагностировать EU/RU контуры.
  - RULE-SET,speedtest-net,🧪 Speedtest

  # Ресурсы, которые НЕ должны идти через РФ, даже если домен выглядит российским.
  - RULE-SET,ru-eu-exceptions,🌍 World / EU
  - RULE-SET,ru-inside,🌍 World / EU
  - RULE-SET,refilter_domains,🌍 World / EU
  - RULE-SET,refilter_ipsum,🌍 World / EU,no-resolve
  - RULE-SET,ru-bundle,🌍 World / EU
  - RULE-SET,rknasnblock,🌍 World / EU,no-resolve

  # Российские приложения/сайты/IP — через РФ-ноды.
  - RULE-SET,ru-services-inline,🇷🇺 RU Sites
  - RULE-SET,ru-apps,🇷🇺 RU Sites
  - RULE-SET,geosite-ru,🇷🇺 RU Sites
  - RULE-SET,geoip-for-ru,🇷🇺 RU Sites,no-resolve

  # Финальный default: быстрый EU-контур NL/DE.
  - MATCH,🌍 World / EU
$cybervpn_premium_smart_ru_yaml$,
        null,
        202
    )
    on conflict (template_type, name) do update
    set template_yaml = excluded.template_yaml,
        template_json = null,
        view_position = excluded.view_position,
        updated_at = now()
    returning uuid
),
template_row as (
    select uuid from template_upsert
    union all
    select uuid
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'CyberVPN Premium Smart RU'
    limit 1
),
external_squad_upsert as (
    insert into external_squads (
        name,
        subscription_settings,
        host_overrides,
        response_headers,
        hwid_settings,
        custom_remarks,
        view_position
    )
    values (
        'CYBERVPN_PREMIUM_SMART_RU',
        '{
          "profileTitle": "CyberVPN Premium Smart RU",
          "supportLink": "https://cyber-vpn.org/support",
          "profileUpdateInterval": 24,
          "isProfileWebpageUrlEnabled": true,
          "happAnnounce": "CyberVPN Premium Smart RU: DE 25G + RU 25G smart routing. RU-сервисы работают без отключения VPN. Torrent запрещён."
        }'::jsonb,
        '{}'::jsonb,
        '{
          "x-cybervpn-plan": "premium_smart_ru",
          "x-cybervpn-routing": "de-primary-ru-smart",
          "x-cybervpn-unlimited": "true"
        }'::jsonb,
        '{}'::jsonb,
        '{"purpose":"Premium Smart RU MIHOMO template override for DE/NL/RU smart-routing users"}'::jsonb,
        202
    )
    on conflict (name) do update
    set updated_at = now(),
        subscription_settings = excluded.subscription_settings,
        response_headers = excluded.response_headers,
        custom_remarks = excluded.custom_remarks,
        view_position = excluded.view_position
    returning uuid
),
external_squad_row as (
    select uuid from external_squad_upsert
    union all
    select uuid from external_squads where name = 'CYBERVPN_PREMIUM_SMART_RU'
    limit 1
),
external_template_link as (
    insert into external_squads_templates (
        external_squad_uuid,
        template_uuid,
        template_type
    )
    select external_squad_row.uuid, template_row.uuid, 'MIHOMO'
    from external_squad_row, template_row
    on conflict (external_squad_uuid, template_type) do update
    set template_uuid = excluded.template_uuid
    returning external_squad_uuid
),
internal_squad_upsert as (
    insert into internal_squads (
        name,
        view_position
    )
    values (
        'CYBERVPN_PREMIUM_SMART_RU_NODES',
        202
    )
    on conflict (name) do update
    set updated_at = now(),
        view_position = excluded.view_position
    returning uuid
),
internal_squad_row as (
    select uuid from internal_squad_upsert
    union all
    select uuid from internal_squads where name = 'CYBERVPN_PREMIUM_SMART_RU_NODES'
    limit 1
),
smart_inbound_rows as (
    select uuid
    from config_profile_inbounds
    where tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
),
internal_squad_inbound_links as (
    insert into internal_squad_inbounds (
        internal_squad_uuid,
        inbound_uuid
    )
    select internal_squad_row.uuid, smart_inbound_rows.uuid
    from internal_squad_row, smart_inbound_rows
    on conflict do nothing
    returning inbound_uuid
),
smart_node_names(name) as (
    values
        ('🇩🇪 DE Frankfurt 01 25G'),
        ('🇳🇱 NL Amsterdam 01 10G'),
        ('🇷🇺 RU Moscow 01 25G'),
        ('🇷🇺 RU SPB 01 25G')
),
smart_node_rows as (
    select nodes.uuid, nodes.name
    from nodes
    join smart_node_names on smart_node_names.name = nodes.name
),
smart_node_inbound_links as (
    insert into config_profile_inbounds_to_nodes (
        config_profile_inbound_uuid,
        node_uuid
    )
    select smart_inbound_rows.uuid, smart_node_rows.uuid
    from smart_inbound_rows, smart_node_rows
    on conflict do nothing
    returning node_uuid, config_profile_inbound_uuid
),
plugin_update as (
    update node_plugin
    set plugin_config = '{
          "ingressFilter": {"enabled": false, "blockedIps": []},
          "egressFilter": {"enabled": true, "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"], "blockedPorts": [25, 465, 587]},
          "torrentBlocker": {"enabled": true, "ignoreLists": {"ip": [], "userId": []}, "blockDuration": 86400},
          "connectionDrop": {"enabled": false, "whitelistIps": []},
          "sharedLists": [
            {"name": "ext:tor-exit-nodes", "type": "ipList", "items": []},
            {"name": "ext:tor-relays", "type": "ipList", "items": []}
          ]
        }'::jsonb,
        view_position = 202,
        updated_at = now()
    where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION'
    returning uuid
),
plugin_upsert as (
    insert into node_plugin (
        name,
        plugin_config,
        view_position
    )
    select
        'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION',
        '{
          "ingressFilter": {"enabled": false, "blockedIps": []},
          "egressFilter": {"enabled": true, "blockedIps": ["ext:tor-exit-nodes", "ext:tor-relays"], "blockedPorts": [25, 465, 587]},
          "torrentBlocker": {"enabled": true, "ignoreLists": {"ip": [], "userId": []}, "blockDuration": 86400},
          "connectionDrop": {"enabled": false, "whitelistIps": []},
          "sharedLists": [
            {"name": "ext:tor-exit-nodes", "type": "ipList", "items": []},
            {"name": "ext:tor-relays", "type": "ipList", "items": []}
          ]
        }'::jsonb,
        202

    where not exists (select 1 from plugin_update)
      and not exists (
          select 1
          from node_plugin
          where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION'
      )
    returning uuid
),
plugin_row as (
    select uuid from plugin_update
    union all
    select uuid from plugin_upsert
    union all
    select uuid
    from node_plugin
    where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION'
    limit 1
),
smart_node_plugin_assignment as (
    update nodes
    set active_plugin_uuid = plugin_row.uuid,
        updated_at = now()
    from plugin_row
    where nodes.name in (select name from smart_node_names)
      and (
          nodes.active_plugin_uuid is null
          or nodes.active_plugin_uuid = plugin_row.uuid
      )
    returning nodes.uuid
)
select
    (select count(*) from internal_squad_inbound_links) as linked_internal_squad_inbounds,
    (select count(*) from smart_node_inbound_links) as linked_node_inbounds,
    (select count(*) from smart_node_plugin_assignment) as plugin_assigned_nodes;

do $cybervpn_premium_smart_ru_validation$
declare
    v_external_squad_uuid uuid;
    v_internal_squad_uuid uuid;
    v_plugin_uuid uuid;
    v_template_uuid uuid;
    v_template_link_count integer;
    v_inbound_count integer;
    v_internal_squad_inbound_count integer;
    v_smart_node_count integer;
    v_linked_node_inbounds integer;
    v_conflicting_active_plugin_count integer;
    v_plugin_assigned_node_count integer;
    v_conflicting_node_names text;
begin
    select uuid
    into v_external_squad_uuid
    from external_squads
    where name = 'CYBERVPN_PREMIUM_SMART_RU';

    select uuid
    into v_internal_squad_uuid
    from internal_squads
    where name = 'CYBERVPN_PREMIUM_SMART_RU_NODES';

    select uuid
    into v_plugin_uuid
    from node_plugin
    where name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION';

    select uuid
    into v_template_uuid
    from subscription_templates
    where template_type = 'MIHOMO'
      and name = 'CyberVPN Premium Smart RU';

    if v_external_squad_uuid is null then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU external squad was not created';
    end if;
    if v_internal_squad_uuid is null then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU_NODES internal squad was not created';
    end if;
    if v_plugin_uuid is null then
        raise exception 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION plugin was not created';
    end if;
    if v_template_uuid is null then
        raise exception 'CyberVPN Premium Smart RU MIHOMO template was not created';
    end if;

    select count(*)
    into v_template_link_count
    from external_squads_templates
    where external_squad_uuid = v_external_squad_uuid
      and template_uuid = v_template_uuid
      and template_type = 'MIHOMO';
    if v_template_link_count <> 1 then
        raise exception 'CyberVPN Premium Smart RU MIHOMO template link is missing or duplicated: %', v_template_link_count;
    end if;

    select count(*)
    into v_inbound_count
    from config_profile_inbounds
    where tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443');
    if v_inbound_count < 2 then
        raise exception 'Expected at least 2 Smart RU inbounds, found %', v_inbound_count;
    end if;

    select count(*)
    into v_internal_squad_inbound_count
    from internal_squad_inbounds
    where internal_squad_uuid = v_internal_squad_uuid;
    if v_internal_squad_inbound_count < 2 then
        raise exception 'Expected Smart RU internal squad to contain at least 2 inbounds, found %',
            v_internal_squad_inbound_count;
    end if;

    select count(*)
    into v_smart_node_count
    from nodes
    where name in (
        '🇩🇪 DE Frankfurt 01 25G',
        '🇳🇱 NL Amsterdam 01 10G',
        '🇷🇺 RU Moscow 01 25G',
        '🇷🇺 RU SPB 01 25G'
    );
    if v_smart_node_count <> 4 then
        raise exception 'Expected 4 Premium Smart RU nodes by exact Remnawave name, found %', v_smart_node_count;
    end if;

    select count(*)
    into v_linked_node_inbounds
    from config_profile_inbounds_to_nodes
    join config_profile_inbounds
      on config_profile_inbounds.uuid = config_profile_inbounds_to_nodes.config_profile_inbound_uuid
    join nodes
      on nodes.uuid = config_profile_inbounds_to_nodes.node_uuid
    where config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
      and nodes.name in (
          '🇩🇪 DE Frankfurt 01 25G',
          '🇳🇱 NL Amsterdam 01 10G',
          '🇷🇺 RU Moscow 01 25G',
          '🇷🇺 RU SPB 01 25G'
      );
    if v_linked_node_inbounds < 8 then
        raise exception 'Expected at least 8 Smart RU node inbound links, found %', v_linked_node_inbounds;
    end if;

    select count(*), string_agg(name, ', ' order by name)
    into v_conflicting_active_plugin_count, v_conflicting_node_names
    from nodes
    where name in (
        '🇩🇪 DE Frankfurt 01 25G',
        '🇳🇱 NL Amsterdam 01 10G',
        '🇷🇺 RU Moscow 01 25G',
        '🇷🇺 RU SPB 01 25G'
    )
      and active_plugin_uuid is not null
      and active_plugin_uuid <> v_plugin_uuid;
    if v_conflicting_active_plugin_count > 0 then
        raise exception 'Refusing to overwrite existing active plugin on Premium Smart RU nodes: %',
            v_conflicting_node_names;
    end if;

    select count(distinct nodes.uuid)
    into v_plugin_assigned_node_count
    from nodes
    where nodes.name in (
        '🇩🇪 DE Frankfurt 01 25G',
        '🇳🇱 NL Amsterdam 01 10G',
        '🇷🇺 RU Moscow 01 25G',
        '🇷🇺 RU SPB 01 25G'
    )
      and nodes.active_plugin_uuid = v_plugin_uuid;
    if v_plugin_assigned_node_count <> 4 then
        raise exception 'Expected plugin_assigned_node_count=4, found %', v_plugin_assigned_node_count;
    end if;
end
$cybervpn_premium_smart_ru_validation$;

commit;

select
    external_squads.uuid as external_squad_uuid,
    external_squads.name as external_squad_name,
    subscription_templates.uuid as template_uuid,
    subscription_templates.name as template_name,
    internal_squads.uuid as internal_squad_uuid,
    internal_squads.name as internal_squad_name,
    node_plugin.uuid as node_plugin_uuid,
    node_plugin.name as node_plugin_name,
    external_squads_templates.template_type,
    (
        select count(*)
        from internal_squad_inbounds
        where internal_squad_inbounds.internal_squad_uuid = internal_squads.uuid
    ) as internal_squad_inbound_count,
    (
        select count(*)
        from config_profile_inbounds_to_nodes
        join config_profile_inbounds
          on config_profile_inbounds.uuid = config_profile_inbounds_to_nodes.config_profile_inbound_uuid
        join nodes
          on nodes.uuid = config_profile_inbounds_to_nodes.node_uuid
        where config_profile_inbounds.tag in ('VLESS_REALITY_443', 'VLESS_XHTTP_REALITY_8443')
          and nodes.name in (
              '🇩🇪 DE Frankfurt 01 25G',
              '🇳🇱 NL Amsterdam 01 10G',
              '🇷🇺 RU Moscow 01 25G',
              '🇷🇺 RU SPB 01 25G'
          )
    ) as linked_node_inbounds,
    (
        select count(distinct nodes.uuid)
        from nodes
        where nodes.name in (
            '🇩🇪 DE Frankfurt 01 25G',
            '🇳🇱 NL Amsterdam 01 10G',
            '🇷🇺 RU Moscow 01 25G',
            '🇷🇺 RU SPB 01 25G'
        )
          and nodes.active_plugin_uuid = node_plugin.uuid
    ) as plugin_assigned_node_count
from external_squads
join external_squads_templates
  on external_squads_templates.external_squad_uuid = external_squads.uuid
join subscription_templates
  on subscription_templates.uuid = external_squads_templates.template_uuid
cross join internal_squads
cross join node_plugin
where external_squads.name = 'CYBERVPN_PREMIUM_SMART_RU'
  and external_squads_templates.template_type = 'MIHOMO'
  and subscription_templates.name = 'CyberVPN Premium Smart RU'
  and internal_squads.name = 'CYBERVPN_PREMIUM_SMART_RU_NODES'
  and node_plugin.name = 'CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION';
