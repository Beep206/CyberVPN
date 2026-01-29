# PRD: CyberVPN Task Worker — Микросервис фоновых задач на TaskIQ

## Метаданные
- **Версия**: 1.0.0
- **Дата**: 2026-01-29
- **Автор**: Claude Code
- **Статус**: Ready for Review
- **Метод**: RPG (Repository Planning Graph)
- **Язык реализации**: Python 3.13+
- **Фреймворк**: TaskIQ + RedisStreamBroker

---

## 1. Overview

### Problem Statement

CyberVPN — VPN-бизнес платформа с cyberpunk-тематикой. Существующий FastAPI backend (`backend/`) предоставляет REST API, WebSocket и SSE для admin dashboard. Однако **в системе полностью отсутствует фоновая обработка задач**:

1. **Notification Queue без потребителя** — Таблица `notification_queue` в PostgreSQL накапливает уведомления для отправки через Telegram Bot API. Записи содержат поля `status` (pending/sent/failed), `attempts`, `scheduled_at`, `error_message` — но **ни один процесс не потребляет эту очередь**. Уведомления вставляются и остаются необработанными навсегда.

2. **Нет периодических задач** — Отсутствуют:
   - Проверка истечения подписок и автоматическое отключение пользователей
   - Мониторинг здоровья VPN-нод (серверов)
   - Верификация ожидающих платежей через CryptoBot API
   - Очистка устаревших данных (токены, логи, кеш)
   - Агрегация статистики и bandwidth данных
   - Синхронизация данных с Remnawave API

3. **Нет асинхронных операций** — Bulk-операции (массовое отключение пользователей, сброс трафика) выполняются синхронно в HTTP-хендлерах, блокируя ответ клиенту.

4. **Нет отчётности** — Отсутствует автоматическая генерация ежедневных/еженедельных отчётов для администраторов.

**Текущее состояние**: Backend обрабатывает только входящие HTTP-запросы. Всё, что требует отложенного, периодического или фонового выполнения — не работает.

### Target Users

| Роль | Как использует Task Worker |
|------|--------------------------|
| **Super Admin** | Получает автоматические отчёты и алерты о критических событиях |
| **Admin** | Запускает bulk-операции асинхронно, получает уведомления о завершении |
| **Operator** | Видит real-time статус серверов благодаря периодическим health-check'ам |
| **Support** | Уведомления пользователям отправляются автоматически (напоминания о подписке) |
| **Backend API** | Делегирует тяжёлые/отложенные задачи в Task Worker через Redis Streams |

### Success Metrics

#### Операционные метрики (Quality)
- Время обработки уведомления от постановки в очередь до отправки: p95 < 60 секунд
- Процент успешной доставки Telegram уведомлений: > 98%
- Время обнаружения падения VPN-ноды: < 3 минуты
- Время верификации ожидающего платежа: < 10 минут
- Процент задач завершённых без ошибок: > 99.5%
- Количество "застрявших" задач (stuck > 5 минут): 0

#### Метрики надёжности (Reliability)
- Uptime воркера: > 99.9%
- Потеря задач при рестарте воркера: 0 (благодаря Redis Streams ACK)
- Корректная обработка при недоступности внешних сервисов (Remnawave, Telegram): circuit breaker срабатывает за < 5 секунд
- Восстановление после краша: автоматический рестарт через Docker healthcheck < 30 секунд

#### Метрики производительности (Performance)
- Throughput: > 100 задач/минуту при пиковой нагрузке
- Потребление памяти воркера: < 512 MB при нормальной работе
- CPU утилизация: < 30% при нормальной нагрузке
- Размер очереди задач в Redis: < 1000 в стабильном состоянии

#### Метрики мониторинга (Observability)
- 100% задач трекаются в Prometheus метриках
- Structured logging для каждой задачи с correlation ID
- Grafana дашборд с real-time статусом всех типов задач
- Alert rules для аномалий (рост очереди, рост ошибок)

#### Tracking Events

| Метрика | Event | Prometheus Counter/Histogram |
|---------|-------|------------------------------|
| Task Executed | `task.executed` | `taskiq_task_total{task_name, status}` |
| Task Duration | `task.duration` | `taskiq_task_duration_seconds{task_name}` |
| Task Failed | `task.failed` | `taskiq_task_errors_total{task_name, error_type}` |
| Task Retried | `task.retried` | `taskiq_task_retries_total{task_name}` |
| Notification Sent | `notification.sent` | `cybervpn_notifications_total{type, status}` |
| Server Health | `server.health_checked` | `cybervpn_server_health{node_uuid, status}` |
| Payment Verified | `payment.verified` | `cybervpn_payments_verified_total{status}` |
| Queue Depth | `queue.depth` | `taskiq_queue_depth{queue_name}` |

---

## 1.5 User Personas (в контексте Task Worker)

### Backend Developer
**Использование**: Добавляет новые типы задач, настраивает расписания, дебажит проблемы с обработкой.
**Потребности**: Понятная структура кода, типизация, тестируемость, логирование.
**Pain Points**: Сложность отладки асинхронных задач, отсутствие видимости состояния очереди.

### DevOps Engineer
**Использование**: Деплоит воркер, мониторит метрики, настраивает алерты, масштабирует воркеры.
**Потребности**: Docker-образ, health-check'и, Prometheus метрики, Grafana дашборды, горизонтальное масштабирование.
**Pain Points**: Непонятное состояние задач, нет метрик, сложность диагностики.

### Admin Platform User
**Использование**: Запускает массовые операции, ожидает уведомлений, видит статус задач.
**Потребности**: Быстрый отклик API, прогресс-бар для bulk-операций, алерты о проблемах.
**Pain Points**: Операции "зависают", уведомления не приходят, нет прозрачности.

---

## 1.6 User Journeys (в контексте Task Worker)

### Journey 1: Обработка уведомления из очереди
1. FastAPI backend вставляет запись в `notification_queue` (status='pending')
2. Task Worker берёт запись из таблицы (каждые 30 секунд)
3. Worker вызывает Telegram Bot API для отправки сообщения
4. При успехе: обновляет status='sent', sent_at=now()
5. При ошибке: инкрементирует attempts, записывает error_message
6. При attempts >= 5: помечает status='failed', отправляет алерт админу

### Journey 2: Истечение подписки пользователя
1. Scheduler запускает задачу `check_expiring_subscriptions` каждый час
2. Worker запрашивает список пользователей через Remnawave API
3. Фильтрует пользователей с expire_at в ближайшие 24ч / 3 дня / 7 дней
4. Для каждого: ставит в очередь Telegram уведомление с напоминанием
5. Отдельная задача `disable_expired_users` (каждые 15 минут) отключает просроченных

### Journey 3: Массовая операция (Bulk Disable Users)
1. Admin нажимает "Disable Selected" в dashboard для 500 пользователей
2. FastAPI backend получает запрос, отправляет задачу `execute_bulk_operation` в TaskIQ
3. Backend немедленно возвращает `202 Accepted` с `job_id`
4. Worker обрабатывает пользователей пачками по 50
5. Прогресс записывается в Redis: `cybervpn:bulk:{job_id}:progress` = `{processed: 250, total: 500}`
6. Frontend опрашивает прогресс через SSE/WebSocket
7. По завершении: Worker отправляет уведомление админу

### Journey 4: Падение VPN-ноды
1. Scheduler запускает `check_server_health` каждые 2 минуты
2. Worker проверяет все VPN-ноды через Remnawave API
3. Нода `nl-01` не отвечает (is_connected=false)
4. Worker записывает состояние в Redis history
5. Worker отправляет срочный алерт в Telegram администраторам
6. Worker публикует SSE-событие для обновления dashboard в реальном времени
7. При следующей проверке: если нода восстановилась — отправляет "resolved" алерт

---

## 2. Functional Decomposition (Capability Tree)

### Capability 1: Обработка уведомлений (Notification Processing)

Обработка очереди Telegram-уведомлений с гарантированной доставкой и retry-логикой.

#### Feature 1.1: Потребление очереди уведомлений
- **Description**: Периодически извлекает pending-уведомления из таблицы `notification_queue` и отправляет через Telegram Bot API
- **Inputs**: PostgreSQL query: `notification_queue WHERE status='pending' AND scheduled_at <= now() ORDER BY scheduled_at LIMIT 50`
- **Outputs**: Обновлённые записи: status='sent'/status='failed', sent_at, error_message
- **Behavior**: Каждые 30 секунд извлекает батч до 50 записей. Для каждой вызывает Telegram Bot API `sendMessage`. При HTTP 429 (rate limit) — backoff 1 секунда. При успехе — обновляет status и sent_at. При ошибке — инкрементирует attempts. При attempts >= 5 — помечает failed.

#### Feature 1.2: Отправка мгновенного уведомления (On-Demand)
- **Description**: Немедленная отправка Telegram-сообщения по запросу из FastAPI backend
- **Inputs**: `telegram_id: int`, `message: str`, `notification_type: str`, `parse_mode: str = 'HTML'`
- **Outputs**: `TaskiqResult` с `is_err: bool`, `return_value: dict(message_id, sent_at)`
- **Behavior**: Отправляет сообщение напрямую через Telegram Bot API. Retry: 3 попытки с экспоненциальным backoff (10s, 30s, 90s). Не использует notification_queue таблицу.

#### Feature 1.3: Массовая рассылка (Broadcast)
- **Description**: Отправка уведомления группе пользователей с rate-limiting
- **Inputs**: `telegram_ids: list[int]`, `message: str`, `notification_type: str`
- **Outputs**: `BroadcastResult(sent: int, failed: int, errors: list[dict])`
- **Behavior**: Отправляет сообщения последовательно с rate-limit 30 msgs/sec (ограничение Telegram). Использует batch-insert в notification_queue для deferred отправки. Трекает прогресс в Redis.

---

### Capability 2: Жизненный цикл подписок (Subscription Lifecycle)

Автоматическое управление подписками: проверка истечения, напоминания, отключение, сброс трафика.

#### Feature 2.1: Проверка истекающих подписок
- **Description**: Периодическая проверка пользователей с подписками, истекающими в ближайшее время
- **Inputs**: Remnawave API: `GET /api/users` → фильтр по `expire_at`
- **Outputs**: Telegram-уведомления пользователям с напоминанием о продлении
- **Behavior**: Каждый час запрашивает всех активных пользователей. Фильтрует по bracket'ам: 7 дней, 3 дня, 24 часа, 6 часов до истечения. Для каждого bracket'а отправляет соответствующее уведомление. Дедупликация через Redis ключ: `cybervpn:sub_reminder:{user_uuid}:{bracket}` с TTL = bracket_duration.

#### Feature 2.2: Отключение просроченных пользователей
- **Description**: Автоматическая деактивация пользователей с истёкшей подпиской
- **Inputs**: Remnawave API: пользователи с `expire_at < now()` AND `status = 'active'`
- **Outputs**: Remnawave API: `PATCH /api/users/{uuid}` → status=disabled. Telegram-уведомление.
- **Behavior**: Каждые 15 минут. Запрашивает просроченных пользователей. Для каждого: отключает через Remnawave API, отправляет Telegram уведомление о деактивации с инструкцией по продлению. Логирует в audit.

#### Feature 2.3: Сброс ежемесячного трафика
- **Description**: Обнуление счётчиков трафика для активных пользователей в начале месяца
- **Inputs**: Remnawave API: все пользователи с активной подпиской
- **Outputs**: Remnawave API: сброс `used_traffic_bytes = 0`
- **Behavior**: 1-го числа каждого месяца в 00:00 UTC. Запрашивает всех активных пользователей. Пачками по 100 вызывает Remnawave API для сброса трафика. Отправляет broadcast-уведомление.

#### Feature 2.4: Автопродление подписок
- **Description**: Автоматическое продление подписок для пользователей с настроенным auto-renew
- **Inputs**: Пользователи с `auto_renew=true` и `expire_at < now() + 1 hour`
- **Outputs**: Создание invoice через CryptoBot, уведомление пользователя
- **Behavior**: Каждые 30 минут проверяет пользователей с auto-renew. Создаёт CryptoBot invoice. Отправляет уведомление со ссылкой на оплату. При успешной оплате (webhook) — продлевает подписку.

---

### Capability 3: Мониторинг здоровья серверов (Server Health Monitoring)

Периодическая проверка VPN-нод, обнаружение проблем, алертинг.

#### Feature 3.1: Health Check VPN-нод
- **Description**: Регулярная проверка состояния всех VPN-серверов через Remnawave API
- **Inputs**: Remnawave API: `GET /api/nodes` → список нод с `is_connected`, `is_disabled`, `is_connecting`
- **Outputs**: Redis: `cybervpn:health:{node_uuid}:current` = status JSON. Telegram-алерт при изменении статуса.
- **Behavior**: Каждые 2 минуты. Запрашивает все ноды. Для каждой определяет статус (online/offline/warning/maintenance). Сравнивает с предыдущим состоянием в Redis. При изменении: записывает в историю `cybervpn:health:{node_uuid}:history` (sorted set, score=timestamp), отправляет алерт. Retry: 2 попытки с 15s gap.

#### Feature 3.2: Сбор bandwidth-снапшотов
- **Description**: Периодический сбор данных о пропускной способности серверов
- **Inputs**: Remnawave API: bandwidth stats endpoint
- **Outputs**: Redis time-series: `cybervpn:bandwidth:{node_uuid}:{timestamp}`
- **Behavior**: Каждые 5 минут. Запрашивает текущую статистику bandwidth для каждой ноды. Сохраняет в Redis sorted set с TTL 48 часов (для построения графиков). Каждый час агрегирует 5-минутные снапшоты в часовые бакеты.

#### Feature 3.3: Проверка доступности внешних сервисов
- **Description**: Мониторинг доступности Remnawave API, Redis, PostgreSQL
- **Inputs**: Health-check endpoints и connection tests
- **Outputs**: Redis: `cybervpn:health:services:{service_name}` = status. Алерт при недоступности.
- **Behavior**: Каждые 60 секунд. Проверяет:
  - Remnawave API: GET /health
  - PostgreSQL: SELECT 1
  - Redis: PING
  - Telegram Bot API: getMe
  При 3 последовательных неудачах — отправляет critical алерт.

---

### Capability 4: Обработка платежей (Payment Processing)

Асинхронная верификация платежей, активация подписок, retry неудачных вебхуков.

#### Feature 4.1: Верификация ожидающих платежей
- **Description**: Периодическая проверка статуса pending-платежей через CryptoBot API
- **Inputs**: PostgreSQL: `payments WHERE status='pending' AND created_at > now() - interval '24 hours'`
- **Outputs**: Обновлённый status (completed/failed), активация подписки, Telegram-уведомление
- **Behavior**: Каждые 5 минут. Для каждого pending платежа вызывает CryptoBot API `getInvoices(invoice_ids=[...])`. При status='paid': обновляет payment → completed, вызывает Remnawave API для активации/продления подписки, отправляет confirmation в Telegram. При истечении (> 24ч): обновляет → failed, уведомляет пользователя.

#### Feature 4.2: Обработка завершения платежа (On-Demand)
- **Description**: Асинхронная обработка webhook'а о завершении платежа
- **Inputs**: `payment_id: UUID`, `invoice_data: dict`, `provider: str`
- **Outputs**: Активированная подписка, уведомление пользователя
- **Behavior**: Вызывается из FastAPI при получении webhook. Проверяет подпись webhook. Обновляет запись в payments. Активирует подписку через Remnawave. Записывает в audit_logs. Отправляет Telegram confirmation. Retry: 3 попытки, exponential backoff (30s, 2m, 10m).

#### Feature 4.3: Retry неудачных вебхуков
- **Description**: Повторная обработка неуспешных webhook'ов
- **Inputs**: PostgreSQL: `webhook_logs WHERE is_valid=true AND processed_at IS NULL AND created_at > now() - interval '24 hours'`
- **Outputs**: Обработанные вебхуки, обновлённые webhook_logs записи
- **Behavior**: Каждые 30 минут. Извлекает необработанные валидные вебхуки. Повторно выполняет обработку в зависимости от типа (payment, user_event, server_event). Макс. 3 попытки per webhook.

#### Feature 4.4: Генерация финансовых отчётов
- **Description**: Ежедневная агрегация данных по платежам
- **Inputs**: PostgreSQL: `payments WHERE created_at >= today - 1 day`
- **Outputs**: Агрегированные данные: total_revenue, count_by_plan, count_by_provider, avg_amount
- **Behavior**: Ежедневно в 00:30 UTC. Собирает статистику за прошедшие сутки. Сохраняет в Redis: `cybervpn:stats:payments:{date}`. Включает в daily report.

---

### Capability 5: Агрегация аналитики (Analytics Aggregation)

Периодический сбор и агрегация данных для dashboard аналитики.

#### Feature 5.1: Ежедневная агрегация статистики
- **Description**: Сбор ключевых бизнес-метрик за сутки
- **Inputs**: Remnawave API (users, servers), PostgreSQL (payments, audit_logs)
- **Outputs**: Redis: `cybervpn:stats:daily:{date}` = JSON с метриками
- **Behavior**: Ежедневно в 00:05 UTC. Собирает:
  - Количество пользователей по статусам (active, disabled, expired, limited)
  - Новые регистрации за сутки
  - Общий bandwidth по всем нодам
  - Доход по планам подписок
  - Количество и типы admin-операций
  Хранит в Redis с TTL 90 дней.

#### Feature 5.2: Почасовая агрегация bandwidth
- **Description**: Агрегация 5-минутных bandwidth снапшотов в часовые бакеты
- **Inputs**: Redis: `cybervpn:bandwidth:{node_uuid}:*` (5-минутные снапшоты)
- **Outputs**: Redis: `cybervpn:bandwidth:hourly:{node_uuid}:{hour}` = sum/avg/max
- **Behavior**: Каждый час в :05. Суммирует 12 пятиминутных снапшотов за прошедший час. Рассчитывает sum, avg, max, min для каждой ноды. Хранит с TTL 30 дней. Удаляет агрегированные 5-минутные ключи старше 48ч.

#### Feature 5.3: Real-time метрики для dashboard
- **Description**: Обновление кешированных метрик для мгновенного отображения в dashboard
- **Inputs**: Remnawave API, Redis counters
- **Outputs**: Redis: `cybervpn:dashboard:realtime` = JSON snapshot
- **Behavior**: Каждые 30 секунд обновляет:
  - Общее количество онлайн-пользователей
  - Текущий bandwidth aggregate
  - Количество активных серверов
  - Последние 5 событий (platform events)
  Используется dashboard для мгновенного отображения без запроса к API.

---

### Capability 6: Очистка устаревших данных (Data Cleanup)

Автоматическая очистка expired данных для поддержания производительности.

#### Feature 6.1: Очистка expired refresh-токенов
- **Description**: Удаление просроченных и отозванных JWT refresh-токенов
- **Inputs**: PostgreSQL: `refresh_tokens WHERE expires_at < now() OR revoked_at IS NOT NULL`
- **Outputs**: Количество удалённых записей в логе
- **Behavior**: Ежедневно в 02:00 UTC. `DELETE FROM refresh_tokens WHERE expires_at < now() OR revoked_at IS NOT NULL`. Логирует количество удалённых записей.

#### Feature 6.2: Архивация старых audit-логов
- **Description**: Удаление/архивация audit_logs старше настраиваемого периода
- **Inputs**: PostgreSQL: `audit_logs WHERE created_at < now() - interval '{AUDIT_RETENTION_DAYS} days'`
- **Outputs**: Количество удалённых/архивированных записей
- **Behavior**: Еженедельно (воскресенье 03:00 UTC). Retention period: 90 дней (настраивается). Удаляет батчами по 1000 записей чтобы не блокировать таблицу. Логирует количество.

#### Feature 6.3: Очистка старых webhook-логов
- **Description**: Удаление обработанных webhook_logs старше 30 дней
- **Inputs**: PostgreSQL: `webhook_logs WHERE created_at < now() - interval '30 days'`
- **Outputs**: Количество удалённых записей
- **Behavior**: Еженедельно (понедельник 03:00 UTC). Удаляет батчами по 1000.

#### Feature 6.4: Очистка очереди уведомлений
- **Description**: Удаление обработанных и failed уведомлений
- **Inputs**: PostgreSQL: `notification_queue WHERE status IN ('sent', 'failed') AND created_at < now() - interval '7 days'`
- **Outputs**: Количество удалённых записей
- **Behavior**: Ежедневно в 01:00 UTC.

#### Feature 6.5: Инвалидация устаревшего кеша
- **Description**: Очистка Redis-ключей с устаревшими данными
- **Inputs**: Redis: паттерны `cybervpn:cache:*`, `cybervpn:stats:daily:*` (старше 90 дней)
- **Outputs**: Количество удалённых ключей
- **Behavior**: Ежедневно в 04:00 UTC. SCAN + UNLINK для паттернов. Не использует KEYS (может заблокировать Redis). Чистит:
  - Stats старше retention period
  - Health history старше 7 дней
  - Bandwidth snapshots старше 48 часов (raw) / 30 дней (hourly)

---

### Capability 7: Синхронизация с Remnawave (Remnawave Sync)

Периодическая синхронизация данных из Remnawave VPN backend для кеширования и визуализации.

#### Feature 7.1: Синхронизация геолокаций серверов
- **Description**: Обновление таблицы `server_geolocations` данными из Remnawave (для 3D карты)
- **Inputs**: Remnawave API: `GET /api/nodes` → список нод с IP, country_code, city
- **Outputs**: PostgreSQL: upsert в `server_geolocations` (latitude, longitude, country, city, region)
- **Behavior**: Каждые 6 часов. Для каждой ноды: если geolocation отсутствует — определяет координаты по country_code/IP. Использует статический маппинг country→coordinates (no external geo API dependency). Upsert в БД.

#### Feature 7.2: Синхронизация статистики пользователей
- **Description**: Периодическое обновление кеша пользовательской статистики
- **Inputs**: Remnawave API: user stats, traffic stats
- **Outputs**: Redis: `cybervpn:users:stats:summary` = JSON(total, active, disabled, expired, limited, online)
- **Behavior**: Каждые 10 минут. Запрашивает агрегированные данные из Remnawave. Кеширует в Redis с TTL 15 минут. Dashboard использует кеш вместо прямых запросов к Remnawave.

#### Feature 7.3: Синхронизация конфигураций нод
- **Description**: Кеширование конфигураций VPN-нод для быстрого доступа
- **Inputs**: Remnawave API: node configs, inbounds, hosts
- **Outputs**: Redis: `cybervpn:nodes:config:{node_uuid}` = JSON config
- **Behavior**: Каждые 30 минут. Запрашивает конфигурации всех нод. Кеширует в Redis с TTL 35 минут. Используется для быстрого отображения в dashboard без запроса к Remnawave.

---

### Capability 8: Генерация отчётов (Report Generation)

Автоматическое формирование и отправка отчётов администраторам.

#### Feature 8.1: Ежедневный отчёт
- **Description**: Формирование и отправка ежедневного сводного отчёта
- **Inputs**: Redis: `cybervpn:stats:daily:*`, `cybervpn:stats:payments:*`, health history
- **Outputs**: Telegram-сообщение в формате HTML с ключевыми метриками
- **Behavior**: Ежедневно в 06:00 UTC (09:00 МСК). Содержание:
  - Новые пользователи / отток / всего активных
  - Доход за сутки (по планам, по методам оплаты)
  - Uptime серверов (% за 24ч)
  - Bandwidth usage (total, per node top-5)
  - Инциденты за сутки (server down/up events)
  - Топ-5 ошибок (из логов)
  Форматирует как HTML с emoji для Telegram.

#### Feature 8.2: Еженедельный отчёт
- **Description**: Расширенный еженедельный отчёт с трендами
- **Inputs**: Redis: агрегированные daily-данные за 7 дней
- **Outputs**: Telegram-сообщение с графиками (text-based) и сравнениями
- **Behavior**: Еженедельно (понедельник 07:00 UTC). Дополнительно к daily:
  - Тренд: рост/падение пользователей (% к предыдущей неделе)
  - Тренд: доход (% к предыдущей неделе)
  - Самые проблемные ноды (по количеству инцидентов)
  - Среднее время отклика API
  - Рекомендации (если есть аномалии)

#### Feature 8.3: Алертинг при аномалиях
- **Description**: Мгновенное уведомление при обнаружении аномальных показателей
- **Inputs**: Prometheus metrics, Redis counters
- **Outputs**: Telegram alert с severity level (info/warning/critical)
- **Behavior**: Проверяется при каждом выполнении мониторинговых задач:
  - Server offline > 5 минут → CRITICAL
  - Error rate > 5% за последние 15 минут → WARNING
  - Queue depth > 500 → WARNING
  - Payment failure rate > 10% → CRITICAL
  - Worker memory > 80% limit → WARNING

---

### Capability 9: Массовые операции (Bulk Operations)

Асинхронное выполнение тяжёлых batch-операций с прогресс-трекингом.

#### Feature 9.1: Массовое управление пользователями
- **Description**: Batch disable/enable/reset traffic для списка пользователей
- **Inputs**: `operation: str (disable|enable|reset_traffic|delete)`, `user_uuids: list[UUID]`, `params: dict`, `initiated_by: str`
- **Outputs**: Redis progress: `cybervpn:bulk:{job_id}:progress` = JSON(processed, total, failed, errors). Telegram-уведомление по завершении.
- **Behavior**: Обрабатывает пользователей пачками по 50. Для каждого: вызывает соответствующий метод Remnawave API. Записывает прогресс в Redis после каждой пачки. При ошибке на конкретном пользователе: логирует и продолжает (partial failure OK). По завершении: отправляет summary через Telegram, публикует SSE-event.

#### Feature 9.2: Массовая рассылка уведомлений
- **Description**: Batch-отправка уведомлений всем пользователям или группе
- **Inputs**: `telegram_ids: list[int]` (или 'all'), `message: str`, `notification_type: str`
- **Outputs**: `BroadcastResult(sent: int, failed: int, total: int, duration_seconds: float)`
- **Behavior**: Использует notification_queue таблицу для deferred отправки. Вставляет все записи одним batch INSERT. Фоновая задача process_notification_queue обрабатывает в порядке очереди. Rate limit: 30 msgs/sec (Telegram ограничение).

#### Feature 9.3: Экспорт данных
- **Description**: Генерация CSV/JSON экспорта для аналитиков
- **Inputs**: `export_type: str (users|payments|servers|audit)`, `date_range: tuple[datetime, datetime]`, `format: str (csv|json)`
- **Outputs**: Сгенерированный файл в `/tmp/exports/{job_id}.{format}`, ссылка для скачивания
- **Behavior**: Запрашивает данные из PostgreSQL батчами по 1000. Стримит в файл (не загружает всё в память). Загружает файл в S3/MinIO или хранит локально с TTL. Отправляет ссылку админу через Telegram. Cleanup файлов старше 24ч.

---

## 3. Structural Decomposition

### Repository Structure

```
services/task-worker/
├── src/
│   ├── __init__.py
│   ├── broker.py                      # TaskIQ broker + result backend configuration
│   ├── config.py                      # Pydantic Settings (env variables)
│   ├── worker.py                      # Worker entry point (taskiq worker src.worker:broker)
│   ├── dependencies.py                # Shared dependency injection (DB, Redis, HTTP clients)
│   │
│   ├── tasks/                         # Task definitions by domain
│   │   ├── __init__.py
│   │   ├── notifications/             # Capability 1: Notification Processing
│   │   │   ├── __init__.py
│   │   │   ├── process_queue.py       # Feature 1.1: process_notification_queue
│   │   │   ├── send_notification.py   # Feature 1.2: send_notification (on-demand)
│   │   │   └── broadcast.py           # Feature 1.3: broadcast_message
│   │   ├── subscriptions/             # Capability 2: Subscription Lifecycle
│   │   │   ├── __init__.py
│   │   │   ├── check_expiring.py      # Feature 2.1: check_expiring_subscriptions
│   │   │   ├── disable_expired.py     # Feature 2.2: disable_expired_users
│   │   │   ├── reset_traffic.py       # Feature 2.3: reset_monthly_traffic
│   │   │   └── auto_renew.py          # Feature 2.4: auto_renew_subscriptions
│   │   ├── monitoring/                # Capability 3: Server Health Monitoring
│   │   │   ├── __init__.py
│   │   │   ├── health_check.py        # Feature 3.1: check_server_health
│   │   │   ├── bandwidth.py           # Feature 3.2: collect_bandwidth_snapshots
│   │   │   └── service_check.py       # Feature 3.3: check_external_services
│   │   ├── payments/                  # Capability 4: Payment Processing
│   │   │   ├── __init__.py
│   │   │   ├── verify_pending.py      # Feature 4.1: verify_pending_payments
│   │   │   ├── process_completion.py  # Feature 4.2: process_payment_completion (on-demand)
│   │   │   ├── retry_webhooks.py      # Feature 4.3: retry_failed_webhooks
│   │   │   └── financial_stats.py     # Feature 4.4: aggregate_financial_stats
│   │   ├── analytics/                 # Capability 5: Analytics Aggregation
│   │   │   ├── __init__.py
│   │   │   ├── daily_stats.py         # Feature 5.1: aggregate_daily_stats
│   │   │   ├── hourly_bandwidth.py    # Feature 5.2: aggregate_bandwidth_hourly
│   │   │   └── realtime_metrics.py    # Feature 5.3: update_realtime_metrics
│   │   ├── cleanup/                   # Capability 6: Data Cleanup
│   │   │   ├── __init__.py
│   │   │   ├── tokens.py              # Feature 6.1: cleanup_expired_tokens
│   │   │   ├── audit_logs.py          # Feature 6.2: archive_old_audit_logs
│   │   │   ├── webhook_logs.py        # Feature 6.3: cleanup_old_webhook_logs
│   │   │   ├── notifications.py       # Feature 6.4: cleanup_notification_queue
│   │   │   └── cache.py               # Feature 6.5: invalidate_stale_cache
│   │   ├── sync/                      # Capability 7: Remnawave Sync
│   │   │   ├── __init__.py
│   │   │   ├── geolocations.py        # Feature 7.1: sync_server_geolocations
│   │   │   ├── user_stats.py          # Feature 7.2: sync_user_stats
│   │   │   └── node_configs.py        # Feature 7.3: sync_node_configs
│   │   ├── reports/                   # Capability 8: Report Generation
│   │   │   ├── __init__.py
│   │   │   ├── daily_report.py        # Feature 8.1: generate_daily_report
│   │   │   ├── weekly_report.py       # Feature 8.2: generate_weekly_report
│   │   │   └── anomaly_alert.py       # Feature 8.3: check_anomalies
│   │   └── bulk/                      # Capability 9: Bulk Operations
│   │       ├── __init__.py
│   │       ├── user_operations.py     # Feature 9.1: execute_bulk_user_operation
│   │       ├── broadcast.py           # Feature 9.2: execute_bulk_broadcast
│   │       └── export.py              # Feature 9.3: generate_data_export
│   │
│   ├── middleware/                     # Custom TaskIQ middleware chain
│   │   ├── __init__.py
│   │   ├── logging_mw.py             # Structured logging (structlog) per task
│   │   ├── metrics_mw.py             # Prometheus counters/histograms per task
│   │   ├── error_handler_mw.py       # Global error handler → Telegram alert for critical
│   │   └── retry_mw.py               # Custom retry with per-task policies
│   │
│   ├── schedules/                     # Cron/periodic task schedule definitions
│   │   ├── __init__.py
│   │   └── cron.py                    # All periodic schedules (RedisScheduleSource)
│   │
│   ├── services/                      # Shared infrastructure services
│   │   ├── __init__.py
│   │   ├── database.py                # AsyncSessionLocal factory (asyncpg + SQLAlchemy 2)
│   │   ├── redis_client.py            # Redis connection pool (redis.asyncio)
│   │   ├── remnawave_client.py        # Remnawave HTTP client (httpx)
│   │   ├── telegram_client.py         # Telegram Bot API client (httpx)
│   │   ├── cryptobot_client.py        # CryptoBot Payment API client (httpx)
│   │   └── cache_service.py           # Redis cache wrapper (prefix: cybervpn:)
│   │
│   ├── models/                        # Own ORM model copies (independent from backend)
│   │   ├── __init__.py
│   │   ├── base.py                    # SQLAlchemy Base, mixins (TimestampMixin, etc.)
│   │   ├── notification_queue.py      # NotificationQueueModel
│   │   ├── payment.py                 # PaymentModel
│   │   ├── refresh_token.py           # RefreshTokenModel
│   │   ├── audit_log.py              # AuditLogModel
│   │   ├── webhook_log.py            # WebhookLogModel
│   │   ├── subscription_plan.py      # SubscriptionPlanModel
│   │   └── server_geolocation.py     # ServerGeolocationModel
│   │
│   └── utils/                         # Shared utilities
│       ├── __init__.py
│       ├── formatting.py              # HTML message templates for Telegram
│       ├── converters.py              # bytes_to_gb, format_duration, etc.
│       └── constants.py               # Redis key prefixes, retry policies, schedule crons
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Fixtures: InMemoryBroker, mock DB, mock Redis, mock httpx
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── tasks/
│   │   │   ├── test_notifications.py
│   │   │   ├── test_subscriptions.py
│   │   │   ├── test_monitoring.py
│   │   │   ├── test_payments.py
│   │   │   ├── test_analytics.py
│   │   │   ├── test_cleanup.py
│   │   │   ├── test_sync.py
│   │   │   ├── test_reports.py
│   │   │   └── test_bulk.py
│   │   ├── middleware/
│   │   │   ├── test_logging.py
│   │   │   ├── test_metrics.py
│   │   │   └── test_retry.py
│   │   └── services/
│   │       ├── test_remnawave_client.py
│   │       ├── test_telegram_client.py
│   │       └── test_cache_service.py
│   └── integration/
│       ├── __init__.py
│       ├── test_broker.py             # Task serialization/deserialization via Redis
│       ├── test_schedules.py          # Schedule registration & trigger
│       └── test_end_to_end.py         # Full flow: dispatch → execute → verify side effects
│
├── pyproject.toml                     # Project metadata + dependencies
├── Dockerfile                         # Multi-stage: builder + runtime
├── .env.example                       # Environment variables template
└── README.md                          # Setup, architecture, usage docs
```

### Module Definitions

#### Module: `broker`
- **Maps to capability**: Все (инфраструктурная основа)
- **Responsibility**: Конфигурация TaskIQ broker, result backend, schedule source
- **Exports**:
  - `broker: RedisStreamBroker` — основной экземпляр брокера
  - `result_backend: RedisAsyncResultBackend` — хранение результатов
  - `schedule_source: RedisScheduleSource` — источник расписаний

#### Module: `config`
- **Maps to capability**: Все (конфигурация)
- **Responsibility**: Загрузка и валидация environment variables через pydantic-settings
- **Exports**:
  - `Settings` — класс настроек
  - `get_settings()` — cached singleton

#### Module: `tasks/*`
- **Maps to capability**: 1:1 маппинг (каждый subdirectory = capability)
- **Responsibility**: Определение задач с декоратором `@broker.task`
- **Exports**: Функции задач для использования в schedules и on-demand dispatch

#### Module: `middleware`
- **Maps to capability**: Cross-cutting concerns (логирование, метрики, retry, ошибки)
- **Responsibility**: TaskIQ middleware chain
- **Exports**: Middleware-классы для регистрации в broker

#### Module: `services`
- **Maps to capability**: Все (shared infrastructure)
- **Responsibility**: Клиенты для внешних сервисов и БД
- **Exports**: Фабрики и клиенты (get_db_session, get_redis, RemnawaveClient, etc.)

#### Module: `models`
- **Maps to capability**: Data access (cleanup, payments, notifications)
- **Responsibility**: SQLAlchemy ORM-модели (собственные копии, не import из backend)
- **Exports**: Model-классы для использования в tasks

#### Module: `schedules`
- **Maps to capability**: Все периодические задачи
- **Responsibility**: Определение cron-расписаний через RedisScheduleSource
- **Exports**: `schedule_source` для `taskiq scheduler`

---

## 4. Dependency Chain

### Foundation Layer (Phase 0) — Инфраструктура
Нет зависимостей — строится первым.

- **config**: Pydantic Settings — загрузка DATABASE_URL, REDIS_URL, REMNAWAVE_URL, TELEGRAM_BOT_TOKEN, CRYPTOBOT_TOKEN. Предоставляет типизированную конфигурацию всем модулям.
- **broker**: RedisStreamBroker + RedisAsyncResultBackend — конфигурация TaskIQ. Предоставляет `@broker.task` декоратор и `broker.startup()/shutdown()`.
- **models/base**: SQLAlchemy Base class + mixins. Предоставляет базу для всех ORM-моделей.

### Data Access Layer (Phase 1)
- **models/***: Depends on [models/base]. ORM-модели таблиц. Предоставляет типизированный доступ к PostgreSQL.
- **services/database**: Depends on [config]. Async SQLAlchemy session factory. Предоставляет `get_db_session()`.
- **services/redis_client**: Depends on [config]. Redis connection pool. Предоставляет `get_redis()`.

### External Client Layer (Phase 2)
- **services/remnawave_client**: Depends on [config]. HTTP client для Remnawave API.
- **services/telegram_client**: Depends on [config]. HTTP client для Telegram Bot API.
- **services/cryptobot_client**: Depends on [config]. HTTP client для CryptoBot API.
- **services/cache_service**: Depends on [services/redis_client]. Cache wrapper с prefix.

### Middleware Layer (Phase 3)
- **middleware/logging_mw**: Depends on [config]. Structured logging.
- **middleware/metrics_mw**: Depends on [config]. Prometheus counters.
- **middleware/error_handler_mw**: Depends on [services/telegram_client]. Alert при critical errors.
- **middleware/retry_mw**: Depends on [config]. Per-task retry policies.

### Core Task Layer (Phase 4)
- **tasks/notifications/***: Depends on [services/database, services/telegram_client, models/notification_queue]
- **tasks/monitoring/***: Depends on [services/remnawave_client, services/redis_client, services/telegram_client]
- **tasks/cleanup/***: Depends on [services/database, services/redis_client, models/*]

### Business Task Layer (Phase 5)
- **tasks/subscriptions/***: Depends on [services/remnawave_client, tasks/notifications (для уведомлений)]
- **tasks/payments/***: Depends on [services/database, services/cryptobot_client, services/remnawave_client, tasks/notifications]
- **tasks/sync/***: Depends on [services/remnawave_client, services/database, services/redis_client]

### Analytics & Reports Layer (Phase 6)
- **tasks/analytics/***: Depends on [services/redis_client, services/remnawave_client]
- **tasks/reports/***: Depends on [tasks/analytics (для данных), services/telegram_client]

### Bulk Operations Layer (Phase 7)
- **tasks/bulk/***: Depends on [services/remnawave_client, services/redis_client, tasks/notifications]

### Scheduling & Integration Layer (Phase 8)
- **schedules/cron**: Depends on [все tasks/*]. Регистрация всех периодических задач.
- **worker**: Depends on [broker, middleware/*, schedules/*]. Entry point для `taskiq worker`.
- **dependencies**: Depends on [services/*]. Dependency injection для FastAPI-TaskIQ sharing.

---

## 5. Implementation Roadmap

### Phase 0: Foundation (Фундамент)
**Goal**: Рабочий TaskIQ воркер, подключённый к Redis и PostgreSQL, запускается в Docker.

**Entry Criteria**: Чистый `services/task-worker/` directory.

**Tasks**:
- [ ] Создать `pyproject.toml` с зависимостями (depends on: none)
  - Acceptance: `pip install -e .` выполняется без ошибок
  - Test: `python -c "import taskiq; import taskiq_redis"` работает
- [ ] Реализовать `config.py` — Settings через pydantic-settings (depends on: none)
  - Acceptance: Все env-переменные загружаются и валидируются
  - Test: Unit test для Settings с .env.example
- [ ] Реализовать `broker.py` — RedisStreamBroker + RedisAsyncResultBackend (depends on: config)
  - Acceptance: `broker.startup()` подключается к Redis
  - Test: Integration test с InMemoryBroker
- [ ] Создать `models/base.py` — SQLAlchemy Base + TimestampMixin (depends on: none)
  - Acceptance: Base.metadata доступен
  - Test: Unit test для mixin fields
- [ ] Создать `worker.py` — entry point (depends on: broker)
  - Acceptance: `taskiq worker src.worker:broker` запускается
  - Test: Smoke test запуска воркера
- [ ] Создать `Dockerfile` + расширение `docker-compose.yml` (depends on: все выше)
  - Acceptance: `docker compose up cybervpn-worker` запускает воркер
  - Test: `docker compose ps` показывает healthy

**Exit Criteria**: `taskiq worker src.worker:broker` запускается в Docker, подключается к Redis/PostgreSQL, health check проходит.

**Delivers**: Базовый воркер, готовый к добавлению задач.

---

### Phase 1: Data Access & External Clients (Слой доступа к данным)
**Goal**: Все ORM-модели и клиенты внешних сервисов работают.

**Entry Criteria**: Phase 0 complete.

**Tasks**:
- [ ] Реализовать все ORM-модели в `models/` (depends on: models/base)
  - Acceptance: Модели соответствуют таблицам backend PostgreSQL
  - Test: Unit tests для каждой модели (column types, relationships)
- [ ] Реализовать `services/database.py` (depends on: config)
  - Acceptance: `async with get_db_session() as session` работает
  - Test: Integration test с PostgreSQL
- [ ] Реализовать `services/redis_client.py` (depends on: config)
  - Acceptance: `await redis.ping()` возвращает True
  - Test: Integration test с Redis
- [ ] Реализовать `services/remnawave_client.py` (depends on: config)
  - Acceptance: `await client.health_check()` возвращает статус
  - Test: Unit test с mock httpx
- [ ] Реализовать `services/telegram_client.py` (depends on: config)
  - Acceptance: `await client.send_message(chat_id, text)` работает
  - Test: Unit test с mock httpx
- [ ] Реализовать `services/cryptobot_client.py` (depends on: config)
  - Acceptance: `await client.get_invoices(ids)` работает
  - Test: Unit test с mock httpx
- [ ] Реализовать `services/cache_service.py` (depends on: redis_client)
  - Acceptance: get/set/delete с prefix работают
  - Test: Unit test с fakeredis

**Exit Criteria**: Все модели и клиенты имеют unit/integration тесты. `pytest` проходит.

**Delivers**: Слой инфраструктуры, готовый для задач.

---

### Phase 2: Notification Processing (Критический Path)
**Goal**: notification_queue наконец обрабатывается. Telegram уведомления доставляются.

**Entry Criteria**: Phase 1 complete.

**Tasks**:
- [ ] Реализовать `tasks/notifications/process_queue.py` (depends on: database, telegram_client, models/notification_queue)
  - Acceptance: pending-записи из notification_queue обрабатываются и отправляются
  - Test: Unit test с mock DB и mock Telegram; проверка retry при ошибке; проверка status transition
- [ ] Реализовать `tasks/notifications/send_notification.py` (depends on: telegram_client)
  - Acceptance: On-demand уведомление отправляется и возвращает result
  - Test: Unit test с mock Telegram
- [ ] Реализовать `tasks/notifications/broadcast.py` (depends on: database, telegram_client)
  - Acceptance: Batch-рассылка с rate limiting работает
  - Test: Unit test с проверкой rate limit и partial failure
- [ ] Реализовать `utils/formatting.py` — HTML-шаблоны сообщений (depends on: none)
  - Acceptance: Шаблоны для всех типов уведомлений (expiry, payment, alert)
  - Test: Unit test для форматирования
- [ ] Добавить schedule для process_queue в `schedules/cron.py` (depends on: process_queue)
  - Acceptance: Задача запускается каждые 30 секунд
  - Test: Integration test с mock scheduler

**Exit Criteria**: Вставленные в notification_queue записи обрабатываются в течение 60 секунд. Telegram-сообщения доставляются. Failed после 5 попыток.

**Delivers**: Рабочая система уведомлений. Самый критичный feature.

---

### Phase 3: Server Health Monitoring (Параллельно с Phase 2)
**Goal**: VPN-ноды проверяются каждые 2 минуты. Алерты при падении.

**Entry Criteria**: Phase 1 complete (может выполняться параллельно с Phase 2).

**Tasks**:
- [ ] Реализовать `tasks/monitoring/health_check.py` (depends on: remnawave_client, redis_client, telegram_client)
  - Acceptance: Все ноды проверены, статус сохранён в Redis, алерт при изменении
  - Test: Unit test с mock API; проверка state transition detection
- [ ] Реализовать `tasks/monitoring/bandwidth.py` (depends on: remnawave_client, redis_client)
  - Acceptance: 5-минутные снапшоты bandwidth сохраняются в Redis
  - Test: Unit test с mock API
- [ ] Реализовать `tasks/monitoring/service_check.py` (depends on: remnawave_client, redis_client, database)
  - Acceptance: PostgreSQL, Redis, Remnawave, Telegram проверяются, алерт при 3 последовательных ошибках
  - Test: Unit test с mock services
- [ ] Добавить schedules для мониторинга (depends on: все tasks/monitoring)
  - Acceptance: health_check каждые 2 мин, bandwidth каждые 5 мин, service_check каждые 60 сек

**Exit Criteria**: Падение ноды обнаруживается за < 3 минуты. Алерт приходит в Telegram.

**Delivers**: Real-time мониторинг инфраструктуры.

---

### Phase 4: Subscription Lifecycle (Зависит от Phase 2)
**Goal**: Подписки проверяются автоматически. Просроченные пользователи отключаются.

**Entry Criteria**: Phase 2 complete (нужны уведомления).

**Tasks**:
- [ ] Реализовать `tasks/subscriptions/check_expiring.py` (depends on: remnawave_client, notifications)
  - Acceptance: Пользователи с подписками, истекающими в 7д/3д/24ч, получают напоминания
  - Test: Unit test с mock users и проверкой дедупликации
- [ ] Реализовать `tasks/subscriptions/disable_expired.py` (depends on: remnawave_client, notifications)
  - Acceptance: Просроченные пользователи отключаются через Remnawave API
  - Test: Unit test с mock API
- [ ] Реализовать `tasks/subscriptions/reset_traffic.py` (depends on: remnawave_client)
  - Acceptance: Трафик сбрасывается 1-го числа каждого месяца
  - Test: Unit test с mock API
- [ ] Реализовать `tasks/subscriptions/auto_renew.py` (depends on: remnawave_client, cryptobot_client, notifications)
  - Acceptance: Auto-renew создаёт invoice и уведомляет пользователя
  - Test: Unit test с mock CryptoBot
- [ ] Добавить schedules для подписок (depends on: все tasks/subscriptions)

**Exit Criteria**: Ежечасно проверяются подписки. Просроченные — отключаются за 15 минут. Напоминания отправляются.

**Delivers**: Полный автоматический lifecycle подписок.

---

### Phase 5: Payment Processing & Cleanup (Зависит от Phase 2, 4)
**Goal**: Платежи верифицируются автоматически. Устаревшие данные очищаются.

**Entry Criteria**: Phase 2 complete, Phase 4 partially complete.

**Tasks**:
- [ ] Реализовать `tasks/payments/verify_pending.py` (depends on: database, cryptobot_client, remnawave_client, notifications)
  - Acceptance: Pending-платежи проверяются каждые 5 минут
  - Test: Unit test с mock CryptoBot API
- [ ] Реализовать `tasks/payments/process_completion.py` (depends on: database, remnawave_client, notifications)
  - Acceptance: Webhook-triggered платёж обрабатывается, подписка активируется
  - Test: Unit test с mock services
- [ ] Реализовать `tasks/payments/retry_webhooks.py` (depends on: database)
  - Acceptance: Необработанные вебхуки переобрабатываются
  - Test: Unit test с mock DB
- [ ] Реализовать `tasks/payments/financial_stats.py` (depends on: database, redis_client)
  - Acceptance: Ежедневная агрегация платёжной статистики
  - Test: Unit test
- [ ] Реализовать все задачи в `tasks/cleanup/` (depends on: database, redis_client)
  - tokens.py, audit_logs.py, webhook_logs.py, notifications.py, cache.py
  - Acceptance: Данные старше retention period удаляются
  - Test: Unit tests для каждой задачи

**Exit Criteria**: Платежи обрабатываются автоматически. Устаревшие данные очищаются по расписанию.

**Delivers**: Автоматизированные платежи и поддержка чистоты данных.

---

### Phase 6: Analytics, Sync & Reports
**Goal**: Dashboard получает актуальные данные. Отчёты генерируются.

**Entry Criteria**: Phase 3, 5 complete.

**Tasks**:
- [ ] Реализовать `tasks/analytics/daily_stats.py` (depends on: remnawave_client, database, redis_client)
- [ ] Реализовать `tasks/analytics/hourly_bandwidth.py` (depends on: redis_client)
- [ ] Реализовать `tasks/analytics/realtime_metrics.py` (depends on: remnawave_client, redis_client)
- [ ] Реализовать `tasks/sync/geolocations.py` (depends on: remnawave_client, database)
- [ ] Реализовать `tasks/sync/user_stats.py` (depends on: remnawave_client, redis_client)
- [ ] Реализовать `tasks/sync/node_configs.py` (depends on: remnawave_client, redis_client)
- [ ] Реализовать `tasks/reports/daily_report.py` (depends on: redis_client, telegram_client)
- [ ] Реализовать `tasks/reports/weekly_report.py` (depends on: redis_client, telegram_client)
- [ ] Реализовать `tasks/reports/anomaly_alert.py` (depends on: redis_client, telegram_client)
- [ ] Добавить все schedules для Phase 6 задач

**Exit Criteria**: Dashboard-данные кешируются и обновляются. Ежедневные/еженедельные отчёты приходят в Telegram.

**Delivers**: Полная аналитика и отчётность.

---

### Phase 7: Bulk Operations
**Goal**: Массовые операции выполняются асинхронно с прогресс-трекингом.

**Entry Criteria**: Phase 2, Phase 6 partially complete.

**Tasks**:
- [ ] Реализовать `tasks/bulk/user_operations.py` (depends on: remnawave_client, redis_client, notifications)
  - Acceptance: Bulk disable/enable/reset работает пачками по 50, прогресс в Redis
  - Test: Unit test с mock API
- [ ] Реализовать `tasks/bulk/broadcast.py` (depends on: notifications)
  - Acceptance: Массовая рассылка через notification_queue
  - Test: Unit test
- [ ] Реализовать `tasks/bulk/export.py` (depends on: database, redis_client)
  - Acceptance: CSV/JSON экспорт генерируется и доступен для скачивания
  - Test: Unit test

**Exit Criteria**: Admin может запускать bulk-операции из dashboard, видеть прогресс, получать результат.

**Delivers**: Асинхронные массовые операции.

---

### Phase 8: Middleware, Metrics & Hardening
**Goal**: Production-ready observability, error handling, retry logic.

**Entry Criteria**: Phase 2-7 complete.

**Tasks**:
- [ ] Реализовать `middleware/logging_mw.py` (depends on: config)
  - Acceptance: Каждая задача логируется с task_name, args, duration, status
  - Test: Unit test
- [ ] Реализовать `middleware/metrics_mw.py` (depends on: config)
  - Acceptance: Prometheus endpoint доступен, метрики обновляются
  - Test: Integration test
- [ ] Реализовать `middleware/error_handler_mw.py` (depends on: telegram_client)
  - Acceptance: Unhandled exceptions отправляют алерт в Telegram
  - Test: Unit test
- [ ] Реализовать `middleware/retry_mw.py` (depends on: config)
  - Acceptance: Каждый домен имеет свою retry-политику
  - Test: Unit test
- [ ] Создать Grafana dashboard для TaskIQ метрик (depends on: metrics_mw)
  - Acceptance: Dashboard показывает task throughput, latency, error rate, queue depth
- [ ] Добавить Prometheus scrape config в `infra/prometheus/` (depends on: metrics_mw)
- [ ] Настроить AlertManager rules для TaskIQ (depends on: dashboard)
- [ ] Security hardening: audit environment, secrets management (depends on: all)

**Exit Criteria**: Prometheus собирает метрики. Grafana dashboard работает. Алерты настроены. Structured logging для всех задач.

**Delivers**: Production-grade observability и надёжность.

---

## 6. Test Strategy

### Test Pyramid

```
          /\
         /E2E\          ← 10% (Docker-based: dispatch → execute → verify DB/Redis)
        /------\
       /Integr. \       ← 20% (Redis broker, PostgreSQL queries, HTTP client mocks)
      /----------\
     / Unit Tests \     ← 70% (Pure logic, mock all I/O, fast)
    /--------------\
```

### Coverage Requirements
- Line coverage: **85%** minimum
- Branch coverage: **80%** minimum
- Function coverage: **90%** minimum
- All task functions: **100%** coverage

### Critical Test Scenarios

#### Notification Processing (Capability 1)
**Happy path**:
- 10 pending уведомлений → все отправлены → status='sent', sent_at заполнен
- Expected: Все 10 записей обновлены, Telegram API вызван 10 раз

**Edge cases**:
- Пустая очередь (0 pending) → задача завершается без ошибок
- notification_queue заблокирована другой транзакцией → задача ждёт lock или пропускает
- Telegram API возвращает 429 (rate limit) → backoff и retry

**Error cases**:
- Telegram API недоступен → attempts инкрементируется, error_message записывается
- После 5 неудач → status='failed', больше не обрабатывается
- PostgreSQL connection timeout → задача фейлится, retry через middleware

**Integration points**:
- process_queue → TelegramClient.send_message → DB update
- broadcast → notification_queue INSERT → process_queue pickup

---

#### Subscription Lifecycle (Capability 2)
**Happy path**:
- Пользователь с expire_at = now + 23h → получает "24 часа" напоминание
- Пользователь с expire_at = now - 1h → отключается через Remnawave API

**Edge cases**:
- Пользователь уже получил напоминание (Redis deduplicate key exists) → skip
- Пользователь без telegram_id → skip notification, still disable

**Error cases**:
- Remnawave API возвращает 503 → retry через 60s, максимум 3 попытки
- Remnawave API возвращает 404 для пользователя → логировать, skip

---

#### Server Health Monitoring (Capability 3)
**Happy path**:
- Все ноды online → обновить Redis status, no alert
- Нода перешла offline → алерт в Telegram, запись в history

**Edge cases**:
- Нода was offline, now online → "resolved" алерт
- Нода в состоянии "connecting" → status=warning, no critical alert

**Error cases**:
- Remnawave API timeout → retry 2 раза, затем log warning
- Redis unavailable → fallback: print to stdout, do not crash

---

#### Payment Processing (Capability 4)
**Happy path**:
- Pending payment → CryptoBot says "paid" → activate subscription → notify user
- Pending payment > 24h → mark as failed

**Edge cases**:
- Payment already completed (idempotency) → skip, return success
- Payment amount mismatch → alert admin, do not activate

**Error cases**:
- CryptoBot API timeout → retry 3 times with exponential backoff
- Subscription activation fails in Remnawave → revert payment status? → alert admin

---

#### Bulk Operations (Capability 9)
**Happy path**:
- 500 users disable → processed in batches of 50 → progress updated 10 times → completion notification

**Edge cases**:
- Empty user list → immediate completion, no errors
- Duplicate UUIDs in list → deduplicate before processing

**Error cases**:
- 10 out of 500 users fail to disable → partial success reported → failed UUIDs listed
- Redis unavailable for progress tracking → continue without progress (graceful degradation)

### Test Generation Guidelines

1. **Каждая задача** имеет минимум 3 unit-теста: happy path, edge case, error case
2. **Mock all I/O**: используй `unittest.mock.AsyncMock` для httpx clients, `fakeredis` для Redis, SQLAlchemy `AsyncSession` mock для DB
3. **InMemoryBroker** для integration тестов — проверяет serialization/deserialization
4. **Parametrize** тесты для разных входных данных (разные notification types, разные payment statuses)
5. **Fixtures**: conftest.py предоставляет `mock_db_session`, `mock_redis`, `mock_telegram_client`, `mock_remnawave_client`, `in_memory_broker`
6. **No sleep() в тестах** — используй `freezegun` для контроля времени

---

## 7. Architecture & Technology Stack

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      CyberVPN Platform                          │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────┐ │
│  │  Admin Panel  │────▶│   FastAPI Backend │────▶│  Task      │ │
│  │  (Next.js 16) │     │   (REST API)      │     │  Worker    │ │
│  └──────────────┘     └──────────────────┘     │  (TaskIQ)  │ │
│         │                      │                └─────┬──────┘ │
│         │                      │                      │        │
│         │              ┌───────▼───────┐      ┌───────▼──────┐│
│         │              │  PostgreSQL   │      │ Redis/Valkey ││
│         │              │  17.7         │      │ 8.1          ││
│         │              └───────────────┘      └──────────────┘│
│         │                                            │        │
│         │              ┌───────────────┐      ┌──────▼──────┐│
│         └─────────────▶│  Remnawave    │      │ Prometheus  ││
│                        │  VPN Backend  │      │ + Grafana   ││
│                        └───────────────┘      └─────────────┘│
│                                                               │
│  ┌──────────────┐     ┌──────────────────┐                   │
│  │  Telegram     │◀────│  TaskIQ          │                   │
│  │  Bot API      │     │  Scheduler       │                   │
│  └──────────────┘     └──────────────────┘                   │
│                                                               │
│  ┌──────────────┐                                            │
│  │  CryptoBot    │                                            │
│  │  Payment API  │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
FastAPI Backend                Task Worker                   External Services
      │                            │                              │
      │  ── kiq() ──▶ Redis Stream │                              │
      │                            │── process ──▶ Remnawave API  │
      │                            │── send ──▶ Telegram Bot API  │
      │                            │── verify ──▶ CryptoBot API   │
      │                            │                              │
      │  ◀── Redis PubSub ──       │── write ──▶ PostgreSQL       │
      │     (SSE/WebSocket)        │── cache ──▶ Redis            │
      │                            │── metrics ──▶ Prometheus     │
```

### Technology Stack

| Компонент | Технология | Версия | Обоснование |
|-----------|-----------|--------|-------------|
| **Task Queue** | TaskIQ | >=0.11 | Async-first, модульный, Python-native, production-tested |
| **Broker** | taskiq-redis (RedisStreamBroker) | >=1.0 | Durable (ACK), consumer groups, горизонтальное масштабирование |
| **Result Backend** | taskiq-redis (RedisAsyncResultBackend) | >=1.0 | Async, TTL для результатов, тот же Redis instance |
| **Scheduler** | taskiq + RedisScheduleSource | >=1.0 | Cron expressions, Redis-backed, persistent |
| **Runtime** | Python | >=3.13 | Совпадает с backend, latest stable |
| **Framework** | FastAPI (taskiq-fastapi) | >=0.3 | Dependency sharing с backend |
| **ORM** | SQLAlchemy | >=2.0 | Async, совпадает с backend |
| **DB Driver** | asyncpg | latest | Fastest async PostgreSQL driver |
| **Cache/Queue** | Redis (via redis-py) | >=5.0 | Совпадает с backend; Valkey 8.1 compatible |
| **HTTP Client** | httpx | latest | Async, совпадает с backend |
| **Config** | pydantic-settings | latest | Typed env variables |
| **Logging** | structlog | latest | Structured JSON logging |
| **Metrics** | prometheus-client | latest | Prometheus exposition format |
| **Testing** | pytest + pytest-asyncio | latest | Async test support |
| **Mocking** | fakeredis + respx | latest | Redis mock + httpx mock |
| **Time control** | freezegun | latest | Deterministic time in tests |

### Decision: TaskIQ over Celery/ARQ

- **Rationale**: TaskIQ — единственный async-first task queue для Python. Celery не поддерживает async задачи нативно. ARQ — минимальный, без middleware, без dependency injection, без scheduling. TaskIQ предоставляет: модульную архитектуру (brokers, backends, middleware), интеграцию с FastAPI, типизированные задачи (PEP-612), RedisStreamBroker с ACK.
- **Trade-offs**: Меньше community/ecosystem чем Celery. Менее зрелый. Но для async-only проекта (Python 3.13 + FastAPI) — идеальный выбор.
- **Alternatives considered**: Celery (нет async), ARQ (нет middleware/scheduler), Dramatiq (нет async), Huey (sync-only).

### Decision: RedisStreamBroker over PubSub/ListQueue

- **Rationale**: Единственный broker в taskiq-redis, поддерживающий acknowledgment. При крэше воркера задача будет перепоставлена другому consumer'у в группе. PubSub теряет задачи при disconnect. ListQueue теряет задачи при крэше.
- **Trade-offs**: Чуть сложнее setup (consumer groups), чуть выше latency (+1-2ms).
- **Alternatives considered**: PubSub (no ACK), ListQueue (no ACK), NATS (дополнительная инфраструктура), RabbitMQ (дополнительная инфраструктура).

### Decision: Собственные ORM-модели (не shared с backend)

- **Rationale**: Полная независимость микросервиса. Backend может менять модели без немедленного влияния на воркер. Разные migraton strategies. Можно развивать независимо.
- **Trade-offs**: Дублирование кода моделей. Риск рассинхронизации схемы. Необходимость ручной синхронизации при изменениях.
- **Alternatives considered**: Shared package в `packages/shared-models` (больше coupling), Direct import из backend (tight coupling, import path hell).
- **Mitigation**: CI check сравнивающий модели в обоих сервисах. Alembic migrations только в backend — воркер читает те же таблицы.

### Decision: Два Docker-контейнера (worker + scheduler)

- **Rationale**: TaskIQ разделяет worker (выполняет задачи) и scheduler (отправляет периодические задачи в очередь). Это best practice: scheduler должен быть singleton (чтобы задачи не дублировались), workers могут масштабироваться горизонтально.
- **Trade-offs**: +1 container в docker-compose.
- **Alternatives considered**: Один container с обоими процессами (менее надёжно, сложнее масштабировать).

---

## 8. Docker & Infrastructure Integration

### Docker Compose Extension

Добавить в существующий `infra/docker-compose.yml`:

```yaml
  cybervpn-worker:
    build:
      context: ../services/task-worker
      dockerfile: Dockerfile
    container_name: cybervpn-worker
    profiles: ["worker"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-local_dev_postgres}@remnawave-db:5432/${POSTGRES_DB:-postgres}
      - REDIS_URL=redis://remnawave-redis:6379/0
      - REMNAWAVE_URL=http://remnawave:3000
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
      - CRYPTOBOT_TOKEN=${CRYPTOBOT_TOKEN:-}
      - ADMIN_TELEGRAM_IDS=${ADMIN_TELEGRAM_IDS:-}
      - WORKER_CONCURRENCY=${WORKER_CONCURRENCY:-2}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    command: taskiq worker src.worker:broker --workers ${WORKER_CONCURRENCY:-2} --fs-discover
    depends_on:
      remnawave-db:
        condition: service_healthy
      remnawave-redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import asyncio; from src.services.redis_client import check_redis; asyncio.run(check_redis())'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - remnawave-network
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"

  cybervpn-scheduler:
    build:
      context: ../services/task-worker
      dockerfile: Dockerfile
    container_name: cybervpn-scheduler
    profiles: ["worker"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-local_dev_postgres}@remnawave-db:5432/${POSTGRES_DB:-postgres}
      - REDIS_URL=redis://remnawave-redis:6379/0
      - REMNAWAVE_URL=http://remnawave:3000
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    command: taskiq scheduler src.worker:broker src.schedules.cron:schedule_source
    depends_on:
      - cybervpn-worker
    networks:
      - remnawave-network
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "3"
```

### Dockerfile (Multi-stage)

```dockerfile
# Stage 1: Builder
FROM python:3.13-slim AS builder
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.13-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check script
COPY healthcheck.py ./
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python healthcheck.py

CMD ["taskiq", "worker", "src.worker:broker", "--workers", "2", "--fs-discover"]
```

### Prometheus Scrape Config

Добавить в `infra/prometheus/prometheus.yml`:

```yaml
  - job_name: 'cybervpn-worker'
    static_configs:
      - targets: ['cybervpn-worker:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## 9. Configuration (Environment Variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Yes | - | Redis/Valkey URL (`redis://host:port/db`) |
| `REMNAWAVE_URL` | Yes | - | Remnawave backend URL (`http://host:port`) |
| `REMNAWAVE_API_TOKEN` | Yes | - | Bearer token для Remnawave API |
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram Bot API token |
| `CRYPTOBOT_TOKEN` | Yes | - | CryptoBot Payment API token |
| `ADMIN_TELEGRAM_IDS` | Yes | - | Comma-separated Telegram IDs для алертов |
| `WORKER_CONCURRENCY` | No | `2` | Количество worker-процессов |
| `LOG_LEVEL` | No | `INFO` | Уровень логирования (DEBUG/INFO/WARNING/ERROR) |
| `RESULT_TTL_SECONDS` | No | `3600` | TTL для результатов задач в Redis |
| `NOTIFICATION_MAX_RETRIES` | No | `5` | Макс. попыток отправки уведомления |
| `NOTIFICATION_BATCH_SIZE` | No | `50` | Размер батча для process_queue |
| `HEALTH_CHECK_INTERVAL_SECONDS` | No | `120` | Интервал проверки здоровья нод |
| `CLEANUP_AUDIT_RETENTION_DAYS` | No | `90` | Retention period для audit логов |
| `CLEANUP_WEBHOOK_RETENTION_DAYS` | No | `30` | Retention period для webhook логов |
| `BULK_BATCH_SIZE` | No | `50` | Размер пачки для bulk-операций |
| `METRICS_PORT` | No | `9090` | Порт для Prometheus metrics endpoint |

---

## 10. Retry Policies Per Domain

| Домен | Макс. Retries | Backoff Strategy | Dead Letter Action |
|-------|--------------|------------------|-------------------|
| **Notifications** (process_queue) | 5 | Exponential: 30s → 1m → 5m → 15m → 1h | status='failed' в DB |
| **Notifications** (send_notification) | 3 | Exponential: 10s → 30s → 90s | Вставка в notification_queue для deferred |
| **Subscriptions** | 3 | Fixed: 60s | Log + alert admin |
| **Health Check** | 2 | Fixed: 15s | Skip (next scheduled run) |
| **Payments** (verify) | 3 | Exponential: 30s → 2m → 10m | Alert admin CRITICAL |
| **Payments** (completion) | 3 | Exponential: 30s → 2m → 10m | Alert admin CRITICAL |
| **Analytics** | 1 | None | Skip (non-critical) |
| **Cleanup** | 2 | Fixed: 5m | Log warning |
| **Sync** | 3 | Fixed: 2m | Skip until next cycle |
| **Reports** | 2 | Fixed: 10m | Alert admin |
| **Bulk Operations** | 0 (internal retry per item) | N/A | Report partial failure |

---

## 11. Risks & Mitigations

### Technical Risks

**Risk: Redis (Valkey) недоступен**
- **Impact**: High — воркер не может получать/отправлять задачи
- **Likelihood**: Low — Redis в Docker с healthcheck
- **Mitigation**: Circuit breaker на Redis connection. Worker gracefully деградирует (логирует в stdout). Auto-reconnect при восстановлении.
- **Fallback**: Задачи в Redis Streams сохраняются и будут обработаны после восстановления (durability).

**Risk: Remnawave API rate limiting**
- **Impact**: Medium — sync/bulk задачи замедляются
- **Likelihood**: Medium — при большом количестве пользователей
- **Mitigation**: Rate limiter в RemnawaveClient (asyncio.Semaphore). Batch requests где поддерживается API. Exponential backoff при 429.
- **Fallback**: Увеличить интервалы sync-задач.

**Risk: Database connection exhaustion**
- **Impact**: High — задачи не могут читать/писать данные
- **Likelihood**: Low — при правильной настройке pool
- **Mitigation**: Отдельный connection pool для воркера (pool_size=5, max_overflow=10). Connection recycling (pool_recycle=3600). Health check перед каждым batch.
- **Fallback**: Reduce worker concurrency.

**Risk: Telegram Bot API rate limits (30 msgs/sec)**
- **Impact**: Medium — уведомления задерживаются
- **Likelihood**: High — при broadcast на 1000+ пользователей
- **Mitigation**: Rate limiter (asyncio.Semaphore(25)). Deferred delivery через notification_queue. Priority queue (critical первым).
- **Fallback**: Увеличить batch interval.

**Risk: Worker crash во время выполнения задачи**
- **Impact**: Medium — задача потеряна или выполнена частично
- **Likelihood**: Low — Python crashes редки
- **Mitigation**: RedisStreamBroker с ACK — задача перепоставляется другому consumer'у. Idempotent task design (проверка status перед действием). Docker restart policy.
- **Fallback**: Manual requeue через admin API.

### Dependency Risks

**Risk: Schema drift между backend и worker ORM-моделями**
- **Impact**: High — runtime errors при несовпадении column types
- **Likelihood**: Medium — backend развивается быстрее
- **Mitigation**: CI job сравнивающий model definitions. Alembic migrations только в backend — worker использует read-only (кроме notification_queue status updates). Manual sync process documented.
- **Fallback**: Shared package migration в future version.

**Risk: TaskIQ framework breaking changes**
- **Impact**: Medium — необходимость рефакторинга
- **Likelihood**: Low — stable API since v0.11
- **Mitigation**: Pinned versions в pyproject.toml. Dependabot для security updates only. Comprehensive test suite validates API surface.
- **Fallback**: Fork и maintenance.

### Scope Risks

**Risk: Feature creep — добавление новых типов задач**
- **Impact**: Low — модульная архитектура позволяет добавлять
- **Likelihood**: High — бизнес-требования растут
- **Mitigation**: Каждый новый тип задачи = отдельный PR. Feature flag через config. Модульная структура tasks/ позволяет изолированное добавление.

**Risk: Недооценка сложности Remnawave API интеграции**
- **Impact**: Medium — задержка Phase 3-4
- **Likelihood**: Medium — API может иметь undocumented quirks
- **Mitigation**: Реиспользовать паттерны из существующего backend RemnawaveClient. Thorough error handling. Mock API для тестов.
- **Fallback**: Fallback к direct PostgreSQL queries через общую БД Remnawave (не рекомендуется).

---

## 12. Constraints & Assumptions

### Constraints
1. **Python 3.13+** — совпадает с backend, не downgrade
2. **TaskIQ** — не Celery, не ARQ, не Dramatiq (требование пользователя)
3. **RedisStreamBroker** — не PubSub/ListQueue (требование пользователя)
4. **Собственные ORM-модели** — не shared package, не import из backend (требование пользователя)
5. **Prometheus + Grafana** — полная observability (требование пользователя)
6. **Valkey 8.1** — существующий Redis-compatible, не добавлять дополнительную инфраструктуру
7. **PostgreSQL 17.7** — существующая БД, не создавать отдельную
8. **Docker Compose** — интеграция через profiles в существующий stack

### Assumptions
1. Remnawave API доступен по HTTP на порту 3000 и поддерживает Bearer token auth
2. Telegram Bot API доступен без VPN/прокси из Docker-контейнера
3. CryptoBot API доступен и настроен с валидным API token
4. PostgreSQL schema создаётся и мигрируется backend-сервисом (worker не запускает migrations)
5. Redis/Valkey имеет достаточно памяти для task queue + result backend + cache (минимум 256MB)
6. Один инстанс scheduler (singleton) достаточен — горизонтально масштабируются только workers
7. Все временные метки в UTC
8. Admin dashboard будет адаптирован для отображения прогресса bulk-операций (отдельная задача frontend)

---

## 13. Appendix

### Glossary

| Термин | Описание |
|--------|----------|
| **TaskIQ** | Async-first distributed task queue для Python |
| **RedisStreamBroker** | TaskIQ broker на базе Redis Streams с ACK support |
| **Kicker** | TaskIQ объект для формирования и отправки задачи (`.kiq()`) |
| **Consumer Group** | Redis Streams механизм для распределения задач между воркерами |
| **ACK (Acknowledgment)** | Подтверждение успешной обработки задачи |
| **Schedule Source** | TaskIQ компонент для хранения cron-расписаний в Redis |
| **Middleware** | TaskIQ перехватчик для cross-cutting concerns (logging, metrics, retry) |
| **Remnawave** | VPN backend management platform (xray-core based) |
| **Valkey** | Open-source Redis-compatible in-memory data store |
| **CryptoBot** | Telegram-based cryptocurrency payment gateway |

### References

- [TaskIQ Documentation](https://taskiq-python.github.io/)
- [TaskIQ GitHub](https://github.com/taskiq-python/taskiq)
- [TaskIQ-Redis](https://github.com/taskiq-python/taskiq-redis) — brokers и result backends
- [TaskIQ-FastAPI](https://github.com/taskiq-python/taskiq-fastapi) — интеграция с FastAPI
- [Redis Streams](https://redis.io/docs/data-types/streams/) — underlying transport
- [Remnawave API](http://localhost:3000) — VPN backend (local)
- [Telegram Bot API](https://core.telegram.org/bots/api) — notification delivery
- [CryptoBot API](https://help.crypt.bot/crypto-pay-api) — payment processing

### Open Questions

1. **Remnawave API rate limits**: Какой максимальный RPS поддерживает Remnawave API? (нужно тестировать)
2. **Auto-renew flow**: Поддерживает ли CryptoBot recurring payments или только one-time invoices?
3. **Export storage**: Использовать S3/MinIO для экспортов или локальный volume?
4. **Multi-region**: Нужна ли поддержка нескольких task-worker инстансов в разных регионах?
5. **Backend API для dispatch**: Нужен ли REST endpoint в worker для отправки задач (помимо прямого `.kiq()`)?

---

## 14. Task Master Integration

### Как Task Master обрабатывает этот PRD

1. **Capabilities → Main Tasks**: Каждая из 9 Capabilities становится main task
2. **Features → Subtasks**: Каждая Feature становится subtask
3. **Dependencies**: Dependency Chain определяет порядок выполнения
4. **Phases → Priority**: Phase 0 = highest, Phase 8 = lowest

### Рекомендуемый порядок парсинга

```bash
# 1. Парсинг PRD
task-master parse-prd .taskmaster/docs/task-worker-service.md --append

# 2. Анализ сложности
task-master analyze-complexity --research

# 3. Расширение задач в subtasks
task-master expand --all --research

# 4. Начало работы
task-master next
```

### Маппинг Capabilities → Tasks

| Capability | Expected Task ID | Priority |
|-----------|-----------------|----------|
| Foundation (Phase 0) | Task N+1 | Highest |
| Data Access (Phase 1) | Task N+2 | High |
| Notification Processing (Phase 2) | Task N+3 | High (Critical Path) |
| Server Health Monitoring (Phase 3) | Task N+4 | High |
| Subscription Lifecycle (Phase 4) | Task N+5 | Medium-High |
| Payment Processing (Phase 5) | Task N+6 | Medium-High |
| Analytics & Sync (Phase 6) | Task N+7 | Medium |
| Bulk Operations (Phase 7) | Task N+8 | Medium |
| Middleware & Hardening (Phase 8) | Task N+9 | Standard |

(N = текущий максимальный task ID в tasks.json)
