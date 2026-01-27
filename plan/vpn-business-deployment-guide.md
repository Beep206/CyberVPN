# 🚀 VPN-бизнес на Remnawave: Полное руководство по запуску

> **Версия:** 1.0 | **Дата:** Январь 2026  
> **Конфигурация:** 10 локаций, 3 протокола, полная автоматизация  
> **Целевая аудитория:** DevOps-специалисты

---

## 📋 Содержание

1. [Обзор архитектуры](#1-обзор-архитектуры)
2. [Выбор инфраструктуры](#2-выбор-инфраструктуры)
3. [Подготовка к запуску](#3-подготовка-к-запуску)
4. [Установка главного сервера](#4-установка-главного-сервера)
5. [Развёртывание VPN-нод](#5-развёртывание-vpn-нод)
6. [Настройка протоколов](#6-настройка-протоколов)
7. [Блокировка торрентов](#7-блокировка-торрентов)
8. [Telegram-бот и платежи](#8-telegram-бот-и-платежи)
9. [Мониторинг и алерты](#9-мониторинг-и-алерты)
10. [Бэкапы и восстановление](#10-бэкапы-и-восстановление)
11. [Subscription Links](#11-subscription-links)
12. [Запуск и тестирование](#12-запуск-и-тестирование)
13. [Чек-листы](#13-чек-листы)
14. [Финансовая модель](#14-финансовая-модель)

---

## 1. Обзор архитектуры

### 1.1 Схема инфраструктуры

```
┌─────────────────────────────────────────────────────────────────────┐
│                         КЛИЕНТЫ                                      │
│              Hiddify / Nekobox / v2rayN / Shadowrocket               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              │ Subscription URL
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ГЛАВНЫЙ СЕРВЕР (Panel)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │
│  │ Remnawave   │ │ PostgreSQL  │ │ Valkey      │ │ Prometheus    │  │
│  │ Backend     │ │ 17.x        │ │ (Redis)     │ │ + Grafana     │  │
│  │ :3000       │ │ :5432       │ │ :6379       │ │ :9090/:3002   │  │
│  │ (127.0.0.1) │ │             │ │             │ │              │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────────┘  │
│                                                                      │
│  OS: Ubuntu 24.04 | RAM: 4GB | CPU: 2 vCPU | SSD: 40GB              │
│  Провайдер: BuyVM (Luxembourg) | Цена: уточнить на сайте            │
└─────────────────────────────┬───────────────────────────────────────┘
                               │
                               │ Node API (NODE_PORT, mTLS)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         10 VPN-НОД                                   │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│  │ USA-W   │ │ USA-E   │ │ LUX     │ │ ICE     │                    │
│  │ BuyVM   │ │Hosteons │ │ BuyVM   │ │ 1984.is │                    │
│  │ $3.50   │ │ $2.50   │ │ $3.50   │ │ €5      │                    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘                    │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│  │ MOLDOVA │ │ POLAND  │ │ NETHER  │ │ TURKEY  │                    │
│  │WebCare  │ │Inferno  │ │Hosteons │ │Inferno  │                    │
│  │ $12     │ │ $5      │ │ $3      │ │ $6      │                    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘                    │
│                                                                      │
│  ┌─────────┐ ┌─────────┐                                            │
│  │ KAZAKH  │ │ RUSSIA  │                                            │
│  │ TBD     │ │ TBD     │                                            │
│  │ $7-12   │ │ $6-10   │                                            │
│  └─────────┘ └─────────┘                                            │
│                                                                      │
│  Каждая нода: Ubuntu 24.04 LTS (или 22.04) | RAM: 1-2GB | CPU: 1-2 vCPU │
│  Протоколы: VLESS-Reality + XHTTP-Reality + VLESS-WS-TLS (direct)   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Стек технологий

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Panel** | Remnawave Backend | 2.x |
| **Node** | Remnawave Node (Xray-core) | latest |
| **Database** | PostgreSQL | 17.x (актуальные миноры 17.7/16.11 на 2025-11) |
| **Cache** | Valkey (Redis-совместимый) | 8.x |
| **Bot** | Remnashop | latest |
| **Payments** | CryptoBot + YooKassa | - |
| **Monitoring** | Prometheus + Grafana | latest |
| **Backup** | remnawave-backup-restore или pgBackRest | latest |
| **Reverse Proxy** | Caddy | 2.x |
| **Container** | Docker + Docker Compose | latest |

### 1.3 Протоколы (в порядке приоритета)

| # | Протокол | Транспорт | Порт | Назначение |
|---|----------|-----------|------|------------|
| 1 | VLESS | TCP + Reality | 443 | Основной |
| 2 | VLESS | XHTTP + Reality | 8443 | Экспериментальный, нужен клиент с XHTTP |
| 3 | VLESS | WebSocket + TLS | 2083 | Резерв, прямое подключение (без CDN) |

---

## 2. Выбор инфраструктуры

### 2.1 Требования к провайдерам

| Критерий | Обязательно | Желательно |
|----------|-------------|------------|
| Torrent-политика | Разрешён / Игнорируют DMCA | Offshore |
| Bandwidth | Unmetered или >5TB | 10Gbps+ |
| Оплата | Криптовалюта | Без KYC |
| Локация | Не в РФ для P2P | Близко к РФ |

> Примечание: отсутствие рекламы (например, в YouTube) не является свойством провайдера. Это зависит от региона, IP-репутации и настроек пользователя. Рассматривайте это как гипотезу, а не гарантию.

### 2.2 Альтернативы и проверка AUP

1. Сначала проверяйте AUP/ToS каждого провайдера на P2P/BitTorrent и жалобы правообладателей.
2. Для RU/KZ узлов рекомендуется блокировать торренты на уровне Xray/iptables и не продавать их как P2P-локации.
3. Любые заявления про "без рекламы" требуют реального тестирования на целевых клиентах.

Мини-стратегия выбора:
- Оффшорные/нейтральные юрисдикции = лучше для P2P (меньше DMCA-рисков).
- Крупные публичные облака = обычно запрещают P2P, но дают хороший SLA и стабильность.
- RU/KZ узлы = полезны для низкой задержки, но лучше выключить P2P.

### 2.3 Финальный выбор: 10 локаций

| # | Локация | Провайдер | План | Цена/мес | RAM | Bandwidth | Torrent |
|---|---------|-----------|------|----------|-----|-----------|---------|
| 1 | **США West** | BuyVM | KVM Slice 1GB | $3.50 | 1GB | Unmetered | ✅ |
| 2 | **США East** | Hosteons | KVM 1GB | $2.50 | 1GB | Unmetered | ✅ |
| 3 | **Люксембург** | BuyVM | KVM Slice 1GB | $3.50 | 1GB | Unmetered | ✅ |
| 4 | **Исландия** | 1984.is | VPS Small | €5.00 | 1GB | 1TB | ✅ |
| 5 | **Молдова** ⭐ | WebCare360 | VPS Basic | $12.00 | 2GB | 1Gbps | ✅ |
| 6 | **Польша** | Inferno Solutions | VPS S | $5.00 | 1GB | 1Gbps | ✅ |
| 7 | **Нидерланды** | Hosteons | KVM 1GB | $3.00 | 1GB | Unmetered | ✅ |
| 8 | **Турция** | Inferno Solutions | VPS S | $6.00 | 1GB | 1Gbps | ✅ |
| 9 | **Казахстан** | RUVDS (Алматы/Астана) | VPS Start | от 139 руб/мес (тариф старт) | 0.5-1GB | 1Gbps | ⚠️ Ограничить |
| 10 | **Россия** | RUVDS (Москва/СПб) | VPS Start | от 139 руб/мес (тариф старт) | 0.5-1GB | 1Gbps | ⚠️ Ограничить |

> ⚠️ Параметры и цены постоянно меняются — всегда сверяйте AUP/ToS и тарифы у провайдера. Блокировка рекламы YouTube не гарантируется и зависит от IP-репутации и региона.
> Источник по RU/KZ: RUVDS заявляет VPS Start от 139 руб/мес и наличие ДЦ в Алматы/Астане (сайт RUVDS, 2026).

**Итого за ноды: ≈$40.50 + RU/KZ по актуальным тарифам (проверить цены)**

### 2.4 Главный сервер (Panel)

| Параметр | Значение |
|----------|----------|
| **Провайдер** | BuyVM (Luxembourg) |
| **План** | KVM Slice 4GB |
| **Цена** | ≈$7 (пример) |
| **RAM** | 4GB |
| **CPU** | 2 vCPU |
| **SSD** | 40GB |
| **Bandwidth** | Unmetered |

### 2.5 Общий бюджет инфраструктуры

| Статья | Стоимость/мес |
|--------|---------------|
| Главный сервер | ≈$7 |
| 10 VPN-нод | $40.50 + RU/KZ тарифы |
| Домен (.com) | $0.83 (≈$10/год) |
| Cloudflare | $0 (Free plan) |
| **Итого** | **≈$48/мес + RU/KZ тарифы (пересчитать по актуальным тарифам)** |

---

## 3. Подготовка к запуску

### 3.1 Регистрация аккаунтов

#### Шаг 3.1.1: Домен

```bash
# Рекомендуемые регистраторы (принимают крипту):
# - Njalla (njal.la) — максимальная приватность
# - Porkbun (porkbun.com) — дёшево
# - Namecheap (namecheap.com) — популярный

# Выбираем домен, например: myvpn.cc или securenet.io
```

#### Шаг 3.1.2: Cloudflare

```bash
# 1. Регистрация на cloudflare.com
# 2. Добавить домен
# 3. Изменить NS-записи у регистратора на Cloudflare
# 4. Включить режим "Proxied" для поддомена panel.myvpn.cc
# 5. SSL/TLS → Full (strict)
```

> ⚠️ Важно: в Self-Serve условиях Cloudflare (обновление 2025-09-12) запрещено использовать сервисы Cloudflare для предоставления VPN/прокси. Используйте Cloudflare только для панели/страницы подписки. VPN-ноды должны быть в режиме DNS-only. Для проксирования VPN через Cloudflare нужен Spectrum/Enterprise или провайдер, который явно разрешает VPN-трафик.

#### Шаг 3.1.3: Платёжные системы

```bash
# CryptoBot (Telegram):
# 1. Открыть @CryptoBot
# 2. /pay → Create App
# 3. Сохранить API Token

# YooKassa (для РФ карт):
# 1. Регистрация на yookassa.ru
# 2. Подключить магазин (ИП/ООО вне РФ или через посредника)
# 3. Получить shopId и secretKey
```

#### Шаг 3.1.4: Telegram Bot

```bash
# 1. Открыть @BotFather
# 2. /newbot
# 3. Имя: MyVPN Bot
# 4. Username: myvpn_bot
# 5. Сохранить токен: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 3.2 Заказ серверов

#### Шаг 3.2.1: BuyVM (Panel + 2 ноды)

```bash
# 1. https://buyvm.net
# 2. Order → KVM Slice (выбрать Luxembourg)
# 3. Оплата: Bitcoin/Litecoin
# 4. После активации — записать IP адреса

# Заказать:
# - 1x KVM Slice 4GB (Panel) — Luxembourg
# - 1x KVM Slice 1GB (Node USA-W) — Las Vegas
# - 1x KVM Slice 1GB (Node LUX) — Luxembourg
```

#### Шаг 3.2.2: Остальные провайдеры

```bash
# Hosteons (2 ноды):
# https://hosteons.com → KVM VPS → NY и Amsterdam

# 1984.is (1 нода):
# https://1984.is → VPS Small → Iceland

# WebCare360 (1 нода):
# https://webcare360.com → VPS → Moldova

# Inferno Solutions (2 ноды):
# https://inferno.name → VPS → Poland и Turkey
```

### 3.3 DNS-записи в Cloudflare

```bash
# A-записи (VPN-ноды всегда DNS only):

# Панель (Proxied ON допустим, это обычный веб-трафик):
panel.myvpn.cc    →  [IP панели]     (Proxied)

# Subscription page (если используете):
sub.myvpn.cc      →  [IP панели]     (Proxied)

# Ноды (DNS only — прямое подключение):
us-west.myvpn.cc  →  [IP BuyVM LV]   (DNS only)
us-east.myvpn.cc  →  [IP Hosteons NY](DNS only)
eu-lux.myvpn.cc   →  [IP BuyVM LUX]  (DNS only)
eu-ice.myvpn.cc   →  [IP 1984.is]    (DNS only)
eu-mol.myvpn.cc   →  [IP WebCare]    (DNS only)
eu-pol.myvpn.cc   →  [IP Inferno PL] (DNS only)
eu-nld.myvpn.cc   →  [IP Hosteons NL](DNS only)
eu-tur.myvpn.cc   →  [IP Inferno TR] (DNS only)
```

---

## 4. Установка главного сервера

### 4.1 Базовая настройка Ubuntu

```bash
# Подключаемся к серверу
ssh root@[IP_PANEL]

# Обновление системы
apt update && apt upgrade -y

# Установка базовых пакетов
apt install -y curl wget git htop nano ufw fail2ban

# Настройка часового пояса
timedatectl set-timezone UTC

# Создание пользователя
adduser deploy
usermod -aG sudo deploy

# Настройка SSH
nano /etc/ssh/sshd_config
# Изменить:
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes

# Добавить SSH ключ для пользователя deploy
su - deploy
mkdir -p ~/.ssh
echo "ваш_публичный_ключ" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
exit

# Перезапуск SSH
systemctl restart sshd
```

### 4.2 Настройка файрвола

```bash
# UFW настройка
ufw default deny incoming
ufw default allow outgoing

# SSH (желательно ограничить своим IP)
ufw allow 22/tcp

# HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Remnawave Panel и метрики не открываем наружу (только 127.0.0.1)
# Если нужен доступ к Grafana/Prometheus — ограничьте по IP:
# ufw allow from <ADMIN_IP> to any port 3002 proto tcp
# ufw allow from <ADMIN_IP> to any port 9090 proto tcp

# Включение
ufw enable
ufw status
```

### 4.3 Установка Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh

# Добавление пользователя в группу docker
usermod -aG docker deploy

# Установка Docker Compose
apt install -y docker-compose-plugin

# Проверка
docker --version
docker compose version
```

### 4.4 Установка Remnawave Backend (Panel)

```bash
# Переключаемся на пользователя deploy
su - deploy

# Создание директории
sudo mkdir -p /opt/remnawave && sudo chown -R deploy:deploy /opt/remnawave
cd /opt/remnawave

# Скачивание docker-compose и .env sample (официальный backend)
curl -o docker-compose.yml https://raw.githubusercontent.com/remnawave/backend/refs/heads/main/docker-compose-prod.yml
curl -o .env https://raw.githubusercontent.com/remnawave/backend/refs/heads/main/.env.sample
```

### 4.5 Конфигурация .env файла

```bash
nano .env
```

> Примечание: после изменения `.env` нужно пересоздать контейнеры (`docker compose down && docker compose up -d`).

```env
### APP ###
APP_PORT=3000
METRICS_PORT=3001

### DATABASE ###
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_strong_db_password_here
POSTGRES_DB=postgres
DATABASE_URL="postgresql://postgres:your_strong_db_password_here@remnawave-db:5432/postgres"

### REDIS / VALKEY ###
REDIS_HOST=remnawave-redis
REDIS_PORT=6379

### JWT ###
# Секреты минимум 64 hex: openssl rand -hex 64
JWT_AUTH_SECRET=your_auth_secret_64_hex
JWT_API_TOKENS_SECRET=your_api_tokens_secret_64_hex

### FRONT_END / SUBSCRIPTION ###
# SUB_PUBLIC_DOMAIN без http/https
FRONT_END_DOMAIN=panel.myvpn.cc
SUB_PUBLIC_DOMAIN=panel.myvpn.cc/api/sub

### METRICS (Basic Auth) ###
METRICS_USER=admin
METRICS_PASS=your_metrics_password

### TELEGRAM NOTIFICATIONS (optional) ###
IS_TELEGRAM_NOTIFICATIONS_ENABLED=false
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_NOTIFY_USERS_CHAT_ID=your_telegram_id
```

```bash
# После правок .env пересоздать контейнеры
cd /opt/remnawave
docker compose down && docker compose up -d
```

### 4.6 Docker Compose для Remnawave Backend

```bash
nano docker-compose.yml
```

```yaml
x-common: &common
  ulimits:
    nofile:
      soft: 1048576
      hard: 1048576
  restart: always
  networks:
    - remnawave-network

x-logging: &logging
  logging:
    driver: json-file
    options:
      max-size: 100m
      max-file: 5

x-env: &env
  env_file: .env

services:
  remnawave:
    image: remnawave/backend:2
    container_name: remnawave
    hostname: remnawave
    <<: [*common, *logging, *env]
    ports:
      - 127.0.0.1:3000:${APP_PORT:-3000}
      - 127.0.0.1:3001:${METRICS_PORT:-3001}
    healthcheck:
      test: ['CMD-SHELL', 'curl -f http://localhost:${METRICS_PORT:-3001}/health']
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    depends_on:
      remnawave-db:
        condition: service_healthy
      remnawave-redis:
        condition: service_healthy

  remnawave-db:
    image: postgres:17.7
    container_name: remnawave-db
    hostname: remnawave-db
    <<: [*common, *logging, *env]
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - TZ=UTC
    ports:
      - 127.0.0.1:6767:5432
    volumes:
      - remnawave-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}']
      interval: 3s
      timeout: 10s
      retries: 3

  remnawave-redis:
    image: valkey/valkey:8.1-alpine
    container_name: remnawave-redis
    hostname: remnawave-redis
    <<: [*common, *logging]
    command: >
      valkey-server
      --save ""
      --appendonly no
      --maxmemory-policy noeviction
      --loglevel warning
    healthcheck:
      test: ['CMD', 'valkey-cli', 'ping']
      interval: 3s
      timeout: 3s
      retries: 3

networks:
  remnawave-network:
    name: remnawave-network
    driver: bridge
    external: false

volumes:
  remnawave-db-data:
    name: remnawave-db-data
    driver: local
    external: false
```

> Remnawave Backend и метрики доступны только на 127.0.0.1 — внешний доступ должен идти через reverse proxy.

### 4.7 Конфигурация Caddy (отдельный контейнер)

```bash
mkdir -p /opt/remnawave/caddy && cd /opt/remnawave/caddy
nano Caddyfile
```

```caddy
https://panel.myvpn.cc {
    reverse_proxy * http://remnawave:3000
}

# Subscription page (опционально)
https://sub.myvpn.cc {
    reverse_proxy * http://remnawave-subscription-page:3010
}

:443 {
    tls internal
    respond 204
}
```

```bash
nano docker-compose.yml
```

```yaml
services:
  caddy:
    image: caddy:2.9
    container_name: caddy
    hostname: caddy
    restart: always
    ports:
      - "0.0.0.0:80:80"
      - "0.0.0.0:443:443"
    networks:
      - remnawave-network
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-ssl-data:/data

networks:
  remnawave-network:
    name: remnawave-network
    driver: bridge
    external: true

volumes:
  caddy-ssl-data:
    driver: local
    external: false
    name: caddy-ssl-data
```

### 4.8 Запуск Backend

```bash
# Запуск Remnawave Backend
cd /opt/remnawave
docker compose up -d && docker compose logs -f -t remnawave

# Запуск Caddy
cd /opt/remnawave/caddy
docker compose up -d && docker compose logs -f -t caddy

# Проверка статуса
cd /opt/remnawave
docker compose ps

# Проверка доступности
curl -I https://panel.myvpn.cc
```

### 4.9 Первый вход в панель

```bash
# 1. Открыть в браузере: https://panel.myvpn.cc
# 2. Создать первого администратора через мастер/регистрацию
# 3. Включить 2FA (Settings → Security)
# 4. Создать API токен (Settings → API Tokens)
```

---

## 5. Развёртывание VPN-нод

### 5.1 Добавление ноды в панели (официальный поток)

```bash
# 1. Открыть панель: https://panel.myvpn.cc
# 2. Nodes → Management → кнопка “+”
# 3. Указать Node Port (например 2222; не пересекать с 443/8443/2083)
# 4. Нажать “Copy docker-compose.yml”
```

### 5.2 Установка ноды на сервере

```bash
# SSH на сервер ноды
ssh root@[IP_NODE]

# Установка Docker
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh

# Файрвол: открываем VPN-порты и Node Port только от IP панели
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 443/tcp
ufw allow 8443/tcp
ufw allow 2083/tcp
ufw allow from <PANEL_IP> to any port <NODE_PORT> proto tcp
ufw --force enable

# Развёртывание ноды
mkdir -p /opt/remnanode && cd /opt/remnanode
nano docker-compose.yml
# Вставить docker-compose.yml из панели (там уже есть NODE_PORT и SECRET_KEY)
docker compose up -d && docker compose logs -f -t
```

> Для TLS-транспорта (не Reality) сертификаты монтируются в панель и отправляются на ноды автоматически. На ноде не нужен certbot.

### 5.3 Завершение и проверка

```bash
# В карточке ноды нажать “Next”, выбрать Config Profile и “Create”.
# В Nodes → Management статус должен стать Online.
```

### 5.4 Таблица конфигурации всех нод

| Нода | Домен | IP | VPN порты | Node Port | Country Code |
|------|-------|----|-----------|-----------|--------------|
| US-West | us-west.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | US |
| US-East | us-east.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | US |
| EU-Luxembourg | eu-lux.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | LU |
| EU-Iceland | eu-ice.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | IS |
| EU-Moldova | eu-mol.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | MD |
| EU-Poland | eu-pol.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | PL |
| EU-Netherlands | eu-nld.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | NL |
| EU-Turkey | eu-tur.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | TR |
| KZ-Almaty | kz-alm.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | KZ |
| RU-Moscow | ru-mow.myvpn.cc | [IP] | 443, 8443, 2083 | 2222 | RU |

> Node Port можно менять, но он должен быть доступен только с IP панели (mTLS) и не пересекаться с VPN-портами.

---

## 6. Настройка протоколов

### 6.1 Создание Config Profile в панели

```bash
# Панель → Config Profiles → Create New

# Имя: MultiProtocol-v1
# Описание: VLESS Reality + XHTTP + WS-TLS (direct) with torrent blocking
```

### 6.2 Конфигурация Xray (JSON)

```json
{
  "log": {
    "loglevel": "warning",
    "access": "/var/log/xray/access.log",
    "error": "/var/log/xray/error.log"
  },
  
  "api": {
    "tag": "api",
    "services": ["HandlerService", "StatsService"]
  },
  
  "stats": {},
  
  "policy": {
    "levels": {
      "0": {
        "statsUserUplink": true,
        "statsUserDownlink": true
      }
    },
    "system": {
      "statsInboundUplink": true,
      "statsInboundDownlink": true,
      "statsOutboundUplink": true,
      "statsOutboundDownlink": true
    }
  },
  
  "inbounds": [
    {
      "tag": "vless-reality",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "www.microsoft.com:443",
          "xver": 0,
          "serverNames": [
            "www.microsoft.com",
            "microsoft.com"
          ],
          "privateKey": "СГЕНЕРИРОВАТЬ_КЛЮЧ",
          "shortIds": ["", "0123456789abcdef"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"],
        "metadataOnly": false
      }
    },
    
    {
      "tag": "vless-xhttp",
      "port": 8443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "xhttp",
        "xhttpSettings": {
          "mode": "auto",
          "path": "/xhttp"
        },
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "www.google.com:443",
          "xver": 0,
          "serverNames": [
            "www.google.com",
            "google.com"
          ],
          "privateKey": "СГЕНЕРИРОВАТЬ_КЛЮЧ",
          "shortIds": ["", "fedcba9876543210"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"],
        "metadataOnly": false
      }
    },
    
    {
      "tag": "vless-ws-tls",
      "port": 2083,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "/ws"
        },
        "security": "tls",
        "tlsSettings": {
          "certificates": [
            {
              "certificateFile": "/var/lib/remnawave/configs/xray/ssl/fullchain.pem",
              "keyFile": "/var/lib/remnawave/configs/xray/ssl/privkey.key"
            }
          ]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls"],
        "metadataOnly": false
      }
    },
    
    {
      "tag": "api",
      "port": 10085,
      "listen": "127.0.0.1",
      "protocol": "dokodemo-door",
      "settings": {
        "address": "127.0.0.1"
      }
    }
  ],
  
  "outbounds": [
    {
      "tag": "direct",
      "protocol": "freedom",
      "settings": {}
    },
    {
      "tag": "blocked",
      "protocol": "blackhole",
      "settings": {
        "response": {
          "type": "http"
        }
      }
    }
  ],
  
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "inboundTag": ["api"],
        "outboundTag": "api"
      },
      {
        "type": "field",
        "protocol": ["bittorrent"],
        "outboundTag": "blocked"
      },
      {
        "type": "field",
        "domain": [
          "tracker",
          "torrent",
          "announce",
          "bttracker",
          "opentracker",
          "dht",
          "peer",
          "p2p"
        ],
        "outboundTag": "blocked"
      },
      {
        "type": "field",
        "port": "6881-6889,6969,51413,6771,2710,7777",
        "outboundTag": "blocked"
      },
      {
        "type": "field",
        "ip": ["geoip:private"],
        "outboundTag": "blocked"
      }
    ]
  }
}
```

> Для TLS-инбаундов сертификаты должны быть смонтированы в панель (`/var/lib/remnawave/configs/xray/ssl/`) — панель сама отправит их на ноды.

### 6.3 Генерация ключей Reality

```bash
# На любом сервере с установленным Xray
docker run --rm ghcr.io/xtls/xray-core:latest xray x25519

# Вывод:
# Private key: MC4CAQAwBQYDK2VuBCIEIGHlNOBCxxxxxxxxxxxxxx
# Public key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Private key → в конфиг сервера (privateKey)
# Public key → для клиентов (pbk=)
```

### 6.4 Оценка обхода блокировок в РФ (WS-TLS vs WS-CDN)

- **WS-TLS direct**: работает на 443 и выглядит как обычный HTTPS-трафик, но WebSocket-рукопожатие и SNI остаются видимыми для DPI. В реальности это средняя устойчивость и подходит как резерв.
- **WS-CDN**: может скрывать origin только если CDN разрешает проксирование VPN/прокси. В Cloudflare Self-Serve это запрещено и может привести к блокировке аккаунта. Кроме того, CDN-домены часто попадают под блокировки по SNI/репутации.
- **Вывод**: для РФ лучший основной вариант — Reality на 443, WS-TLS оставить как fallback. WS-CDN использовать только если у вас есть легальный CDN/Enterprise-договор, который разрешает VPN-трафик.

---

## 7. Блокировка торрентов

### 7.1 Уровень 1: Xray Routing (уже в конфиге выше)

```json
{
  "routing": {
    "rules": [
      {
        "type": "field",
        "protocol": ["bittorrent"],
        "outboundTag": "blocked"
      }
    ]
  }
}
```

> Блокировки по портам не дают 100% гарантии: BitTorrent может использовать случайные порты и шифрование. Используйте также лимиты скорости/сессий и юридическую политику сервиса.

### 7.2 Уровень 2: iptables на каждой ноде

```bash
# Создаём скрипт блокировки торрентов
cat > /opt/block-torrent.sh << 'EOF'
#!/bin/bash

# Блокировка типичных BitTorrent портов
iptables -A OUTPUT -p tcp --dport 6881:6889 -j DROP
iptables -A OUTPUT -p udp --dport 6881:6889 -j DROP
iptables -A OUTPUT -p tcp --dport 6969 -j DROP
iptables -A OUTPUT -p udp --dport 6969 -j DROP
iptables -A OUTPUT -p udp --dport 51413 -j DROP
iptables -A OUTPUT -p tcp --dport 51413 -j DROP

# Блокировка DHT
iptables -A OUTPUT -p udp --dport 6771 -j DROP

# Блокировка популярных tracker портов
iptables -A OUTPUT -p tcp --dport 2710 -j DROP
iptables -A OUTPUT -p udp --dport 2710 -j DROP

# Сохранение правил
iptables-save > /etc/iptables/rules.v4

echo "Torrent ports blocked!"
EOF

chmod +x /opt/block-torrent.sh
/opt/block-torrent.sh

# Автозапуск при перезагрузке
apt install -y iptables-persistent
```

### 7.3 Уровень 3: Systemd service для постоянной блокировки

```bash
cat > /etc/systemd/system/block-torrent.service << 'EOF'
[Unit]
Description=Block Torrent Traffic
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/block-torrent.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable block-torrent
systemctl start block-torrent
```

---

## 8. Telegram-бот и платежи

### 8.1 Установка Remnashop

> Remnashop — сторонний проект. Перед запуском проверьте совместимость с текущей версией Remnawave и платежных провайдеров.

```bash
# На главном сервере
cd /opt/remnawave

# Клонирование
git clone https://github.com/snoups/remnashop.git
cd remnashop

# Копирование конфига
cp .env.example .env
nano .env
```

### 8.2 Конфигурация Remnashop

```env
# ===== BOT =====
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789,987654321

# ===== REMNAWAVE API =====
REMNAWAVE_API_URL=http://remnawave:3000/api
REMNAWAVE_API_TOKEN=your_api_token_from_panel

# ===== DATABASE =====
DATABASE_URL=postgresql://postgres:your_db_password@remnawave-db:5432/remnashop

# ===== PAYMENTS =====

# CryptoBot (основной)
CRYPTOBOT_ENABLED=true
CRYPTOBOT_TOKEN=your_cryptobot_token
CRYPTOBOT_NETWORK=mainnet

# YooKassa (РФ карты)
YOOKASSA_ENABLED=true
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=your_secret_key

# Telegram Stars
TELEGRAM_STARS_ENABLED=true

# ===== PRICING =====
# Цены в рублях
PRICE_1_MONTH=299
PRICE_3_MONTHS=699
PRICE_6_MONTHS=1199
PRICE_12_MONTHS=1999

# Пробный период
TRIAL_ENABLED=true
TRIAL_DAYS=2
TRIAL_TRAFFIC_GB=2

# ===== REFERRAL =====
REFERRAL_ENABLED=true
REFERRAL_BONUS_DAYS=7
REFERRAL_LEVEL_2_PERCENT=5

# ===== LOCALIZATION =====
DEFAULT_LANGUAGE=ru
```

```bash
# Создать отдельную БД для Remnashop (один раз)
docker exec -it remnawave-db psql -U postgres -c "CREATE DATABASE remnashop;"
```

### 8.3 Docker Compose для Remnashop

```bash
nano docker-compose.yml
```

Добавить в существующий docker-compose.yml:

```yaml
  # Remnashop Bot
  remnashop:
    image: ghcr.io/snoups/remnashop:latest
    container_name: remnashop
    restart: unless-stopped
    depends_on:
      - remnawave-db
      - remnawave
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - ADMIN_IDS=${ADMIN_IDS}
      - REMNAWAVE_API_URL=http://remnawave:3000/api
      - REMNAWAVE_API_TOKEN=${REMNAWAVE_API_TOKEN}
      - DATABASE_URL=${DATABASE_URL}
      - CRYPTOBOT_ENABLED=${CRYPTOBOT_ENABLED}
      - CRYPTOBOT_TOKEN=${CRYPTOBOT_TOKEN}
      - YOOKASSA_ENABLED=${YOOKASSA_ENABLED}
      - YOOKASSA_SHOP_ID=${YOOKASSA_SHOP_ID}
      - YOOKASSA_SECRET_KEY=${YOOKASSA_SECRET_KEY}
    networks:
      - remnawave-network
```

### 8.4 Запуск бота

```bash
docker compose up -d remnashop
docker compose logs -f remnashop

# Проверка работы бота
# Открыть @myvpn_bot в Telegram
# Отправить /start
```

### 8.5 Настройка тарифов в панели

```bash
# Панель → Plans → Create Plan

# План 1: Тест
# - Name: Тестовый 2 дня
# - Duration: 2 days
# - Traffic: 2 GB
# - Price: 0 RUB
# - Device Limit: 1

# План 2: Месяц
# - Name: 1 месяц
# - Duration: 30 days
# - Traffic: Unlimited
# - Price: 299 RUB
# - Device Limit: 3

# План 3: 3 месяца
# - Name: 3 месяца
# - Duration: 90 days
# - Traffic: Unlimited
# - Price: 699 RUB
# - Device Limit: 5

# План 4: Год
# - Name: 12 месяцев
# - Duration: 365 days
# - Traffic: Unlimited
# - Price: 1999 RUB
# - Device Limit: 5

# План 5: Premium (спец-нода)
# - Name: Premium (спец-нода)
# - Duration: 30 days
# - Traffic: Unlimited
# - Price: 399 RUB
# - Device Limit: 3
# - Nodes: Moldova (без гарантий по YouTube/рекламе)
```

### 8.6 Варианты бота (доработка/создание)

1. **Fork Remnashop**: быстрое внедрение, минимальная разработка, но функционал ограничен тем, что поддерживает проект.
2. **Собственный бот + Remnawave API**: максимальная гибкость (промокоды, рефералы, кастомные тарифы), но требуется разработка и поддержка.
3. **Гибрид**: subscription page для выдачи ключей + минимальный бот только для оплаты/саппорта (меньше нагрузки и проще UX).

### 8.7 Крипто без CryptoBot: 3 варианта

1. **BTCPay Server (self-hosted)**: non-custodial, полный контроль, webhook-уведомления. Минусы: самостоятельная поддержка и резервирование.
2. **Crypto-процессоры с API** (NOWPayments, CoinPayments, Coinbase Commerce): быстрое подключение, авто-конвертация, но возможен KYC и ограничения по странам.
3. **Прямые on-chain платежи**: собственные кошельки + мониторинг адресов (xpub/HD) через explorer API. Нужно аккуратно обрабатывать курс, TTL счёта и подтверждения.

### 8.8 Карты РФ для физлиц без ИП/ООО (юридические ограничения)

В РФ эквайринг и приём карт для предпринимательской деятельности требуют легального статуса (самозанятость/ИП/ООО). Без статуса это риск нарушений.

Законные варианты, которые не делают вас эквайером напрямую:

1. **Telegram Stars**: пользователи платят картой через Telegram, вы получаете Stars (фактически Telegram выступает обработчиком).
2. **Merchant of Record/маркетплейс**: сервис продаёт от своего имени, вы получаете выплаты как партнёр (уточнить доступность для RU).
3. **Партнёр/агент с юрлицом**: платежи принимает партнёр, вы получаете комиссию по договору.

### 8.9 Промокоды и рефералы (без давления на маржу)

- Промокоды: скидка 10-15% только на первую оплату, не суммируются с реферальными бонусами.
- Рефералы: бонусы в днях, а не в деньгах (например, +7 дней рефереру и +3 дня рефералу после первой оплаты реферала).
- Лимиты: максимум 30 бонусных дней в месяц на одного реферера.

---

## 9. Мониторинг и алерты

### 9.1 Установка Prometheus + Grafana

```bash
cd /opt/remnawave

# Добавить в docker-compose.yml:
```

```yaml
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - remnawave-network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "127.0.0.1:3002:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=your_grafana_password
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - remnawave-network
```

### 9.2 Конфигурация Prometheus

```bash
mkdir -p /opt/remnawave/prometheus
nano /opt/remnawave/prometheus/prometheus.yml
```

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files: []

scrape_configs:
  # Remnawave metrics (Basic Auth обязательна)
  - job_name: 'remnawave'
    static_configs:
      - targets: ['remnawave:3001']
    metrics_path: /metrics
    basic_auth:
      username: admin
      password: your_metrics_password

  # Ноды: добавляйте только если у вас есть отдельные экспортеры/метрики

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 9.3 Grafana Dashboard

```bash
# 1. Открыть http://127.0.0.1:3002 (через SSH-туннель)
# 2. Войти: admin / your_grafana_password
# 3. Configuration → Data Sources → Add Prometheus
#    - URL: http://prometheus:9090
# 4. Import Dashboard → ID: 19349 (Xray dashboard)
# 5. Создать собственные панели:
#    - Active connections
#    - Traffic per node
#    - User statistics
#    - Error rates
```

### 9.4 Telegram алерты

> Примечание: в стандартном Alertmanager нет встроенного Telegram receiver — используйте webhook/relay или кастомный билд с поддержкой Telegram.

```bash
# Установка Alertmanager
# Добавить в docker-compose.yml:
```

```yaml
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    restart: unless-stopped
    ports:
      - "127.0.0.1:9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    networks:
      - remnawave-network
```

```bash
mkdir -p /opt/remnawave/alertmanager
nano /opt/remnawave/alertmanager/alertmanager.yml
```

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'telegram'

receivers:
  - name: 'telegram'
    webhook_configs:
      - url: 'https://your-telegram-relay.example.com/alert'
```

---

## 10. Бэкапы и восстановление

### 10.1 Установка backup-скрипта

```bash
cd /opt/remnawave
git clone https://github.com/distillium/remnawave-backup-restore.git backup
cd backup
cp .env.example .env
nano .env
```

```env
# Telegram для отправки бэкапов
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Пути
POSTGRES_CONTAINER=remnawave-db
BACKUP_DIR=/opt/backups

# Расписание (cron)
BACKUP_SCHEDULE=0 3 * * *  # Каждый день в 3:00
```

### 10.2 Скрипт бэкапа

```bash
nano /opt/remnawave/backup/backup.sh
```

```bash
#!/bin/bash

# ============================================
# Remnawave Backup Script
# ============================================

set -e

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="remnawave_backup_${DATE}.tar.gz"

# Создание директории
mkdir -p $BACKUP_DIR

# Бэкап PostgreSQL
# При необходимости замените пользователя/БД на ваши значения из .env
echo "Backing up PostgreSQL..."
docker exec remnawave-db pg_dump -U postgres postgres > $BACKUP_DIR/db_${DATE}.sql

# Бэкап конфигов
echo "Backing up configs..."
tar -czf $BACKUP_DIR/configs_${DATE}.tar.gz \
    /opt/remnawave/.env \
    /opt/remnawave/docker-compose.yml \
    /opt/remnawave/caddy/Caddyfile \
    /opt/remnawave/prometheus/

# Объединение в один архив
cd $BACKUP_DIR
tar -czf $BACKUP_FILE db_${DATE}.sql configs_${DATE}.tar.gz
rm db_${DATE}.sql configs_${DATE}.tar.gz

# Отправка в Telegram
echo "Sending to Telegram..."
curl -F "chat_id=${TELEGRAM_CHAT_ID}" \
     -F "document=@${BACKUP_DIR}/${BACKUP_FILE}" \
     -F "caption=🔒 Backup: ${DATE}" \
     "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument"

# Очистка старых бэкапов (старше 7 дней)
find $BACKUP_DIR -name "remnawave_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}"
```

```bash
chmod +x /opt/remnawave/backup/backup.sh
```

### 10.3 Автоматизация через cron

```bash
crontab -e

# Добавить:
# Ежедневный бэкап в 3:00
0 3 * * * /opt/remnawave/backup/backup.sh >> /var/log/backup.log 2>&1

# Еженедельный полный бэкап в воскресенье
0 4 * * 0 /opt/remnawave/backup/full-backup.sh >> /var/log/backup.log 2>&1
```

### 10.4 Восстановление из бэкапа

```bash
nano /opt/remnawave/backup/restore.sh
```

```bash
#!/bin/bash

# ============================================
# Remnawave Restore Script
# ============================================

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh backup_file.tar.gz"
    exit 1
fi

BACKUP_FILE=$1
RESTORE_DIR="/tmp/restore_$(date +%s)"

# Распаковка
mkdir -p $RESTORE_DIR
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# Остановка сервисов
cd /opt/remnawave
docker compose down

# Восстановление БД
docker compose up -d postgres
sleep 10
cat $RESTORE_DIR/db_*.sql | docker exec -i remnawave-db psql -U postgres postgres

# Восстановление конфигов
tar -xzf $RESTORE_DIR/configs_*.tar.gz -C /

# Запуск
docker compose up -d

# Очистка
rm -rf $RESTORE_DIR

echo "Restore completed!"
```

---

## 11. Subscription Links

### 11.1 Формат subscription link

```bash
# URL формат:
# Subscription page (если установлена):
https://sub.myvpn.cc/{short_uuid}

# Или через панель:
https://panel.myvpn.cc/api/sub/{short_uuid}
```

### 11.2 Содержимое subscription (автоматически генерируется)

Клиент получает список всех доступных серверов и протоколов:

```
vless://uuid@us-west.myvpn.cc:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.microsoft.com&fp=chrome&pbk=PUBLIC_KEY&sid=0123456789abcdef&type=tcp#US-West-Reality

vless://uuid@us-west.myvpn.cc:8443?encryption=none&security=reality&sni=www.google.com&fp=chrome&pbk=PUBLIC_KEY&sid=fedcba9876543210&type=xhttp&path=/xhttp#US-West-XHTTP

vless://uuid@us-west.myvpn.cc:2083?encryption=none&security=tls&type=ws&path=/ws&host=us-west.myvpn.cc#US-West-WS

# ... и так для всех 10 локаций
```

### 11.3 Настройка Subscription Page

```bash
# 1. В /opt/remnawave/.env выставить SUB_PUBLIC_DOMAIN=sub.myvpn.cc (без https)
#    и пересоздать контейнер remnawave
# 2. Установить remnawave/subscription-page и создать API Token в панели
# 3. В .env subscription-page:
#    REMNAWAVE_PANEL_URL=http://remnawave:3000
#    REMNAWAVE_API_TOKEN=API_TOKEN_FROM_REMNAWAVE
# 4. Добавить sub.myvpn.cc в Caddy и проксировать на remnawave-subscription-page:3010
# 5. Настроить страницу в Panel → Subscription Page Builder
```

```bash
mkdir -p /opt/remnawave/subscription && cd /opt/remnawave/subscription
nano docker-compose.yml
```

```yaml
services:
  remnawave-subscription-page:
    image: remnawave/subscription-page:latest
    container_name: remnawave-subscription-page
    hostname: remnawave-subscription-page
    restart: always
    env_file:
      - .env
    ports:
      - "127.0.0.1:3010:3010"
    networks:
      - remnawave-network

networks:
  remnawave-network:
    name: remnawave-network
    driver: bridge
    external: true
```

```bash
nano .env
# APP_PORT=3010
# REMNAWAVE_PANEL_URL=http://remnawave:3000
# REMNAWAVE_API_TOKEN=API_TOKEN_FROM_REMNAWAVE
docker compose up -d && docker compose logs -f -t
```

### 11.4 Приоритет протоколов в клиентах

Клиенты (Hiddify, Nekobox) автоматически тестируют и выбирают лучший:

```
1. VLESS-Reality (порт 443) — если работает, используется
2. VLESS-XHTTP (порт 8443) — если Reality заблокирован
3. VLESS-WS-TLS (порт 2083) — резерв, прямое подключение
```

---

## 12. Запуск и тестирование

### 12.1 Финальный чек-лист перед запуском

```bash
# ===== СЕРВЕРА =====
[ ] Все 10 нод online
[ ] Панель доступна по https://panel.myvpn.cc
[ ] Все ноды подключены к панели (Nodes → статус зелёный)

# ===== ПРОТОКОЛЫ =====
[ ] VLESS-Reality работает (тест с телефона)
[ ] VLESS-XHTTP работает
[ ] VLESS-WS-TLS работает (прямое подключение)

# ===== БЛОКИРОВКИ =====
[ ] Торренты заблокированы (тест: скачать .torrent файл)
[ ] Приватные IP заблокированы

# ===== ПЛАТЕЖИ =====
[ ] CryptoBot принимает платежи (тест: 1 TON)
[ ] YooKassa принимает карты (тест: 1 рубль)
[ ] Telegram Stars работает (если включено)

# ===== БОТ =====
[ ] Бот отвечает на /start
[ ] Создание пробной подписки работает
[ ] Выдача ключей работает
[ ] Реферальная система работает

# ===== МОНИТОРИНГ =====
[ ] Prometheus собирает метрики
[ ] Grafana показывает дашборды
[ ] Telegram алерты приходят

# ===== БЭКАПЫ =====
[ ] Ручной бэкап работает
[ ] Бэкап отправляется в Telegram
[ ] Восстановление протестировано
```

### 12.2 Тестирование подключения

```bash
# На клиенте (Android/iOS):

# 1. Установить Hiddify
# 2. Добавить subscription: https://sub.myvpn.cc/test-uuid
# 3. Обновить подписку
# 4. Подключиться к каждой локации
# 5. Проверить:
#    - YouTube работает
#    - Instagram работает  
#    - Speedtest (ожидание: >50 Mbps)
#    - IP показывает страну сервера
```

### 12.3 Стресс-тест

```bash
# На сервере ноды:
apt install -y iperf3

# Запуск сервера
iperf3 -s -p 5201

# На клиенте через VPN:
iperf3 -c [IP_НОДЫ] -p 5201 -t 30

# Ожидаемые результаты:
# Значения зависят от тарифа и времени суток — фиксируйте собственный baseline
```

---

## 13. Чек-листы

### 13.1 Ежедневные задачи

```markdown
## Ежедневный чек-лист

- [ ] Проверить статус всех нод в панели
- [ ] Проверить Grafana на аномалии
- [ ] Проверить баланс CryptoBot
- [ ] Ответить на тикеты поддержки
- [ ] Проверить Telegram алерты
```

### 13.2 Еженедельные задачи

```markdown
## Еженедельный чек-лист

- [ ] Обновить Docker images (panel, nodes)
- [ ] Проверить SSL сертификаты
- [ ] Анализ метрик использования
- [ ] Проверить работу всех протоколов
- [ ] Тест бэкапа и восстановления
- [ ] Проверить логи на ошибки
- [ ] Обновить блоклисты торрентов
```

### 13.3 Ежемесячные задачи

```markdown
## Ежемесячный чек-лист

- [ ] Обновить Ubuntu на всех серверах
- [ ] Ротация API ключей
- [ ] Аудит безопасности
- [ ] Анализ финансов (выручка, расходы)
- [ ] Проверить актуальность протоколов
- [ ] Обновить документацию
- [ ] Планирование масштабирования
```

### 13.4 При блокировке протокола

```markdown
## Экстренный чек-лист: блокировка протокола

1. [ ] Определить какой протокол заблокирован
2. [ ] Проверить работу резервных протоколов
3. [ ] Уведомить пользователей в Telegram-канале
4. [ ] Обновить конфигурацию:
   - [ ] Изменить SNI на легитимные домены/фронты, которые вы контролируете
   - [ ] Переключить на XHTTP если заблокирован Reality
   - [ ] Активировать WS-TLS direct fallback
5. [ ] Перезапустить ноды
6. [ ] Протестировать подключение
7. [ ] Обновить subscription
8. [ ] Уведомить пользователей о восстановлении
```

---

## 14. Финансовая модель

### 14.1 Базовые метрики

- **ARPU**: средний доход на пользователя за месяц.
- **Churn**: доля пользователей, которые не продлили подписку в следующем месяце.
- **Cost per user**: инфраструктура / активные пользователи.
- **LTV**: ARPU * (1 / churn).

### 14.2 Тарифы и скидки

Рекомендации без сильного давления на маржу:

- 1 месяц: базовая цена `P1` (например, 299 RUB).
- 3 месяца: `P3 = P1 * 2.7` (скидка ~10%).
- 6 месяцев: `P6 = P1 * 5.1` (скидка ~15%).
- 12 месяцев: `P12 = P1 * 9.0` (скидка ~25%).

### 14.3 Тест и промокоды

- **Тест**: 2 дня, лимит трафика (2-5 GB), 1 устройство.
- **Промокоды**: одноразовые, -10%/-15% на первую оплату, TTL 7-14 дней.
- **Комбинации**: промокоды не суммируются с реферальными бонусами.

### 14.4 Реферальная система

- Бонус начисляется только после первой оплаты реферала.
- Формула бонусов в днях:
  - реферал: +3 дня
  - реферер: +7 дней
- Лимит: до 30 бонусных дней/мес на одного реферера.

### 14.5 Пример расчета маржи

```
Gross Profit = Revenue - InfraCost - PaymentFees
InfraCost per user = InfraCost / ActiveUsers
Payback months (approx) = CAC / (ARPU - InfraCost per user)
```

> Не давите скидками: удерживайте совокупные бонусы (рефералы + промокоды) в пределах 15-25% от выручки.

---

## 📊 Сводка проекта

| Параметр | Значение |
|----------|----------|
| **Ежемесячные затраты** | ≈$48 + RU/KZ тарифы |
| **Точка безубыточности** | 30-40 клиентов |
| **Время развёртывания** | 1-2 дня |
| **Протоколы** | VLESS-Reality, XHTTP, WS-TLS |
| **Локации** | 10 стран |
| **Автоматизация** | 100% (бот + автовыдача) |

---

## 🔗 Полезные ссылки

- [Remnawave Backend GitHub](https://github.com/remnawave/backend)
- [Remnawave Docs](https://docs.rw/)
- [Remnashop GitHub](https://github.com/snoups/remnashop)
- [Cloudflare Network Ports](https://developers.cloudflare.com/fundamentals/reference/network-ports/)
- [Cloudflare Self-Serve Terms (2025-09-12)](https://www.cloudflare.com/terms/)
- [PostgreSQL Releases (2025-11)](https://www.postgresql.org/)
- [RUVDS тарифы и дата-центры (2026)](https://ruvds.com/)
- [Xray-core Documentation](https://xtls.github.io/)
- [Hiddify Client](https://hiddify.com/)
- [NTC.party (обсуждение блокировок)](https://ntc.party/)

---

> **Автор:** Сгенерировано Claude AI  
> **Версия:** 1.0  
> **Дата:** Январь 2026
