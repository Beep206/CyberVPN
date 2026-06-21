# Техническое задание: надёжная реферальная атрибуция CyberVPN

**Проект:** `Beep206/CyberVPN`
**Зона изменений:** пользовательский frontend + customer backend + referral/growth platform
**Исходная ветка:** `fix/referral-attribution-persistence-20260619`
**Состояние аудита:** 19 июня 2026 года
**Снимок ветки на момент аудита:** `71371602f45ab35476f293ca9238ca0cede9cf74`
**Снимок `main` на момент аудита:** `3c44ed35ede414fd9a665acca4ba76a572ce2078`

---

## 1. Назначение документа

Нужно полностью исправить пользовательский referral onboarding flow, чтобы реферальная атрибуция:

1. не терялась после удаления query-параметра из адресной строки;
2. переживала перезагрузку страницы, переходы между страницами и auth-редиректы;
3. корректно работала с email/password, OTP, username-only, OAuth, magic link и другими customer auth flow;
4. не терялась при переходе между `cyber-vpn.net` и `my.cyber-vpn.net`;
5. закреплялась на backend один раз и не могла быть перезаписана;
6. была защищена от self-referral, конфликта с partner attribution и конкурентных запросов;
7. имела наблюдаемость, аудит, полный набор тестов и синхронизированный OpenAPI-контракт;
8. не ломала существующие invite, promo, gift, partner и Telegram flow.

Документ описывает не только исходный пользовательский дефект, но и все обнаруженные проблемы текущей ветки, которые необходимо устранить перед merge.

---

## 2. Исходный дефект

Пользователь выполняет следующий сценарий:

1. открывает реферальную ссылку:
   ```text
   /referral?code=XSK2SAQE
   ```
2. удаляет `/referral?code=XSK2SAQE` из URL или переходит на другую страницу;
3. повторно открывает сайт;
4. проходит регистрацию;
5. у реферера новый пользователь не появляется.

### Корневая причина исходной реализации

В исходном коде:

- referral code использовался только как часть URL;
- защищённый `/referral` мог инициировать auth redirect;
- форма регистрации не передавала referral code;
- `/auth/register` не принимал referral code;
- после создания customer account отсутствовал единый claim-процесс;
- `mobile_users.referred_by_user_id` фактически не заполнялся web onboarding flow.

Добавление только `localStorage` не устраняет проблему полностью. Нужны клиентское сохранение, серверная валидация и атомарное закрепление связи.

---

## 3. Текущее состояние проблемной ветки

На момент аудита ветка:

- опережает старую базу на 16 коммитов;
- отстаёт от актуального `main` на 4 коммита;
- содержит два конкурирующих способа claim;
- содержит временный GitHub Actions workflow;
- не содержит обновлённый OpenAPI snapshot;
- не содержит обновлённые generated API types;
- содержит frontend-код, нарушающий действующее ESLint-правило `no-console`;
- не покрывает ключевые browser и API сценарии тестами.

### Модифицированные области

```text
backend/src/application/use_cases/referrals/claim_referral_attribution.py
backend/src/presentation/api/v1/referral/routes.py
backend/src/presentation/api/v1/referral/schemas.py
backend/src/presentation/api/v1/codes/routes.py
backend/tests/unit/application/use_cases/referrals/test_claim_referral_attribution.py

frontend/src/app/[locale]/layout.tsx
frontend/src/app/api/referral-attribution/route.ts
frontend/src/app/providers/referral-attribution-provider.tsx
frontend/src/features/referral-attribution/constants.ts
frontend/src/features/referral-attribution/storage.ts
frontend/src/features/referral-attribution/storage.test.ts
frontend/src/lib/api/referral.ts
frontend/src/proxy.ts
frontend/src/widgets/referral-cabinet/referral-cabinet-model.ts
frontend/src/widgets/referral-cabinet/__tests__/referral-cabinet-model.test.ts

.github/workflows/tmp-regenerate-referral-api-artifacts.yml
```

---

# 4. Реестр обнаруженных неисправностей

## REF-001. Ветка разошлась с `main`

**Критичность:** Blocker.

Ветка находится в состоянии `diverged`: `ahead 16`, `behind 4`.

### Риск

- конфликт с последними OAuth/auth изменениями;
- запуск тестов на устаревшей базе;
- merge commit может скрыть несовместимости;
- generated i18n/API artifacts могут быть пересобраны не из актуального кода.

### Требование

Перед дальнейшей разработкой:

```powershell
git fetch origin
git checkout fix/referral-attribution-persistence-20260619
git rebase origin/main
```

После rebase повторно проверить весь diff. Не выполнять слепой `merge main`, если репозиторий использует линейную историю для feature-веток.

---

## REF-002. Реализованы два канонических claim-пути

**Критичность:** Blocker.

Сейчас присутствуют:

```text
POST /api/v1/referral/claim
POST /api/v1/codes/resolve
action_context = signup
```

Оба пути вызывают `ClaimReferralAttributionUseCase`, но имеют разные:

- response model;
- HTTP status;
- error mapping;
- очистку cookie;
- observability;
- семантику `already_claimed`;
- поведение при `UserNotFoundError`.

### Риск

Один frontend начнёт использовать `/referral/claim`, другой — `/codes/resolve`, после чего бизнес-правила разойдутся.

### Требование

Оставить **один** канонический endpoint:

```text
POST /api/v1/referral/attribution/claim
```

Допустимый упрощённый путь:

```text
POST /api/v1/referral/claim
```

Из `backend/src/presentation/api/v1/codes/routes.py` удалить специальную обработку:

```python
payload.action_context == GrowthCodeActionContext.SIGNUP
```

`/codes/resolve` должен продолжать только разрешать/проверять growth code, но не менять final referral binding.

---

## REF-003. `codes/resolve` возвращает HTTP 200 для отклонённого claim

**Критичность:** High.

В текущей ветке self-referral, partner conflict и истёкшее окно превращаются в `GrowthCodeResolutionOutcome` с HTTP 200.

В `/referral/claim` те же состояния возвращаются как 404/409/422.

### Требование

Единый claim endpoint должен иметь один контракт ошибок. Клиент не должен угадывать результат по двум несовместимым схемам.

---

## REF-004. OpenAPI snapshot не обновлён

**Критичность:** Blocker.

Хэш:

```text
backend/docs/api/openapi.json
branch == main
```

При этом backend уже содержит новый endpoint и новые Pydantic schemas.

### Результат

CI `check-generated-artifacts.sh` обязательно обнаружит drift.

### Требование

После финализации API:

```powershell
cd backend
python scripts\export_openapi.py
```

Закоммитить:

```text
backend/docs/api/openapi.json
```

---

## REF-005. Generated API types не обновлены

**Критичность:** Blocker.

Хэш `frontend/src/lib/api/generated/types.ts` в ветке совпадает с `main`, хотя API изменён.

Обновить:

```text
frontend/src/lib/api/generated/types.ts
admin/src/lib/api/generated/types.ts
partner/src/lib/api/generated/types.ts
```

Команды:

```powershell
cd frontend
npm run generate:api-types

cd ..\admin
npm run generate:api-types

cd ..\partner
npm run generate:api-types
```

Ручной интерфейс `ReferralClaimResponse` в `frontend/src/lib/api/referral.ts` после генерации заменить типом из `operations`.

---

## REF-006. В ветке оставлен временный workflow

**Критичность:** Blocker.

Не должен попасть в merge:

```text
.github/workflows/tmp-regenerate-referral-api-artifacts.yml
```

### Требование

Удалить файл. Generated artifacts должны создаваться штатными локальными командами или постоянным CI, а не одноразовым workflow в feature-ветке.

---

## REF-007. Frontend не проходит ESLint

**Критичность:** Blocker.

В `frontend/eslint.config.mjs` разрешён только:

```js
console.error
```

Новые файлы используют `console.warn`:

```text
frontend/src/features/referral-attribution/storage.ts
frontend/src/app/providers/referral-attribution-provider.tsx
```

### Требование

Не отключать правило на весь проект.

Рекомендуемые варианты:

1. использовать существующий frontend telemetry/logger;
2. отправлять ошибки в Sentry;
3. для ожидаемых storage failures не логировать каждую попытку;
4. для действительно неожиданных ошибок использовать централизованный logger.

Не добавлять многочисленные `eslint-disable no-console`.

---

## REF-008. Атрибуция теряется между поддоменами

**Критичность:** Critical.

`localStorage` разделён по origin:

```text
https://cyber-vpn.net
https://my.cyber-vpn.net
```

Host-only cookie также не переходит между этими хостами.

### Проблемный сценарий

1. пользователь открывает:
   ```text
   https://cyber-vpn.net/pricing?ref=XSK2SAQE
   ```
2. code сохраняется на public origin;
3. пользователь нажимает Register;
4. регистрация открывается на:
   ```text
   https://my.cyber-vpn.net/register
   ```
5. query-параметр не перенесён;
6. cookie и localStorage недоступны на `my`;
7. referral теряется.

### Требование

Выбрать один из вариантов.

#### Рекомендуемый вариант

Создать канонический redirect route:

```text
https://cyber-vpn.net/r/XSK2SAQE
```

Он должен перенаправлять на:

```text
https://my.cyber-vpn.net/{locale}/register?ref=XSK2SAQE
```

На cabinet host код сохраняется до удаления query string.

#### Дополнительное требование

Все CTA с public-сайта обязаны переносить referral attribution:

```text
/register?ref=...
/login?ref=...
/pricing -> register
```

Не полагаться на parent-domain cookie без отдельного security review. Cookie с `Domain=.cyber-vpn.net` будет отправляться также на другие поддомены и создаёт риск cookie tossing.

---

## REF-009. Referral link строится из `window.location.origin`

**Критичность:** High.

Текущий код формирует ссылку из origin открытого кабинета и имеет fallback:

```text
https://cybervpn.example
```

### Риски

- серверный render может сформировать примерный домен;
- возможен hydration mismatch;
- пользователь может скопировать неверную ссылку до hydration;
- staging/custom host начнёт генерировать неканонические production-ссылки;
- miniapp или alternate host сформирует неправильную ссылку.

### Требование

Использовать один конфигурационный источник:

```text
NEXT_PUBLIC_REFERRAL_ORIGIN=https://my.cyber-vpn.net
```

или существующий `SITE_URL`, если его семантика подходит.

Функция `buildReferralLink()` должна быть детерминированной и не обращаться к `window`.

---

## REF-010. Legacy `/referral?code=` ведёт на защищённую страницу

**Критичность:** Medium.

Старая ссылка должна поддерживаться, но для неавторизованного пользователя её целевым действием должна быть регистрация, а не открытие dashboard referral cabinet.

### Требование

Legacy URL:

```text
/referral?code=XSK2SAQE
```

должен выполнять 301/302/307 на:

```text
/{locale}/register?ref=XSK2SAQE
```

После переходного периода referral cabinet остаётся доступным по защищённому route, но acquisition URL должен быть отдельным:

```text
/r/{code}
```

---

## REF-011. Query aliases принимаются на любом pathname

**Критичность:** Medium.

Сейчас глобально распознаются:

```text
ref
referral
referral_code
```

Это может захватить чужой технический `ref` на документации, support или partner surface.

### Требование

Определить один канонический параметр:

```text
ref
```

Legacy aliases разрешать только на утверждённых acquisition routes:

```text
/register
/login
/r/{code}
/referral legacy landing
```

Для произвольных marketing pages допустим только канонический `ref`, если это явно утверждено продуктом.

OAuth `code` должен и дальше исключаться.

---

## REF-012. Cookie и localStorage содержат разные TTL-модели

**Критичность:** High.

Cookie хранит только code. Local storage хранит:

```text
capturedAt
expiresAt
```

При reconciliation `replaceReferralAttribution()` создаёт новый `capturedAt` и продлевает TTL.

### Пример

1. cookie A существует 29 дней;
2. localStorage содержит B;
3. сервер возвращает first-touch A;
4. frontend заменяет localStorage на A;
5. A получает ещё 30 дней.

### Требование

Никогда не продлевать TTL при reconciliation.

Cookie/API должны возвращать исходные:

```text
captured_at
expires_at
attribution_id
```

Local storage копирует эти значения без изменения.

---

## REF-013. Backend не знает время реального клика

**Критичность:** High.

Backend проверяет возраст customer account, но не first-touch timestamp.

### Риски

- нельзя доказать, когда был зафиксирован клик;
- browser TTL невозможно проверить сервером;
- невозможен корректный audit;
- невозможно отличить referral capture до регистрации от позднего ввода кода.

### Требование

Создать серверную attribution session или использовать существующий append-only attribution layer.

Рекомендуемая модель:

```text
referral_attribution_sessions
```

Поля:

```text
id UUID PK
token_hash VARCHAR UNIQUE NOT NULL
growth_code_id UUID FK growth_codes.id
referrer_user_id UUID FK mobile_users.id
claimed_by_user_id UUID NULL FK mobile_users.id
status pending|claimed|expired|rejected
source_host VARCHAR
source_path VARCHAR
campaign_params JSONB
evidence_payload JSONB
first_seen_at TIMESTAMPTZ
expires_at TIMESTAMPTZ
claimed_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

В browser cookie хранить только криптографически случайный opaque token. В БД хранить только hash token.

Допустимый облегчённый вариант — signed cookie с `code`, `captured_at`, `expires_at`, но server-side session предпочтительнее.

---

## REF-014. Не используется существующий attribution audit layer

**Критичность:** High.

В проекте уже есть:

```text
backend/src/infrastructure/database/models/attribution_touchpoint_model.py
backend/src/application/use_cases/attribution/record_touchpoint.py
```

### Требование

Не создавать параллельный несвязанный audit-механизм.

Записывать append-only touchpoints:

```text
explicit_code
deep_link
campaign_params
```

Для referral необходимо добавить в touchpoint одну из ссылок:

```text
growth_code_id
referrer_user_id
referral_attribution_session_id
```

Не хранить только сырой referral code в произвольном JSON без relational reference.

---

## REF-015. Invalid cookie всегда побеждает валидный body fallback

**Критичность:** High.

В `/referral/claim` сейчас:

```python
referral_code = cookie_code or body_code
```

Если cookie повреждена или содержит несуществующий code, валидный localStorage fallback не используется.

### Требование

Алгоритм:

1. отдельно нормализовать cookie;
2. отдельно нормализовать fallback body;
3. валидировать cookie;
4. если cookie синтаксически/семантически invalid — очистить её;
5. только после этого использовать fallback;
6. не перезаписывать валидную first-touch cookie вторым code.

---

## REF-016. Клиент определяет terminal failure только по HTTP status

**Критичность:** High.

Сейчас permanent errors определяются:

```text
400, 404, 409, 422
```

Это слишком грубо.

### Требование

Использовать стабильные backend error codes:

```text
REFERRAL_CODE_INVALID
REFERRAL_CODE_NOT_FOUND
REFERRAL_CODE_INACTIVE
REFERRAL_SELF_ATTRIBUTION_BLOCKED
REFERRAL_PARTNER_ATTRIBUTION_CONFLICT
REFERRAL_ALREADY_CLAIMED
REFERRAL_ATTRIBUTION_EXPIRED
REFERRAL_PROGRAM_DISABLED
REFERRAL_USER_NOT_READY
REFERRAL_TRANSIENT_FAILURE
```

Frontend должен иметь явную таблицу:

```text
terminal -> очистить pending attribution
retryable -> сохранить и повторить
success -> очистить
already_claimed -> очистить
```

Не очищать referral только потому, что backend вернул неизвестный `400`.

---

## REF-017. Retry не имеет backoff и лимита

**Критичность:** Medium.

После transient failure `claimAttemptRef` сбрасывается. Новый route/state update может снова отправить request.

### Требование

Использовать контролируемую retry policy:

```text
max attempts: 3
delays: 1s, 3s, 10s
retry on: network error, 502, 503, 504
do not retry on: 400, 404, 409, 422
401: дождаться завершения session restore
403 program disabled: не спамить; retry только после capability/config refresh
```

Также повторять при событии `online`, но не чаще установленного интервала.

---

## REF-018. Capture endpoint не проверяет существование code

**Критичность:** Medium.

Next route проверяет только regex.

### Требование

Public capture endpoint должен:

1. нормализовать code;
2. найти referral owner;
3. проверить activity/program policy;
4. исключить другие типы growth code;
5. создать attribution session;
6. выставить HttpOnly cookie;
7. вернуть нейтральный результат.

Referral code является публичным share identifier, поэтому его existence validation допустима, но endpoint обязан иметь rate limit.

---

## REF-019. Отсутствует rate limiting

**Критичность:** Medium.

Нужны отдельные лимиты:

```text
capture: per IP + per code
claim: per authenticated user
```

Пример policy:

```text
capture: 20 запросов / 10 минут / IP
claim: 10 запросов / 10 минут / user
```

Лимиты должны использовать существующую Redis/rate-limit инфраструктуру проекта.

---

## REF-020. Partner conflict проверяется не полностью

**Критичность:** High.

`list_active_for_user(user_id, storefront_id=None)` учитывает только global bindings. Storefront-specific binding может быть пропущен.

### Требование

Referral claim должен проверять:

```text
mobile_users.partner_user_id
mobile_users.partner_account_id
customer_commercial_bindings global
customer_commercial_bindings storefront-specific
pending partner attribution/session
explicit partner code in current acquisition context
```

Product policy должна однозначно определить приоритет:

```text
existing immutable partner binding > referral
existing immutable referral binding > новый partner/referral code
```

Нельзя незаметно менять commercial owner.

---

## REF-021. Не гарантировано создание mobile shadow для каждого auth flow

**Критичность:** High.

Referral API использует:

```text
get_current_mobile_user_id
```

Если customer session существует, но `mobile_users` shadow не создан, endpoint возвращает `USER_NOT_FOUND`.

### Требование

Провести аудит всех customer session issuance paths:

```text
password login
email OTP verify
username-only login
OAuth callback
magic link verify
magic link OTP
passkey/WebAuthn
Telegram web login
Telegram miniapp
Telegram bot link
2FA completion
account linking
```

До возврата authenticated customer session должен существовать согласованный `mobile_users` record.

Добавить общий application service:

```text
EnsureCustomerPrincipalProjectionUseCase
```

Не копировать `_ensure_customer_web_mobile_shadow()` по нескольким routes.

---

## REF-022. Referral code генерируется с гонкой и без collision retry

**Критичность:** High.

`GetReferralCodeUseCase`:

- сначала читает code;
- затем генерирует;
- не блокирует строку;
- не обрабатывает unique collision;
- параллельные GET могут вернуть разные codes.

### Требование

В `get_referral_code.py`:

1. `SELECT ... FOR UPDATE` customer row;
2. повторно проверить существующий code под lock;
3. генерировать cryptographically secure code;
4. обрабатывать `IntegrityError`;
5. retry до 5 раз;
6. при исчерпании вернуть контролируемую domain error;
7. добавить concurrency integration test.

Альтернатива: генерировать referral code при создании `mobile_users`.

---

## REF-023. Нет индекса по `referred_by_user_id`

**Критичность:** High для production scale.

Stats выполняют:

```sql
WHERE mobile_users.referred_by_user_id = :referrer
```

PostgreSQL не создаёт индекс автоматически для FK.

### Требование

Alembic migration:

```sql
CREATE INDEX ix_mobile_users_referred_by_user_id
ON mobile_users (referred_by_user_id);
```

---

## REF-024. Нет DB-level защиты self-referral

**Критичность:** Medium.

Application service блокирует self-referral, но прямое обновление, legacy flow или ошибочный admin script могут создать:

```text
referred_by_user_id == id
```

### Требование

Добавить CHECK constraint:

```sql
CHECK (
  referred_by_user_id IS NULL
  OR referred_by_user_id <> id
)
```

---

## REF-025. Не определён канонический referral field

**Критичность:** High.

В проекте существуют:

```text
admin_users.referred_by_id
mobile_users.referred_by_user_id
```

Rewards/stats работают через `mobile_users`.

### Требование

Зафиксировать:

```text
mobile_users.referred_by_user_id = canonical commercial referral binding
```

Для `admin_users.referred_by_id` выбрать одно:

1. удалить после backfill;
2. объявить deprecated projection;
3. синхронизировать через единый projection service.

Не выполнять независимый dual-write в разных routes.

---

## REF-026. Нет claim timestamp и immutable audit record

**Критичность:** High.

Одного FK недостаточно для расследования спорных начислений.

### Требование

Минимально хранить:

```text
referral_claimed_at
referral_source_code_id
referral_attribution_session_id
```

Предпочтительно final binding дополнять append-only событием/touchpoint.

Нельзя сохранять чувствительные данные или полный IP без утверждённой retention policy.

---

## REF-027. Pydantic contract не соответствует фактической валидации

**Критичность:** Medium.

Schema разрешает строку до 64 символов, use case принимает только 4–12.

### Требование

Request schema должна содержать единый pattern:

```text
^[A-Z0-9_-]{4,12}$
```

Или, если будет opaque token, body вообще не должен принимать raw code в основном path.

---

## REF-028. Error envelope неоднороден

**Критичность:** Medium.

Сейчас возможны:

```json
{"detail": "string"}
```

```json
{"detail": {"code": "...", "message": "..."}}
```

```json
{
  "accepted": false,
  "reject_reason": "...",
  "user_message_key": "..."
}
```

### Требование

Для claim использовать стандартный проектный error contract:

```json
{
  "detail": {
    "code": "REFERRAL_SELF_ATTRIBUTION_BLOCKED",
    "message": "Self-referral is not allowed"
  }
}
```

OpenAPI должен документировать все terminal states.

---

## REF-029. Cookie cleanup неодинаков для разных клиентов

**Критичность:** Medium.

Cookie удаляется backend только при success. При terminal error её удаляет конкретный React provider.

### Требование

Backend должен возвращать/устанавливать cleanup cookie для всех terminal outcomes:

```text
claimed
already_claimed
invalid
not_found
self_referral
partner_conflict
expired
```

Для retryable outcome cookie сохраняется.

---

## REF-030. First-touch policy не зафиксирована как продуктовый контракт

**Критичность:** High.

Текущий код реализует first-touch неявно.

### Требование

Зафиксировать:

```text
Attribution model: first valid referral touch wins.
TTL: 30 calendar days.
Final user binding: immutable.
A later referral link never overwrites an active pending touch.
An existing final binding always wins.
```

Если продукт хочет last-touch, это должно быть отдельным решением и другой реализацией.

---

## REF-031. Concurrent browser capture не атомарен

**Критичность:** Medium.

Две вкладки могут одновременно отправить разные codes до установки первой cookie. Последний `Set-Cookie` может победить.

### Требование

Server-side attribution session должна обеспечивать first-touch по browser attribution identifier.

Варианты:

- opaque browser attribution ID cookie создаётся до code capture;
- Redis/DB `SET NX`;
- DB unique constraint на active browser attribution session.

---

## REF-032. Нет UX-индикации referral onboarding

**Критичность:** Medium.

Пользователь не понимает, сохранён ли referral.

### Требование

На registration page показать нейтральный блок:

```text
Реферальное приглашение применено
Код: XSK2••••
```

Не показывать email/login/имя реферера.

Состояния:

```text
capturing
captured
invalid
expired
claimed
```

Invalid referral не должен блокировать обычную регистрацию.

---

## REF-033. Share actions доступны до загрузки code

**Критичность:** Low/Medium.

Не формировать ссылку с пустым `ref`.

### Требование

Пока `referralCode` не загружен:

- disable Copy link;
- disable Share;
- показывать loading state;
- не создавать `...?ref=`.

---

## REF-034. Неполное тестовое покрытие

**Критичность:** Blocker.

Сейчас есть tests для storage и части use case, но отсутствуют:

- proxy capture;
- cross-domain redirect;
- Next cookie route;
- provider state machine;
- backend route contract;
- concurrent DB claim;
- concurrent referral code generation;
- auth flow E2E;
- generated OpenAPI contract;
- partner conflict по storefront binding;
- cookie/body precedence;
- cleanup semantics.

Полная матрица приведена ниже.

---

## REF-035. Нет production observability

**Критичность:** High.

`console.warn` не является production telemetry.

### Требование

Backend metrics:

```text
referral_attribution_capture_total{result,source}
referral_attribution_claim_total{result,source}
referral_attribution_claim_duration_seconds
referral_attribution_pending_current
referral_attribution_expired_total
```

Structured logs:

```text
event
user_id
attribution_id
result
reason_code
source_host
```

Не логировать raw cookie token. Referral code допустимо хешировать или маскировать.

Frontend:

- Sentry breadcrumb на capture/claim result;
- не отправлять raw referral code как PII-like tag;
- никаких бесконечных console logs.

---

## REF-036. Нет privacy/cookie документации

**Критичность:** Medium.

### Требование

Обновить:

```text
Cookie Policy
Privacy Policy / analytics attribution section
data retention documentation
```

Указать:

- назначение referral attribution cookie;
- first-party характер;
- срок 30 дней;
- отсутствие auth token внутри;
- условия удаления после claim/expiry.

---

# 5. Целевая архитектура

## 5.1 Каноническая ссылка

Основной формат:

```text
https://my.cyber-vpn.net/{locale}/register?ref=XSK2SAQE
```

Короткий share URL:

```text
https://cyber-vpn.net/r/XSK2SAQE
```

Short route должен сохранить locale/campaign params и перенаправить на cabinet registration.

Legacy:

```text
/referral?code=XSK2SAQE
```

поддерживается только как redirect compatibility.

---

## 5.2 Canonical capture flow

### Endpoint

```text
POST /api/v1/referral/attribution/capture
```

Endpoint публичный, но rate-limited.

### Request

```json
{
  "referral_code": "XSK2SAQE",
  "source_host": "cyber-vpn.net",
  "source_path": "/pricing",
  "campaign_params": {
    "utm_source": "customer_share"
  }
}
```

Все source fields должны очищаться и ограничиваться по длине. Не доверять forwarded host без общей trusted-proxy политики.

### Success response

```json
{
  "status": "captured",
  "attribution_id": "uuid",
  "captured_at": "2026-06-19T12:00:00Z",
  "expires_at": "2026-07-19T12:00:00Z",
  "masked_code": "XSK2••••"
}
```

### Cookie

```text
name: cv_ref_attribution
value: opaque random token
HttpOnly: true
Secure: true in production
SameSite: Lax
Path: /
Max-Age: 2592000
```

Cookie должна быть host-only на cabinet host.

### Invalid code

Регистрация остаётся доступной. UI получает controlled invalid state.

---

## 5.3 Local storage fallback

Local storage не является source of truth.

Структура:

```json
{
  "version": 2,
  "attributionId": "uuid-or-null",
  "code": "XSK2SAQE",
  "capturedAt": 1781870400000,
  "expiresAt": 1784462400000,
  "source": "url"
}
```

Правила:

1. first valid touch wins;
2. `expiresAt` не продлевается при чтении/синхронизации;
3. запись удаляется после claim/terminal rejection/expiry;
4. timestamp проверяется:
   - `capturedAt <= now + допустимый clock skew`;
   - `expiresAt > capturedAt`;
   - `expiresAt - capturedAt <= configured TTL`;
5. storage errors не ломают страницу;
6. при blocked localStorage основной cookie flow продолжает работать.

---

## 5.4 Canonical claim flow

### Endpoint

```text
POST /api/v1/referral/attribution/claim
```

Endpoint authenticated.

Основной request body пустой:

```json
{}
```

Backend читает opaque attribution cookie.

Recovery body разрешён только при отсутствии cookie:

```json
{
  "fallback_referral_code": "XSK2SAQE"
}
```

### Success

```json
{
  "status": "claimed",
  "referrer_user_id": "uuid",
  "claimed_at": "2026-06-19T12:10:00Z"
}
```

Idempotent result:

```json
{
  "status": "already_claimed",
  "referrer_user_id": "uuid",
  "claimed_at": "2026-06-19T12:10:00Z"
}
```

No pending:

```json
{
  "status": "no_pending"
}
```

Не возвращать клиенту лишние сведения о referrer.

---

## 5.5 Atomic claim transaction

В одной DB transaction:

1. получить текущего mobile customer;
2. `SELECT ... FOR UPDATE`;
3. если final referral уже есть — вернуть `already_claimed`;
4. загрузить attribution session под lock;
5. проверить expiry/status;
6. получить canonical referral growth code;
7. проверить referrer:
   - существует;
   - active;
   - тот же customer realm;
   - не равен текущему user;
8. проверить partner/commercial conflict;
9. установить:
   ```text
   mobile_users.referred_by_user_id
   referral_claimed_at
   referral_source_code_id
   ```
10. пометить attribution session `claimed`;
11. создать append-only touchpoint/event;
12. flush;
13. commit выполняет session boundary проекта;
14. удалить pending cookie в response.

Не выполнять внутренний `commit()` внутри use case, если session lifecycle уже управляется `get_db`.

---

## 5.6 Source of truth

```text
Final binding:
mobile_users.referred_by_user_id

Referral share identifier:
mobile_users.referral_code / canonical growth-code shadow

Pending attribution:
referral_attribution_sessions

Audit:
attribution_touchpoints / growth code resolution events
```

---

# 6. Изменения по файлам

## Backend

### Оставить и переработать

```text
backend/src/application/use_cases/referrals/claim_referral_attribution.py
```

Требования:

- не зависеть от двух presentation routes;
- единые domain errors;
- transaction-safe;
- проверка same realm;
- полный partner conflict;
- запись audit touchpoint;
- без самостоятельного commit;
- clock dependency для тестов.

### Удалить signup mutation из

```text
backend/src/presentation/api/v1/codes/routes.py
```

### Создать/переработать canonical routes

```text
backend/src/presentation/api/v1/referral/routes.py
backend/src/presentation/api/v1/referral/schemas.py
```

Предпочтительный path:

```text
/referral/attribution/capture
/referral/attribution/claim
```

### Обновить

```text
backend/src/application/use_cases/referrals/get_referral_code.py
```

Добавить row lock и collision retry.

### Добавить migration

```text
backend/alembic/versions/<revision>_referral_attribution_hardening.py
```

Migration:

- index `referred_by_user_id`;
- self-referral check;
- claim metadata columns или session table;
- нужные touchpoint FK/indexes;
- безопасный downgrade.

### Унифицировать customer projection

Создать application service и использовать во всех auth success paths.

### Обновить exports

```text
backend/src/application/use_cases/referrals/__init__.py
```

---

## Frontend

### Canonical configuration

Добавить валидируемую public config:

```text
NEXT_PUBLIC_REFERRAL_ORIGIN
```

Не использовать `cybervpn.example`.

### Переработать

```text
frontend/src/features/referral-attribution/constants.ts
frontend/src/features/referral-attribution/storage.ts
frontend/src/app/providers/referral-attribution-provider.tsx
```

Provider должен быть явной state machine:

```text
idle
capturing
captured
claiming
claimed
terminal_error
retry_wait
```

### Next route

```text
frontend/src/app/api/referral-attribution/route.ts
```

Выбрать одно:

1. удалить и обращаться напрямую к backend через `/api/v1`;
2. оставить как BFF, но только проксировать canonical backend capture/clear API.

Он не должен иметь независимую бизнес-логику и собственную несовместимую валидацию.

### Proxy

```text
frontend/src/proxy.ts
```

Proxy может:

- распознавать canonical acquisition parameter;
- сохранять query при redirect;
- выполнять legacy redirect.

Proxy не должен становиться вторым business backend.

### Registration UI

Обновить:

```text
frontend/src/app/[locale]/(auth)/register/page.tsx
```

Показать capture status, не блокируя регистрацию.

### Referral share URL

Обновить:

```text
frontend/src/widgets/referral-cabinet/referral-cabinet-model.ts
frontend/src/widgets/referral-cabinet/referral-cabinet-dashboard.tsx
```

Использовать configured canonical origin.

### API client

```text
frontend/src/lib/api/referral.ts
```

Все типы — из generated OpenAPI.

---

# 7. Политика ошибок

| Code | HTTP | Terminal | Действие frontend |
|---|---:|---|---|
| `REFERRAL_CODE_INVALID` | 422 | да | очистить, показать invalid |
| `REFERRAL_CODE_NOT_FOUND` | 404 | да | очистить |
| `REFERRAL_CODE_INACTIVE` | 409 | да | очистить |
| `REFERRAL_SELF_ATTRIBUTION_BLOCKED` | 409 | да | очистить, нейтральное сообщение |
| `REFERRAL_PARTNER_ATTRIBUTION_CONFLICT` | 409 | да | очистить |
| `REFERRAL_ATTRIBUTION_EXPIRED` | 410 | да | очистить |
| `REFERRAL_ALREADY_CLAIMED` | 200 | да | очистить |
| `REFERRAL_PROGRAM_DISABLED` | 403 | условно | не спамить; ждать config refresh |
| `REFERRAL_USER_NOT_READY` | 409/425 | нет | retry после projection/session |
| `RATE_LIMITED` | 429 | нет | учитывать `Retry-After` |
| network/502/503/504 | соответствующий | нет | bounded retry |

---

# 8. Тестовая матрица

## 8.1 Frontend unit tests

### Query parsing

- `?ref=XSK2SAQE`;
- lowercase -> uppercase;
- legacy `?code=` только на legacy route;
- OAuth `?code=` не захватывается;
- malformed code;
- пустой code;
- слишком длинный code;
- чужой `ref` на неразрешённом route.

### Storage

- first touch;
- second touch не перезаписывает;
- expiry;
- timestamp tampering;
- corrupt JSON;
- quota error;
- localStorage unavailable;
- reconciliation не продлевает TTL;
- storage event между вкладками.

### Link builder

- production origin;
- locale;
- URL encoding;
- отсутствие fallback example;
- empty code не формирует link.

---

## 8.2 Frontend route/proxy tests

- capture cookie attributes;
- legacy redirect сохраняет code;
- public -> cabinet redirect сохраняет referral;
- existing first-touch cookie не перезаписывается;
- invalid query не устанавливает cookie;
- OAuth callback не устанавливает referral cookie;
- DELETE/cleanup;
- no-cache headers;
- production Secure;
- local development non-Secure.

---

## 8.3 Provider tests

С MSW и Zustand:

- capture до auth;
- claim после session restore;
- email OTP;
- username-only login;
- OAuth callback;
- magic link;
- transient retry;
- terminal cleanup;
- 429 Retry-After;
- program disabled;
- StrictMode double effect;
- unmount during request;
- cookie-only path;
- localStorage-only recovery;
- invalid cookie + valid fallback;
- no infinite requests on navigation.

---

## 8.4 Backend unit tests

### Claim use case

- success;
- idempotent same code;
- existing binding + different requested code;
- self-referral;
- inactive referrer;
- missing referrer;
- wrong realm;
- partner user;
- partner account;
- global commercial binding;
- storefront-specific binding;
- expired attribution;
- invalid token;
- invalid code;
- disabled program;
- audit touchpoint;
- no internal commit;
- cleanup decision.

### Referral code generation

- existing code returned;
- concurrent requests return same code;
- unique collision retry;
- retry exhaustion;
- generated pattern.

---

## 8.5 Backend integration tests

- real PostgreSQL two-session concurrent claim;
- two different codes race: only first commits;
- same code race: both get consistent result;
- DB self-check constraint;
- index exists;
- capture session expiry;
- token hash lookup;
- cookie set/delete contract;
- rate limit;
- OpenAPI documented responses.

---

## 8.6 End-to-end acceptance tests

### E2E-01 — исходный пользовательский сценарий

1. открыть:
   ```text
   /register?ref=XSK2SAQE
   ```
2. удалить query из URL;
3. перезагрузить страницу;
4. перейти на главную;
5. вернуться на регистрацию;
6. зарегистрироваться;
7. подтвердить OTP;
8. проверить:
   ```text
   referred_user.referred_by_user_id == referrer.id
   ```
9. проверить, что stats referrer показывают +1.

### E2E-02 — public marketing domain

1. открыть public pricing с referral;
2. перейти в cabinet;
3. зарегистрироваться;
4. binding сохранён.

### E2E-03 — OAuth

Referral -> Google/GitHub OAuth -> callback -> dashboard -> claim.

### E2E-04 — magic link

Referral -> magic link -> new account -> claim.

### E2E-05 — username-only

Referral -> username registration -> login позже -> claim в допустимой policy.

### E2E-06 — first touch

A -> затем B -> регистрация -> закреплён A.

### E2E-07 — self-referral

Собственный code -> claim blocked, final binding не создан.

### E2E-08 — partner conflict

Existing partner binding -> referral blocked.

### E2E-09 — private mode

Local storage unavailable -> cookie path работает.

### E2E-10 — cookie blocked

Local storage fallback работает в пределах утверждённой policy.

### E2E-11 — expiry

После TTL claim не выполняется.

### E2E-12 — existing old user

Нельзя задним числом присвоить referral, если policy это запрещает.

---

# 9. OpenAPI и generated artifacts

После окончательного API выполнить:

```powershell
cd backend
python scripts\export_openapi.py

cd ..\frontend
npm run generate:api-types
npm run prepare:i18n

cd ..\admin
npm run generate:api-types

cd ..\partner
npm run generate:api-types
```

Проверить:

```powershell
git status --short
git diff --check
```

В Git Bash:

```bash
bash scripts/check-api-contract.sh --verbose
bash scripts/check-generated-artifacts.sh
```

В коммит должны попасть все generated изменения. Не редактировать generated files вручную.

---

# 10. Локальная проверка на Windows

## Backend

```powershell
cd backend

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m ruff check src tests

python -m pytest `
  tests/unit/application/use_cases/referrals/test_claim_referral_attribution.py `
  -q

python -m pytest `
  tests/integration `
  -q
```

Для integration tests поднять штатный Docker stack проекта.

## Frontend

```powershell
cd frontend
npm ci
npm run prepare:i18n
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Admin и partner generated types

```powershell
cd admin
npm ci
npm run generate:api-types
npx tsc --noEmit

cd ..\partner
npm ci
npm run generate:api-types
npx tsc --noEmit
```

---

# 11. Порядок выполнения работ

## PR-1 — восстановление merge-ready состояния

1. rebase на `origin/main`;
2. удалить temporary workflow;
3. выбрать один claim endpoint;
4. удалить signup mutation из `/codes/resolve`;
5. исправить ESLint;
6. унифицировать API error contract;
7. обновить OpenAPI и generated types;
8. добавить endpoint/provider/proxy tests;
9. добиться зелёных lint/typecheck/unit/build.

PR-1 нельзя merge, пока отсутствует cross-domain acceptance test.

## PR-2 — production attribution persistence

1. server-side attribution session;
2. opaque HttpOnly token;
3. capture endpoint;
4. touchpoint integration;
5. DB index/check/metadata migration;
6. collision-safe referral code generation;
7. full partner conflict;
8. rate limits;
9. observability;
10. privacy documentation;
11. PostgreSQL concurrency tests;
12. E2E auth matrix.

Если изменения выполняются в одной ветке, всё равно сохранять эту последовательность коммитов.

---

# 12. Definition of Done

Задача считается завершённой только если одновременно выполнено всё ниже.

## Git

- [ ] Ветка rebased на актуальный `main`.
- [ ] Нет временных workflows.
- [ ] Нет unrelated изменений.
- [ ] `git diff --check` проходит.
- [ ] Нет merge conflict markers.
- [ ] Commit history понятна и тематически разделена.

## API

- [ ] Существует один canonical claim endpoint.
- [ ] `/codes/resolve` не меняет referral binding.
- [ ] OpenAPI обновлён.
- [ ] Frontend/admin/partner generated types обновлены.
- [ ] Все error codes задокументированы.
- [ ] Capture и claim rate-limited.

## Data integrity

- [ ] Final binding immutable.
- [ ] Concurrent claim безопасен.
- [ ] Self-referral запрещён application + DB.
- [ ] Partner conflict учитывает все bindings.
- [ ] `referred_by_user_id` индексирован.
- [ ] Referral code generation concurrency-safe.
- [ ] Capture timestamp проверяется backend.
- [ ] Есть append-only audit trail.

## Frontend

- [ ] URL можно удалить — referral не теряется.
- [ ] Reload не удаляет referral.
- [ ] Cross-domain flow работает.
- [ ] Cookie blocked/localStorage blocked сценарии обработаны.
- [ ] Нет hydration URL с `cybervpn.example`.
- [ ] Нет `console.warn` ESLint violations.
- [ ] Retry ограничен и имеет backoff.
- [ ] Пользователь видит статус приглашения.
- [ ] Invalid referral не блокирует регистрацию.

## Auth flows

- [ ] Email/password + OTP.
- [ ] Username-only.
- [ ] OAuth.
- [ ] Magic link.
- [ ] Passkey/WebAuthn.
- [ ] 2FA completion.
- [ ] Telegram flows либо поддержаны, либо явно исключены и не регрессировали.

## Tests/CI

- [ ] Backend unit tests зелёные.
- [ ] Backend integration tests зелёные.
- [ ] Frontend Vitest зелёный.
- [ ] ESLint зелёный.
- [ ] TypeScript зелёный.
- [ ] Frontend build зелёный.
- [ ] API contract check зелёный.
- [ ] Generated artifacts check зелёный.
- [ ] E2E исходного сценария зафиксирован как regression test.

---

# 13. Итоговая бизнес-гарантия

После реализации пользователь может:

1. открыть реферальную ссылку;
2. удалить referral query из адресной строки;
3. перезагрузить браузер;
4. перейти на другие страницы;
5. пройти внешний OAuth или email verification;
6. вернуться позже в пределах TTL;
7. завершить регистрацию;

и referral binding будет создан ровно один раз на backend.

При этом:

- второй referral code не перезапишет первый;
- собственный code не применится;
- partner attribution не будет повреждена;
- browser-side данные не считаются доверенными;
- начисления будут использовать canonical `mobile_users.referred_by_user_id`;
- каждый capture/claim будет расследуем через audit trail;
- ветка будет проходить обязательные проверки репозитория и будет готова к merge.
