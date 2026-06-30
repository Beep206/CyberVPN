# Техническое задание v7.6.2  
# Direct Production Rollout: Remnawave 2.8.0, XHTTP-ноды, Node Metrics, Multi-use Invites, Mini App и RSC/CORS

**Проект:** CyberVPN  
**Версия ТЗ:** v7.6.2  
**Основание:** после реализации v7.5.1 в репозитории основной функционал multi-use invite codes реализован, но перед production необходимо закрыть оставшиеся риски: backend/concurrency тесты, preview UX, Telegram/Mini App device context, корректный расчёт лимитов fan-out, legacy invite repository paths и фактическую RSC/CORS production-проблему.

---

## 0A. Управленческое решение: Remnawave 2.8.0 обновляется сразу на production

Принято решение выполнять обновление Remnawave `2.7.4 -> 2.8.0` **сразу на production**, без отдельного staging-этапа и без затяжной бюрократии.

Это ТЗ поэтому строится как **direct production rollout**:

```text
1. Быстрый production preflight.
2. Обязательный backup.
3. Короткий freeze только на операции, которые пишут в Remnawave.
4. Обновление Remnawave image до 2.8.0.
5. Автоматические production smoke checks.
6. Немедленный rollback при красных проверках.
7. Пост-проверка Mini App, Bot, Premium Smart RU, multi-use invite и cabinet RSC routes.
```

Важно: “без бюрократии” не означает “без страховки”. Backup, write-freeze, smoke и rollback являются обязательными техническими шагами, потому Remnawave хранит VPN-пользователей, subscription URLs, squads, hosts, templates и API tokens.

Запрещено выпускать обновление вслепую без:

```text
- backup Remnawave/Postgres;
- фиксации старого image digest;
- smoke проверки Remnawave API;
- smoke проверки CyberVPN provisioning;
- smoke проверки Telegram Mini App;
- rollback-команды под рукой.
```

## 1. Цель

Довести v7.5.1 до production-ready состояния.

Система должна гарантировать:

1. Многоразовый root invite-code может быть активирован разными пользователями.
2. Один пользователь не может активировать один и тот же multi-use invite-code повторно.
3. После каждой успешной активации root multi-use code пользователь получает:
   - Premium Smart RU lifetime;
   - 5 устройств;
   - безлимитный/fair-use трафик;
   - 12 уникальных child invite-кодов.
4. Child invite-коды могут оставаться одноразовыми.
5. Активные/неиспользованные invite-коды в клиентской зоне всегда отображаются сверху.
6. Использованные invite-коды всегда отображаются ниже активных.
7. Telegram Bot и Telegram Mini App работают с multi-use invite codes без ошибки отсутствующего device context.
8. Preview/resolve показывает корректный статус, если пользователь уже активировал multi-use code.
9. Race condition не может превысить `max_redemptions`.
10. Production больше не должен иметь RSC/CORS redirect `my.cyber-vpn.net -> cyber-vpn.net` для routes личного кабинета.
11. Telegram Mini App больше не должен падать с ошибкой `Произошёл сбой WebView`.
12. Remnawave должен быть безопасно обновлён с 2.7.4 до 2.8.0 с проверкой контрактов, миграций и новых возможностей.
13. Новые Remnawave 2.8.0 node metrics должны быть заведены в мониторинг, dashboards и alerts.
14. XHTTP должен быть рабочим режимом на выбранных Remnawave-нодаx, с node/host tags, response rules, client QA и rollback.

---

## 2. Текущее состояние

### 2.1. Что уже реализовано

В v7.5.1 уже добавлено:

- `usage_mode = single_use | multi_use` для invite codes;
- `max_redemptions`;
- `redeemed_count`;
- `active_redemptions_count`;
- `reversed_redemptions_count`;
- `per_user_redemption_cap`;
- `multi_use_policy`;
- root/child usage mode в campaign version;
- batch usage mode override;
- migration `20260629_invite_multi_use_v751.py`;
- сортировка клиентских invite-кодов через backend `status_sort_order` и frontend fallback helper;
- Telegram Bot sorting helper;
- admin UI поля для root/child usage mode;
- Premium Smart RU lifetime preset с root `multi_use`, child `single_use`, 12 child invites и 5 devices.

### 2.2. Что осталось доработать

Оставшиеся риски:

1. Недостаточно backend integration/concurrency тестов.
2. Preview/resolve может принять multi-use code, хотя текущий пользователь уже активировал его ранее.
3. Telegram Bot/Mini App apply может падать, если `device_key_hash` не сформирован.
4. `global_issue_cap` может быть слишком низким относительно `root_max_redemptions × child_invite_count`.
5. Legacy repository methods `get_available_by_code()` и `mark_used()` остаются опасными для multi-use.
6. Production всё ещё показывает RSC/CORS redirect на cabinet routes.
7. Не хватает smoke/evidence checklist после deploy.

---

## 3. P0. Backend integration/concurrency tests

### 3.1. Обязательные integration tests

Создать файл:

```text
backend/tests/integration/test_multi_use_invite_codes.py
```

или разбить на:

```text
backend/tests/integration/invites/test_multi_use_redemption.py
backend/tests/integration/invites/test_multi_use_concurrency.py
backend/tests/integration/invites/test_multi_use_child_invites.py
```

### 3.2. Test: root multi-use redeem by two different users

Scenario:

```text
Given:
  campaign root_usage_mode=multi_use
  root_max_redemptions=100
  root_per_user_redemption_cap=1
  child_usage_mode=single_use
  child_invite_count=12
  grant_plan_code=premium_smart_ru
  grant_duration_mode=lifetime
  grant_device_limit_override=5

When:
  User A redeems root code
  User B redeems same root code

Then:
  both redemptions succeed
  InviteCode.active_redemptions_count = 2
  InviteCode.redeemed_count = 2
  InviteCode.status = active
  InviteCode.is_used = false
  User A has Premium Smart RU entitlement
  User B has Premium Smart RU entitlement
  User A owns 12 child invite-codes
  User B owns 12 child invite-codes
  all child invite-codes usage_mode=single_use
```

### 3.3. Test: same user second redemption blocked

Scenario:

```text
Given:
  User A redeemed multi-use root code

When:
  User A redeems same code again

Then:
  response/error = INVITE_CODE_ALREADY_REDEEMED_BY_USER
  no second entitlement grant
  no second child batch
  active_redemptions_count unchanged
  redeemed_count unchanged
```

### 3.4. Test: max_redemptions exhaustion

Scenario:

```text
Given:
  root_usage_mode=multi_use
  root_max_redemptions=2

When:
  User A redeems
  User B redeems
  User C redeems

Then:
  User A success
  User B success
  User C blocked as exhausted
  InviteCode.status=exhausted
  InviteCode.is_used=true
  InviteCode.exhausted_at is not null
  active_redemptions_count=2
```

### 3.5. Test: parallel redemption race

Scenario:

```text
Given:
  root_usage_mode=multi_use
  root_max_redemptions=50

When:
  100 concurrent unique users redeem same code

Then:
  exactly 50 success
  exactly 50 exhausted/conflict
  active_redemptions_count=50
  redeemed_count=50
  no duplicate entitlement grants
  no duplicate child batches for same user
```

Implementation notes:

- использовать PostgreSQL integration test, не только SQLite;
- использовать `asyncio.gather`;
- для каждого user формировать отдельный `device_key_hash`;
- для IP cap временно настроить risk policy так, чтобы не блокировать concurrency раньше `max_redemptions`, либо распределить IP hash.

### 3.6. Test: child single-use generated after multi-use root redemption

Scenario:

```text
Given:
  root_usage_mode=multi_use
  child_usage_mode=single_use
  child_invite_count=12

When:
  User A redeems root code

Then:
  User A receives exactly 12 child invite-codes
  each child code:
    usage_mode=single_use
    max_redemptions=1
    per_user_redemption_cap=1
    owner_user_id=User A
    parent_invite_code_id=root code id
    root_invite_code_id=root code id
```

### 3.7. Test: tree for multi-use root

Scenario:

```text
Root code SMART-RU-VIP
├── User A redemption
└── User B redemption
```

Assertions:

```text
two InviteTreeEdge rows with same redeemed_invite_code_id/root_invite_code_id
different redemption_id
different invitee_user_id
tree API returns both users
child_batch_id is filled for both
```

---

## 4. P0. Preview/resolve must detect already redeemed by current user

### 4.1. Проблема

Сейчас apply/redeem корректно блокирует повторную активацию multi-use code тем же пользователем. Но preview/resolve может вернуть `accepted=true`, потому проверяет exhaustion/single-use state, но не проверяет user-level redemption history.

Это создаёт плохой UX:

```text
preview: код принят
apply: вы уже активировали этот код
```

### 4.2. Требование

В `ResolveGrowthCodeUseCase._resolve_invite(...)` добавить async user-level проверку:

```python
async def _has_user_redeemed_invite(
    self,
    *,
    invite_code_id: UUID,
    user_id: UUID,
) -> bool:
    ...
```

Проверка:

```sql
SELECT 1
FROM invite_redemptions
WHERE invite_code_id = :invite_code_id
  AND invitee_user_id = :user_id
  AND status = 'redeemed'
LIMIT 1
```

### 4.3. Изменить `_resolve_invite`

Текущий `_resolve_invite` должен стать async, если ещё не async.

Логика:

```python
if user_id is not None and await self._has_user_redeemed_invite(invite_code_id=invite.id, user_id=user_id):
    return GrowthCodeResolutionOutcome(
        accepted=False,
        code_type=GrowthCodeType.INVITE,
        action_context=action_context,
        result=GrowthCodeResolutionStatus.REJECTED,
        reject_reason=GrowthCodeRejectReason.CODE_ALREADY_REDEEMED,
        user_message_key="growth_codes.invite.already_redeemed_by_user",
        issuer_type=self._invite_issuer_type(invite.source),
        owner_type="customer",
        resolved_code_id=invite.id,
    )
```

### 4.4. API/UX behavior

Preview endpoint должен вернуть:

```json
{
  "accepted": false,
  "detected_code_type": "invite",
  "status": "rejected",
  "message_key": "growth_codes.invite.already_redeemed_by_user",
  "next_action": "show_error"
}
```

### 4.5. Tests

- preview returns accepted for first-time User A;
- apply succeeds;
- preview for User A returns already redeemed;
- preview for User B still returns accepted;
- exhausted code preview returns exhausted.

---

## 5. P0. Telegram Bot / Mini App device context

### 5.1. Проблема

Multi-use/lifetime invite redemption требует `device_key_hash` и `client_ip_hash` для anti-abuse. Web может иметь device cookie/header, но Telegram Bot server-to-server apply может не иметь device cookie.

Если device context отсутствует, redeem может упасть:

```text
Invite redemption requires device context
```

### 5.2. Требование для Telegram Bot

В server-to-server Telegram Bot apply flow backend должен формировать deterministic device context:

```python
device_key_source = f"telegram_bot:{telegram_id}"
device_key_hash = hash_device_key(device_key_source)
client_ip_hash = hash_runtime_key("telegram_bot:server_to_server")
```

Но лучше IP hash формировать из real Telegram user/session context, если есть trusted source:

```text
telegram_id
chat_id
bot_instance_id
```

В `customer_onboarding/routes.py` изменить `_invite_redemption_runtime_context(...)` или добавить отдельный helper:

```python
def _invite_redemption_runtime_context_for_surface(
    *,
    request: Request,
    source_surface: str,
    telegram_id: int | None,
) -> InviteRedemptionRuntimeContext:
    if source_surface == "telegram_bot" and telegram_id is not None:
        return InviteRedemptionRuntimeContext(
            client_ip_hash=_hash_runtime_key(f"telegram_bot:{telegram_id}:ipless"),
            device_key_hash=hash_device_key(f"telegram_bot:{telegram_id}"),
        )
    ...
```

### 5.3. Требование для Telegram Mini App

Mini App должен иметь stable device id.

Frontend Mini App:

- если `__Host-cvpn_device_id` отсутствует, backend/session middleware должен выпустить его;
- если cookie unavailable внутри Telegram WebView, frontend должен отправлять `X-CyberVPN-Device-ID`;
- значение должно быть stable per Telegram Mini App install/session.

Рекомендуемый вариант:

```text
device id = sha256("miniapp:" + telegram_user_id + ":" + init_data_hash)
```

Важно: не использовать raw initData в логах или persistent client storage.

### 5.4. Backend acceptance

Onboarding apply для `source_surface=telegram_bot` и `source_surface=miniapp` не должен падать из-за отсутствующего browser cookie.

### 5.5. Tests

- `/customer/onboarding/growth-code/apply` with `source_surface=telegram_bot`, `telegram_id`, no cookies -> success.
- `/customer/onboarding/growth-code/apply` with `source_surface=miniapp`, valid auth, no device cookie but header `X-CyberVPN-Device-ID` -> success.
- Missing device context in normal web still blocked for high-risk lifetime/multi-use campaigns.
- Logs do not include raw Telegram initData or raw invite code.

---

## 6. P1. Admin UI: global issue cap / fan-out estimator

### 6.1. Проблема

Для multi-use root code:

```text
root_max_redemptions = 100000
child_invite_count = 12
global_issue_cap = 100000
```

Фактический fan-out может потребовать:

```text
root codes count + root_max_redemptions × child_invite_count
= 1 + 100000 × 12
= 1 200 001
```

Если `global_issue_cap=100000`, кампания остановится примерно после 8 333 root redemptions.

### 6.2. Требование

В admin UI добавить preview-калькулятор:

```text
Root max redemptions: 100000
Root batch count: 1
Child invite count: 12
Max generation depth: 5
Estimated first-generation child invite issuance: 1 200 000
Minimum recommended global_issue_cap: 1 200 001
Current global_issue_cap: 100000
Status: too low
```

### 6.3. Backend validation/warning

В `ValidateInviteCampaignVersionUseCase` добавить warning:

```python
estimated_first_generation_issue = root_max_redemptions * child_invite_count
if global_issue_cap < estimated_first_generation_issue:
    warnings.append(
        "global_issue_cap is lower than root_max_redemptions × child_invite_count; campaign may stop early"
    )
```

Если `publish=true` и `global_issue_cap` слишком низкий, поведение:

- не блокировать полностью;
- но вернуть warning;
- в admin UI показывать warning красным/жёлтым.

### 6.4. Acceptance

- UI показывает расчёт перед созданием/публикацией.
- Backend validation возвращает warning.
- Operator понимает, почему кампания может остановиться раньше.

---

## 7. P1. Legacy invite repository paths

### 7.1. Проблема

В `InviteCodeRepository` остались legacy methods:

```python
get_available_by_code()
mark_used()
```

Они используют старую single-use модель и могут сломать multi-use, если кто-то вызовет их для multi-use code.

### 7.2. Требование

Проверить все call sites:

```bash
rg "get_available_by_code|mark_used" backend/src backend/tests
```

### 7.3. Вариант A — удалить

Если call sites нет:

- удалить методы;
- удалить тесты;
- заменить на новые repository methods.

### 7.4. Вариант B — оставить legacy-only с guard

Если методы нужны:

```python
async def mark_used(self, id: UUID, used_by_user_id: UUID) -> InviteCodeModel | None:
    invite_code = await self._session.get(InviteCodeModel, id)
    if invite_code is None:
        return None
    if invite_code.usage_mode == "multi_use":
        raise RuntimeError("mark_used is not allowed for multi_use invite codes")
    ...
```

`get_available_by_code()`:

```python
WHERE usage_mode = 'single_use'
```

или переименовать:

```python
get_available_single_use_by_code()
```

### 7.5. Tests

- `mark_used()` raises for multi-use.
- `mark_used()` still works for legacy single-use.
- No production multi-use flow calls `mark_used()`.

---

## 8. P1. Admin inventory and code detail hardening

### 8.1. Inventory columns

Убедиться, что admin inventory показывает:

```text
Usage mode
Redemptions
Remaining
Max redemptions
Per-user cap
First redeemed
Last redeemed
Exhausted
Status sort order
```

### 8.2. Detail/drawer for multi-use code

Добавить detail drawer:

```text
Code summary
Redemption policy
Grant policy
Child policy
Latest redemptions
Tree entry
Risk/audit events
```

Для multi-use:

```text
Total redeemed
Active redemptions
Reversed redemptions
Remaining redemptions
Max redemptions
Last 50 redeeming users
Export redemptions CSV
```

### 8.3. Tests

- Inventory displays multi-use counters.
- Filtering by `usage_mode=multi_use` works.
- Detail drawer lists redemptions.
- Export does not expose raw invite code unless explicit batch export permission.

---

## 9. P1. Reversal/counter correctness

### 9.1. Проблема

Multi-use reversal должен обновлять counters:

```text
active_redemptions_count--
reversed_redemptions_count++
remaining_redemptions++
```

Если код был `exhausted`, после reversal он может стать снова `active`, если policy разрешает.

### 9.2. Требование

В reverse redemption flow:

```python
if redemption.usage_mode_snapshot == "multi_use":
    invite.active_redemptions_count = max(invite.active_redemptions_count - 1, 0)
    invite.reversed_redemptions_count += 1
    if invite.status == "exhausted" and invite.active_redemptions_count < invite.max_redemptions:
        invite.status = "active"
        invite.is_used = False
        invite.exhausted_at = None
```

Но повторная активация тем же user после reversal должна зависеть от policy:

```text
default: deny same user after reversal
optional future: allow after reversal with admin override
```

Для текущей итерации:

```text
same user cannot redeem same invite again even after reversal
```

### 9.3. Tests

- reverse one redemption updates counters.
- exhausted code becomes active if active_count below cap.
- same user cannot redeem again after reversal.
- unused child invites from that redemption are revoked if cascade mode says so.

---

## 10. P0/P1. RSC/CORS production routing smoke

### 10.1. Проблема

Production still shows:

```text
my.cyber-vpn.net/en-EN/rewards/*?_rsc=...
→ cyber-vpn.net/en-EN
→ CORS blocked
```

This blocks customer cabinet navigation and invite pages.

### 10.2. Требование

After every deploy run external smoke:

```bash
HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh
```

Manual probes:

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

Fail if:

```text
HTTP 30x
Location: https://cyber-vpn.net/...
Location: https://www.cyber-vpn.net/...
```

Accept:

```text
200
204
404
```

### 10.3. Fingerprint check

Add to deploy evidence:

```bash
curl -s https://cyber-vpn.net/runtime/fingerprint
curl -s https://my.cyber-vpn.net/runtime/fingerprint
curl -s https://api.cyber-vpn.net/api/v1/runtime/fingerprint
```

All must report same release/git_sha/origin marker.

### 10.4. Cloudflare purge

After deploy:

```text
purge cyber-vpn.net/*
purge my.cyber-vpn.net/*
purge api.cyber-vpn.net/*
```

Then test in incognito/private browser.

---

## 10A. P0. Telegram Mini App WebView crash: «Произошёл сбой WebView»

### 10A.1. Симптом

Telegram Bot на `/start` уже отвечает корректно:

```text
🔄 С возвращением, Beep!

Что хотите сделать дальше?
```

и показывает кнопки меню. Это означает, что базовая bot registration/session часть уже работает лучше, чем раньше.

Но при открытии Mini App внутри Telegram пользователь видит:

```text
Произошёл сбой WebView
```

Это отдельная P0-проблема Telegram Mini App surface. Её нельзя считать закрытой только потому, что обычный URL `/miniapp` отдаёт `200` через curl или открывается в desktop browser.

### 10A.2. Гипотеза

Mini App может падать в Telegram WebView по одной или нескольким причинам:

```text
1. Mini App URL в BotFather/menu button ведёт не на canonical route.
2. /miniapp делает redirect на /dashboard, /register, /login или другой origin.
3. customer_site_mode=cabinet_only не пропускает /miniapp во внешнем runtime.
4. Cloudflare/edge отдаёт старый frontend bundle или challenge/interstitial.
5. Telegram WebView получает RSC/CORS redirect my.cyber-vpn.net -> cyber-vpn.net.
6. JavaScript падает до первого render из-за отсутствующего window.Telegram.WebApp или initData parsing.
7. Auth provider запускает web registration/login flow вместо Telegram Mini App auth.
8. CSP, security headers или mixed content ломают загрузку chunks/API.
9. Next.js chunk/cache mismatch после deploy.
10. Service Worker или browser cache отдаёт старый chunk.
11. Locale route /ru-RU/miniapp или /en-EN/miniapp не совпадает с реальными routes.
12. API origin внутри Mini App недоступен или отвечает redirect/401/HTML вместо JSON.
```

### 10A.3. Цель

Mini App должен стабильно открываться внутри Telegram WebView и показывать CyberVPN Mini App UI, а не:

```text
Произошёл сбой WebView
страницу регистрации
личный кабинет dashboard
пустой экран
Cloudflare/interstitial
web login flow
```

### 10A.4. Canonical Mini App URL

Зафиксировать один canonical URL:

```text
https://cyber-vpn.net/ru-RU/miniapp
```

Дополнительно разрешённые маршруты:

```text
https://cyber-vpn.net/ru-RU/miniapp/home
https://cyber-vpn.net/ru-RU/miniapp/onboarding/code
https://cyber-vpn.net/ru-RU/miniapp/diagnostics
https://cyber-vpn.net/ru-RU/miniapp/health
```

Bot menu button, inline keyboard и backend settings должны использовать этот canonical URL или URL, возвращённый backend runtime config.

Запрещено:

```text
https://my.cyber-vpn.net/ru-RU/miniapp
https://cyber-vpn.net/ru-RU/dashboard
https://cyber-vpn.net/ru-RU/register
https://my.cyber-vpn.net/ru-RU/dashboard
```

если это не явный redirect policy, согласованный отдельно.

### 10A.5. Telegram Bot menu button verification

При старте bot service логировать sanitized Mini App URL:

```text
telegram_miniapp_configured
bot_username=...
miniapp_url_host=cyber-vpn.net
miniapp_url_path=/ru-RU/miniapp
menu_button_type=web_app
```

Добавить startup validation:

```python
if not settings.miniapp_url.startswith("https://"):
    raise RuntimeError("Telegram Mini App URL must be HTTPS")

if "/miniapp" not in settings.miniapp_url:
    raise RuntimeError("Telegram Mini App URL must point to /miniapp")
```

Добавить диагностику:

```text
GET /webhook/telegram/diagnostics
```

Response должен включать:

```json
{
  "miniapp_url": "https://cyber-vpn.net/ru-RU/miniapp",
  "miniapp_url_host": "cyber-vpn.net",
  "miniapp_url_path": "/ru-RU/miniapp",
  "menu_button_configured": true
}
```

Секреты не возвращать.

### 10A.6. Mini App health route

Добавить максимально лёгкий route:

```text
GET /ru-RU/miniapp/health
```

Требования:

```text
- не требует auth;
- не вызывает Telegram initData auth;
- не делает API calls;
- не использует тяжёлые клиентские bundles;
- отдаёт простой статический экран/JSON;
- должен открываться в Telegram WebView.
```

Response для route handler:

```json
{
  "ok": true,
  "surface": "telegram_miniapp",
  "release": "...",
  "git_sha": "...",
  "origin_marker": "..."
}
```

Цель: отличить route/edge/WebView проблему от auth/application boot problem.

### 10A.7. Mini App diagnostics route

Добавить route:

```text
/ru-RU/miniapp/diagnostics
```

UI должен показывать:

```text
Telegram WebApp detected: yes/no
initData present: yes/no
initDataUnsafe.user.id present: yes/no
platform: ios/android/tdesktop/web/unknown
version: Telegram WebApp version
colorScheme
viewportHeight
API base URL
runtime fingerprint
frontend release/git_sha
backend fingerprint reachable: yes/no
client capabilities reachable: yes/no
auth session restore: success/fail/skipped
```

Важно:

```text
Не показывать raw initData.
Не логировать raw initData.
Не отправлять raw initData в сторонние сервисы.
```

### 10A.8. Client-side error boundary для Mini App

В `frontend/src/app/[locale]/miniapp/layout.tsx` или ближайшем Mini App provider добавить отдельный error boundary:

```text
MiniAppErrorBoundary
```

Он должен:

1. Перехватывать render/runtime ошибки.
2. Показывать user-friendly fallback:

```text
Не удалось открыть Mini App.
Попробуйте обновить окно или открыть через кнопку бота ещё раз.
Код диагностики: ...
```

3. Отправлять sanitized error event в backend:

```text
POST /api/v1/client-errors/miniapp
```

Payload:

```json
{
  "surface": "miniapp",
  "route": "/ru-RU/miniapp",
  "telegram_platform": "android",
  "telegram_version": "7.10",
  "webapp_version": "6.9",
  "error_name": "TypeError",
  "error_message": "sanitized message",
  "chunk": "optional chunk name",
  "release": "...",
  "git_sha": "..."
}
```

Запрещено:

```text
raw initData
raw invite codes
tokens
cookies
subscription URLs
```

### 10A.9. Global Mini App JS crash capture

В Mini App client bootstrap добавить:

```ts
window.addEventListener('error', ...)
window.addEventListener('unhandledrejection', ...)
```

Только для `/miniapp` routes.

Отправлять sanitized telemetry:

```text
miniapp_webview_js_error
miniapp_webview_unhandled_rejection
miniapp_auth_restore_failed
miniapp_init_data_missing
miniapp_api_unexpected_html
miniapp_chunk_load_failed
```

Если ошибка `ChunkLoadError`:

```text
показать кнопку "Обновить Mini App"
очистить Next cache/service worker, если применимо
выполнить location.reload()
```

### 10A.10. Mini App auth flow hardening

Mini App должен использовать отдельный flow:

```text
1. Detect Telegram WebApp.
2. Call Telegram.WebApp.ready().
3. Try session restore.
4. If session restore success -> open Mini App.
5. If no session -> authenticate via initData.
6. If initData missing inside Telegram WebView -> show diagnostics, not register page.
7. If auth fails because registration closed -> show onboarding/code entry, not web register page.
8. If user is pending_onboarding -> open /miniapp/onboarding/code.
9. If user has access -> open /miniapp/home.
```

Запрещено в Mini App:

```text
redirect to /register
redirect to /login
redirect to cabinet dashboard
cross-origin redirect during RSC fetch
```

### 10A.11. Security headers / CSP check

Проверить headers для:

```text
https://cyber-vpn.net/ru-RU/miniapp
https://cyber-vpn.net/ru-RU/miniapp/home
https://cyber-vpn.net/ru-RU/miniapp/diagnostics
```

Требования:

```text
- no Cloudflare challenge/interstitial
- content-type text/html for app pages
- no X-Frame-Options DENY that breaks Telegram WebView if applicable
- CSP allows own scripts/chunks/styles/images/API endpoints
- no mixed content http:// resources
- no redirect to my.cyber-vpn.net or /dashboard
```

Примечание: Telegram Mini App обычно открывается в WebView, не как обычный iframe, но security headers всё равно могут ломать scripts/chunks/API. Нужно проверить фактическое поведение на Android/iOS/Desktop Telegram.

### 10A.12. Edge / Cloudflare Mini App bypass

Для `/miniapp` routes:

```text
cyber-vpn.net/*/miniapp*
```

Cloudflare должен:

```text
- не показывать challenge;
- не включать HTML rewriting, которое ломает Telegram WebView;
- не отдавать stale JS chunks после deploy;
- не редиректить на my.cyber-vpn.net;
- не кэшировать auth-sensitive API responses.
```

Добавить deploy step:

```text
Purge Cloudflare cache for:
cyber-vpn.net/*miniapp*
cyber-vpn.net/_next/static/*
```

### 10A.13. Mini App API response hardening

В Mini App auth/session/client capabilities API calls проверять:

```text
content-type application/json
status code
redirected flag
final URL
```

Если API вернул HTML вместо JSON, показать diagnostics:

```text
API вернул HTML/redirect вместо JSON.
Проверьте edge routing и API origin.
```

### 10A.14. RSC/CORS linkage

Mini App WebView crash может быть связан с уже известной RSC/CORS проблемой, где cabinet routes получают redirect:

```text
my.cyber-vpn.net/en-EN/rewards/*?_rsc=...
→ cyber-vpn.net/en-EN
```

Это уже зафиксировано как отдельный production blocker в ТЗ, но для Mini App нужно добавить отдельные RSC probes:

```bash
curl -I 'https://cyber-vpn.net/ru-RU/miniapp?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component' \
  -H 'Next-Router-State-Tree: []' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Dest: empty'

curl -I 'https://cyber-vpn.net/ru-RU/miniapp/home?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component'
```

Fail condition:

```text
HTTP 30x
Location: https://my.cyber-vpn.net/...
Location: https://cyber-vpn.net/ru-RU/dashboard
Location: /register
Location: /login
```

### 10A.15. Manual Telegram WebView QA matrix

Проверить Mini App внутри Telegram:

```text
Android Telegram stable
iOS Telegram stable
Telegram Desktop
Telegram Web K, если применимо
```

Для каждого:

```text
/start -> кнопка Mini App -> открывается Mini App
/start -> меню -> Mini App -> открывается Mini App
Mini App health route opens
Mini App diagnostics route opens
Mini App home route opens
Mini App onboarding code route opens
No "Произошёл сбой WebView"
No blank screen
No redirect to register/login/dashboard
```

### 10A.16. Required production evidence

Перед закрытием задачи приложить:

```text
1. Telegram getWebhookInfo без pending 401.
2. Bot /start screenshot/log: работает.
3. Mini App open from Telegram Android: works.
4. Mini App open from Telegram iOS: works.
5. /miniapp/health external curl.
6. /miniapp/diagnostics external curl.
7. Runtime fingerprints:
   - https://cyber-vpn.net/runtime/fingerprint
   - https://api.cyber-vpn.net/api/v1/runtime/fingerprint
8. RSC smoke for cabinet routes.
9. RSC smoke for miniapp routes.
10. Cloudflare purge confirmation.
```

### 10A.17. Acceptance criteria

Mini App WebView task is accepted only if:

- [ ] Bot `/start` still works and shows menu/buttons.
- [ ] Mini App opens from Telegram menu button.
- [ ] Mini App opens from inline keyboard button.
- [ ] `https://cyber-vpn.net/ru-RU/miniapp` does not redirect to dashboard/register/login.
- [ ] `https://cyber-vpn.net/ru-RU/miniapp/health` works in browser and Telegram WebView.
- [ ] `https://cyber-vpn.net/ru-RU/miniapp/diagnostics` works in browser and Telegram WebView.
- [ ] Telegram WebView no longer shows `Произошёл сбой WebView`.
- [ ] Mini App auth does not open web registration page.
- [ ] Pending onboarding user sees code entry flow.
- [ ] Existing user sees Mini App home.
- [ ] Client-side Mini App errors are captured with sanitized telemetry.
- [ ] No raw initData, invite code, token, cookie or subscription URL is logged.
- [ ] RSC/CORS probes for Mini App routes do not redirect cross-origin.
- [ ] Production evidence is attached to deploy notes.

## 10B. P0/P1. Remnawave 2.8.0: обновление с 2.7.4, миграция, проверка контрактов и использование новых возможностей

### 10B.0. Direct production note

Release notes Remnawave 2.8.0 must be treated as source of truth for new behavior. CyberVPN must not enable new protocol features globally during the direct production upgrade. The upgrade goal is first compatibility and stability, then controlled enablement of new features.

### 10B.0A. Дополнительное обязательное решение: node metrics и XHTTP входят в scope релиза

В этом релизе нужно не только обновить Remnawave до `2.8.0`, но и **ввести в эксплуатацию новые возможности**, важные для CyberVPN:

```text
1. Node CPU load metrics и связанные node observability-метрики должны быть заведены в Prometheus/Grafana/alerts.
2. XHTTP должен реально работать на выбранных нодах, а не остаться только в коде или выключенным feature flag.
3. XHTTP включается не всем сразу, а через controlled rollout:
   - сначала dedicated XHTTP test node/host;
   - затем internal/test пользователи;
   - затем Premium Smart RU canary;
   - затем production cohort.
4. Если XHTTP ломает клиентские конфиги, основной VPN-доступ должен продолжать работать через текущие stable transports.
```

Финальный acceptance по Remnawave 2.8.0 не считается выполненным, пока:

```text
- node CPU load metrics видны в dashboard;
- есть alerts по CPU load / node health;
- есть хотя бы одна XHTTP-capable нода;
- тестовый пользователь получает subscription config с XHTTP;
- Mihomo import с XHTTP проходит;
- iOS/Android/Desktop QA по XHTTP выполнен или XHTTP ограничен только совместимыми клиентами.
```

### 10B.1. Контекст

Сейчас в инфраструктурном Ansible default используется образ:

```yaml
control_plane_stack_remnawave_image: remnawave/backend:2.7.4
```

Целевое обновление:

```yaml
control_plane_stack_remnawave_image: remnawave/backend:2.8.0
```

или, если принято использовать GHCR:

```yaml
control_plane_stack_remnawave_image: ghcr.io/remnawave/backend:2.8.0
```

Важно: в production запрещено использовать `latest`. Образ должен быть закреплён конкретным tag и желательно digest.

Официальный release `remnawave/backend v2.8.0` опубликован 29 Jun 16:09 и содержит изменения относительно `2.7.4...2.8.0`. В release notes заявлены новые возможности и исправления, которые потенциально влияют на CyberVPN-интеграцию:

```text
- xhttp transport / xhttp opts / session-table / session-length для Mihomo;
- Hysteria2 support и Hysteria2 link generation;
- ECH settings в Xray JSON generator;
- tun protocol в inbound config;
- KCP parameter handling;
- v2plus client в JSON subscription fallback clients;
- base64 transformation в TemplateEngine;
- DESCRIPTION template key;
- ASN support для Node Plugin;
- Node CPU load average metrics 1/5/15;
- query stats for multiple nodes;
- verifyPeerCertByName / mihomoIpVersion;
- multiple tags for hosts;
- excludeHostsByTags в response rules;
- proxyUrl для nodes;
- nodeConsumptionMultiplier;
- custom billing node;
- scoped API tokens;
- expireAt для API tokens;
- cursor-based endpoint for fetching all users;
- DIRECT_URL для Prisma;
- fixes по HWID limit, HWID race condition, request IP в upsert HWID device;
- subscription query encoding `%20` вместо `+` для iOS SNI/host bug;
- unlimited traffic handling in templates;
- CSP/connect-src fixes;
- webhook schema fixes;
- response rules validation fixes.
```

### 10B.2. Главная цель

Обновить Remnawave с `2.7.4` до `2.8.0` так, чтобы:

```text
1. не сломать выдачу VPN-конфигов;
2. не сломать Premium Smart RU;
3. не сломать Telegram Bot / Mini App;
4. не сломать lifetime/multi-use invite activation;
5. не сломать Remnawave webhooks;
6. не сломать Helix adapter;
7. не сломать текущие subscription URLs;
8. использовать новые возможности 2.8.0 только через feature flags и staged rollout.
```

### 10B.3. Что нельзя делать

Запрещено:

```text
- обновлять production сразу на latest;
- одновременно обновлять Remnawave и делать major upgrade PostgreSQL;
- включать Hysteria2/xhttp/ECH/tun по умолчанию всем пользователям;
- менять production response rules без staging validation;
- ротировать API tokens без dual-token/rollback плана;
- удалять старые шаблоны подписок до проверки новых;
- менять Smart RU squads без тестового пользователя и rollback.
```

---

## 10B.4. Preflight discovery

Перед кодовыми изменениями собрать фактическое состояние production.

### 10B.4.1. Версии и digest

На production:

```bash
docker inspect remnawave --format '{{.Config.Image}} {{.Image}}'
docker exec remnawave node -v || true
docker exec remnawave printenv | sort | grep -E 'REMNAWAVE|POSTGRES|REDIS|FRONT|PANEL|SUB|METRICS|HELIX|JWT|API|DATABASE'
```

Зафиксировать:

```text
current image tag
current image digest
current Remnawave app version
current database version
current environment variables
current ports
current healthcheck status
```

### 10B.4.2. Бэкап

Перед обновлением обязательно:

```bash
pg_dump -Fc -h <postgres_host> -U <user> -d <db> -f remnawave_pre_2_8_0.dump
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml logs --tail=300 remnawave > remnawave_pre_2_8_0.log
```

Также сохранить export текущих сущностей через Remnawave API или прямой read-only snapshot:

```text
users
nodes
internal squads
external squads
hosts
inbounds
subscription templates
response rules
api tokens metadata
webhook settings
```

Не экспортировать raw secrets в общий артефакт.

### 10B.4.3. Контракты CyberVPN → Remnawave

Проверить все текущие CyberVPN calls:

```text
GET /api/users/{uuid}
GET /api/users/by-username/{username}
GET /api/users/by-telegram-id/{telegram_id}
GET /api/users
POST /api/users
PATCH /api/users
POST /api/users/{uuid}/actions/revoke
DELETE /api/users/{uuid}
GET /internal-squads
GET /api/subscriptions/by-uuid/{uuid}
GET /api/nodes
GET /api/inbounds
GET /api/hosts
```

В CyberVPN есть `RemnawaveClient`, который нормализует base URL и добавляет `/api` к path, а также validated methods через Pydantic-схемы. Поэтому после 2.8.0 важно проверить, что upstream response envelopes и новые fields не ломают validation.

---

## 10B.5. Infrastructure changes

### 10B.5.1. Обновить Ansible default image

Файл:

```text
infra/ansible/roles/control_plane_stack/defaults/main.yml
```

Заменить:

```yaml
control_plane_stack_remnawave_image: remnawave/backend:2.7.4
```

на:

```yaml
control_plane_stack_remnawave_image: remnawave/backend:2.8.0
```

или:

```yaml
control_plane_stack_remnawave_image: ghcr.io/remnawave/backend:2.8.0
```

### 10B.5.2. Не обновлять PostgreSQL major в этом же релизе

Release notes Remnawave 2.8.0 упоминают обновление PostgreSQL в compose files. Для CyberVPN в этом ТЗ:

```text
PostgreSQL остаётся на текущей production major версии.
```

Если потребуется PostgreSQL major upgrade, создать отдельное ТЗ:

```text
Remnawave PostgreSQL major upgrade
```

с отдельным `pg_upgrade`, rollback, logical backup и restore rehearsal.

### 10B.5.3. Pull policy

Для production:

```yaml
control_plane_stack_pull_policy: always
```

или гарантированный `docker compose pull remnawave` перед restart.

Но после pull фиксировать digest:

```bash
docker image inspect remnawave/backend:2.8.0 --format '{{index .RepoDigests 0}}'
```

### 10B.5.4. Healthcheck

Текущий compose healthcheck проверяет:

```text
http://localhost:3001/health
```

Оставить, но добавить deploy smoke:

```bash
curl -f http://127.0.0.1:3005/api/system/health || curl -f http://127.0.0.1:3005/health
curl -f http://127.0.0.1:3001/health
curl -u "$METRICS_USER:$METRICS_PASS" http://127.0.0.1:3001/metrics | head
```

---

## 10B.6. API tokens: scoped tokens and expiration

### 10B.6.1. Новая возможность

Remnawave 2.8.0 добавляет scoped API tokens и `expireAt` для API tokens.

### 10B.6.2. Требование

Разделить токены:

```text
CyberVPN backend token:
  users:read
  users:create
  users:update
  users:delete/revoke
  subscriptions:read
  internal-squads:read
  nodes:read
  hosts:read
  inbounds:read

CyberVPN worker token:
  users:read
  subscriptions:read
  metrics/read if needed
  abuse actions only if worker really disables users

Helix adapter token:
  only scopes needed for Helix manifests/integration
```

Точные названия scopes взять из Remnawave 2.8.0 API/admin UI.

### 10B.6.3. Backend config

Добавить optional env metadata:

```env
REMNAWAVE_TOKEN_EXPIRES_AT=2027-01-01T00:00:00Z
REMNAWAVE_TOKEN_SCOPE_LABEL=cybervpn-backend-prod
REMNAWAVE_TOKEN_ROTATION_WARNING_DAYS=14
```

В readiness/runtime fingerprint добавить warning:

```json
{
  "remnawave_token_expires_at": "...",
  "remnawave_token_expires_in_days": 13,
  "remnawave_token_rotation_required": true
}
```

Не возвращать сам token.

### 10B.6.4. Rotation plan

1. Создать новые scoped tokens в Remnawave 2.8.0.
2. Добавить их в vault.
3. Развернуть backend/worker/helix с новыми tokens.
4. Проверить smoke.
5. Удалить старые tokens.
6. Проверить audit notification в Remnawave.

---

## 10B.7. Контракты и Pydantic-схемы CyberVPN

### 10B.7.1. Update response schemas

Файл:

```text
backend/src/infrastructure/remnawave/contracts.py
```

Добавить/проверить поля, появившиеся или изменившиеся в 2.8.0:

```text
Host:
  tags: list[str]
  verifyPeerCertByName: bool | None
  mihomoIpVersion: str | None
  pinnedPeerCertSha256: str | None
  xhttpExtraParams / xhttp extra fields if exposed
  ech settings if exposed
  excludeHostsByTags if response rules exposed

Node:
  note: str | None
  proxyUrl: str | None
  nodeConsumptionMultiplier: float | None
  consumptionMultiplier alias compatibility
  CPU load averages if node/system metrics response exposes them

User:
  HWID active headers/fields if exposed
  user identifier numeric ID fields if returned
  traffic limit filtering fields if list response includes them
  usedTrafficPercentage if returned

Subscription:
  v2plus client compatibility fields
  Hysteria2 link fields
  xhttp link fields
  tun/mihomo fields
```

### 10B.7.2. Extra fields policy

Pydantic schemas should stay tolerant to additional upstream fields:

```python
extra = "ignore"
```

Do not use `extra="forbid"` for Remnawave user/node/host/subscription responses unless intentionally strict and covered by tests.

### 10B.7.3. Contract tests

Create:

```text
backend/tests/integration/remnawave/test_remnawave_2_8_contracts.py
```

Test with recorded fixtures from Remnawave 2.8.0:

```text
user response
user list response
node response with CPU/load fields
host response with multiple tags
host response with pinnedPeerCertSha256
host response with mihomoIpVersion
subscription response with xhttp/hysteria2/v2plus fields
internal squads response
```

---

## 10B.8. User provisioning compatibility

### 10B.8.1. Existing user payload mapping

Current CyberVPN normalizes payload fields:

```text
expire_at -> expireAt
telegram_id -> telegramId
traffic_limit_bytes -> trafficLimitBytes
hwid_device_limit -> hwidDeviceLimit
external_squad_uuid -> externalSquadUuid
active_internal_squads -> activeInternalSquads
```

It also removes explicit `trafficLimitBytes=null`, because Remnawave treats missing traffic limit as unlimited and rejects explicit null.

### 10B.8.2. Required tests

After 2.8.0, verify:

```text
create user with Premium Smart RU:
  externalSquadUuid = Smart RU external squad
  activeInternalSquads = Smart RU internal squads
  hwidDeviceLimit = 5
  trafficLimitBytes omitted for unlimited
  expireAt sentinel or omitted according to lifetime mode

create lifetime user:
  CyberVPN entitlement expires_at = null
  upstream Remnawave behavior follows REMNAWAVE_LIFETIME_EXPIRY_MODE:
    sentinel -> 2099-12-31T23:59:59Z
    none -> omit expireAt if Remnawave 2.8.0 supports it

update user:
  patch does not wipe squads
  patch does not wipe subscription template
  patch does not set trafficLimitBytes=null

get by telegram_id:
  still returns one user or safe none
```

### 10B.8.3. Lifetime expiry mode decision

Production smoke must decide whether Remnawave 2.8.0 supports missing `expireAt` for users.

If yes:

```env
REMNAWAVE_LIFETIME_EXPIRY_MODE=none
```

If no:

```env
REMNAWAVE_LIFETIME_EXPIRY_MODE=sentinel
REMNAWAVE_LIFETIME_EXPIRE_AT=2099-12-31T23:59:59Z
```

Acceptance: no production change to lifetime mode until production smoke confirms behavior.

---

## 10B.9. HWID behavior update

### 10B.9.1. Release changes

Remnawave 2.8.0 includes fixes around HWID limit handling, race condition on HWID devices check, missing request IP in HWID upsert, and header rename from `x-hwid-limit` to `x-hwid-active`.

### 10B.9.2. CyberVPN impact

Search all code for:

```text
x-hwid-limit
x-hwid-active
hwid
hwidDeviceLimit
```

If CyberVPN reads response headers from subscription/config endpoints, update to new header:

```text
x-hwid-active
```

Maintain compatibility:

```python
active_hwid = response.headers.get("x-hwid-active") or response.headers.get("x-hwid-limit")
```

### 10B.9.3. Tests

- user with 5 devices gets correct `hwidDeviceLimit=5`;
- 6th device behavior is blocked/limited as expected;
- subscription/config response exposes current active HWID header;
- request IP is present where Remnawave expects it;
- Telegram Mini App / Bot connection flow is not blocked incorrectly by HWID.

---

## 10B.10. XHTTP и новые transport/protocol features Remnawave 2.8.0

### 10B.10.1. XHTTP — обязательный рабочий режим на выбранных нодах

Remnawave 2.8.0 добавляет поддержку `xhttp` transport в Mihomo generator, новые `xhttp-opts`, поддержку `session-table` и `session-length`, а также исправления обработки XHTTP settings и casing `uplinkHTTPMethod`.

В CyberVPN XHTTP должен быть введён как **production-supported transport для выбранных нод**, но через controlled rollout.

### 10B.10.2. Feature flags

Добавить backend/runtime flags:

```env
REMNAWAVE_FEATURE_XHTTP_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_MIHOMO_ENABLED=true
REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=canary
REMNAWAVE_FEATURE_XHTTP_ALLOWED_PLAN_CODES=premium_smart_ru
REMNAWAVE_FEATURE_XHTTP_ALLOWED_USER_SEGMENTS=internal,beta,premium_smart_ru_canary
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=false
```

Значения по этапам:

```text
Phase 1:
  REMNAWAVE_FEATURE_XHTTP_ENABLED=true
  REMNAWAVE_FEATURE_XHTTP_ROLLOUT_MODE=internal

Phase 2:
  rollout_mode=canary

Phase 3:
  rollout_mode=premium_smart_ru

Phase 4:
  rollout_mode=stable
```

Rollback:

```env
REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true
```

При rollback XHTTP должен исчезнуть из новых subscription configs, но существующие stable transports должны остаться.

### 10B.10.3. Node/host tagging

В Remnawave 2.8.0 есть multiple host tags. Для XHTTP ввести tag policy:

```text
node tags:
  xhttp
  xhttp_canary
  premium_smart_ru
  stable
  no_torrent
  ru
  eu

host tags:
  xhttp
  mihomo
  premium_smart_ru
  canary
```

Минимум:

```text
1 dedicated XHTTP node
1 dedicated XHTTP host
1 XHTTP-compatible inbound/transport
1 response rule, которая включает XHTTP только для canary/allowed cohorts
```

### 10B.10.4. Response rules

Использовать новые Remnawave 2.8.0 host tags и `excludeHostsByTags`.

Пример policy:

```json
{
  "includeHostsByTags": ["xhttp", "premium_smart_ru"],
  "excludeHostsByTags": ["maintenance", "legacy", "broken_xhttp"],
  "rolloutMode": "canary"
}
```

Если Remnawave поддерживает только exclude rule, CyberVPN должен добиться нужного результата через:

```text
- отдельные hosts/templates для XHTTP;
- host tags;
- rollout cohorts;
- response rules;
- fallback stable hosts.
```

### 10B.10.5. Subscription template / client support

Проверить и при необходимости обновить templates:

```text
CyberVPN Premium Smart RU
Mihomo RU bundle
JSON fallback template
Xray JSON template
```

XHTTP должен корректно попадать в:

```text
Mihomo config
JSON subscription fallback
QR/subscription URL flow, если применимо
```

Не включать XHTTP в клиенты, где он не поддерживается или ломает импорт.

### 10B.10.6. XHTTP client QA matrix

Обязательная проверка:

```text
Mihomo Desktop
Mihomo Party
Clash Verge / compatible fork, если используется
Android client with Mihomo core
iOS client with Mihomo-compatible import, если используется
Windows client import
macOS client import
Linux client import
```

Для каждого:

```text
- subscription URL импортируется;
- XHTTP proxy присутствует;
- stable fallback proxy присутствует;
- подключение работает;
- DNS работает;
- скорость/latency приемлемые;
- при отключении XHTTP ноды fallback работает.
```

### 10B.10.7. XHTTP node smoke

После production update:

```bash
# проверить hosts/inbounds через Remnawave API
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/hosts | jq '.'

curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/inbounds | jq '.'
```

Проверить, что есть XHTTP host/inbound:

```text
transport/protocol contains xhttp
host tags contains xhttp
not disabled
assigned to intended node
```

Создать test user:

```text
plan=premium_smart_ru
segment=xhttp_canary
```

Проверить generated subscription:

```text
contains xhttp outbound/proxy
contains stable fallback outbound/proxy
does not include maintenance/broken hosts
```

### 10B.10.8. XHTTP observability

Добавить метрики/логи:

```text
cybervpn_remnawave_xhttp_users_total
cybervpn_remnawave_xhttp_subscription_generated_total
cybervpn_remnawave_xhttp_subscription_failed_total
cybervpn_remnawave_xhttp_canary_enabled_total
cybervpn_remnawave_xhttp_rollback_total
```

Если Remnawave metrics содержит per-node/per-protocol counters, отобразить XHTTP separately:

```text
xhttp active users
xhttp traffic
xhttp errors
xhttp node availability
```

Если upstream per-protocol metrics нет, CyberVPN должен логировать хотя бы выдачу XHTTP configs и node/host tags.

### 10B.10.9. Hysteria2 / ECH / tun / v2plus

Эти возможности остаются в scope исследования и contract compatibility, но не должны блокировать XHTTP rollout.

Flags:

```env
REMNAWAVE_FEATURE_HYSTERIA2_ENABLED=false
REMNAWAVE_FEATURE_ECH_ENABLED=false
REMNAWAVE_FEATURE_TUN_ENABLED=false
REMNAWAVE_FEATURE_V2PLUS_ENABLED=false
```

Их можно включать только после отдельного QA.

### 10B.10.10. Acceptance criteria для XHTTP

- [ ] Remnawave обновлён до 2.8.0.
- [ ] Есть минимум одна XHTTP-capable нода.
- [ ] Есть XHTTP host/inbound/template.
- [ ] XHTTP host имеет tags.
- [ ] Response rules не отдают XHTTP всем пользователям без rollout.
- [ ] Premium Smart RU canary user получает XHTTP config.
- [ ] Stable fallback transport остаётся в config.
- [ ] Mihomo import работает.
- [ ] Android/iOS/Desktop QA выполнен или несовместимые клиенты исключены.
- [ ] XHTTP можно выключить feature flag без отката Remnawave.
- [ ] XHTTP metrics/logs видны в monitoring.

## 10B.11. Host tags and response rules

### 10B.11.1. Multiple host tags

Release 2.8.0 replaces single host tag with multiple tags.

Update contracts and admin tooling to support:

```json
{
  "tags": ["premium", "smart_ru", "no_torrent", "mihomo"]
}
```

Backward compatibility:

```python
tags = response.tags or ([response.tag] if response.tag else [])
```

### 10B.11.2. excludeHostsByTags

Use new response rules capability:

```text
excludeHostsByTags
```

For Premium Smart RU:

```json
{
  "excludeHostsByTags": ["torrent_allowed_only", "legacy", "maintenance"]
}
```

Use cases:

```text
- exclude maintenance hosts from subscription generation;
- exclude incompatible hosts from Mini App recommended config;
- implement smart routing host segmentation;
- exclude high-risk or experimental hosts from stable users.
```

### 10B.11.3. Acceptance

- existing host selection still works if only old tag exists;
- multiple tags are displayed in admin diagnostics;
- response rules do not leak raw code/user identifiers;
- Premium Smart RU receives only intended hosts.

---

## 10B.12. Node observability, metrics, dashboards и alerts

### 10B.12.1. Новые метрики Remnawave 2.8.0 обязательны к использованию

Remnawave 2.8.0 добавляет Node CPU load average в Prometheus metrics для 1, 5 и 15 минут. Эти метрики должны быть заведены в production monitoring сразу после обновления.

Требуется обнаружить фактические metric names через:

```bash
curl -fsS http://127.0.0.1:3001/metrics | grep -Ei 'node|cpu|load|traffic|online|xray|remnawave'
```

Не хардкодить названия до discovery. В ТЗ использовать logical names:

```text
node_cpu_load_1m
node_cpu_load_5m
node_cpu_load_15m
node_online_users
node_traffic_rx_bytes
node_traffic_tx_bytes
node_status
node_xray_version
node_remnawave_node_version
node_consumption_multiplier
```

### 10B.12.2. Prometheus scrape

Проверить scrape Remnawave metrics endpoint:

```text
http://remnawave:3001/metrics
```

или через локальный bind:

```text
http://127.0.0.1:3001/metrics
```

Если metrics защищены basic auth:

```yaml
basic_auth:
  username: <METRICS_USER>
  password: <METRICS_PASS>
```

Добавить/обновить Prometheus job:

```yaml
- job_name: remnawave
  scrape_interval: 15s
  scrape_timeout: 10s
  static_configs:
    - targets:
        - remnawave:3001
```

### 10B.12.3. Grafana dashboards

Создать dashboard:

```text
CyberVPN / Remnawave Nodes
```

Panels:

```text
1. Node CPU Load 1m by node
2. Node CPU Load 5m by node
3. Node CPU Load 15m by node
4. Node online/offline status
5. Node online users
6. Node traffic RX/TX rate
7. Node total traffic
8. Node Xray version
9. Node Remnawave Node version
10. Node errors / failed queries
11. Node consumption multiplier
12. XHTTP-capable nodes status
13. XHTTP canary users count
14. Premium Smart RU users per node
```

Dashboard variables:

```text
environment
node_name
node_uuid
country
tag
transport
plan_code
```

### 10B.12.4. Alerts

Добавить alerts:

#### High node CPU load

```text
Warning:
  node_cpu_load_5m > 0.80 * cpu_cores for 10m

Critical:
  node_cpu_load_15m > 1.00 * cpu_cores for 15m
```

Если cpu_cores недоступен в metrics, использовать абсолютный threshold per node config.

#### Node down

```text
node_status == 0 for 2m
```

#### Node metrics missing

```text
absent(node_cpu_load_1m{job="remnawave"}) for 5m
```

#### XHTTP canary errors

```text
xhttp subscription generation failures > 5 in 10m
```

#### Premium Smart RU node imbalance

```text
one node carries > 60% of Premium Smart RU online users for 15m
```

### 10B.12.5. Query stats for multiple nodes

Remnawave 2.8.0 adds query stats for multiple nodes. CyberVPN monitoring/scheduler should prefer batch stats when available.

Add gateway method:

```python
async def get_nodes_stats_batch(node_uuids: list[str]) -> dict[str, Any]:
    ...
```

Fallback:

```python
for node_uuid in node_uuids:
    await get_node_stats(node_uuid)
```

Acceptance:

```text
- batch endpoint used if available;
- fallback works if endpoint returns 404/501;
- scheduler does not generate N+1 overload for many nodes;
- metrics are tagged by node_uuid/node_name.
```

### 10B.12.6. Node tags and metrics correlation

Host/node tags from Remnawave 2.8.0 must be propagated to monitoring labels where possible:

```text
xhttp
premium_smart_ru
canary
stable
maintenance
country
provider
```

If Prometheus labels cannot be extended directly, build CyberVPN-side metadata map:

```text
node_uuid -> tags
node_uuid -> country
node_uuid -> provider
node_uuid -> xhttp_enabled
```

Use it in dashboards/alerts.

### 10B.12.7. nodeConsumptionMultiplier and custom billing node

Remnawave 2.8.0 introduces `nodeConsumptionMultiplier` and custom billing node support.

For this release:

```text
- display nodeConsumptionMultiplier in diagnostics/dashboard;
- do not change billing/traffic accounting logic yet;
- do not charge users differently based on multiplier;
- create separate accounting ТЗ if monetization depends on it.
```

### 10B.12.8. Backend diagnostics endpoint

Add internal/admin endpoint:

```text
GET /api/v1/admin/remnawave/nodes/diagnostics
```

Response:

```json
{
  "nodes": [
    {
      "uuid": "...",
      "name": "...",
      "status": "connected",
      "cpu_load_1m": 0.42,
      "cpu_load_5m": 0.38,
      "cpu_load_15m": 0.31,
      "online_users": 124,
      "xray_version": "...",
      "node_version": "...",
      "tags": ["xhttp", "premium_smart_ru"],
      "xhttp_enabled": true,
      "consumption_multiplier": 1.0
    }
  ],
  "metrics_source": "prometheus|remnawave_api|mixed",
  "updated_at": "..."
}
```

Protect with admin permission.

### 10B.12.9. Acceptance criteria для node metrics

- [ ] Remnawave `/metrics` доступен production Prometheus.
- [ ] Node CPU load 1m/5m/15m видны в Grafana.
- [ ] Есть alerts по CPU load.
- [ ] Есть alert на отсутствие node metrics.
- [ ] Есть dashboard по online users и traffic.
- [ ] XHTTP-capable nodes видны отдельным фильтром.
- [ ] Query stats for multiple nodes используется или documented fallback включён.
- [ ] Metrics smoke включён в deploy evidence.
- [ ] После обновления 2.8.0 нет роста CyberVPN 502 из-за Remnawave validation.

## 10B.13. Cursor-based all-users sync

Release 2.8.0 adds cursor-based pagination endpoint for fetching all users.

### 10B.13.1. Requirement

Add new RemnawaveGateway method:

```python
async def get_all_cursor(self, cursor: str | None = None, limit: int = 1000) -> RemnawaveCursorPage[User]:
    ...
```

Fallback to current offset method if endpoint unavailable.

### 10B.13.2. Use cases

```text
- user reconciliation job;
- migration verification;
- entitlement vs upstream audit;
- abuse scan;
- Remnawave drift report.
```

### 10B.13.3. Acceptance

- sync 10k users without offset drift;
- no duplicate users;
- no missing users;
- safe resume from cursor;
- stores last cursor/checkpoint.

---

## 10B.14. Templates and unlimited traffic display

Release 2.8.0 includes template changes:

```text
base64 template transformation
DESCRIPTION template key
unlimited traffic limit in trafficLeft
```

### 10B.14.1. Requirement

Review CyberVPN subscription templates:

```text
CyberVPN Premium Smart RU
Mihomo RU bundle
default templates
JSON fallback templates
```

Add template compatibility test:

```text
user with trafficLimitBytes omitted -> subscription template displays Unlimited correctly
lifetime user -> no broken expires/traffic placeholders
DESCRIPTION key available
base64 transformation does not break QR / subscription URL
```

### 10B.14.2. Mini App impact

Mini App QR/config bootstrap must still work:

```text
iOS
Android
Windows
macOS
Linux
Mihomo
v2rayN / v2rayNG
sing-box where applicable
```

---

## 10B.15. Webhook and CSP fixes

Release 2.8.0 mentions webhook schema fixes and CSP/connect-src changes.

### 10B.15.1. Webhook

Verify Remnawave webhook payload schema against CyberVPN:

```text
backend/src/presentation/api/v1/remnawave_webhook routes
signature/timestamp checks
max body bytes
event types
unknown fields
```

Tests:

```text
valid webhook passes
missing schema does not crash
unknown event type is logged safely
oversized body rejected
bad signature rejected
```

### 10B.15.2. CSP / Mini App

Because Mini App still has WebView crash risk, test Remnawave panel CSP does not affect:

```text
cyber-vpn.net/ru-RU/miniapp
subdomain subscription links
subscription public base URL
Remnawave panel domain
```

If Remnawave subscription page uses CSP connect-src, ensure subscription URL and assets load correctly.

---

## 10B.16. Direct production rollout plan

### 10B.16.1. Общая стратегия

Отдельного staging-этапа нет. Обновление выполняется сразу на production, но в безопасном порядке:

```text
Phase 0: подготовка команд и переменных
Phase 1: production preflight read-only
Phase 2: backup и фиксация rollback state
Phase 3: короткий write-freeze provisioning операций
Phase 4: обновление Remnawave до 2.8.0
Phase 5: Remnawave health/API smoke
Phase 6: CyberVPN contract smoke
Phase 7: включение write-path обратно
Phase 8: E2E проверка пользователей и Telegram Mini App
Phase 9: Cloudflare/cache purge и RSC/CORS smoke
```

Ориентировочное production maintenance window:

```text
15–30 минут
```

Ожидаемое влияние:

```text
- существующие VPN-сессии, скорее всего, продолжат работать;
- новые выдачи конфигов / создание пользователей / invite activation могут быть временно заморожены;
- Telegram Bot / Mini App могут быть ограничены на время write-freeze только в части активации новых доступов.
```

---

### 10B.16.2. Phase 0 — подготовка перед окном

На production заранее подготовить:

```bash
export RELEASE_TS="$(date -u +%Y%m%dT%H%M%SZ)"
export REMNAWAVE_OLD_IMAGE="$(docker inspect remnawave --format '{{.Config.Image}}' || true)"
export REMNAWAVE_OLD_DIGEST="$(docker inspect remnawave --format '{{.Image}}' || true)"
export REMNAWAVE_NEW_IMAGE="remnawave/backend:2.8.0"
```

Зафиксировать:

```bash
echo "$REMNAWAVE_OLD_IMAGE" > "/tmp/remnawave-old-image-$RELEASE_TS.txt"
echo "$REMNAWAVE_OLD_DIGEST" > "/tmp/remnawave-old-digest-$RELEASE_TS.txt"
```

Проверить, что production реально использует Remnawave 2.7.4:

```bash
docker inspect remnawave --format '{{.Config.Image}} {{.Image}}'
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml ps remnawave
```

---

### 10B.16.3. Phase 1 — production preflight read-only

Проверить Remnawave до обновления:

```bash
curl -fsS http://127.0.0.1:3005/api/system/health || curl -fsS http://127.0.0.1:3005/health
curl -fsS http://127.0.0.1:3001/health
docker logs --tail=200 remnawave > "/tmp/remnawave-preupdate-$RELEASE_TS.log"
```

Проверить CyberVPN backend:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://api.cyber-vpn.net/api/v1/runtime/fingerprint
```

Проверить текущую RSC/CORS проблему, чтобы сравнить после обновления:

```bash
HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh || true
```

Проверить Mini App URL:

```bash
curl -I https://cyber-vpn.net/ru-RU/miniapp
curl -I https://cyber-vpn.net/ru-RU/miniapp/health || true
```

---

### 10B.16.4. Phase 2 — обязательный backup

Сделать backup Remnawave/Postgres перед изменением image:

```bash
mkdir -p "/var/backups/cybervpn/manual/$RELEASE_TS"

docker exec remnawave-db pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -Fc \
  -f "/tmp/remnawave-pre-2-8-0-$RELEASE_TS.dump"

docker cp "remnawave-db:/tmp/remnawave-pre-2-8-0-$RELEASE_TS.dump" \
  "/var/backups/cybervpn/manual/$RELEASE_TS/remnawave-pre-2-8-0.dump"
```

Если env переменные Postgres недоступны снаружи, взять их из `remnawave.env` или выполнить:

```bash
docker exec remnawave-db printenv | grep POSTGRES
```

Сохранить текущий compose/env:

```bash
cp /opt/cybervpn/control-plane/current/docker-compose.yml \
  "/var/backups/cybervpn/manual/$RELEASE_TS/docker-compose.pre-remnawave-2-8-0.yml"

cp /opt/cybervpn/control-plane/current/remnawave.env \
  "/var/backups/cybervpn/manual/$RELEASE_TS/remnawave.pre-2-8-0.env"

cp /opt/cybervpn/control-plane/current/backend.env \
  "/var/backups/cybervpn/manual/$RELEASE_TS/backend.pre-remnawave-2-8-0.env"
```

Проверить, что backup реально создан и не пустой:

```bash
ls -lh "/var/backups/cybervpn/manual/$RELEASE_TS/remnawave-pre-2-8-0.dump"
```

---

### 10B.16.5. Phase 3 — короткий write-freeze

Перед обновлением временно заморозить операции, которые создают или меняют Remnawave users:

```text
- trial provisioning;
- paid provisioning;
- invite/lifetime provisioning;
- multi-use invite activation provisioning;
- gift redemption provisioning;
- worker jobs, которые пишут в Remnawave;
- abuse auto-disable jobs, если включены.
```

Рекомендуемый быстрый вариант:

```bash
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml stop cybervpn-worker cybervpn-scheduler
```

Backend можно оставить включённым, но если есть runtime feature flags — временно выставить:

```env
STAGE1_TRIAL_PROVISIONING_ENABLED=false
STAGE1_PAID_PROVISIONING_ENABLED=false
```

Если таких runtime flags нельзя быстро поменять без redeploy, достаточно остановить worker/scheduler и на время окна не запускать массовые активации.

---

### 10B.16.6. Phase 4 — обновление Remnawave image до 2.8.0

Обновить Ansible variable:

```yaml
control_plane_stack_remnawave_image: remnawave/backend:2.8.0
```

или через production override:

```bash
ansible-playbook ... \
  -e control_plane_stack_remnawave_image=remnawave/backend:2.8.0
```

Принудительно скачать image:

```bash
docker pull remnawave/backend:2.8.0
docker image inspect remnawave/backend:2.8.0 --format '{{index .RepoDigests 0}}' \
  > "/var/backups/cybervpn/manual/$RELEASE_TS/remnawave-2-8-0-digest.txt"
```

Перезапустить только Remnawave:

```bash
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml up -d remnawave
```

Проверить логи миграций:

```bash
docker logs -f --tail=200 remnawave
```

Критические ошибки:

```text
migration failed
database schema error
JWT/API token error
cannot connect postgres
cannot connect redis
startup crash loop
```

При таких ошибках сразу перейти к rollback.

---

### 10B.16.7. Phase 5 — Remnawave health/API smoke

После старта 2.8.0:

```bash
docker inspect remnawave --format '{{.Config.Image}} {{.Image}}'
curl -fsS http://127.0.0.1:3001/health
curl -fsS http://127.0.0.1:3005/api/system/health || curl -fsS http://127.0.0.1:3005/health
```

Проверить API через CyberVPN token:

```bash
curl -fsS \
  -H "Authorization: Bearer $REMNAWAVE_TOKEN" \
  http://127.0.0.1:3005/api/users?start=0\&size=1
```

Проверить основные сущности:

```bash
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" http://127.0.0.1:3005/api/nodes
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" http://127.0.0.1:3005/api/hosts
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" http://127.0.0.1:3005/api/inbounds
curl -fsS -H "Authorization: Bearer $REMNAWAVE_TOKEN" http://127.0.0.1:3005/api/internal-squads || true
```

---

### 10B.16.8. Phase 6 — CyberVPN Remnawave contract smoke на production

Проверить из backend container:

```bash
docker exec cybervpn-backend python - <<'PY'
import asyncio
from src.infrastructure.remnawave.client import remnawave_client

async def main():
    print("health", await remnawave_client.health_check())
    print("users", type(await remnawave_client.get("/api/users", params={"start": 0, "size": 1})))

asyncio.run(main())
PY
```

Проверить validated contracts:

```bash
docker exec cybervpn-backend pytest tests/integration/remnawave -q || true
```

Если тесты не включены в production image, выполнить smoke-скрипт через endpoint backend:

```bash
curl -fsS https://api.cyber-vpn.net/api/v1/runtime/fingerprint
curl -fsS https://api.cyber-vpn.net/api/v1/client/capabilities
```

---

### 10B.16.9. Phase 7 — включить worker/scheduler обратно

Если Remnawave API smoke зелёный:

```bash
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml up -d cybervpn-worker cybervpn-scheduler
```

Проверить:

```bash
docker logs --tail=100 cybervpn-worker
docker logs --tail=100 cybervpn-scheduler
```

---

### 10B.16.10. Phase 8 — production E2E smoke

#### Premium Smart RU / lifetime invite / multi-use invite

Проверить тестовым пользователем:

```text
1. Активировать test multi-use root invite.
2. Убедиться, что пользователь получил Premium Smart RU lifetime.
3. Убедиться, что device_limit=5.
4. Убедиться, что trafficLimitBytes отсутствует или отображается как Unlimited.
5. Убедиться, что создано 12 child invite-codes.
6. Убедиться, что child invite-codes single_use.
7. Открыть connection bootstrap и получить subscription_url/QR.
```

#### Remnawave user

Через Remnawave API проверить созданного пользователя:

```text
externalSquadUuid = Smart RU external squad
activeInternalSquads содержит Smart RU internal squad
hwidDeviceLimit = 5
expireAt соответствует lifetime mode
trafficLimitBytes отсутствует для unlimited
subscriptionUrl существует
```

#### Telegram Bot

```text
/start
/code <test_multi_use_invite>
connection bootstrap
```

#### Telegram Mini App

```text
/start -> открыть Mini App
/ru-RU/miniapp/health
/ru-RU/miniapp/diagnostics
onboarding code apply
connection QR
```

---

### 10B.16.11. Phase 9 — Cloudflare purge и RSC/CORS smoke

Обязательно выполнить purge:

```text
cyber-vpn.net/*
my.cyber-vpn.net/*
api.cyber-vpn.net/*
cyber-vpn.net/_next/static/*
```

Проверить RSC cabinet routes, потому текущий production лог показывает redirect:

```text
my.cyber-vpn.net/en-EN/rewards/*?_rsc=...
→ cyber-vpn.net/en-EN
```

Команды:

```bash
HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh

curl -I 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component' \
  -H 'Next-Router-State-Tree: []' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Dest: empty'

curl -I 'https://my.cyber-vpn.net/en-EN/messages?_rsc=probe' \
  -H 'RSC: 1' \
  -H 'Accept: text/x-component'
```

Fail condition:

```text
HTTP 30x
Location: https://cyber-vpn.net/...
```

Accept:

```text
200 / 204 / 404
```

Проверить Mini App routes:

```bash
curl -I https://cyber-vpn.net/ru-RU/miniapp
curl -I https://cyber-vpn.net/ru-RU/miniapp/health
curl -I https://cyber-vpn.net/ru-RU/miniapp/diagnostics
```

---

### 10B.16.12. Решение после production smoke

Если все проверки зелёные:

```text
- оставить Remnawave 2.8.0;
- зафиксировать digest;
- сохранить deploy evidence;
- через 1 час проверить logs/metrics;
- через 24 часа проверить Remnawave API errors, CyberVPN 502, Mini App errors, invite activation errors.
```

Если есть красные проверки:

```text
- не ждать;
- выполнить rollback;
- приложить конкретный failure log;
- не продолжать feature enablement xhttp/Hysteria2/ECH.
```

---

## 10B.17. Direct production rollback

### 10B.17.1. Быстрый app rollback

Если Remnawave 2.8.0 не стартует, но DB совместима с 2.7.4:

```bash
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml stop remnawave

# вернуть старый image в compose/env/ansible override
export CONTROL_PLANE_STACK_REMNAWAVE_IMAGE="$REMNAWAVE_OLD_IMAGE"

docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml up -d remnawave
```

Проверить:

```bash
docker logs --tail=200 remnawave
curl -fsS http://127.0.0.1:3001/health
curl -fsS http://127.0.0.1:3005/api/system/health || curl -fsS http://127.0.0.1:3005/health
```

### 10B.17.2. Full restore rollback

Если после 2.8.0 Remnawave применил несовместимые DB migrations:

```bash
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml stop remnawave cybervpn-worker cybervpn-scheduler cybervpn-backend

# restore dump
docker cp "/var/backups/cybervpn/manual/$RELEASE_TS/remnawave-pre-2-8-0.dump" \
  "remnawave-db:/tmp/remnawave-restore.dump"

docker exec remnawave-db pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  "/tmp/remnawave-restore.dump"

# вернуть старый image
docker compose -f /opt/cybervpn/control-plane/current/docker-compose.yml up -d remnawave cybervpn-backend cybervpn-worker cybervpn-scheduler
```

После restore:

```bash
curl -fsS http://127.0.0.1:3001/health
curl -fsS http://127.0.0.1:8000/health
```

### 10B.17.3. Rollback decision rule

Rollback выполнять сразу, если:

```text
- Remnawave не стартует дольше 5 минут;
- healthcheck не проходит;
- CyberVPN не может создать/прочитать пользователя Remnawave;
- subscription URL/QR не генерируется;
- Premium Smart RU provisioning ломается;
- Remnawave API возвращает массовые 5xx;
- migration error в логах;
- Mini App/Bot activation массово падает из-за Remnawave.
```

Не откатывать только из-за неактивированных experimental features:

```text
xhttp
Hysteria2
ECH
tun
v2plus
```

если базовый provisioning работает.

## 10B.18. CyberVPN code changes

### 10B.18.1. Required

- Update Ansible default image to `2.8.0`.
- Add Remnawave 2.8.0 contract fixtures.
- Update `contracts.py` for new fields.
- Add compatibility for host `tags`.
- Add compatibility for `pinnedPeerCertSha256` replacing `allowInsecure`.
- Add compatibility for `verifyPeerCertByName`.
- Add compatibility for `mihomoIpVersion`.
- Add compatibility for `proxyUrl`.
- Add compatibility for node `note`.
- Add compatibility for node consumption multiplier.
- Add cursor-based users sync method with fallback.
- Add metrics scraping tests for new load average metrics.
- Add token expiration readiness warning.
- Add feature flags for xhttp/hysteria2/ECH/tun.

### 10B.18.2. Optional / P2

- Admin UI for node tags and nodeConsumptionMultiplier.
- Response rule editor for `excludeHostsByTags`.
- Template editor support for DESCRIPTION/base64 transformations.
- Smart RU experimental connection modes.
- Traffic cost analytics using custom billing node.

---

## 10B.19. Tests

### 10B.19.1. Backend contract tests

```bash
cd backend
pytest tests/integration/remnawave/test_remnawave_2_8_contracts.py
pytest tests/integration/remnawave/test_remnawave_user_provisioning_2_8.py
pytest tests/integration/remnawave/test_remnawave_subscription_templates_2_8.py
pytest tests/integration/remnawave/test_remnawave_hwid_2_8.py
pytest tests/integration/remnawave/test_remnawave_webhooks_2_8.py
```

### 10B.19.2. Existing CyberVPN regression tests

```bash
pytest tests/integration/invites/test_multi_use_redemption.py
pytest tests/integration/invites/test_multi_use_child_invites.py
pytest tests/integration/customer_onboarding
pytest tests/integration/customer_subscriptions
pytest tests/integration/remnawave
```

### 10B.19.3. Manual client tests

```text
iOS import subscription
Android import subscription
Windows v2rayN import
macOS client import
Linux client import
Mihomo import
Mini App QR scan
```

### 10B.19.4. Monitoring tests

```text
Prometheus scrapes Remnawave metrics
Node CPU load panels show data
Backend Remnawave API latency/error metrics visible
No increase in Remnawave 4xx/5xx
No increase in CyberVPN 502 validation errors
```

---

## 10B.20. Acceptance criteria

Task is accepted only if:

- [ ] Remnawave image is pinned to `2.8.0` or digest.
- [ ] Production backup and restore rehearsal are documented.
- [ ] Direct production upgrade from 2.7.4 to 2.8.0 succeeds.
- [ ] CyberVPN backend contract tests pass against 2.8.0.
- [ ] Premium Smart RU provisioning works.
- [ ] Lifetime invite provisioning works.
- [ ] Multi-use invite provisioning works.
- [ ] Telegram Bot `/start` still works.
- [ ] Telegram Mini App opens without WebView crash.
- [ ] Subscription URLs work for old and new users.
- [ ] QR connection bootstrap works.
- [ ] Remnawave webhooks validate.
- [ ] API token scopes are documented and rotated safely.
- [ ] No raw Remnawave token is logged.
- [ ] HWID 5-device behavior works.
- [ ] Unlimited traffic display works.
- [ ] RSC/CORS smoke still passes for cabinet routes.
- [ ] Rollback commands are prepared, backup exists, and restore procedure is documented.
- [ ] Node CPU load metrics 1m/5m/15m заведены в Grafana.
- [ ] Alerts по node CPU load, node down и missing metrics работают.
- [ ] XHTTP включён минимум на одной production/canary ноде.
- [ ] XHTTP host/inbound/template настроены и помечены tags.
- [ ] Premium Smart RU canary user получает XHTTP config и stable fallback.
- [ ] XHTTP можно отключить feature flag без отката Remnawave.
- [ ] New 2.8.0 features are behind feature flags unless explicitly approved; XHTTP is explicitly approved for controlled node rollout.

---

## 10B.21. Sources

Primary source:

```text
https://github.com/remnawave/backend/releases/tag/2.8.0
```

Repository references:

```text
infra/ansible/roles/control_plane_stack/defaults/main.yml
backend/src/infrastructure/remnawave/client.py
backend/src/infrastructure/remnawave/user_gateway.py
backend/src/infrastructure/remnawave/contracts.py
infra/ansible/inventories/production/group_vars/control_plane_production/main.yml
```

## 11. Observability

Add metrics:

```text
invite_multi_use_redeemed_total
invite_multi_use_blocked_already_user_total
invite_multi_use_exhausted_total
invite_multi_use_concurrency_conflict_total
invite_multi_use_child_batch_issued_total
invite_multi_use_reversal_total
invite_multi_use_device_context_missing_total
invite_customer_sort_order_served_total
```

Add structured logs:

```python
logger.info(
    "invite_multi_use_redeemed",
    extra={
        "invite_code_id": str(invite.id),
        "code_prefix": invite.code_prefix,
        "campaign_id": str(invite.campaign_id) if invite.campaign_id else None,
        "redeemer_user_id": str(user_id),
        "redemption_sequence": invite_redemption.redemption_sequence,
        "active_redemptions_count": invite.active_redemptions_count,
        "max_redemptions": invite.max_redemptions,
    },
)
```

Do not log raw invite code.

---

## 12. Acceptance criteria

### 12.1. Multi-use backend

- [ ] Multi-use root code can be redeemed by multiple different users.
- [ ] Same user second redemption is blocked.
- [ ] `max_redemptions` is enforced.
- [ ] Parallel redemption cannot exceed cap.
- [ ] Each successful redemption creates one `invite_redemptions` row.
- [ ] Each successful redemption creates one entitlement grant.
- [ ] Each successful redemption issues configured child invite count.
- [ ] Child invite usage mode follows campaign policy.
- [ ] Tree shows multiple users under one root multi-use code.

### 12.2. Preview UX

- [ ] First-time user preview returns accepted.
- [ ] Already redeemed user preview returns rejected with `already_redeemed_by_user`.
- [ ] Exhausted multi-use code preview returns exhausted.
- [ ] User B can still preview accepted after User A redeemed.

### 12.3. Telegram/Mini App

- [ ] Telegram Bot `/code` works for multi-use code without browser cookies.
- [ ] Telegram Bot repeated `/code` by same user returns already redeemed.
- [ ] Mini App apply works with stable device context.
- [ ] Mini App repeated apply returns already redeemed.
- [ ] Missing device context does not affect trusted Telegram Bot server-to-server path.

### 12.4. Client sorting

- [ ] Web customer invite list shows active/unused codes first.
- [ ] Used codes are below active codes.
- [ ] Expired/revoked codes are below used codes.
- [ ] Mini App invite list uses the same sorting.
- [ ] Telegram Bot invite list uses the same sorting.
- [ ] Backend returns `status_sort_order`.
- [ ] Frontend fallback helper works if backend field is missing.

### 12.5. Admin

- [ ] Admin can select root `multi_use`.
- [ ] Admin can select child `single_use`.
- [ ] Admin sees root/child max redemptions.
- [ ] Admin sees estimated fan-out and recommended `global_issue_cap`.
- [ ] Admin can filter inventory by usage mode.
- [ ] Admin can inspect redemption list for a multi-use code.

### 12.6. Production routing

- [ ] `/rewards/invites` opens in cabinet without CORS errors.
- [ ] `/messages` opens in cabinet without CORS errors.
- [ ] RSC smoke passes externally.
- [ ] Runtime fingerprints match external frontend/backend.
- [ ] Cloudflare purge is documented in deploy evidence.

---

## 13. Required commands before release

Backend:

```bash
cd backend
pytest tests/integration/invites/test_multi_use_redemption.py
pytest tests/integration/invites/test_multi_use_concurrency.py
pytest tests/integration/invites/test_multi_use_child_invites.py
pytest tests/integration/invites/test_multi_use_preview.py
pytest tests/integration/invites/test_multi_use_reversal.py
pytest tests/security/test_stage1_registration_kill_switch.py
```

Frontend:

```bash
cd frontend
npm test -- sort-invite-codes
npm test -- customer-growth
npm test -- proxy
```

Admin:

```bash
cd admin
npm test -- invite-codes-console
```

Telegram Bot:

```bash
cd services/telegram-bot
pytest tests/unit/test_api_client.py
pytest tests/unit/test_connection_flow.py
pytest tests/integration/test_connection_flow.py
```

Smoke:

```bash
HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh
```

---

## 14. Rollback

If multi-use redemption causes production incidents:

1. Pause affected invite campaign.
2. Revoke active root multi-use codes.
3. Keep already granted entitlements active unless abuse confirmed.
4. Disable `multi_use` creation in admin UI with feature flag:
   ```text
   GROWTH_INVITE_MULTI_USE_ENABLED=false
   ```
5. Keep `single_use` invite flow enabled.
6. Run audit report for:
   ```text
   invite_code_id
   redeemed_count
   active_redemptions_count
   child_issued_count
   suspicious device/IP clusters
   ```

If RSC/CORS issue persists:

1. Temporarily set customer site mode to `full_site`.
2. Purge Cloudflare cache.
3. Restart frontend and edge Caddy.
4. Run RSC smoke.
5. Re-enable `cabinet_only` only after smoke passes.

---

## 15. Out of scope

This ТЗ does not change:

- pricing catalog;
- Premium Smart RU plan definition;
- payment checkout;
- wallet;
- partner commissions;
- promo/gift code economics;
- ML anti-fraud models.

This ТЗ only hardens v7.5.1 multi-use invite code production readiness and the customer invite UX.
