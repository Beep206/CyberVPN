# Техническое задание v7.6.4
# Admin Invite Campaign UX/Error Hardening + создание нужного Premium Smart RU Multi-use Invite

**Проект:** CyberVPN
**Версия ТЗ:** v7.6.4
**Статус:** требуется к выполнению
**Основание:** при создании invite campaign в админке возник React crash `Minified React error #31`, а в поле «План доступа» отображаются только duration-specific варианты `Premium Smart RU` на `30/90/180/365` дней, из-за чего непонятно, как создать бессрочный invite. Также в браузере всё ещё виден RSC/CORS redirect с `my.cyber-vpn.net` на `cyber-vpn.net`.

---

## 1. Цели ТЗ

Нужно закрыть три задачи:

1. **Исправить ошибку админки при отображении backend validation errors.**
   Сейчас FastAPI/Pydantic может вернуть `detail` как массив объектов `{loc,msg,type}`, а React пытается отрендерить объект напрямую и падает с `Minified React error #31`.

2. **Улучшить UX создания бессрочного invite.**
   Админ должен понимать, что «бессрочный Premium Smart RU» — это не отдельный тариф в списке планов, а комбинация:
   ```text
   plan_code = premium_smart_ru
   grant_duration_mode = lifetime
   grant_duration_days = null
   ```

3. **Создать и документировать точный invite campaign профиль для владельца проекта.**
   Нужно создать многоразовый root invite-code, который:
   ```text
   - активируется многими пользователями;
   - каждый пользователь может активировать его только 1 раз;
   - выдаёт Premium Smart RU бессрочно;
   - выдаёт 5 устройств;
   - traffic policy: Unlimited / fair_use;
   - выдаёт каждому активировавшему 12 уникальных одноразовых child invite-кодов;
   - child invite-коды также выдают Premium Smart RU бессрочно, 5 устройств.
   ```

---

## 2. Контекст ошибки

### 2.1. Симптом

В production admin UI при создании кампании появилась ошибка:

```text
Error Code: UNKNOWN
Message: Minified React error #31
object with keys {loc, msg, type}
```

Это означает, что React получил объект как child node. Типичный backend response в таком случае:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Input should be valid",
      "type": "value_error"
    }
  ]
}
```

### 2.2. Корневая причина

`getErrorMessage()` в admin frontend ожидает, что `error.response.data.detail` является строкой. Если `detail` — массив объектов, функция возвращает объект/массив, после чего React пытается отрендерить его в UI и падает.

### 2.3. Пользовательский эффект

Админ не видит реальную причину ошибки backend validation. Вместо нормального сообщения вроде:

```text
body.global_issue_cap: Field required
```

или:

```text
multi_use invite campaigns require global_issue_cap
```

падает весь React UI.

---

## 3. P0. Исправить безопасное отображение API errors в админке

### 3.1. Файл

```text
admin/src/features/growth/lib/formatting.ts
```

### 3.2. Требование

Заменить текущую реализацию `getErrorMessage()` на безопасную, которая всегда возвращает `string`.

Функция должна уметь обрабатывать:

```text
- string detail;
- object detail;
- array detail;
- FastAPI/Pydantic errors: {loc,msg,type};
- nested detail/message/error/code;
- AxiosError;
- RateLimitError;
- обычный Error;
- unknown fallback.
```

### 3.3. Рекомендуемая реализация

```ts
import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';

function formatLocation(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(String).join('.');
  }

  return typeof value === 'string' ? value : '';
}

function stringifyApiDetail(value: unknown): string | null {
  if (!value) return null;

  if (typeof value === 'string') {
    return value;
  }

  if (Array.isArray(value)) {
    const messages = value
      .map((item) => stringifyApiDetail(item))
      .filter((item): item is string => Boolean(item));

    return messages.length ? messages.join('; ') : null;
  }

  if (typeof value === 'object') {
    const record = value as {
      loc?: unknown;
      msg?: unknown;
      message?: unknown;
      detail?: unknown;
      error?: unknown;
      code?: unknown;
      type?: unknown;
    };

    const nested =
      stringifyApiDetail(record.detail)
      ?? stringifyApiDetail(record.message)
      ?? stringifyApiDetail(record.error)
      ?? stringifyApiDetail(record.msg);

    if (nested) {
      const location = formatLocation(record.loc);
      return location ? `${location}: ${nested}` : nested;
    }

    if (typeof record.code === 'string' && record.code.trim()) {
      return record.code.trim();
    }

    if (typeof record.type === 'string' && record.type.trim()) {
      const location = formatLocation(record.loc);
      return location ? `${location}: ${record.type.trim()}` : record.type.trim();
    }

    try {
      return JSON.stringify(value);
    } catch {
      return null;
    }
  }

  return String(value);
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof RateLimitError) {
    return error.message;
  }

  if (error instanceof AxiosError) {
    const data = error.response?.data as
      | {
          detail?: unknown;
          message?: unknown;
          error?: unknown;
          code?: unknown;
        }
      | undefined;

    return (
      stringifyApiDetail(data?.detail)
      ?? stringifyApiDetail(data?.message)
      ?? stringifyApiDetail(data?.error)
      ?? stringifyApiDetail(data?.code)
      ?? fallback
    );
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}
```

### 3.4. Acceptance criteria

- [ ] `getErrorMessage()` всегда возвращает строку.
- [ ] React больше не падает с error #31 при backend validation errors.
- [ ] Ошибки FastAPI/Pydantic отображаются человекочитаемо.
- [ ] Если backend вернул `{loc,msg,type}`, UI показывает `body.field: message`.
- [ ] Если backend вернул массив ошибок, UI показывает все ошибки через `;`.
- [ ] Добавлены unit tests на formatter.

### 3.5. Unit tests

Добавить тесты:

```text
admin/src/features/growth/lib/formatting.test.ts
```

Cases:

```ts
detail as string -> returns string
detail as [{loc,msg,type}] -> returns "body.field: msg"
detail as nested object -> returns nested message
detail as array of strings -> joins with "; "
unknown error -> fallback
RateLimitError -> error.message
```

---

## 4. P0. Исправить UX выбора бессрочного Premium Smart RU

### 4.1. Проблема

В поле «План доступа» сейчас отображаются duration-specific планы:

```text
Premium Smart RU · 30 days
Premium Smart RU · 90 days
Premium Smart RU · 180 days
Premium Smart RU · 365 days
```

Отдельного «Premium Smart RU бессрочно» в списке нет. Это технически нормально, потому бессрочность задаётся не тарифной записью, а campaign policy:

```text
grant_duration_mode = lifetime
grant_duration_days = null
```

Но для оператора это непонятно.

### 4.2. UX-решение

Добавить явное пояснение в форму campaign creation.

В блоке «План доступа» добавить helper text:

```text
Для бессрочного доступа не нужен отдельный бессрочный тариф.
Выберите режим срока “Бессрочно” или используйте код плана premium_smart_ru.
Если выбран конкретный план на 30/90/180/365 дней, его срок будет переопределён режимом “Бессрочно”.
```

В блоке `Grant Duration Mode = lifetime` показать badge:

```text
Бессрочный доступ: duration_days будет отправлен как null.
```

### 4.3. Улучшить выбор plan family

Добавить рядом с plan dropdown отдельный быстрый selector:

```text
Plan Family / Код плана:
- premium_smart_ru
- basic
- plus
- pro
- max
- test
```

Для текущей задачи достаточно:

```text
premium_smart_ru
```

Когда выбран `Plan Family = premium_smart_ru`:

```text
grant_plan_id = null
grant_plan_code = premium_smart_ru
```

То есть при бессрочной кампании оператор не должен выбирать UUID конкретного тарифа на 30/90/180/365 дней.

### 4.4. Поведение preset

Кнопка:

```text
Применить бессрочный пресет Premium Smart RU
```

должна:

```text
grantPlanId = ''
grantPlanCode = 'premium_smart_ru'
grantDurationMode = 'lifetime'
grantDurationDays = ''

childGrantPlanId = ''
childGrantPlanCode = 'premium_smart_ru'
childGrantDurationMode = 'lifetime'
childGrantDurationDays = ''
```

### 4.5. Acceptance criteria

- [ ] В UI явно написано, что бессрочность задаётся `Duration Mode = lifetime`.
- [ ] Оператор не обязан искать отдельный бессрочный план в списке.
- [ ] При применении Premium Smart RU lifetime preset `grant_plan_id` пустой, `grant_plan_code=premium_smart_ru`.
- [ ] При применении preset `child_grant_plan_id` пустой, `child_grant_plan_code=premium_smart_ru`.
- [ ] Если оператор выбирает plan id и lifetime, UI показывает предупреждение: “Срок выбранного плана будет переопределён lifetime policy”.
- [ ] Ошибка backend validation больше не приводит к React crash.

---

## 5. P0. Исправить backend validation UX для campaign creation

### 5.1. Проблема

Даже после исправления frontend formatter, backend должен отдавать более понятные ошибки для типовых случаев.

### 5.2. Требование

В backend validation для invite campaigns добавить domain-level ошибки с понятным `code` и `message_key`.

Примеры:

```json
{
  "code": "INVITE_CAMPAIGN_GLOBAL_ISSUE_CAP_REQUIRED",
  "message_key": "invite_campaign.global_issue_cap_required",
  "message": "Lifetime campaigns with 10 or more child invites require global_issue_cap."
}
```

```json
{
  "code": "INVITE_CAMPAIGN_LIFETIME_ACK_REQUIRED",
  "message_key": "invite_campaign.lifetime_ack_required",
  "message": "Lifetime campaign acknowledgement is required."
}
```

```json
{
  "code": "INVITE_CAMPAIGN_MULTI_USE_ACK_REQUIRED",
  "message_key": "invite_campaign.multi_use_ack_required",
  "message": "Multi-use acknowledgement is required."
}
```

### 5.3. Acceptance criteria

- [ ] Типовые ошибки campaign validation возвращают `code/message/message_key`.
- [ ] Admin UI показывает message string, а не object.
- [ ] В логах backend нет raw invite codes.
- [ ] OpenAPI обновлён.

---

## 6. Какой invite нужно создать для владельца проекта

Нужно создать **одну campaign** и **один root batch с одним многоразовым root invite-code**.

### 6.1. Итоговая логика

```text
Root invite-code:
- usage_mode = multi_use
- max_redemptions = 100000
- per_user_redemption_cap = 1
- expires_at = null
- grant_plan_code = premium_smart_ru
- grant_duration_mode = lifetime
- grant_device_limit_override = 5

При активации root-code:
- пользователь получает Premium Smart RU бессрочно;
- пользователь получает 5 устройств;
- пользователь получает Unlimited / fair_use traffic policy;
- пользователь получает 12 child invite-codes.

Child invite-codes:
- usage_mode = single_use
- max_redemptions = 1
- per_user_redemption_cap = 1
- expires_at = null
- child_grant_plan_code = premium_smart_ru
- child_grant_duration_mode = lifetime
- child_grant_device_limit_override = 5
```

---

## 7. Поля Campaign, которые нужно заполнить

### 7.1. Основные поля

```text
Campaign Key:
premium_smart_ru_lifetime_multi_root_2026_06_30

Name:
Premium Smart RU Lifetime Multi-use Root

Description:
Многоразовый root invite: Premium Smart RU lifetime, 5 devices, 12 unique single-use child invites.

Owner Mode:
system

Allowed Surfaces:
web
miniapp
telegram_bot
```

### 7.2. Grant / доступ пользователя

```text
План доступа:
оставить пустым / fallback

Код плана доступа:
premium_smart_ru

Срок доступа:
lifetime / Бессрочно

Дней доступа:
пусто

Лимит устройств:
5
```

В API это должно уйти так:

```json
{
  "grant_plan_id": null,
  "grant_plan_code": "premium_smart_ru",
  "grant_duration_mode": "lifetime",
  "grant_duration_days": null,
  "grant_device_limit_override": 5
}
```

### 7.3. Root invite policy

```text
Root Invite Expiry Mode:
none / Без срока

Root Invite Expiry Days:
пусто

Root Invite Expires At:
пусто

Root Usage Mode:
multi_use / Многоразовый

Root Max Redemptions:
100000

Root Per User Redemption Cap:
1
```

API:

```json
{
  "root_invite_expiry_mode": "none",
  "root_invite_expiry_days": null,
  "root_invite_expires_at": null,
  "root_usage_mode": "multi_use",
  "root_max_redemptions": 100000,
  "root_per_user_redemption_cap": 1
}
```

### 7.4. Child grant / дочерний доступ

```text
Дочерний план доступа:
оставить пустым / fallback

Код дочернего плана доступа:
premium_smart_ru

Срок дочернего доступа:
lifetime / Бессрочно

Дней дочернего доступа:
пусто

Лимит устройств дочернего доступа:
5
```

API:

```json
{
  "child_grant_plan_id": null,
  "child_grant_plan_code": "premium_smart_ru",
  "child_grant_duration_mode": "lifetime",
  "child_grant_duration_days": null,
  "child_grant_device_limit_override": 5
}
```

### 7.5. Child invite policy

```text
Child Invite Count:
12

Child Invite Free Days:
0

Child Invite Expiry Mode:
none / Без срока

Child Invite Expiry Days:
пусто

Child Invite Expires At:
пусто

Child Usage Mode:
single_use / Одноразовый

Child Max Redemptions:
1

Child Per User Redemption Cap:
1

Max Generation Depth:
5
```

API:

```json
{
  "child_invite_count": 12,
  "child_invite_free_days": 0,
  "child_invite_expiry_mode": "none",
  "child_invite_expiry_days": null,
  "child_invite_expires_at": null,
  "child_usage_mode": "single_use",
  "child_max_redemptions": 1,
  "child_per_user_redemption_cap": 1,
  "max_generation_depth": 5
}
```

### 7.6. Risk policy

```text
Per User Redeem Cap:
1

Max Redemptions Per Device:
1

Max Redemptions Per IP Window:
3

Velocity Window Hours:
24

Require No Active Access:
включено

Block Self Redemption:
включено

High Risk Context:
включено

Deny Disposable Email:
включено

Deny Known Abuse Subject:
включено

Multi-use Acknowledgement:
включено

Lifetime Campaign Acknowledgement:
включено

Raw Export Enabled:
включено
```

API:

```json
{
  "require_no_active_access": true,
  "block_self_redemption": true,
  "risk_policy": {
    "per_user_redeem_cap": 1,
    "high_risk_context": true,
    "max_redemptions_per_device": 1,
    "max_redemptions_per_ip_window": 3,
    "velocity_window_hours": 24,
    "deny_disposable_email": true,
    "deny_known_abuse_subject": true
  },
  "multi_use_acknowledgement": true,
  "lifetime_campaign_acknowledgement": true,
  "export_policy": {
    "raw_export_enabled": true
  }
}
```

### 7.7. Caps

```text
Global Issue Cap:
1500000

Max Per Batch:
1000

Max Per Owner:
12

Max Daily Issued:
10000
```

Почему `1500000`:

```text
1 root-code + 100000 root activations × 12 child invite-codes = 1 200 001
```

Ставим `1500000` с запасом.

API:

```json
{
  "caps": {
    "global_issue_cap": 1500000,
    "max_per_batch": 1000,
    "max_per_owner": 12,
    "max_daily_issued": 10000
  }
}
```

### 7.8. Dates / publish

```text
Starts At:
пусто

Expires At:
пусто

Publish Now:
лучше выключить при первом создании

Reason:
create premium smart ru lifetime multi-use root campaign
```

---

## 8. Payload для создания Campaign

После заполнения форма должна отправить примерно такой payload:

```json
{
  "campaign_key": "premium_smart_ru_lifetime_multi_root_2026_06_30",
  "name": "Premium Smart RU Lifetime Multi-use Root",
  "description": "Многоразовый root invite: Premium Smart RU lifetime, 5 devices, 12 unique single-use child invites.",
  "owner_mode": "system",
  "starts_at": null,
  "expires_at": null,
  "allowed_surfaces": ["web", "miniapp", "telegram_bot"],
  "allowed_geos": [],
  "allowed_markets": [],
  "allowed_segments": [],
  "risk_policy_key": null,

  "grant_plan_id": null,
  "grant_plan_code": "premium_smart_ru",
  "grant_duration_mode": "lifetime",
  "grant_duration_days": null,
  "grant_device_limit_override": 5,

  "root_invite_expiry_mode": "none",
  "root_invite_expiry_days": null,
  "root_invite_expires_at": null,
  "root_usage_mode": "multi_use",
  "root_max_redemptions": 100000,
  "root_per_user_redemption_cap": 1,

  "child_grant_plan_id": null,
  "child_grant_plan_code": "premium_smart_ru",
  "child_grant_duration_mode": "lifetime",
  "child_grant_duration_days": null,
  "child_grant_device_limit_override": 5,

  "child_invite_count": 12,
  "child_invite_free_days": 0,
  "child_invite_expiry_mode": "none",
  "child_invite_expiry_days": null,
  "child_invite_expires_at": null,
  "child_usage_mode": "single_use",
  "child_max_redemptions": 1,
  "child_per_user_redemption_cap": 1,
  "max_generation_depth": 5,

  "require_no_active_access": true,
  "block_self_redemption": true,
  "risk_policy": {
    "per_user_redeem_cap": 1,
    "high_risk_context": true,
    "max_redemptions_per_device": 1,
    "max_redemptions_per_ip_window": 3,
    "velocity_window_hours": 24,
    "deny_disposable_email": true,
    "deny_known_abuse_subject": true
  },
  "export_policy": {
    "raw_export_enabled": true
  },
  "notification_policy": {},
  "caps": {
    "global_issue_cap": 1500000,
    "max_per_batch": 1000,
    "max_per_owner": 12,
    "max_daily_issued": 10000
  },
  "multi_use_policy": {
    "high_risk_context": true,
    "cap_mode": "limited",
    "root_max_redemptions": 100000,
    "child_max_redemptions": 1
  },
  "multi_use_acknowledgement": true,
  "lifetime_campaign_acknowledgement": true,
  "publish": false,
  "reason": "create premium smart ru lifetime multi-use root campaign"
}
```

---

## 9. Создание root batch после публикации Campaign

После успешного создания campaign:

1. Открыть созданную campaign.
2. Нажать `Publish`.
3. Перейти во вкладку `Create Batch`.

Заполнить batch:

```text
Campaign:
выбрать созданную campaign

Owner User ID:
пусто

Owner User IDs:
пусто

Expiry Mode:
campaign_default

Count:
1

Batch Usage Mode:
campaign_default

Max Redemptions Per Code:
пусто

Per User Redemption Cap:
1

Expiry Days:
пусто

Expires At:
пусто

Idempotency Key:
premium-smart-ru-root-2026-06-30-001

Reason:
issue one multi-use root invite code
```

API payload:

```json
{
  "owner_user_id": null,
  "owner_user_ids": [],
  "count": 1,
  "expiry_mode": "campaign_default",
  "expiry_days": null,
  "expires_at": null,
  "usage_mode": "campaign_default",
  "max_redemptions_per_code": null,
  "per_user_redemption_cap": 1,
  "idempotency_key": "premium-smart-ru-root-2026-06-30-001",
  "reason": "issue one multi-use root invite code"
}
```

---

## 10. Проверка после создания root invite-code

### 10.1. Inventory filter

Открыть `Inventory` и выставить:

```text
Campaign Key:
premium_smart_ru_lifetime_multi_root_2026_06_30

Usage Mode:
multi_use

Generation Depth:
0

Plan Code:
premium_smart_ru
```

Ожидаемо:

```text
usage_mode = multi_use
max_redemptions = 100000
remaining_redemptions = 100000
per_user_redemption_cap = 1
status = issued или active
generation_depth = 0
expires_at = null
```

### 10.2. Тест активации

Пользователь A:

```text
1. Регистрируется.
2. Вводит root invite-code.
3. Получает Premium Smart RU lifetime.
4. Получает 12 child invite-codes.
```

Пользователь B:

```text
1. Регистрируется.
2. Вводит тот же root invite-code.
3. Тоже получает Premium Smart RU lifetime.
4. Тоже получает свои 12 child invite-codes.
```

Повторная активация User A:

```text
Должна быть отклонена:
Вы уже активировали этот invite-code.
```

### 10.3. Проверка child invite-codes

В Inventory:

```text
Campaign Key:
premium_smart_ru_lifetime_multi_root_2026_06_30

Generation Depth:
1

Owner User ID:
UUID пользователя A
```

Ожидаемо:

```text
12 кодов
usage_mode = single_use
max_redemptions = 1
per_user_redemption_cap = 1
grant_plan_code = premium_smart_ru
grant_duration_mode = lifetime
device_limit_override = 5
```

---

## 11. RSC/CORS blocker всё ещё нужно учитывать

В production-логе всё ещё видна ошибка:

```text
Access to fetch at 'https://cyber-vpn.net/en-EN'
redirected from 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=...'
from origin 'https://my.cyber-vpn.net' has been blocked by CORS policy.
```

Это мешает открывать `/rewards/invites` в личном кабинете.

Перед пользовательской проверкой invite list нужно выполнить:

```text
1. Cloudflare purge:
   cyber-vpn.net/*
   my.cyber-vpn.net/*
   api.cyber-vpn.net/*
   cyber-vpn.net/_next/static/*
   my.cyber-vpn.net/_next/static/*

2. Incognito / hard refresh.

3. Проверить:
   https://my.cyber-vpn.net/en-EN/rewards/invites
   https://my.cyber-vpn.net/ru-RU/rewards/invites
```

Если ошибка сохраняется, нужно снять Network evidence:

```text
- request URL;
- status;
- response headers;
- Location header;
- loaded JS chunk build id;
- runtime fingerprint.
```

---

## 12. Acceptance criteria

Работа считается закрытой, если:

- [ ] Ошибка React #31 больше не воспроизводится.
- [ ] Admin UI показывает backend validation errors строкой.
- [ ] В UI понятно, что бессрочный доступ задаётся `Duration Mode = lifetime`.
- [ ] Не требуется искать отдельный бессрочный тариф в списке планов.
- [ ] Premium Smart RU lifetime preset использует `grant_plan_code=premium_smart_ru`, а не обязательный `grant_plan_id`.
- [ ] Campaign создаётся с указанными полями.
- [ ] Campaign успешно публикуется.
- [ ] Batch создаёт один root multi-use invite-code.
- [ ] Root invite-code активируется разными пользователями.
- [ ] Один пользователь не может активировать root invite-code повторно.
- [ ] После активации пользователь получает Premium Smart RU lifetime.
- [ ] После активации пользователь получает 12 unique single-use child invite-codes.
- [ ] Child invite-коды дают Premium Smart RU lifetime.
- [ ] Inventory показывает root/child policies корректно.
- [ ] `/rewards/invites` открывается без RSC/CORS redirect после purge.
