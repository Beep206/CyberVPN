# Построение VPN-сервиса с Remnawave: Полный технический план реализации

**Экосистема Remnawave предоставляет production-ready VPN-панель с SDK на Python, TypeScript, Go и Rust**, что позволяет быстро разработать подписочный VPN-сервис. Этот документ содержит проверенные технические спецификации, исправленные версии фреймворков и паттерны реализации, оптимизированные для поддержки соло-разработчиком.

**Критические исправления версий:** FastAPI 0.128 не существует — последняя стабильная версия **0.121.2** (ноябрь 2025). Next.js **16.1.5** подтверждён как январский релиз 2026. React **19.2.4** и aiogram **3.24.0** — актуальные версии.

---

## Содержание

1. [Архитектура экосистемы Remnawave и возможности SDK](#1-архитектура-экосистемы-remnawave-и-возможности-sdk)
2. [FastAPI Backend: паттерны реализации](#2-fastapi-backend-паттерны-реализации)
3. [Next.js 16 Frontend: архитектура](#3-nextjs-16-frontend-архитектура)
4. [Aiogram 3: Telegram-бот с платежами Stars](#4-aiogram-3-telegram-бот-с-платежами-stars)
5. [React 19 Admin Panel с Refine](#5-react-19-admin-panel-с-refine)
6. [Схема базы данных](#6-схема-базы-данных)
7. [Интеграция платёжных шлюзов](#7-интеграция-платёжных-шлюзов)
8. [Реферальная система](#8-реферальная-система)
9. [Деплой и мониторинг](#9-деплой-и-мониторинг)
10. [Чеклист безопасности](#10-чеклист-безопасности)
11. [Пошаговый план реализации](#11-пошаговый-план-реализации)

---

## 1. Архитектура экосистемы Remnawave и возможности SDK

### 1.1 Обзор репозиториев

Организация Remnawave поддерживает **16 публичных репозиториев** с декомпозированной микросервисной архитектурой.

| Репозиторий | Назначение | Технологии |
|-------------|------------|------------|
| `panel` | Основная панель управления | NestJS 11.x, PostgreSQL 17, BullMQ |
| `python-sdk` | Python SDK | httpx, Pydantic |
| `backend-contract` | TypeScript типы | Только типизация |
| `remnawave-api-go` | Go SDK | net/http |
| `remnawave` (Rust) | Rust SDK | reqwest, serde |

### 1.2 Типы инстансов панели

Панель деплоится как три типа инстансов:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Instance                           │
│  • Горизонтально масштабируемый                            │
│  • REST эндпоинты                                          │
│  • Можно запускать несколько реплик                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Scheduler Instance                        │
│  • Singleton (только 1 экземпляр!)                         │
│  • Cron-задачи                                              │
│  • Миграции БД                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Processor Instance                        │
│  • Singleton (только 1 экземпляр!)                         │
│  • Background jobs (BullMQ)                                │
│  • Обработка вебхуков                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Доступные SDK

| SDK | Пакет | Версия | Установка |
|-----|-------|--------|-----------|
| **Python** | `remnawave` | 2.4.4 | `pip install remnawave` |
| **Rust** | `remnawave` | 2.2.4 | `cargo add remnawave` |
| **TypeScript** | `@remnawave/backend-contract` | 2.5.13 | Только типы, нужен свой HTTP-клиент |
| **Go** | `remnawave-api-go` | v2 | `go get github.com/Jolymmiles/remnawave-api-go/v2` |

### 1.4 Python SDK — детальный обзор

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — это основа интеграции твоего FastAPI с Remnawave.

```python
from remnawave import RemnawaveSDK
import os

# Инициализация SDK
remnawave = RemnawaveSDK(
    base_url="https://panel.example.com",
    token=os.environ["REMNAWAVE_TOKEN"],
    caddy_token="optional-caddy-auth"  # Если используешь Caddy
)

# Получение всех пользователей
users = await remnawave.users.get_all_users_v2()

# Создание пользователя
new_user = await remnawave.users.create_user(
    username="user_12345",
    traffic_limit_bytes=107374182400,  # 100 GB
    expire_at="2024-12-31T23:59:59Z"
)

# Отключение пользователя
await remnawave.users.disable_user("user-uuid")

# Получение ссылки подписки
sub_link = await remnawave.users.get_subscription_link("user-uuid")
```

**Доступные контроллеры SDK:**

| Контроллер | Методы | Использование |
|------------|--------|---------------|
| `users` | CRUD, enable/disable, get_subscription_link | Управление подписчиками |
| `nodes` | get_all, get_one, health_check | Мониторинг нод |
| `system` | get_stats, get_bandwidth | Статистика системы |
| `inbounds` | get_all, update | Настройка протоколов |

### 1.5 Система вебхуков

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — вебхуки позволяют реагировать на события без polling.

Remnawave поддерживает **25+ типов событий**:

| Категория | События | Применение |
|-----------|---------|------------|
| **User** | `user.created`, `user.expired`, `user.expires_in_24_hours`, `user.first_connected`, `user.bandwidth_usage_threshold_reached` | Уведомления, автопродление |
| **Node** | `node.created`, `node.offline`, `node.online` | Алертинг |
| **Service** | `service.started`, `service.stopped` | Мониторинг |

**Конфигурация через переменные окружения:**

```bash
WEBHOOK_ENABLED=true
WEBHOOK_URL=https://api.example.com/webhook/remnawave
WEBHOOK_SECRET_KEY=your-secret-key-min-32-chars
```

**Валидация подписи (ОБЯЗАТЕЛЬНО!):**

```python
import hmac
import hashlib
import json

def validate_remnawave_webhook(body: dict, signature: str, secret: str) -> bool:
    """
    Валидация HMAC-SHA256 подписи вебхука Remnawave.
    
    ВНИМАНИЕ: Используй hmac.compare_digest для защиты от timing attacks!
    """
    computed = hmac.new(
        secret.encode('utf-8'),
        json.dumps(body, separators=(',', ':')).encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)
```

**Пример обработчика вебхуков FastAPI:**

```python
from fastapi import APIRouter, Request, HTTPException, Header

router = APIRouter()

@router.post("/webhook/remnawave")
async def handle_remnawave_webhook(
    request: Request,
    x_webhook_signature: str = Header(...)
):
    body = await request.json()
    
    if not validate_remnawave_webhook(body, x_webhook_signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    event_type = body.get("event")
    
    match event_type:
        case "user.expired":
            await handle_user_expired(body["data"])
        case "user.expires_in_24_hours":
            await send_expiration_reminder(body["data"])
        case "user.first_connected":
            await track_first_connection(body["data"])
        case _:
            logger.info(f"Unhandled event: {event_type}")
    
    return {"status": "ok"}
```

---

## 2. FastAPI Backend: паттерны реализации

### 2.1 Версия и зависимости

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — правильные версии = стабильность.

```toml
# pyproject.toml
[project]
name = "vpn-backend"
version = "1.0.0"
requires-python = ">=3.12"

dependencies = [
    # Core
    "fastapi[standard]>=0.121.0,<0.122.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    
    # Database
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    
    # HTTP Client
    "httpx>=0.28.0",
    
    # Background Tasks
    "arq>=0.26.0",
    "redis>=5.2.0",
    
    # Security
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # Rate Limiting
    "slowapi>=0.1.9",
    
    # Monitoring
    "prometheus-fastapi-instrumentator>=7.0.0",
    "sentry-sdk[fastapi]>=2.19.0",
    
    # Remnawave SDK
    "remnawave>=2.4.4",
]
```

### 2.2 Структура проекта

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — правильная структура = поддерживаемость.

```
vpn-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Точка входа, lifespan, middleware
│   ├── config.py               # Pydantic Settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency Injection
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # Агрегирующий роутер
│   │       ├── auth.py         # Аутентификация
│   │       ├── users.py        # Пользователи
│   │       ├── subscriptions.py
│   │       ├── payments.py
│   │       ├── referrals.py
│   │       └── webhooks.py     # Вебхуки от Remnawave и платёжек
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, хеширование
│   │   └── rate_limit.py       # slowapi конфиг
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py          # AsyncSession factory
│   │   ├── models/             # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── subscription.py
│   │   │   ├── payment.py
│   │   │   └── referral.py
│   │   └── repositories/       # CRUD операции
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── user_repo.py
│   │       └── subscription_repo.py
│   │
│   ├── services/               # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── remnawave_service.py
│   │   ├── subscription_service.py
│   │   ├── payment_service.py
│   │   └── notification_service.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── subscription.py
│   │   └── payment.py
│   │
│   └── tasks/                  # ARQ workers
│       ├── __init__.py
│       ├── worker.py           # ARQ worker config
│       ├── subscription_tasks.py
│       └── notification_tasks.py
│
├── migrations/                 # Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

### 2.3 Конфигурация приложения

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — безопасное управление секретами.

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # App
    APP_NAME: str = "VPN Service API"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Remnawave
    REMNAWAVE_URL: str
    REMNAWAVE_TOKEN: str
    REMNAWAVE_WEBHOOK_SECRET: str
    
    # Payment Providers
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    XENDIT_API_KEY: str = ""
    CRYPTOPAY_TOKEN: str = ""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 2.4 Lifespan и Middleware

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — правильная инициализация ресурсов.

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk

from app.config import get_settings
from app.api.v1.router import api_router
from app.core.rate_limit import limiter
from app.db.session import engine

settings = get_settings()

# Sentry инициализация
if not settings.DEBUG:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    
    Startup:
    - Создание HTTP клиента для Remnawave
    - Подключение к Redis
    
    Shutdown:
    - Закрытие всех соединений
    """
    # Startup
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        http2=True
    )
    app.state.settings = settings
    
    yield
    
    # Shutdown
    await app.state.http_client.aclose()
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # В проде указать конкретные домены!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(429, limiter._rate_limit_exceeded_handler)

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Routes
app.include_router(api_router, prefix="/api/v1")
```

### 2.5 Dependency Injection

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — чистый код и тестируемость.

```python
# app/api/deps.py
from typing import Annotated, AsyncGenerator
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.db.session import async_session_maker
from app.config import get_settings, Settings
from app.services.remnawave_service import RemnawaveService
from app.db.repositories.user_repo import UserRepository

settings = get_settings()

# Database Session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Remnawave Service
def get_remnawave_service(request: Request) -> RemnawaveService:
    return RemnawaveService(
        http_client=request.app.state.http_client,
        base_url=settings.REMNAWAVE_URL,
        token=settings.REMNAWAVE_TOKEN
    )

RemnawaveDep = Annotated[RemnawaveService, Depends(get_remnawave_service)]

# Current User (JWT)
async def get_current_user(
    request: Request,
    db: DbSession,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise credentials_exception
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if user is None:
        raise credentials_exception
    
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]
```

### 2.6 Rate Limiting

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — защита от DDoS и abuse.

```python
# app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_user_identifier(request):
    """
    Для авторизованных — по user_id, для анонимных — по IP.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            # Извлекаем user_id из токена
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return f"user:{payload.get('sub')}"
        except:
            pass
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["200/hour"],
    storage_uri="redis://localhost:6379",
    strategy="fixed-window"
)

# Использование в эндпоинтах
@router.get("/subscription")
@limiter.limit("30/minute")  # 30 запросов в минуту
async def get_subscription(request: Request, user: CurrentUser):
    pass

@router.post("/payment/create")
@limiter.limit("5/minute")  # Строже для финансовых операций
async def create_payment(request: Request, user: CurrentUser):
    pass
```

### 2.7 Background Tasks с ARQ

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — асинхронная обработка без блокировки.

```python
# app/tasks/worker.py
from arq import create_pool
from arq.connections import RedisSettings
from app.config import get_settings

settings = get_settings()

async def startup(ctx):
    """Инициализация при старте воркера."""
    ctx["http_client"] = httpx.AsyncClient()
    ctx["db_pool"] = await create_db_pool()

async def shutdown(ctx):
    """Очистка при остановке."""
    await ctx["http_client"].aclose()
    await ctx["db_pool"].close()

class WorkerSettings:
    functions = [
        "app.tasks.subscription_tasks.check_expiring_subscriptions",
        "app.tasks.subscription_tasks.process_subscription_renewal",
        "app.tasks.notification_tasks.send_telegram_notification",
        "app.tasks.notification_tasks.send_expiration_reminder",
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300  # 5 минут

# app/tasks/subscription_tasks.py
async def check_expiring_subscriptions(ctx):
    """
    Cron-задача: проверка подписок, истекающих через 24 часа.
    Запускается каждый час.
    """
    db = ctx["db_pool"]
    
    expiring = await get_expiring_subscriptions(db, hours=24)
    
    for subscription in expiring:
        await ctx["redis"].enqueue_job(
            "send_expiration_reminder",
            subscription.user_id,
            subscription.end_date
        )

async def process_subscription_renewal(ctx, user_id: int, plan_id: int):
    """
    Обработка автопродления подписки после успешного платежа.
    """
    pass
```

**Запуск воркера:**

```bash
arq app.tasks.worker.WorkerSettings
```

### 2.8 Сервис Remnawave

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — основная бизнес-логика.

```python
# app/services/remnawave_service.py
import httpx
from typing import Optional
from datetime import datetime, timedelta

class RemnawaveService:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str, token: str):
        self.client = http_client
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Базовый метод для запросов с retry-логикой."""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(3):
            try:
                response = await self.client.request(
                    method, url, headers=self.headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
    
    async def create_vpn_user(
        self,
        username: str,
        traffic_limit_gb: int = 100,
        expire_days: int = 30,
        max_devices: int = 3
    ) -> dict:
        """
        Создание пользователя VPN в Remnawave.
        
        Returns:
            dict с uuid, subscription_url, и другими данными
        """
        expire_at = (datetime.utcnow() + timedelta(days=expire_days)).isoformat() + "Z"
        
        return await self._request("POST", "/api/users", json={
            "username": username,
            "trafficLimitBytes": traffic_limit_gb * 1024 * 1024 * 1024,
            "expireAt": expire_at,
            "hwidDeviceLimit": max_devices
        })
    
    async def get_subscription_link(self, user_uuid: str) -> str:
        """Получение ссылки подписки для клиентского приложения."""
        result = await self._request("GET", f"/api/users/{user_uuid}/subscription")
        return result["subscriptionUrl"]
    
    async def extend_subscription(self, user_uuid: str, days: int) -> dict:
        """Продление подписки на N дней."""
        return await self._request("PATCH", f"/api/users/{user_uuid}/extend", json={
            "days": days
        })
    
    async def disable_user(self, user_uuid: str) -> dict:
        """Отключение пользователя (при неоплате)."""
        return await self._request("POST", f"/api/users/{user_uuid}/disable")
    
    async def enable_user(self, user_uuid: str) -> dict:
        """Включение пользователя (после оплаты)."""
        return await self._request("POST", f"/api/users/{user_uuid}/enable")
    
    async def get_user_stats(self, user_uuid: str) -> dict:
        """Статистика использования трафика."""
        return await self._request("GET", f"/api/users/{user_uuid}/stats")
    
    async def get_all_nodes(self) -> list:
        """Список всех нод с их статусом."""
        result = await self._request("GET", "/api/nodes")
        return result["nodes"]
    
    async def get_system_stats(self) -> dict:
        """Общая статистика системы."""
        return await self._request("GET", "/api/system/stats")
```

---

## 3. Next.js 16 Frontend: архитектура

### 3.1 Ключевые фичи Next.js 16

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — используй новые возможности!

| Фича | Описание | Применение |
|------|----------|------------|
| **Turbopack по умолчанию** | 5-10x быстрее Fast Refresh | Ускорение разработки |
| **Cache Components** (`"use cache"`) | Кеширование на уровне компонентов | Лендинг, статичные страницы |
| **`proxy.ts`** вместо `middleware.ts` | Более понятное именование | Auth redirect, i18n |
| **React 19 support** | Новые хуки и паттерны | Современный UI |

### 3.2 Структура проекта

```
vpn-frontend/
├── app/
│   ├── [locale]/                    # i18n: en, hi, id, ru
│   │   ├── (marketing)/             # Landing pages (Server Components)
│   │   │   ├── page.tsx             # Главная
│   │   │   ├── pricing/page.tsx     # Тарифы
│   │   │   ├── features/page.tsx    # Возможности
│   │   │   └── layout.tsx
│   │   │
│   │   ├── (dashboard)/             # User portal (Client Components)
│   │   │   ├── dashboard/page.tsx   # Дашборд пользователя
│   │   │   ├── subscription/page.tsx
│   │   │   ├── qr-config/page.tsx   # QR код конфига
│   │   │   ├── referrals/page.tsx
│   │   │   └── layout.tsx
│   │   │
│   │   └── layout.tsx               # Root layout с провайдерами
│   │
│   ├── api/                         # API Routes
│   │   ├── auth/[...nextauth]/route.ts
│   │   └── subscription/route.ts
│   │
│   └── proxy.ts                     # Auth + i18n middleware
│
├── components/
│   ├── ui/                          # shadcn/ui компоненты
│   ├── marketing/                   # Компоненты лендинга
│   └── dashboard/                   # Компоненты дашборда
│
├── lib/
│   ├── api.ts                       # API client
│   ├── auth.ts                      # NextAuth config
│   └── i18n.ts                      # Internationalization
│
├── messages/                        # Переводы
│   ├── en.json
│   ├── hi.json
│   ├── id.json
│   └── ru.json
│
├── hooks/
│   ├── use-subscription.ts
│   └── use-referrals.ts
│
└── next.config.ts
```

### 3.3 Настройка Internationalization

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — локализация = конверсия на целевых рынках.

```typescript
// lib/i18n.ts
import { getRequestConfig } from 'next-intl/server';
import { notFound } from 'next/navigation';

export const locales = ['en', 'hi', 'id', 'ru'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'en';

export default getRequestConfig(async ({ locale }) => {
  if (!locales.includes(locale as Locale)) notFound();
  
  return {
    messages: (await import(`../messages/${locale}.json`)).default,
    timeZone: getTimeZoneForLocale(locale as Locale),
    now: new Date(),
  };
});

function getTimeZoneForLocale(locale: Locale): string {
  const timezones: Record<Locale, string> = {
    en: 'UTC',
    hi: 'Asia/Kolkata',
    id: 'Asia/Jakarta',
    ru: 'Europe/Moscow',
  };
  return timezones[locale];
}
```

```typescript
// proxy.ts (бывший middleware.ts)
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from './lib/i18n';

export default createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'as-needed'
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)']
};
```

**Пример файла переводов (messages/ru.json):**

```json
{
  "common": {
    "subscribe": "Подписаться",
    "login": "Войти",
    "logout": "Выйти"
  },
  "pricing": {
    "title": "Выберите тариф",
    "monthly": "Ежемесячно",
    "yearly": "Ежегодно",
    "save": "Экономия {percent}%"
  },
  "dashboard": {
    "subscription": {
      "active": "Подписка активна",
      "expires": "Истекает {date}",
      "dataUsed": "Использовано {used} из {total} ГБ"
    }
  }
}
```

### 3.4 Real-time подписка с SWR

**⚠️ ВАЖНОСТЬ: СРЕДНЯЯ** — SWR проще TanStack Query для этого кейса.

```typescript
// hooks/use-subscription.ts
import useSWR from 'swr';

interface Subscription {
  id: string;
  status: 'active' | 'expired' | 'pending';
  plan: string;
  expiresAt: string;
  dataUsedBytes: number;
  dataLimitBytes: number;
  configUrl: string;
}

const fetcher = (url: string) => 
  fetch(url, { credentials: 'include' }).then(res => res.json());

export function useSubscription() {
  const { data, error, isLoading, mutate } = useSWR<Subscription>(
    '/api/subscription',
    fetcher,
    {
      refreshInterval: 30000,        // Polling каждые 30 сек
      revalidateOnFocus: true,       // Обновление при фокусе на вкладке
      dedupingInterval: 5000,        // Дедупликация запросов
      errorRetryCount: 3,
    }
  );

  return {
    subscription: data,
    isLoading,
    isError: error,
    refresh: mutate,
  };
}
```

### 3.5 QR-код конфигурации

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — UX для мобильных пользователей.

```typescript
// components/dashboard/config-qr.tsx
'use client';

import { QRCodeSVG } from 'qrcode.react';
import { useSubscription } from '@/hooks/use-subscription';
import { Button } from '@/components/ui/button';
import { Copy, Download } from 'lucide-react';

export function ConfigQR() {
  const { subscription, isLoading } = useSubscription();
  
  if (isLoading) return <Skeleton className="w-64 h-64" />;
  if (!subscription?.configUrl) return null;
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(subscription.configUrl);
    toast.success('Ссылка скопирована!');
  };
  
  return (
    <div className="flex flex-col items-center gap-4">
      <QRCodeSVG 
        value={subscription.configUrl}
        size={256}
        level="H"
        includeMargin
      />
      
      <div className="flex gap-2">
        <Button variant="outline" onClick={copyToClipboard}>
          <Copy className="w-4 h-4 mr-2" />
          Копировать
        </Button>
        <Button variant="outline" asChild>
          <a href={subscription.configUrl}>
            <Download className="w-4 h-4 mr-2" />
            Открыть
          </a>
        </Button>
      </div>
      
      <p className="text-sm text-muted-foreground text-center">
        Отсканируйте QR-код в приложении V2rayNG, Streisand или Hiddify
      </p>
    </div>
  );
}
```

---

## 4. Aiogram 3: Telegram-бот с платежами Stars

### 4.1 Структура бота

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — бот = основной канал продаж.

```
vpn-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py                 # Точка входа
│   ├── config.py               # Настройки
│   │
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py            # /start, deep links
│   │   ├── subscription.py     # Управление подпиской
│   │   ├── payment.py          # Платежи Stars
│   │   ├── referral.py         # Реферальная система
│   │   └── support.py          # FAQ, поддержка
│   │
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── main.py             # Главное меню
│   │   ├── plans.py            # Выбор тарифа
│   │   └── inline.py           # Inline-кнопки
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth.py             # Проверка/создание юзера
│   │   ├── i18n.py             # Локализация
│   │   └── throttling.py       # Anti-spam
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── api_client.py       # Клиент к FastAPI
│   │   └── subscription.py     # Логика подписок
│   │
│   ├── states/
│   │   ├── __init__.py
│   │   └── subscription.py     # FSM states
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── i18n.py             # Fluent локализация
│   │
│   └── locales/                # Переводы
│       ├── en/
│       ├── hi/
│       ├── id/
│       └── ru/
│
├── Dockerfile
└── pyproject.toml
```

### 4.2 Конфигурация и запуск

```python
# bot/config.py
from pydantic_settings import BaseSettings

class BotSettings(BaseSettings):
    BOT_TOKEN: str
    API_BASE_URL: str = "http://localhost:8000/api/v1"
    API_KEY: str
    
    REDIS_URL: str = "redis://localhost:6379"
    
    WEBHOOK_HOST: str = ""
    WEBHOOK_PATH: str = "/webhook/telegram"
    
    # Тарифы в Stars
    PLAN_MONTHLY_STARS: int = 100      # ~$2
    PLAN_QUARTERLY_STARS: int = 250    # ~$5
    PLAN_YEARLY_STARS: int = 800       # ~$16
    
    class Config:
        env_file = ".env"

settings = BotSettings()
```

```python
# bot/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import settings
from bot.handlers import start, subscription, payment, referral
from bot.middlewares import AuthMiddleware, I18nMiddleware, ThrottlingMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    if settings.WEBHOOK_HOST:
        await bot.set_webhook(
            f"{settings.WEBHOOK_HOST}{settings.WEBHOOK_PATH}",
            secret_token=settings.BOT_TOKEN[:32]
        )
        logger.info("Webhook установлен")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logger.info("Webhook удалён")

def create_dispatcher() -> Dispatcher:
    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        state_ttl=3600,
        data_ttl=3600
    )
    
    dp = Dispatcher(storage=storage)
    
    # Middlewares (порядок важен!)
    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(I18nMiddleware())
    
    dp.callback_query.middleware(AuthMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    
    # Handlers
    dp.include_router(start.router)
    dp.include_router(subscription.router)
    dp.include_router(payment.router)
    dp.include_router(referral.router)
    
    return dp

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = create_dispatcher()
    
    if settings.WEBHOOK_HOST:
        # Webhook mode (production)
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        app = web.Application()
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.BOT_TOKEN[:32]
        )
        webhook_handler.register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        
        await web._run_app(app, host="0.0.0.0", port=8080)
    else:
        # Polling mode (development)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.3 Обработчик /start с Deep Links

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — точка входа для рефералов.

```python
# bot/handlers/start.py
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from aiogram.utils.deep_linking import decode_payload

from bot.keyboards.main import get_main_keyboard
from bot.services.api_client import APIClient

router = Router()

@router.message(CommandStart(deep_link=True))
async def start_with_referral(
    message: Message, 
    command: CommandObject,
    api_client: APIClient,
    i18n: dict
):
    """
    Обработка /start с реферальной ссылкой.
    Формат: /start ref_12345 или закодированный payload
    """
    referrer_id = None
    
    if command.args:
        try:
            # Попытка декодировать
            payload = decode_payload(command.args)
        except:
            payload = command.args
        
        if payload.startswith("ref_"):
            referrer_id = int(payload[4:])
    
    # Регистрация/обновление пользователя
    user = await api_client.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        language=message.from_user.language_code or "en",
        referrer_id=referrer_id
    )
    
    # Приветственное сообщение
    if referrer_id:
        text = i18n["start"]["welcome_referred"].format(
            name=message.from_user.first_name
        )
    else:
        text = i18n["start"]["welcome"].format(
            name=message.from_user.first_name
        )
    
    await message.answer(
        text,
        reply_markup=get_main_keyboard(i18n)
    )

@router.message(CommandStart())
async def start_regular(message: Message, api_client: APIClient, i18n: dict):
    """Обычный /start без параметров."""
    await api_client.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        language=message.from_user.language_code or "en"
    )
    
    await message.answer(
        i18n["start"]["welcome"].format(name=message.from_user.first_name),
        reply_markup=get_main_keyboard(i18n)
    )
```

### 4.4 Платежи Telegram Stars

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — монетизация через Telegram.

```python
# bot/handlers/payment.py
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, 
    CallbackQuery,
    LabeledPrice, 
    PreCheckoutQuery, 
    SuccessfulPayment
)
from aiogram.filters import Command

from bot.config import settings
from bot.keyboards.plans import get_plans_keyboard
from bot.services.api_client import APIClient

router = Router()

PLANS = {
    "monthly": {
        "stars": settings.PLAN_MONTHLY_STARS,
        "days": 30,
        "title_key": "plans.monthly.title",
        "description_key": "plans.monthly.description"
    },
    "quarterly": {
        "stars": settings.PLAN_QUARTERLY_STARS,
        "days": 90,
        "title_key": "plans.quarterly.title",
        "description_key": "plans.quarterly.description"
    },
    "yearly": {
        "stars": settings.PLAN_YEARLY_STARS,
        "days": 365,
        "title_key": "plans.yearly.title",
        "description_key": "plans.yearly.description"
    }
}

@router.callback_query(F.data.startswith("buy_plan:"))
async def send_invoice(
    callback: CallbackQuery, 
    bot: Bot,
    i18n: dict
):
    """Отправка инвойса для оплаты Stars."""
    plan_id = callback.data.split(":")[1]
    plan = PLANS.get(plan_id)
    
    if not plan:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return
    
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=i18n[plan["title_key"]],
        description=i18n[plan["description_key"]],
        provider_token="",              # Пусто для Stars!
        currency="XTR",                 # Код валюты Stars
        prices=[
            LabeledPrice(
                label=i18n[plan["title_key"]], 
                amount=plan["stars"]
            )
        ],
        payload=f"{plan_id}:{callback.from_user.id}",
        start_parameter=f"buy_{plan_id}"
    )
    
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    """
    Обязательный обработчик pre_checkout.
    Telegram ждёт ответ в течение 10 секунд!
    """
    # Здесь можно проверить доступность товара
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def payment_success(
    message: Message,
    api_client: APIClient,
    i18n: dict
):
    """
    Обработка успешного платежа.
    
    ВАЖНО: Сохраняй telegram_payment_charge_id для возвратов!
    """
    payment = message.successful_payment
    
    # Парсим payload
    plan_id, user_id = payment.invoice_payload.split(":")
    plan = PLANS[plan_id]
    
    # Активируем подписку через API
    result = await api_client.activate_subscription(
        telegram_id=int(user_id),
        plan_id=plan_id,
        days=plan["days"],
        payment_data={
            "method": "telegram_stars",
            "amount": payment.total_amount,
            "currency": "XTR",
            "charge_id": payment.telegram_payment_charge_id,
            "provider_charge_id": payment.provider_payment_charge_id
        }
    )
    
    if result["success"]:
        await message.answer(
            i18n["payment"]["success"].format(
                plan=i18n[plan["title_key"]],
                expires=result["subscription"]["expires_at"]
            ),
            reply_markup=get_subscription_keyboard(i18n)
        )
    else:
        # Логируем ошибку, но не пугаем юзера
        logger.error(f"Failed to activate subscription: {result}")
        await message.answer(
            i18n["payment"]["processing"],
        )
```

### 4.5 FSM для многошагового взаимодействия

```python
# bot/states/subscription.py
from aiogram.fsm.state import State, StatesGroup

class SubscriptionStates(StatesGroup):
    selecting_plan = State()
    awaiting_payment = State()
    entering_promo = State()

# bot/handlers/subscription.py
from aiogram import Router, F
from aiogram.fsm.context import FSMContext

router = Router()

@router.callback_query(F.data == "subscribe")
async def show_plans(callback: CallbackQuery, state: FSMContext, i18n: dict):
    """Показ тарифов."""
    await state.set_state(SubscriptionStates.selecting_plan)
    
    await callback.message.edit_text(
        i18n["subscription"]["select_plan"],
        reply_markup=get_plans_keyboard(i18n)
    )

@router.callback_query(
    SubscriptionStates.selecting_plan,
    F.data.startswith("select_plan:")
)
async def plan_selected(
    callback: CallbackQuery, 
    state: FSMContext,
    i18n: dict
):
    """Выбран тариф, показываем промокод или оплату."""
    plan_id = callback.data.split(":")[1]
    await state.update_data(selected_plan=plan_id)
    
    await callback.message.edit_text(
        i18n["subscription"]["promo_or_pay"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n["buttons"]["enter_promo"],
                    callback_data="enter_promo"
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n["buttons"]["pay_now"],
                    callback_data=f"buy_plan:{plan_id}"
                )
            ]
        ])
    )
```

### 4.6 Middleware для локализации

```python
# bot/middlewares/i18n.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
import json
from pathlib import Path

class I18nMiddleware(BaseMiddleware):
    def __init__(self, default_locale: str = "en"):
        self.default_locale = default_locale
        self.locales = {}
        self._load_locales()
    
    def _load_locales(self):
        locales_dir = Path(__file__).parent.parent / "locales"
        for locale_dir in locales_dir.iterdir():
            if locale_dir.is_dir():
                locale = locale_dir.name
                messages_file = locale_dir / "messages.json"
                if messages_file.exists():
                    with open(messages_file, "r", encoding="utf-8") as f:
                        self.locales[locale] = json.load(f)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        
        if user:
            # Определяем язык пользователя
            lang = user.language_code or self.default_locale
            
            # Маппинг языковых кодов
            lang_map = {
                "ru": "ru",
                "hi": "hi",
                "id": "id",
                "en": "en"
            }
            
            locale = lang_map.get(lang[:2], self.default_locale)
            data["i18n"] = self.locales.get(locale, self.locales[self.default_locale])
        else:
            data["i18n"] = self.locales[self.default_locale]
        
        return await handler(event, data)
```

---

## 5. React 19 Admin Panel с Refine

### 5.1 Почему Refine, а не React-Admin

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — правильный выбор = меньше кода.

| Критерий | Refine | React-Admin |
|----------|--------|-------------|
| Лицензия | MIT (всё бесплатно) | Enterprise фичи платные |
| Bundle size | ~50% меньше | Больше |
| Архитектура | Headless, hooks-based | Component-based |
| Кастомизация | Полная свобода | Ограничена компонентами |
| UI библиотеки | Любая (Ant, MUI, Mantine, Chakra) | Своя или MUI |

### 5.2 Структура проекта

```
vpn-admin/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   │
│   ├── providers/
│   │   ├── data-provider.ts      # FastAPI интеграция
│   │   ├── auth-provider.ts      # JWT auth
│   │   └── access-control.ts     # RBAC
│   │
│   ├── pages/
│   │   ├── dashboard/
│   │   │   └── index.tsx         # Главный дашборд
│   │   ├── users/
│   │   │   ├── list.tsx
│   │   │   └── show.tsx
│   │   ├── subscriptions/
│   │   │   ├── list.tsx
│   │   │   └── edit.tsx
│   │   ├── payments/
│   │   │   └── list.tsx
│   │   ├── nodes/
│   │   │   └── list.tsx
│   │   └── analytics/
│   │       └── index.tsx
│   │
│   ├── components/
│   │   ├── charts/
│   │   │   ├── RevenueChart.tsx
│   │   │   ├── UsersChart.tsx
│   │   │   └── TrafficChart.tsx
│   │   └── widgets/
│   │       ├── StatsCard.tsx
│   │       └── NodeStatus.tsx
│   │
│   └── lib/
│       └── api.ts
│
├── package.json
└── vite.config.ts
```

### 5.3 Data Provider для FastAPI

```typescript
// src/providers/data-provider.ts
import { DataProvider } from "@refinedev/core";

const API_URL = import.meta.env.VITE_API_URL;

export const dataProvider: DataProvider = {
  getList: async ({ resource, pagination, sorters, filters }) => {
    const { current = 1, pageSize = 10 } = pagination ?? {};
    
    const params = new URLSearchParams({
      skip: String((current - 1) * pageSize),
      limit: String(pageSize),
    });
    
    // Сортировка
    if (sorters && sorters.length > 0) {
      params.append("sort_by", sorters[0].field);
      params.append("sort_order", sorters[0].order);
    }
    
    // Фильтры
    filters?.forEach(filter => {
      if ("field" in filter) {
        params.append(`filter[${filter.field}]`, String(filter.value));
      }
    });
    
    const response = await fetch(`${API_URL}/${resource}?${params}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    });
    
    const data = await response.json();
    
    return {
      data: data.items,
      total: data.total,
    };
  },

  getOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    });
    
    return { data: await response.json() };
  },

  create: async ({ resource, variables }) => {
    const response = await fetch(`${API_URL}/${resource}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
      body: JSON.stringify(variables),
    });
    
    return { data: await response.json() };
  },

  update: async ({ resource, id, variables }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
      body: JSON.stringify(variables),
    });
    
    return { data: await response.json() };
  },

  deleteOne: async ({ resource, id }) => {
    await fetch(`${API_URL}/${resource}/${id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    });
    
    return { data: { id } };
  },

  getApiUrl: () => API_URL,
};
```

### 5.4 Dashboard с аналитикой

```typescript
// src/pages/dashboard/index.tsx
import { useList, useCustom } from "@refinedev/core";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function Dashboard() {
  // Статистика
  const { data: stats } = useCustom({
    url: "/stats/overview",
    method: "get",
  });

  // Выручка за последние 30 дней
  const { data: revenueData } = useCustom({
    url: "/stats/revenue",
    method: "get",
    config: {
      query: { days: 30 }
    }
  });

  // Активные подписки по тарифам
  const { data: planDistribution } = useCustom({
    url: "/stats/subscriptions-by-plan",
    method: "get",
  });

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28'];

  return (
    <div className="p-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatsCard
          title="Активных подписок"
          value={stats?.data?.activeSubscriptions || 0}
          change={stats?.data?.subscriptionsChange}
        />
        <StatsCard
          title="Выручка (месяц)"
          value={`$${stats?.data?.monthlyRevenue || 0}`}
          change={stats?.data?.revenueChange}
        />
        <StatsCard
          title="Новых за сегодня"
          value={stats?.data?.newToday || 0}
        />
        <StatsCard
          title="Онлайн сейчас"
          value={stats?.data?.onlineNow || 0}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Выручка за 30 дней</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={revenueData?.data || []}>
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area 
                  type="monotone" 
                  dataKey="revenue" 
                  stroke="#8884d8" 
                  fill="#8884d8" 
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Plan Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Распределение по тарифам</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={planDistribution?.data || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="count"
                  nameKey="plan"
                  label
                >
                  {planDistribution?.data?.map((entry, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Node Status */}
      <Card>
        <CardHeader>
          <CardTitle>Статус нод</CardTitle>
        </CardHeader>
        <CardContent>
          <NodeStatusGrid />
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## 6. Схема базы данных

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — фундамент всего приложения.

```sql
-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum типы
CREATE TYPE subscription_status AS ENUM ('pending', 'active', 'expired', 'cancelled');
CREATE TYPE payment_method AS ENUM ('telegram_stars', 'upi', 'qris', 'crypto_usdt', 'crypto_ton');
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');

-- Пользователи
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    language VARCHAR(10) DEFAULT 'en',
    
    -- Реферальная система
    referral_code VARCHAR(20) UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(10), 'hex'),
    referred_by_user_id BIGINT REFERENCES users(id),
    referral_bonus_days INT DEFAULT 0,
    
    -- Remnawave связь
    remnawave_user_uuid VARCHAR(100) UNIQUE,
    
    -- Метаданные
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMPTZ
);

-- Индексы для users
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_referral_code ON users(referral_code);
CREATE INDEX idx_users_referred_by ON users(referred_by_user_id);

-- Тарифные планы
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) UNIQUE NOT NULL,  -- monthly, quarterly, yearly
    name VARCHAR(100) NOT NULL,
    duration_days INT NOT NULL,
    
    -- Цены в разных валютах
    price_usd DECIMAL(10,2) NOT NULL,
    price_telegram_stars INT NOT NULL,
    price_inr DECIMAL(10,2),           -- Индия (UPI)
    price_idr DECIMAL(12,2),           -- Индонезия (QRIS)
    
    -- Лимиты
    data_limit_gb INT,                 -- NULL = безлимит
    max_devices INT DEFAULT 3,
    
    -- Активность
    is_active BOOLEAN DEFAULT true,
    sort_order INT DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Начальные тарифы
INSERT INTO plans (slug, name, duration_days, price_usd, price_telegram_stars, price_inr, price_idr, data_limit_gb, max_devices) VALUES
('monthly', 'Monthly', 30, 2.00, 100, 169, 32000, 100, 3),
('quarterly', 'Quarterly', 90, 5.00, 250, 419, 79000, 300, 3),
('yearly', 'Yearly', 365, 16.00, 800, 1339, 255000, NULL, 5);

-- Подписки
CREATE TABLE subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    plan_id INT NOT NULL REFERENCES plans(id),
    
    status subscription_status DEFAULT 'pending',
    
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    
    -- Использование
    data_used_bytes BIGINT DEFAULT 0,
    
    -- Remnawave связь
    remnawave_user_uuid VARCHAR(100),
    subscription_url TEXT,
    
    -- Auto-renewal
    auto_renew BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для subscriptions
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_end_date ON subscriptions(end_date) WHERE status = 'active';
CREATE INDEX idx_subscriptions_active ON subscriptions(user_id, status) WHERE status = 'active';

-- Платежи
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    subscription_id BIGINT REFERENCES subscriptions(id),
    
    method payment_method NOT NULL,
    status payment_status DEFAULT 'pending',
    
    -- Суммы
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    amount_usd DECIMAL(10,2),          -- Конвертированная сумма для отчётов
    
    -- Внешние ID
    external_payment_id VARCHAR(255),  -- ID от провайдера
    telegram_charge_id VARCHAR(255),   -- Для возвратов Stars
    
    -- Метаданные
    metadata JSONB DEFAULT '{}',
    
    -- Идемпотентность
    idempotency_key VARCHAR(100) UNIQUE,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

-- Индексы для payments
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at);
CREATE INDEX idx_payments_idempotency ON payments(idempotency_key);

-- Реферальные транзакции
CREATE TABLE referral_transactions (
    id BIGSERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES users(id),
    referred_id BIGINT NOT NULL REFERENCES users(id),
    payment_id BIGINT REFERENCES payments(id),
    
    bonus_type VARCHAR(50) NOT NULL,   -- 'signup', 'first_payment', 'milestone'
    bonus_days INT NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для referrals
CREATE INDEX idx_referral_tx_referrer ON referral_transactions(referrer_id);
CREATE INDEX idx_referral_tx_referred ON referral_transactions(referred_id);

-- Audit log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

-- Функция обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## 7. Интеграция платёжных шлюзов

### 7.1 Razorpay (UPI для Индии)

**⚠️ ВАЖНОСТЬ: ВЫСОКАЯ** — 85% платежей в Индии через UPI.

```python
# app/services/razorpay_service.py
import razorpay
from app.config import get_settings

settings = get_settings()

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    
    async def create_order(
        self, 
        amount_inr: int,
        subscription_id: int,
        user_id: int
    ) -> dict:
        """
        Создание заказа Razorpay.
        amount_inr в пайсах (100 paise = 1 INR)
        """
        order = self.client.order.create({
            "amount": amount_inr * 100,  # В пайсах!
            "currency": "INR",
            "receipt": f"sub_{subscription_id}",
            "notes": {
                "user_id": str(user_id),
                "subscription_id": str(subscription_id)
            }
        })
        return order
    
    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> bool:
        """Верификация подписи вебхука."""
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

# Вебхук обработчик
@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    db: DbSession,
    subscription_service: SubscriptionService
):
    body = await request.json()
    signature = request.headers.get("X-Razorpay-Signature")
    
    # Верификация подписи
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        await request.body(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401)
    
    event = body.get("event")
    
    if event == "payment.captured":
        payment_data = body["payload"]["payment"]["entity"]
        await subscription_service.activate_from_razorpay(
            payment_id=payment_data["id"],
            order_id=payment_data["order_id"],
            amount=payment_data["amount"] / 100
        )
    
    return {"status": "ok"}
```

### 7.2 Xendit (QRIS для Индонезии)

```python
# app/services/xendit_service.py
import httpx
import base64
from app.config import get_settings

settings = get_settings()

class XenditService:
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
        self.base_url = "https://api.xendit.co"
        auth = base64.b64encode(f"{settings.XENDIT_API_KEY}:".encode()).decode()
        self.headers = {"Authorization": f"Basic {auth}"}
    
    async def create_qris(
        self,
        amount_idr: int,
        subscription_id: int,
        user_id: int
    ) -> dict:
        """Создание QRIS кода для оплаты."""
        response = await self.client.post(
            f"{self.base_url}/qr_codes",
            headers=self.headers,
            json={
                "reference_id": f"sub_{subscription_id}_{user_id}",
                "type": "DYNAMIC",
                "currency": "IDR",
                "amount": amount_idr,
                "callback_url": f"{settings.API_BASE_URL}/webhook/xendit",
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
            }
        )
        response.raise_for_status()
        return response.json()
    
    def verify_callback_token(self, token: str) -> bool:
        """Верификация callback token от Xendit."""
        return hmac.compare_digest(token, settings.XENDIT_CALLBACK_TOKEN)
```

### 7.3 CryptoPay (USDT/TON)

```python
# app/services/cryptopay_service.py
import httpx
from app.config import get_settings

settings = get_settings()

class CryptoPayService:
    def __init__(self, http_client: httpx.AsyncClient):
        self.client = http_client
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": settings.CRYPTOPAY_TOKEN}
    
    async def create_invoice(
        self,
        amount: float,
        asset: str,  # "USDT" или "TON"
        subscription_id: int,
        user_id: int
    ) -> dict:
        """Создание инвойса для криптоплатежа."""
        response = await self.client.post(
            f"{self.base_url}/createInvoice",
            headers=self.headers,
            json={
                "asset": asset,
                "amount": str(amount),
                "description": f"VPN Subscription #{subscription_id}",
                "hidden_message": f"user:{user_id}",
                "payload": f"{subscription_id}:{user_id}",
                "expires_in": 3600  # 1 час
            }
        )
        response.raise_for_status()
        return response.json()["result"]
    
    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Верификация подписи вебхука CryptoPay."""
        secret = hashlib.sha256(settings.CRYPTOPAY_TOKEN.encode()).digest()
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
```

---

## 8. Реферальная система

### 8.1 Генерация и трекинг

```python
# app/services/referral_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

class ReferralService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_referral_stats(self, user_id: int) -> dict:
        """Статистика рефералов пользователя."""
        # Количество приведённых
        total_referred = await self.db.scalar(
            select(func.count(User.id))
            .where(User.referred_by_user_id == user_id)
        )
        
        # Количество оплативших
        paid_referred = await self.db.scalar(
            select(func.count(func.distinct(Payment.user_id)))
            .join(User, Payment.user_id == User.id)
            .where(User.referred_by_user_id == user_id)
            .where(Payment.status == 'completed')
        )
        
        # Заработанные бонусные дни
        user = await self.db.get(User, user_id)
        
        return {
            "total_referred": total_referred,
            "paid_referred": paid_referred,
            "bonus_days_earned": user.referral_bonus_days,
            "referral_code": user.referral_code,
            "referral_link": f"https://t.me/YourBot?start=ref_{user.referral_code}"
        }
    
    async def process_referral_payment(
        self,
        referred_user_id: int,
        payment_id: int
    ):
        """Обработка первого платежа реферала."""
        referred_user = await self.db.get(User, referred_user_id)
        
        if not referred_user.referred_by_user_id:
            return
        
        # Проверяем, что это первый платёж
        existing_bonus = await self.db.scalar(
            select(ReferralTransaction)
            .where(ReferralTransaction.referred_id == referred_user_id)
            .where(ReferralTransaction.bonus_type == 'first_payment')
        )
        
        if existing_bonus:
            return
        
        referrer = await self.db.get(User, referred_user.referred_by_user_id)
        
        # Начисляем бонус рефереру
        BONUS_DAYS = 7
        referrer.referral_bonus_days += BONUS_DAYS
        
        # Записываем транзакцию
        tx = ReferralTransaction(
            referrer_id=referrer.id,
            referred_id=referred_user_id,
            payment_id=payment_id,
            bonus_type='first_payment',
            bonus_days=BONUS_DAYS
        )
        self.db.add(tx)
        
        # Проверяем milestone
        await self._check_milestones(referrer.id)
        
        await self.db.commit()
    
    async def _check_milestones(self, referrer_id: int):
        """Проверка достижения milestone наград."""
        paid_count = await self.db.scalar(
            select(func.count(ReferralTransaction.id))
            .where(ReferralTransaction.referrer_id == referrer_id)
            .where(ReferralTransaction.bonus_type == 'first_payment')
        )
        
        milestones = {
            3: 30,    # 3 реферала = 30 дней
            10: 90,   # 10 рефералов = 90 дней
            25: 180,  # 25 рефералов = 180 дней
        }
        
        for threshold, bonus_days in milestones.items():
            if paid_count == threshold:
                # Проверяем, не получал ли уже
                existing = await self.db.scalar(
                    select(ReferralTransaction)
                    .where(ReferralTransaction.referrer_id == referrer_id)
                    .where(ReferralTransaction.bonus_type == f'milestone_{threshold}')
                )
                
                if not existing:
                    referrer = await self.db.get(User, referrer_id)
                    referrer.referral_bonus_days += bonus_days
                    
                    tx = ReferralTransaction(
                        referrer_id=referrer_id,
                        referred_id=referrer_id,  # self-reference для milestone
                        bonus_type=f'milestone_{threshold}',
                        bonus_days=bonus_days
                    )
                    self.db.add(tx)
```

### 8.2 Лидерборд

```python
@router.get("/referrals/leaderboard")
async def get_leaderboard(
    db: DbSession,
    period: str = Query("month", regex="^(week|month|all)$")
):
    """Топ-10 рефереров за период."""
    
    if period == "week":
        since = datetime.utcnow() - timedelta(days=7)
    elif period == "month":
        since = datetime.utcnow() - timedelta(days=30)
    else:
        since = datetime(2020, 1, 1)
    
    query = (
        select(
            User.id,
            User.username,
            func.count(ReferralTransaction.id).label("referral_count"),
            func.sum(ReferralTransaction.bonus_days).label("total_bonus")
        )
        .join(ReferralTransaction, User.id == ReferralTransaction.referrer_id)
        .where(ReferralTransaction.created_at >= since)
        .where(ReferralTransaction.bonus_type == 'first_payment')
        .group_by(User.id)
        .order_by(func.count(ReferralTransaction.id).desc())
        .limit(10)
    )
    
    result = await db.execute(query)
    
    return [
        {
            "rank": idx + 1,
            "username": row.username or f"User #{row.id}",
            "referral_count": row.referral_count,
            "total_bonus_days": row.total_bonus
        }
        for idx, row in enumerate(result)
    ]
```

---

## 9. Деплой и мониторинг

### 9.1 Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # FastAPI Backend
  api:
    build:
      context: ./vpn-backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://vpn:${DB_PASSWORD}@db:5432/vpn
      - REDIS_URL=redis://redis:6379
      - REMNAWAVE_URL=${REMNAWAVE_URL}
      - REMNAWAVE_TOKEN=${REMNAWAVE_TOKEN}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - vpn-network

  # ARQ Worker
  worker:
    build:
      context: ./vpn-backend
      dockerfile: Dockerfile
    command: arq app.tasks.worker.WorkerSettings
    environment:
      - DATABASE_URL=postgresql://vpn:${DB_PASSWORD}@db:5432/vpn
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - vpn-network

  # Telegram Bot
  bot:
    build:
      context: ./vpn-bot
      dockerfile: Dockerfile
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - API_BASE_URL=http://api:8000/api/v1
      - REDIS_URL=redis://redis:6379
      - WEBHOOK_HOST=${WEBHOOK_HOST}
    depends_on:
      - api
      - redis
    restart: unless-stopped
    networks:
      - vpn-network

  # Next.js Frontend
  frontend:
    build:
      context: ./vpn-frontend
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_URL=${API_URL}
    restart: unless-stopped
    networks:
      - vpn-network

  # React Admin
  admin:
    build:
      context: ./vpn-admin
      dockerfile: Dockerfile
    restart: unless-stopped
    networks:
      - vpn-network

  # Database
  db:
    image: postgres:17-alpine
    environment:
      - POSTGRES_USER=vpn
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=vpn
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    networks:
      - vpn-network

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - vpn-network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - api
      - frontend
      - admin
      - bot
    restart: unless-stopped
    networks:
      - vpn-network

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    restart: unless-stopped
    networks:
      - vpn-network

  # Grafana
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    restart: unless-stopped
    networks:
      - vpn-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  vpn-network:
    driver: bridge
```

### 9.2 Nginx конфигурация

```nginx
# nginx/conf.d/default.conf

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=50r/s;

# API Backend
upstream api {
    server api:8000;
    keepalive 32;
}

# Frontend
upstream frontend {
    server frontend:3000;
}

# Admin Panel
upstream admin {
    server admin:3000;
}

# Telegram Bot webhook
upstream bot {
    server bot:8080;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhooks (higher rate limit)
    location /webhook/ {
        limit_req zone=webhook_limit burst=100 nodelay;
        
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Telegram Bot webhook
    location /webhook/telegram {
        proxy_pass http://bot;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Admin Panel
    location /admin {
        proxy_pass http://admin;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Frontend (default)
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Prometheus metrics (internal only)
    location /metrics {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        
        proxy_pass http://api/metrics;
    }
}
```

### 9.3 GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd vpn-backend
          pip install -e ".[test]"
      
      - name: Run tests
        run: |
          cd vpn-backend
          pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/vpn-service
            git pull origin main
            docker compose -f docker-compose.prod.yml pull
            docker compose -f docker-compose.prod.yml up -d --remove-orphans
            docker system prune -f
```

---

## 10. Чеклист безопасности

**⚠️ ВАЖНОСТЬ: КРИТИЧЕСКАЯ** — обязательно перед запуском!

### 10.1 Обязательные проверки

| Категория | Проверка | Статус |
|-----------|----------|--------|
| **Вебхуки** | HMAC-SHA256 верификация всех вебхуков | ☐ |
| **Вебхуки** | Используется `hmac.compare_digest()` | ☐ |
| **JWT** | Короткий срок жизни access token (≤1 час) | ☐ |
| **JWT** | Уникальный `jti` для отзыва токенов | ☐ |
| **Rate Limiting** | Nginx-уровень (IP) | ☐ |
| **Rate Limiting** | Приложение-уровень (user) | ☐ |
| **SQL** | Только ORM, никаких f-string в запросах | ☐ |
| **CORS** | Только конкретные домены в проде | ☐ |
| **Secrets** | Все секреты в env/Docker secrets | ☐ |
| **Secrets** | Нет секретов в git history | ☐ |
| **HTTPS** | Принудительный редирект HTTP → HTTPS | ☐ |
| **Headers** | X-Frame-Options, X-Content-Type-Options | ☐ |
| **Input** | Pydantic валидация всех входных данных | ☐ |
| **Payments** | Идемпотентность (idempotency_key) | ☐ |
| **Payments** | Проверка суммы после webhook | ☐ |
| **Telegram** | Верификация secret_token webhook | ☐ |
| **DB** | Prepared statements (SQLAlchemy) | ☐ |
| **DB** | Регулярные бекапы | ☐ |
| **Monitoring** | Sentry для ошибок | ☐ |
| **Monitoring** | Prometheus + Grafana | ☐ |

### 10.2 Идемпотентность платежей

```python
async def process_payment_webhook(
    db: AsyncSession,
    idempotency_key: str,
    payment_data: dict
):
    """
    Идемпотентная обработка платежа.
    Защита от двойной обработки при retry вебхуков.
    """
    # Проверяем, не обработан ли уже
    existing = await db.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    
    if existing:
        if existing.status == 'completed':
            return {"status": "already_processed"}
        # Если pending — ждём, не создаём дубликат
        return {"status": "processing"}
    
    # Создаём запись с блокировкой
    async with db.begin():
        payment = Payment(
            idempotency_key=idempotency_key,
            status='processing',
            **payment_data
        )
        db.add(payment)
        await db.flush()
        
        try:
            # Бизнес-логика активации
            await activate_subscription(payment)
            payment.status = 'completed'
        except Exception as e:
            payment.status = 'failed'
            payment.metadata['error'] = str(e)
            raise
```

---

## 11. Пошаговый план реализации

### Фаза 1: Фундамент (Недели 1-2)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 1 | Инициализация репозитория, структура проекта | 🔴 | Monorepo или отдельные репо |
| 2 | Docker Compose для разработки | 🔴 | PostgreSQL, Redis, dev hot-reload |
| 3 | FastAPI: базовая структура, конфиг | 🔴 | Pydantic Settings, lifespan |
| 4 | SQLAlchemy модели + Alembic миграции | 🔴 | Async session, connection pooling |
| 5 | Remnawave SDK интеграция | 🔴 | Тесты подключения, retry logic |
| 6 | JWT аутентификация | 🔴 | Access + Refresh tokens |
| 7 | Rate limiting + базовые эндпоинты | 🟡 | slowapi, /health, /me |

**Чему уделить внимание:**
- Async везде — не блокирующие операции
- Типизация — Pydantic v2 везде
- Тесты — pytest-asyncio с самого начала

### Фаза 2: Telegram Bot (Недели 3-4)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 8 | Aiogram структура, handlers | 🔴 | Router-based архитектура |
| 9 | FSM для подписки | 🔴 | Redis storage |
| 10 | /start с deep links | 🔴 | Реферальные ссылки |
| 11 | Telegram Stars платежи | 🔴 | pre_checkout обязателен! |
| 12 | Локализация (i18n) | 🟡 | Fluent или JSON |
| 13 | Клавиатуры, inline кнопки | 🟡 | UX важен! |
| 14 | Интеграция с FastAPI | 🔴 | httpx клиент |

**Чему уделить внимание:**
- Отвечать на pre_checkout за <10 сек
- Сохранять telegram_payment_charge_id для refunds
- Middleware порядок важен

### Фаза 3: Платежи и подписки (Недели 5-6)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 15 | Subscription service | 🔴 | State machine |
| 16 | Remnawave user provisioning | 🔴 | Создание/продление |
| 17 | Webhook handlers | 🔴 | HMAC верификация! |
| 18 | Razorpay интеграция | 🟡 | UPI для Индии |
| 19 | Xendit интеграция | 🟡 | QRIS для Индонезии |
| 20 | CryptoPay интеграция | 🟡 | USDT/TON для России |
| 21 | Идемпотентность платежей | 🔴 | Redis locks |

**Чему уделить внимание:**
- Идемпотентность — защита от дублей
- Логирование всех платежей
- Graceful handling ошибок

### Фаза 4: Frontend (Недели 7-8)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 22 | Next.js инициализация | 🔴 | App Router, Turbopack |
| 23 | i18n setup (next-intl) | 🔴 | en, hi, id, ru |
| 24 | Landing pages | 🟡 | Server Components, SEO |
| 25 | Auth flow | 🔴 | JWT + cookies |
| 26 | Dashboard + subscription | 🔴 | SWR polling |
| 27 | QR код конфига | 🟡 | react-qr-code |
| 28 | Responsive design | 🟡 | Mobile-first! |

**Чему уделить внимание:**
- Core Web Vitals — скорость = конверсия
- Локализация — КРИТИЧНО для конверсии
- PWA возможности

### Фаза 5: Admin Panel (Неделя 9)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 29 | Refine setup | 🟡 | Data provider для FastAPI |
| 30 | Users CRUD | 🟡 | List, Show, Edit |
| 31 | Subscriptions management | 🟡 | Extend, Cancel |
| 32 | Dashboard + Charts | 🟡 | Recharts |
| 33 | Node monitoring | 🟢 | Real-time status |

### Фаза 6: Реферальная система (Неделя 10)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 34 | Referral service | 🟡 | Бонусы, milestones |
| 35 | Leaderboard API | 🟡 | Week/Month/All |
| 36 | Bot команды рефералов | 🟡 | /invite, /mypoints |
| 37 | Frontend referral page | 🟢 | Share buttons |

### Фаза 7: Production (Недели 11-12)

| День | Задача | Приоритет | Фишки/Внимание |
|------|--------|-----------|----------------|
| 38 | Docker Compose prod | 🔴 | Multi-stage builds |
| 39 | Nginx + SSL | 🔴 | Let's Encrypt |
| 40 | CI/CD pipeline | 🟡 | GitHub Actions |
| 41 | Monitoring stack | 🟡 | Prometheus + Grafana |
| 42 | Sentry integration | 🟡 | Error tracking |
| 43 | Security audit | 🔴 | Checklist выше |
| 44 | Load testing | 🟡 | locust или k6 |
| 45 | Soft launch | 🔴 | Ограниченная аудитория |

---

## Ключевые фишки из мажорных библиотек

### FastAPI 0.121+
- `Annotated` для чистого DI
- Lifespan context manager
- Pydantic v2 с `model_validator`
- Background tasks через `BackgroundTasks`

### Next.js 16
- `"use cache"` директива
- `proxy.ts` вместо middleware
- Turbopack по умолчанию
- Server/Client компоненты

### Aiogram 3.24
- Router-based handlers
- FSM с Redis storage
- Native Stars payments
- Deep linking utils

### React 19
- `use()` hook для promises
- `useEffectEvent` для событий
- `<Activity>` для сохранения состояния
- Improved Suspense

### SQLAlchemy 2.0
- Async native (`AsyncSession`)
- Type annotations
- `select()` вместо Query
- `Mapped[]` для колонок

---

## Итого: что делает проект прибыльным

1. **Remnawave SDK** — экономия 10-100x на инфраструктуре
2. **Telegram Stars** — универсальные платежи без комиссий App Store
3. **Multi-currency** — UPI (Индия), QRIS (Индонезия), крипта (Россия)
4. **Реферальная система** — органический рост с K-фактором 0.3-0.5
5. **Локализация** — конверсия +22% на целевых рынках
6. **$2/месяц** — ниже конкурентов, но с маржой 96%

**Начинай с Фазы 1. Удачи! 🚀**
