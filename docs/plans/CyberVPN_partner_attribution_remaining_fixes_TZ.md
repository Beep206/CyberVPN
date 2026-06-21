# Техническое задание: завершение и hardening partner referral / attribution системы CyberVPN

**Проект:** `Beep206/CyberVPN`
**Базовая ветка:** `main`
**Проверенный commit:** `b77d52bccea545029390826321b7c1a056621517`
**Дата аудита и подготовки ТЗ:** 20 июня 2026 года
**Области:** `backend`, `frontend`, `partner`, `admin`, `services/task-worker`, PostgreSQL, Redis, OpenAPI
**Приоритет:** Critical / Revenue Integrity / Security
**Тип документа:** implementation-ready specification для устранения оставшихся недостатков
**Итоговая цель:** production-ready цепочка
`partner link → anonymous capture → auth → claim → commercial binding → order attribution → payment → earning → statement → payout/reversal`.

---

# 1. Назначение документа

Это ТЗ описывает **оставшиеся работы после уже выполненной реализации Partner Attribution v2**.

Нельзя использовать документ как повод переписать уже работающие части с нуля. Требуется:

1. сохранить реализованную архитектуру;
2. исправить выявленные дефекты безопасности, целостности и финансовой воспроизводимости;
3. завершить partner portal UI;
4. добавить недостающие DB invariants;
5. обеспечить durable processing;
6. доказать весь revenue path реальными integration/E2E-тестами.

---

# 2. Что уже реализовано и должно быть сохранено

На проверенном commit уже существуют:

- `partner_attribution_sessions`;
- public route:
  ```text
  https://cyber-vpn.net/p/{publicToken}
  ```
- backend API:
  ```text
  POST /api/v1/partner-attribution/capture
  POST /api/v1/partner-attribution/transfer/consume
  POST /api/v1/partner-attribution/claim
  ```
- customer frontend `PartnerAttributionProvider`;
- localStorage UX snapshot и HttpOnly cookie;
- automatic claim после восстановления customer session;
- partner code v2 fields:
  ```text
  code_normalized
  public_token_hash
  lifecycle_status
  owner_type
  lane_key
  attribution_model
  attribution_window_seconds
  policy_version_id
  commission_contract_id
  default_storefront_id
  allowed_channels
  allowed_storefront_ids
  allowed_geographies
  ```
- canonical workspace code API:
  ```text
  GET    /partner-workspaces/{workspace_id}/codes
  POST   /partner-workspaces/{workspace_id}/codes
  PATCH  /partner-workspaces/{workspace_id}/codes/{code_id}
  POST   /codes/{code_id}/activate
  POST   /codes/{code_id}/pause
  POST   /codes/{code_id}/revoke
  POST   /codes/{code_id}/archive
  POST   /codes/{code_id}/links
  POST   /codes/{code_id}/qr
  ```
- workspace commercial capabilities endpoint;
- workspace finance summary endpoint;
- touchpoint links с partner attribution session;
- claimed commercial binding;
- immutable `order_attribution_results`;
- canonical `earning_events`;
- source-event idempotency key;
- generated OpenAPI types;
- basic integration test capture → transfer → claim;
- refund/dispute settlement adjustments;
- observability foundations.

Все исправления ниже должны расширять эти компоненты, а не создавать параллельные таблицы и дублирующие endpoints.

---

# 3. Итоговый статус текущей реализации

Основная архитектура построена правильно, но система пока не соответствует критериям полной production-ready реализации.

Критические оставшиеся риски:

1. transfer token можно повторно использовать;
2. transfer token одновременно является cookie token;
3. public token строится детерминированно из UUID;
4. deep-link destination фактически теряется;
5. capture не имеет полноценного rate limiting и browser-level idempotency;
6. claim игнорирует storefront scope;
7. отсутствует DB constraint на единственную active commercial binding;
8. conflict attribution ошибочно завершается как `already_claimed`;
9. `attribution_model` хранится, но order resolver использует hardcoded precedence;
10. earning использует текущие tiers/config вместо immutable contract snapshot;
11. policy evaluation при ошибке работает fail-open;
12. partner portal backend API реализован, но Codes UI всё ещё read-only;
13. finance summary API не подключён к portal runtime;
14. portal продолжает скрывать часть ошибок как пустые списки;
15. отсутствует production-like E2E всей цепочки.

---

# 4. Definition of Done

Задача считается полностью завершённой только если одновременно выполняются все гарантии.

## 4.1. Attribution

- public token не раскрывает internal UUID;
- transfer token одноразовый и короткоживущий;
- transfer token не используется как долгоживущий cookie token;
- после consume повторное использование token невозможно;
- destination, locale, campaign и sub-id доходят до attribution session;
- query можно удалить после consume;
- reload и auth redirects не теряют attribution;
- claim работает при email/password, OTP, OAuth, magic link, passkey и 2FA;
- claim atomic и идемпотентен;
- storefront scope не теряется;
- conflict policy возвращает явный результат;
- self-attribution блокируется;
- eligibility policy применяется одинаково на capture, claim и order.

## 4.2. Commercial binding

- одновременно невозможны две active bindings одного scope;
- invariant обеспечен PostgreSQL partial unique indexes;
- race двух claims завершается одной binding;
- final binding immutable, кроме управляемого supersede/override workflow;
- каждое изменение имеет audit event и reason code.

## 4.3. Order attribution

- реальный `attribution_model` влияет на выбор winner;
- resolver использует capture/claim snapshot, а не mutable current code;
- order attribution result воспроизводим;
- повторный resolve возвращает тот же результат;
- social referral и partner attribution не создают double payout.

## 4.4. Finance

- beneficiary берётся из `order_attribution_result.partner_account_id`;
- commission, markup, currency и hold policy берутся из immutable snapshot;
- денежные вычисления выполняются через `Decimal`;
- earning создаётся ровно один раз;
- transient earning failure имеет durable retry;
- payout policy failure не работает fail-open;
- refund/dispute формирует idempotent adjustment/reversal;
- portal finance summary не смешивает currencies.

## 4.5. Partner portal

- partner может создать code, скопировать ссылку, создать deep link и QR;
- lifecycle actions реально доступны согласно backend capabilities;
- `403`, `404`, empty и network error визуально различаются;
- permission evaluation fail-closed;
- одна runtime graph и одна SSE connection;
- demo fixtures не подменяют production backend;
- finance берётся из canonical finance summary API;
- UI локализован.

## 4.6. Tests

- unit tests зелёные;
- real PostgreSQL concurrency tests зелёные;
- Redis/outbox retry tests зелёные;
- frontend provider tests зелёные;
- partner portal UI tests зелёные;
- полный E2E проходит;
- OpenAPI/generated artifacts синхронизированы;
- migration upgrade и downgrade проверены.

---

# 5. Реестр оставшихся дефектов

| ID | Критичность | Дефект |
|---|---|---|
| PAT-001 | Blocker | Transfer token replayable |
| PAT-002 | Blocker | Transfer token используется как cookie token |
| PAT-003 | High | Transfer token живёт весь attribution window |
| PAT-004 | High | Public token детерминирован из UUID |
| PAT-005 | Blocker | Deep-link destination и locale теряются |
| PAT-006 | High | Capture не имеет browser-level idempotency |
| PAT-007 | High | Capture не имеет полного rate limit |
| PAT-008 | High | Realm/host resolution доверяет неподтверждённым headers |
| PAT-009 | Medium | Campaign payload недостаточно ограничен |
| PAT-010 | High | Frontend transient retry может навсегда прекратиться |
| PAT-011 | High | Cookie fallback contract фактически не работает |
| BND-001 | Blocker | Storefront scope теряется при claim |
| BND-002 | Blocker | Нет partial unique active binding indexes |
| BND-003 | High | Existing conflicting owner возвращается как already_claimed |
| BND-004 | High | Conflict policy не формализована |
| BND-005 | High | Invalid owner_type silently превращается в affiliate |
| BND-006 | High | Claim не создаёт append-only claim touchpoint |
| BND-007 | High | Проверка self-attribution неполная |
| COD-001 | High | Code create idempotency хранится в `sub_id_schema` |
| COD-002 | High | Create code race не обрабатывает `IntegrityError` |
| COD-003 | Blocker | Sensitive commercial fields изменяются partner operator без approval |
| COD-004 | High | Lifecycle transition matrix отсутствует |
| COD-005 | High | Revoked/archived code можно реактивировать |
| COD-006 | High | Eligibility не проверяет active_from/channel/storefront/geo |
| COD-007 | Medium | Lifecycle reason хранится в `sub_id_schema` |
| COD-008 | High | QR fallback возвращает несканируемый SVG с HTTP 200 |
| COD-009 | Medium | `default_destination_url` имеет неверную семантику |
| ORD-001 | Blocker | `attribution_model` не используется resolver |
| ORD-002 | Blocker | Winner строится из mutable current code |
| ORD-003 | Blocker | Order policy snapshot неполный |
| ORD-004 | High | Passive click не прикрепляется к commerce context |
| ORD-005 | High | Quote/order не имеют server-side claim safety net |
| FIN-001 | Blocker | Commission берётся из current tier/config |
| FIN-002 | Blocker | Client count читается из legacy `partner_earnings` |
| FIN-003 | High | Monetary values преобразуются в float |
| FIN-004 | Blocker | Policy evaluation failure работает fail-open |
| FIN-005 | Blocker | Earning processing не основан на durable outbox consumer |
| FIN-006 | High | Legacy и canonical earning paths сосуществуют без строгого cutover |
| FIN-007 | High | Finance summary неполный и использует float |
| UI-001 | Blocker | Codes page не использует реализованные mutations |
| UI-002 | High | Capability endpoint не используется portal UI |
| UI-003 | High | `403/404` скрываются как empty |
| UI-004 | Medium | Safe GET queries имеют `retry: false` |
| UI-005 | High | Permission evaluation может fail-open |
| UI-006 | High | Runtime hook/SSE создаются повторно |
| UI-007 | High | Production local scenario fallback |
| UI-008 | High | Finance UI считает statements на клиенте |
| UI-009 | Low | Money format hardcoded `en-US` |
| UI-010 | Medium | `due_date` используется как updated time |
| HST-001 | High | Unknown partner host silently становится portal |
| LEG-001 | High | Legacy negative markup schema |
| LEG-002 | Medium | Legacy endpoints не имеют formal sunset |
| TST-001 | Blocker | Capture/claim test использует SQLite adapter |
| TST-002 | Blocker | Нет full revenue-path E2E |
| TST-003 | High | Нет provider/storage tests |
| TST-004 | High | Нет code CRUD/lifecycle UI tests |
| TST-005 | High | Нет earning reproducibility/concurrency tests |

---

# 6. Work Package A — безопасность public link и transfer

## PAT-001/PAT-002/PAT-003 — одноразовый transfer и отдельный cookie token

### Текущее поведение

В capture:

```text
token_hash = hash(transfer_token)
transfer_token_hash = hash(transfer_token)
```

После consume тот же raw token становится значением HttpOnly cookie.

Consume не удаляет `transfer_token_hash`, не фиксирует one-time consumption и может повторно вернуть тот же cookie token.

### Риск

Скопированный URL с `pat` можно использовать во втором browser до окончания attribution TTL. Это позволяет:

- украсть attribution session;
- закрепить attribution на другом account;
- повторно использовать browser history URL;
- использовать token после первого consume.

### Целевая модель

В `partner_attribution_sessions` разделить:

```text
session_token_hash
transfer_token_hash
transfer_expires_at
transfer_consumed_at
```

Алгоритм:

1. capture создаёт:
   - session;
   - одноразовый transfer token;
   - `transfer_token_hash`;
   - TTL transfer token 5–15 минут;
2. consume выполняет `SELECT ... FOR UPDATE`;
3. проверяет:
   ```text
   transfer_consumed_at IS NULL
   transfer_expires_at > now
   status in pending/transferred_allowed
   ```
4. генерирует **новый** cookie session token;
5. сохраняет только `session_token_hash`;
6. устанавливает:
   ```text
   transfer_consumed_at = now
   transfer_token_hash = NULL
   ```
7. response устанавливает cookie session token;
8. повторный consume возвращает:
   ```text
   409 PARTNER_TRANSFER_TOKEN_CONSUMED
   ```
   либо идемпотентный ответ только при наличии server-bound browser nonce.

### Cookie

```text
Name: cv_partner_attribution
HttpOnly: true
Secure: production
SameSite: Lax
Path: /
Max-Age: min(session.expires_at - now, configured maximum)
```

### Изменяемые файлы

```text
backend/src/infrastructure/database/models/partner_attribution_session_model.py
backend/src/infrastructure/database/repositories/partner_attribution_session_repo.py
backend/src/application/use_cases/partner_attribution/attribution.py
backend/src/presentation/api/v1/partner_attribution/routes.py
backend/alembic/versions/<new>_partner_transfer_hardening.py
frontend/src/features/partner-attribution/provider.tsx
```

### Tests

- первый consume успешен;
- второй consume возвращает consumed;
- expired transfer возвращает 410;
- session cookie token отличается от transfer token;
- DB не хранит raw token;
- concurrent consume: ровно один success;
- cookie max age не превышает session expiry.

---

## PAT-004 — случайный public slug

### Текущее поведение

Public token:

```text
px_{partner_code_uuid_without_hyphens}
```

### Требование

Public link identifier не должен раскрывать internal UUID.

Рекомендуемая модель:

```text
partner_codes.public_slug VARCHAR(32..64) UNIQUE NOT NULL
```

`public_slug` является публичным identifier, поэтому допустимо хранить его открыто. Secret hash для него не обязателен.

Генерация:

```python
secrets.token_urlsafe(16)
```

Пример:

```text
px_7PqgMj6WqYJ4aRmX
```

`session_token` и `transfer_token` остаются secret и хранятся только в hash.

### Backfill

1. для каждого существующего code сгенерировать random slug;
2. старые deterministic links поддерживать через legacy redirect table до sunset;
3. новый portal выдаёт только random slug;
4. migration не должна менять ссылки без compatibility period.

### Acceptance

- internal UUID невозможно получить из URL;
- slug collision обрабатывается retry;
- legacy link продолжает работать в переходный период;
- новый code получает random slug.

---

## PAT-005 — destination, locale и deep-link metadata

### Текущее поведение

Workspace API формирует:

```text
/p/{token}?to=/path&utm_...&sub_...
```

Но public route передаёт в capture только campaign keys. `to` не используется, а backend всегда формирует:

```text
https://my.cyber-vpn.net/ru-RU/register?pat=...
```

### Целевое решение

Рекомендуется создать persistent entity:

```text
partner_code_links
```

Поля:

```text
id
public_slug
partner_code_id
destination_key
destination_path
locale
campaign_params
sub_ids
status
created_by_admin_user_id
created_at
expires_at
```

Public route:

```text
/p/{link_slug}
```

lookup link определяет:

- partner code;
- locale;
- destination;
- campaign;
- sub IDs.

Нельзя доверять изменяемому `to` из query.

Если persistent links не создаются, query должен иметь HMAC signature и strict allowlist.

### Destination rules

Разрешённые destination keys:

```text
register
pricing
checkout
download
campaign_landing:<id>
storefront:<key>
```

Arbitrary external URL запрещён.

### Locale

1. request locale из созданного link;
2. затем Accept-Language;
3. затем default locale;
4. не использовать hardcoded `ru-RU`.

### Acceptance

- deep link `pricing` приводит на pricing;
- registration link приводит на register;
- locale `en-EN` не превращается в `ru-RU`;
- изменённый query не меняет destination без valid signature/link record;
- source campaign/sub IDs сохраняются в session и touchpoint.

---

## PAT-006/PAT-007 — capture idempotency и rate limits

### Требование

Public capture должен иметь:

```text
per IP
per public slug
per browser attribution key
```

Рекомендуемые лимиты:

```text
30 запросов / 10 минут / IP
100 запросов / 10 минут / slug
5 active sessions / browser attribution key
```

### Browser attribution key

Public route устанавливает first-party HttpOnly cookie:

```text
cv_partner_browser
```

В backend хранится его hash.

Policy:

- `first_eligible_touch` — повторный code не заменяет first touch;
- `last_eligible_touch` — session обновляется новым eligible touch;
- duplicate reload одного URL не создаёт новую session;
- crawler/bot traffic может быть marked non-human.

### Idempotency

Capture принимает:

```text
Idempotency-Key
```

и повторный request возвращает существующую session.

Не хранить idempotency key в `sub_id_schema`.

### Payload limits

```text
max campaign keys: 20
max sub-id keys: 10
max key length: 64
max value length: 200
max JSON payload: 8 KB
```

---

## PAT-008 — trusted realm/host boundary

### Текущее поведение

Realm resolver может принимать `X-Auth-Realm`, а source host может поступать из payload или `X-Forwarded-Host`.

### Требование

Для public capture:

```python
allow_header=False
```

Host должен определяться только из trusted reverse-proxy boundary.

### Реализация

- добавить trusted-proxy middleware;
- принимать `X-Forwarded-Host` только от trusted proxy IP/network;
- иначе использовать `Host`;
- host сверять с allowlist/DB storefront registry;
- client payload `source_host` удалить;
- в audit хранить:
  ```text
  resolved_source_host
  forwarded_host_raw_fingerprint
  host_resolution_source
  ```

### Acceptance

- внешний клиент не может выбрать realm через `X-Auth-Realm`;
- spoofed `X-Forwarded-Host` отклоняется;
- unknown host не создаёт attribution;
- source host нельзя подделать JSON body.

---

## PAT-009 — campaign validation

Разрешить только:

```text
utm_source
utm_medium
utm_campaign
utm_term
utm_content
gclid
fbclid
click_id
sub_id
sub_id_*
```

Дополнительно:

- sanitize Unicode/control characters;
- запретить nested dict/list;
- total size limit;
- не сохранять full URL с secret query;
- redact campaign values в logs.

---

# 7. Work Package B — frontend attribution state machine

## PAT-010 — корректный retry lifecycle

### Текущий дефект

`consumedLocationRef` и `claimAttemptRef` устанавливаются до успешного завершения. После исчерпания retries transient failure может больше не повториться.

### Требование

Реализовать явную state machine:

```text
idle
transfer_detected
consuming
captured
claim_wait_auth
claiming
claimed
terminal_error
retry_wait
```

При retryable error:

```text
attempt key освобождается
nextRetryAt сохраняется
online event запускает retry
visibilitychange может запускать retry
```

Retry policy:

```text
1s
3s
10s
30s
max 5 attempts за одну browser session
```

Retryable:

```text
network
408
425
429
500
502
503
504
PARTNER_ATTRIBUTION_USER_NOT_READY
```

Terminal:

```text
PARTNER_TRANSFER_TOKEN_INVALID
PARTNER_TRANSFER_TOKEN_EXPIRED
PARTNER_TRANSFER_TOKEN_CONSUMED
PARTNER_CODE_REVOKED
PARTNER_CODE_EXPIRED
PARTNER_SELF_ATTRIBUTION_BLOCKED
PARTNER_BINDING_CONFLICT
```

### Дополнительно

- использовать generated OpenAPI types;
- добавить `storage` event для cross-tab;
- сохранять server `captured_at`, а не browser now;
- не хранить raw transfer/session token в localStorage;
- очищать URL только после successful consume или terminal rejection.

---

## PAT-011 — fallback contract

Auth в проекте уже требует first-party HttpOnly cookies. Поэтому отдельный raw token fallback в JavaScript не нужен и создаёт лишнюю поверхность атаки.

### Требование

Удалить:

```text
fallback_token
```

из public client contract, если нет утверждённого secure recovery design.

LocalStorage хранит только UX snapshot:

```text
attribution_id
masked_code
captured_at
expires_at
```

Canonical claim выполняется по HttpOnly cookie.

Если продукт требует recovery при потерянной attribution cookie, использовать:

- server-side authenticated recovery по `attribution_id`;
- signed one-time proof;
- device/session binding;
- короткий TTL.

Не хранить долгоживущий secret в localStorage.

---

# 8. Work Package C — claim и commercial binding

## BND-001 — storefront scope

### Текущий дефект

Capture сохраняет `storefront_id`, но claim создаёт binding без передачи `storefront_id`. Получается global binding.

### Требование

Claim передаёт:

```python
storefront_id=attribution.storefront_id
```

Policy:

| Owner type | Binding scope |
|---|---|
| affiliate | global либо policy-defined |
| performance | order/campaign, обычно не persistent global |
| reseller | storefront/global persistent по contract |
| direct store | storefront only |

Нельзя использовать одну scope policy для всех lanes.

### Acceptance

- reseller storefront attribution не влияет на другой storefront;
- global affiliate attribution работает согласно policy;
- resolver выбирает scoped binding раньше global fallback;
- tests покрывают два storefront.

---

## BND-002 — DB invariants

Добавить PostgreSQL partial unique indexes.

### Global

```sql
CREATE UNIQUE INDEX uq_customer_binding_active_global
ON customer_commercial_bindings (user_id, auth_realm_id)
WHERE binding_status = 'active'
  AND storefront_id IS NULL
  AND binding_type IN (
    'partner_attribution',
    'reseller_binding',
    'contract_assignment',
    'manual_override'
  );
```

### Storefront

```sql
CREATE UNIQUE INDEX uq_customer_binding_active_storefront
ON customer_commercial_bindings (user_id, auth_realm_id, storefront_id)
WHERE binding_status = 'active'
  AND storefront_id IS NOT NULL;
```

Точный состав binding types должен быть утверждён policy owner.

### Transaction

Claim:

1. lock attribution session;
2. lock customer;
3. lock active bindings scope;
4. resolve policy;
5. create/supersede binding;
6. flush;
7. outbox;
8. commit route boundary.

### Tests

Два параллельных claims:

- одинаковый code;
- разные codes;
- разные storefront;
- global + storefront;
- одна transaction rollback.

---

## BND-003/BND-004 — conflict semantics

### Текущий дефект

Любая existing active owner binding приводит к:

```text
session.status = claimed
response.status = already_claimed
```

даже если existing owner — другой партнёр.

### Требование

Разделить результаты:

```text
already_claimed_same_owner
rejected_existing_owner
superseded_by_policy
manual_review_required
```

Session status:

```text
claimed
rejected_conflict
superseded
```

Нельзя помечать attribution `claimed`, если она не стала owner.

### Conflict matrix

| Existing | Incoming | Default |
|---|---|---|
| same partner/code | same | idempotent |
| same account/different code | account policy |
| affiliate | new affiliate | attribution model |
| reseller persistent | affiliate | reject |
| manual override | any | reject |
| contract assignment | any | reject |
| storefront binding A | storefront B | allowed, separate scope |
| social referral | partner | allowed relationship, no double cash payout |

---

## BND-005 — owner type fail-closed

### Текущий дефект

Функция возвращает `affiliate` для неизвестного `owner_type`, поэтому eligibility check фактически не обнаруживает invalid value.

### Требование

```python
def parse_owner_type(raw: str) -> CommercialOwnerType:
    try:
        return CommercialOwnerType(raw)
    except ValueError:
        raise PartnerAttributionError(
            code="PARTNER_OWNER_TYPE_INVALID",
            ...
        )
```

Никаких silent defaults в financial attribution.

---

## BND-006 — claim touchpoint

После успешного claim записывать append-only touchpoint:

```text
touchpoint_type = partner_claim
partner_attribution_session_id
user_id
binding_id в evidence
policy_version_id
source_event_id = partner-claim:{session_id}
idempotency_key = partner-claim:{session_id}
```

Также записывать touchpoint для terminal rejection с safe reason code либо отдельный audit event.

---

## BND-007 — self-attribution

Дополнить проверки:

- legacy owner user;
- `mobile_users.partner_account_id`;
- active partner workspace membership того же identity;
- verified identity linkage;
- same billing entity при reseller policy;
- internal/admin test accounts;
- risk graph signals.

Результат:

```text
409 PARTNER_SELF_ATTRIBUTION_BLOCKED
```

Не раскрывать клиенту детали detection.

---

# 9. Work Package D — partner code governance

## COD-001 — отдельная idempotency storage

Сейчас create idempotency key сохраняется в:

```text
sub_id_schema["_create_idempotency_key"]
```

Это запрещено.

### Требование

Использовать существующую generic idempotency infrastructure либо таблицу:

```text
api_idempotency_records
```

Scope:

```text
principal_id
workspace_id
endpoint
idempotency_key
request_hash
response_reference
expires_at
```

Повтор с другим request body:

```text
409 IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD
```

---

## COD-002 — race-safe code generation

Алгоритм:

1. generate normalized code;
2. insert;
3. catch `IntegrityError`;
4. rollback savepoint;
5. retry до 10 раз;
6. при исчерпании 503.

Для user-provided code collision вернуть 409.

Нельзя полагаться только на read-before-write.

---

## COD-003 — commercial fields только через approval

Partner operator не должен напрямую изменять:

```text
owner_type
lane_key
attribution_model
commission_contract_id
policy_version_id
markup_pct сверх contract defaults
attribution_window_seconds сверх policy
```

### Разделение API

Partner self-service:

```text
label
destination
campaign defaults
sub-id schema
pause/resume
```

Commercial policy mutation:

```text
admin/ops approval workflow
```

Для sensitive change создаётся review request, а не immediate PATCH.

---

## COD-004/COD-005 — lifecycle state machine

Допустимые переходы:

```text
draft → pending_approval
pending_approval → active | rejected
active → paused | revoked | expired
paused → active | revoked | expired
revoked → archived
expired → archived
archived → terminal
```

Запрещено:

```text
revoked → active
archived → active
expired → active
```

Исключение — explicit admin reissue создаёт новый code.

Каждый transition:

- reason code;
- actor;
- timestamp;
- previous/new status;
- audit/outbox event;
- optimistic version.

---

## COD-006 — eligibility policy

Capture и claim обязаны проверять:

```text
is_active
lifecycle_status
approval_status
active_from <= now
expires_at > now
workspace status
lane membership status
contract effective dates
allowed channel
allowed storefront
allowed geography
risk state
```

### Capture-time versus claim-time

Policy должна явно определить:

```text
eligible_at_capture
eligible_at_claim
```

Например, code paused после legitimate click:

- affiliate policy может сохранить capture;
- revoked/fraud code должен invalidate pending sessions.

Нельзя решать это неявно текущим `is_active`.

---

## COD-007 — lifecycle audit

Не сохранять system metadata в `sub_id_schema`.

Создать:

```text
partner_code_events
```

Поля:

```text
id
partner_code_id
partner_account_id
actor_admin_user_id
event_type
reason_code
event_payload
created_at
```

---

## COD-008 — QR failure

Если real QR generation не удалась:

```text
503 PARTNER_QR_GENERATION_FAILED
```

Не возвращать placeholder SVG с HTTP 200, потому что он визуально похож на QR, но не сканируется.

Добавить validation test, который decode generated QR и сравнивает URL.

---

## COD-009 — destination DTO

`default_destination_url` должен быть настоящим customer destination, а `share_url` — public tracking link.

Пример:

```json
{
  "share_url": "https://cyber-vpn.net/p/px_...",
  "default_destination_url": "https://my.cyber-vpn.net/ru-RU/pricing"
}
```

Не возвращать одну и ту же ссылку в обоих полях.

---

# 10. Work Package E — order attribution policy

## ORD-001 — реальный attribution model

### Текущий дефект

Resolver использует фиксированный порядок:

```text
manual override
contract assignment
claimed binding
explicit code
reseller binding
passive click
storefront default
```

Поле `attribution_model` не меняет выбор.

### Требование

Создать policy strategy:

```python
AttributionPolicyResolver
```

Поддержать минимум:

```text
first_eligible_touch
last_eligible_touch
last_eligible_click
persistent_storefront_binding
explicit_code_priority
```

Manual override и contract assignment остаются верхними immutable rules.

### Tests

- click A, click B, first touch → A;
- click A, click B, last touch → B;
- persistent reseller + affiliate click → reseller;
- explicit code priority;
- expired touch исключён;
- wrong storefront исключён.

---

## ORD-002 — snapshot, а не mutable current code

Touchpoint/session должны содержать immutable:

```text
owner_type
partner_account_id
partner_code_id
policy_version_id
commission_contract_id
attribution_model
window
markup policy
commission policy reference
eligibility result
```

Order resolver не должен загружать current code для изменения исторического результата.

Current code можно читать только для integrity validation, но winner terms берутся из snapshot.

---

## ORD-003 — полный order policy snapshot

В `order_attribution_results.policy_snapshot` сохранить:

```json
{
  "resolver_version": "partner_attribution_v3",
  "attribution_model": "last_eligible_touch",
  "policy_version_id": "...",
  "commission_contract_id": "...",
  "commission_rate": "10.0000",
  "markup_rate": "5.0000",
  "hold_days": 14,
  "currency_policy": "order_currency",
  "renewal_policy": "...",
  "refund_policy": "...",
  "source_session_id": "...",
  "captured_at": "...",
  "claim_binding_id": "..."
}
```

Snapshot является immutable.

---

## ORD-004/ORD-005 — commerce safety net

### Проблема

Passive click touchpoint сам по себе не связан с quote/checkout/order. Нормальный путь зависит от успешного frontend claim.

### Требование

При создании authenticated quote backend выполняет:

```text
EnsurePendingPartnerAttributionClaimedUseCase
```

Если есть valid attribution cookie:

1. claim/binding;
2. attach binding/session ID к quote snapshot;
3. record touchpoint linked to quote.

Frontend provider остаётся UX optimization, но financial integrity не зависит от React effect.

---

# 11. Work Package F — earning integrity

## FIN-001 — immutable commission contract

### Текущий дефект

Canonical earning получает `commission_pct` через текущий config и текущее количество clients.

Это делает повторный расчёт невоспроизводимым.

### Требование

Создать/использовать canonical contract version:

```text
partner_commission_contracts
```

Минимальные поля:

```text
id
partner_account_id
version
owner_type
commission_model
commission_rate
markup_rate/cap
hold_days
renewal_policy
refund_policy
currency_policy
effective_from
effective_to
status
created_at
```

При order attribution фиксировать numeric terms.

Earning use case использует только order snapshot.

---

## FIN-002 — canonical tier source

Нельзя считать tier через legacy:

```text
PartnerEarningModel
```

Варианты:

1. tiers фиксируются contract version;
2. tier evaluation выполняется до order commit и сохраняется в snapshot;
3. canonical client count строится из:
   ```text
   commercial bindings / qualifying orders / earning events
   ```
   согласно policy.

После order commit изменение client count не изменяет commission данного order.

---

## FIN-003 — Decimal и precision

Изменить monetary ORM annotations:

```python
Mapped[Decimal]
```

Использовать:

```text
Numeric(20, 8)
```

Запретить:

```python
float(base_amount)
float(markup_amount)
```

API возвращает money как decimal strings.

Rounding policy:

```text
ROUND_HALF_UP
currency minor-unit rules
```

Snapshot хранит exact string values.

---

## FIN-004 — policy failure fail-closed

### Текущий дефект

Если `EvaluateOrderPolicyUseCase` падает, исключение логируется, после чего payout может продолжиться с `policy_evaluation=None`.

### Требование

Cash payout нельзя создавать без успешной policy evaluation.

При ошибке:

```text
raise retryable PartnerPayoutPolicyUnavailable
```

Payment completion может быть зафиксирован, но earning job остаётся pending/retryable.

Referral и partner payout также не должны выполняться без no-double-payout decision.

---

## FIN-005 — durable outbox worker

### Целевая transaction

Payment webhook:

1. validates provider event;
2. обновляет payment/order terminal state;
3. записывает:
   ```text
   payment.completed
   ```
   в transactional outbox;
4. commit;
5. возвращает success provider.

Worker:

1. получает event;
2. загружает order attribution;
3. policy evaluation;
4. создаёт earning idempotently;
5. ack.

Retry:

```text
1m, 5m, 15m, 1h, 6h
```

После max attempts:

```text
DLQ
alert
admin reconciliation item
```

Нельзя полагаться только на повтор webhook провайдера.

---

## FIN-006 — legacy cutover

Canonical order flow использует только `earning_events`.

Legacy `PartnerEarningModel`/wallet path:

- выключен feature flag для canonical orders;
- допускается только для явно legacy payment без order;
- измеряется отдельной metric;
- имеет sunset date.

Не создавать одновременно:

```text
wallet credit + canonical earning event
```

---

## FIN-007 — finance summary

Расширить response:

```json
{
  "currency_code": "USD",
  "pending_amount": "0.00",
  "on_hold_amount": "10.00",
  "available_amount": "20.00",
  "reserved_amount": "5.00",
  "paid_amount": "100.00",
  "reversed_amount": "3.00",
  "next_payout_eligible_amount": "15.00"
}
```

Использовать Decimal strings.

Учитывать:

- holds;
- reserves;
- statement inclusion;
- payout instruction status;
- adjustments;
- refunds/disputes.

---

# 12. Work Package G — partner portal UI

## UI-001/UI-002 — завершить Codes page

Backend mutations уже существуют. Требуется подключить их к UI.

### Обязательные actions

На code card:

```text
Copy link
Share
Generate QR
Create deep link
Edit destination
Pause
Activate
Revoke
Archive
```

В header:

```text
Create code
```

Actions отображаются по:

```text
backend commercial capabilities
code.available_actions
current_permission_keys
workspace governance status
```

### React Query mutations

После success:

```text
invalidate workspace-codes
invalidate commercial-capabilities
show toast
update version
```

Version conflict:

```text
409 → reload card + conflict message
```

### Forms

Create form не должен позволять partner самостоятельно менять sensitive contract terms.

---

## UI-003 — ResourceState

Вместо `T | null`:

```typescript
type ResourceState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: T }
  | { status: 'empty'; data: T }
  | { status: 'forbidden'; code: string }
  | { status: 'unavailable'; code: string }
  | { status: 'error'; error: PortalApiError };
```

UI:

- 403 — permission screen;
- 404 — feature/workspace unavailable;
- 200 [] — empty state;
- network/5xx — retry screen;
- stale cached data — stale badge.

---

## UI-004 — bounded GET retry

Safe GET:

```typescript
retry(failureCount, error) {
  if (is4xx(error)) return false;
  return failureCount < 2;
}
```

429 учитывает `Retry-After`.

Mutations автоматически не повторять без idempotency key.

---

## UI-005 — permission fail-closed

Для canonical state:

```text
currentPermissionKeys = []
```

означает deny.

Только:

```text
currentPermissionKeys === undefined
```

может включать legacy fallback during migration.

После legacy sunset fallback удалить.

---

## UI-006 — единый runtime provider

В partner dashboard layout:

```tsx
<PartnerPortalRuntimeProvider>
  {children}
</PartnerPortalRuntimeProvider>
```

Provider владеет:

- bootstrap query;
- workspace resources;
- finance summary;
- commercial capabilities;
- одной SSE connection.

`PartnerRouteGuard` и pages используют context.

Test обязан подтвердить одну SSE connection.

---

## UI-007 — запрет demo fallback в production

При отсутствии canonical workspace:

```text
onboarding
permission denied
bootstrap error
no workspace
```

Не использовать local scenario finance/codes.

Fixtures импортируются только при:

```text
NODE_ENV !== production
AND explicit simulation flag
```

---

## UI-008/UI-009/UI-010 — finance и даты

- добавить API client `getWorkspaceFinanceSummary`;
- runtime использует response, а не reduce statements;
- currency cards отдельные;
- текущая locale передаётся в `Intl.NumberFormat`;
- не хранить отформатированные money strings в domain state;
- `review_request.due_date` не участвует в `updatedAt`;
- backend должен возвращать `updated_at`.

---

# 13. Work Package H — host/storefront hardening

## HST-001 — unknown host

Текущий resolver возвращает portal context для неизвестного host.

### Требование

Unknown host:

```text
421 Misdirected Request
```

или controlled 404.

### Источник истины

Production host mapping:

```text
DB storefront host registry
+
explicit portal host allowlist
```

Не выводить tenant/brand из произвольного subdomain.

### Дополнительно

- не доверять malformed host;
- не использовать internal listener host как external authority;
- `X-Forwarded-Host` только от trusted proxy;
- add tests Host/header injection.

---

# 14. Work Package I — legacy cleanup

## LEG-001 — markup validation

Legacy schema:

```python
markup_pct: Decimal = Field(ge=Decimal("0"))
```

Верхний предел:

```text
min(schema cap, configured policy max)
```

Все financial percentages — Decimal.

---

## LEG-002 — sunset

Legacy routes:

```text
/partner/dashboard
/partner/codes
/partner/earnings
/partner/bind
```

Добавить:

```text
Deprecation: true
Sunset: <RFC date>
Link: <canonical docs>; rel="successor-version"
```

Partner frontend не должен импортировать legacy `partner.ts`/`referral.ts`.

После reconciliation period:

- disable legacy writes;
- keep read adapter;
- remove routes in separate breaking-change release.

---

# 15. Миграции БД

Создать отдельные revisions, не добавлять всё в одну migration.

## Migration 1 — transfer hardening

```text
partner_attribution_sessions:
  rename token_hash → session_token_hash
  add transfer_expires_at
  add transfer_consumed_at
  add first_seen_at
  add last_seen_at
  add rejection_reason_code
  add destination_path
  add locale
  add sale_channel
  add sub_ids
  add click_id
```

Backfill existing sessions:

- unclaimed transferred sessions invalidate;
- active session cookies потребуется обновить;
- documented rollout.

## Migration 2 — link entity

```text
partner_code_links
```

Unique public slug, status, destination and campaign snapshot.

## Migration 3 — touchpoint idempotency

```sql
CREATE UNIQUE INDEX uq_attribution_touchpoints_idempotency_key
ON attribution_touchpoints (idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX uq_attribution_touchpoints_source_event
ON attribution_touchpoints (auth_realm_id, source_event_id)
WHERE source_event_id IS NOT NULL;
```

## Migration 4 — binding invariants

Partial unique indexes global/storefront.

Перед созданием:

1. audit duplicate active rows;
2. deterministic conflict report;
3. manual/automated resolution;
4. только затем index.

## Migration 5 — contract/snapshot precision

- canonical commission contract table/reference;
- Numeric precision upgrades;
- FKs для `commission_contract_id`;
- exact Decimal snapshot fields.

## Migration 6 — code events/idempotency

- `partner_code_events`;
- API idempotency records;
- удалить system keys из `sub_id_schema`.

---

# 16. Error contract

Единый формат:

```json
{
  "detail": {
    "code": "PARTNER_TRANSFER_TOKEN_CONSUMED",
    "message": "Partner attribution transfer token has already been consumed.",
    "retryable": false,
    "request_id": "..."
  }
}
```

Обязательные codes:

```text
PARTNER_PUBLIC_LINK_NOT_FOUND
PARTNER_PUBLIC_LINK_INACTIVE
PARTNER_TRANSFER_TOKEN_INVALID
PARTNER_TRANSFER_TOKEN_EXPIRED
PARTNER_TRANSFER_TOKEN_CONSUMED
PARTNER_ATTRIBUTION_SESSION_EXPIRED
PARTNER_ATTRIBUTION_USER_NOT_READY
PARTNER_ATTRIBUTION_REALM_MISMATCH
PARTNER_CODE_NOT_ACTIVE
PARTNER_CODE_NOT_YET_ACTIVE
PARTNER_CODE_EXPIRED
PARTNER_CODE_REVOKED
PARTNER_CODE_CHANNEL_BLOCKED
PARTNER_CODE_STOREFRONT_BLOCKED
PARTNER_CODE_GEO_BLOCKED
PARTNER_OWNER_TYPE_INVALID
PARTNER_SELF_ATTRIBUTION_BLOCKED
PARTNER_BINDING_CONFLICT
PARTNER_BINDING_VERSION_CONFLICT
PARTNER_CODE_VERSION_CONFLICT
PARTNER_CODE_LIFECYCLE_TRANSITION_INVALID
PARTNER_QR_GENERATION_FAILED
PARTNER_PAYOUT_POLICY_UNAVAILABLE
PARTNER_EARNING_RETRY_SCHEDULED
PARTNER_EARNING_ALREADY_EXISTS
RATE_LIMITED
```

---

# 17. Observability

## Metrics

```text
partner_public_link_open_total{result}
partner_attribution_capture_total{result,owner_type,lane}
partner_transfer_consume_total{result}
partner_transfer_replay_total
partner_attribution_claim_total{result,reason}
partner_binding_conflict_total{existing_owner,incoming_owner}
partner_order_attribution_total{model,source,result}
partner_order_attribution_mismatch_total
partner_earning_processing_total{result,reason}
partner_earning_retry_queue_depth
partner_earning_dlq_total
partner_finance_reconciliation_mismatch_total{type}
partner_portal_resource_load_total{resource,result}
partner_portal_sse_connections_current
```

## Logs

```text
request_id
source_event_id
workspace_id
partner_account_id
partner_code_id
partner_link_id
attribution_session_id
binding_id
order_id
payment_id
policy_version_id
commission_contract_id
result
reason_code
```

Нельзя логировать raw transfer/session tokens.

## Alerts

- transfer replay spike;
- payment completed без earning task;
- earning DLQ;
- duplicate binding blocked;
- order attribution mismatch;
- currency mismatch;
- finance reconciliation mismatch;
- unknown host spike;
- excessive SSE connections.

---

# 18. Полная тестовая матрица

## 18.1. Unit tests

### Tokens

- transfer token random;
- session token random и отличается;
- hash lookup;
- expiry;
- replay;
- malformed token;
- deterministic UUID token больше не генерируется.

### Code policy

- active_from;
- expires;
- revoked;
- allowed channel;
- storefront;
- geo;
- workspace status;
- owner type invalid;
- lifecycle transitions.

### Attribution model

- first touch;
- last touch;
- last click;
- persistent reseller;
- explicit code priority.

### Money

- Decimal;
- rounding;
- eight-decimal precision;
- multiple currencies;
- fixed snapshot after config change.

---

## 18.2. Real PostgreSQL integration tests

Использовать PostgreSQL, не SQLite adapter.

1. concurrent transfer consume;
2. concurrent identical claim;
3. concurrent different partner claim;
4. global active binding constraint;
5. storefront active binding constraint;
6. code generation collision;
7. idempotency key race;
8. touchpoint duplicate;
9. earning duplicate event;
10. order attribution immutable unique;
11. transaction rollback;
12. migration duplicate cleanup.

---

## 18.3. API tests

### Public capture

- valid;
- invalid link;
- rate limited;
- destination;
- locale;
- campaign;
- payload limit;
- spoofed host;
- X-Auth-Realm ignored.

### Transfer

- success;
- replay;
- expired;
- concurrent;
- cookie properties.

### Claim

- no pending;
- success;
- same owner;
- conflict;
- storefront;
- self-attribution;
- user not ready;
- realm mismatch.

### Workspace code

- create permission;
- create idempotency;
- update version conflict;
- prohibited sensitive field;
- lifecycle transition;
- QR decodes;
- capability contract.

---

## 18.4. Frontend tests

### PartnerAttributionProvider

- transfer success;
- query cleanup;
- transient retry;
- final retry exhaustion then online recovery;
- auth becomes ready;
- claim success;
- claim conflict;
- terminal cleanup;
- cross-tab storage event;
- StrictMode does not duplicate consume/claim;
- unmount abort;
- no raw token in localStorage.

### Partner portal

- code list loading;
- empty;
- forbidden;
- 404 unavailable;
- network error + retry;
- Copy;
- Share;
- QR;
- Create;
- Pause;
- Revoke confirmation;
- optimistic version conflict;
- capabilities hide blocked actions;
- one SSE connection.

### Finance

- USD + EUR separate;
- reversed;
- paid;
- locale ru-RU/en-EN;
- no statement client aggregation.

---

## 18.5. E2E

### E2E-PAT-001 — full affiliate path

```text
partner login
→ create code
→ copy share URL
→ anonymous browser opens link
→ URL cleanup
→ reload
→ register by email
→ OTP
→ claim
→ quote
→ order
→ payment
→ one earning
→ hold/available
→ statement
→ partner portal visibility
```

### E2E-PAT-002 — OAuth

Partner link → OAuth → callback → claim → payment → earning.

### E2E-PAT-003 — transfer replay

Browser A consume success; Browser B same `pat` rejected.

### E2E-PAT-004 — deep link

Generated pricing deep link реально открывает pricing, locale сохраняется.

### E2E-PAT-005 — first/last touch

A → B → order, winner соответствует configured model.

### E2E-PAT-006 — reseller storefront scope

Binding storefront A не применяется в storefront B.

### E2E-PAT-007 — policy failure

Policy service failure не создаёт payout; retry позже создаёт ровно один earning.

### E2E-PAT-008 — config changed after order

Tier/config меняются после order; earning остаётся по order snapshot.

### E2E-PAT-009 — multi-currency

USD и EUR earning/summary не смешиваются.

### E2E-PAT-010 — refund/dispute

Refund создаёт adjustment, dispute блокирует/reverses согласно policy.

---

# 19. Порядок реализации по PR

## PR-1 — Security hotfix

- transfer/session token separation;
- replay protection;
- transfer TTL;
- trusted realm/host;
- rate limits;
- payload limits;
- tests.

## PR-2 — Binding integrity

- storefront scope;
- conflict matrix;
- partial unique indexes;
- row locks;
- claim touchpoint;
- concurrency tests.

## PR-3 — Link/deep-link correctness

- random public slug;
- persistent partner links;
- destination/locale;
- campaign/sub IDs;
- QR hard failure;
- tests.

## PR-4 — Code governance

- sensitive-field approval;
- lifecycle state machine;
- audit events;
- idempotency storage;
- collision retry.

## PR-5 — Attribution policy

- policy strategy;
- immutable candidate snapshot;
- quote safety net;
- full order snapshot;
- tests.

## PR-6 — Finance integrity

- commission contracts;
- Decimal precision;
- fail-closed policy;
- outbox worker;
- canonical tier;
- legacy cutover;
- reconciliation.

## PR-7 — Partner portal completion

- runtime provider;
- resource states;
- codes actions;
- capability client;
- finance summary client;
- localization;
- UI tests.

## PR-8 — E2E and rollout

- full E2E;
- staging rehearsal;
- dashboards/alerts;
- legacy deprecation;
- production feature-flag rollout.

---

# 20. Feature flags

```text
partner_transfer_v3_enabled
partner_random_public_links_enabled
partner_persistent_deep_links_enabled
partner_binding_constraints_enabled
partner_attribution_policy_v3_enabled
partner_quote_claim_safety_net_enabled
partner_earning_outbox_v2_enabled
partner_earning_snapshot_v2_enabled
partner_portal_codes_ui_v2_enabled
partner_portal_finance_summary_v2_enabled
partner_legacy_earning_write_enabled
```

Rollout:

```text
internal
1 workspace
5%
25%
50%
100%
```

Stop conditions:

- transfer replay;
- binding conflict increase;
- order attribution mismatch;
- earning mismatch;
- duplicate earning;
- currency mismatch;
- DLQ growth;
- reconciliation failure.

---

# 21. OpenAPI и generated artifacts

После изменения API:

```powershell
cd backend
python scripts\export_openapi.py

cd ..\frontend
npm run generate:api-types
npm run prepare:i18n

cd ..\partner
npm run generate:api-types
npm run prepare:i18n

cd ..\admin
npm run generate:api-types
npm run prepare:i18n
```

Закоммитить:

```text
backend/docs/api/openapi.json
frontend/src/lib/api/generated/types.ts
partner/src/lib/api/generated/types.ts
admin/src/lib/api/generated/types.ts
```

Удалить ручные API types для partner attribution после генерации.

---

# 22. Проверка на Windows

## Backend

```powershell
cd backend

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m ruff check src tests
python -m pytest tests\unit -q
python -m pytest tests\integration -q
python -m pytest tests\e2e -q
```

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

## Partner

```powershell
cd partner
npm ci
npm run prepare:i18n
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Admin

```powershell
cd admin
npm ci
npm run prepare:i18n
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Contract checks через Git Bash

```bash
bash scripts/check-api-contract.sh --verbose
bash scripts/check-generated-artifacts.sh
```

## Migration checks

```powershell
cd backend
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Отдельно проверить upgrade на копии production-like данных с duplicate bindings.

---

# 23. Финальный acceptance checklist

## Security

- [ ] public slug не содержит UUID;
- [ ] transfer one-time;
- [ ] transfer TTL ≤ 15 минут;
- [ ] cookie token отдельный;
- [ ] no raw token in DB/log/localStorage;
- [ ] trusted host/realm;
- [ ] rate limits;
- [ ] replay test.

## Attribution

- [ ] destination работает;
- [ ] locale работает;
- [ ] campaign/sub IDs сохраняются;
- [ ] claim server-side safety net;
- [ ] storefront scope;
- [ ] conflict status корректный;
- [ ] DB unique binding;
- [ ] self-attribution blocked.

## Order

- [ ] attribution model реально применяется;
- [ ] immutable policy snapshot;
- [ ] current code change не меняет old order;
- [ ] winner explainability полная.

## Finance

- [ ] Decimal only;
- [ ] currency from order;
- [ ] rate from snapshot;
- [ ] fail-closed policy;
- [ ] durable outbox retry;
- [ ] one earning;
- [ ] refund/dispute adjustment;
- [ ] no dual wallet ledger.

## Portal

- [ ] Create/Copy/Share/QR;
- [ ] lifecycle actions;
- [ ] capability-driven UI;
- [ ] error states;
- [ ] one SSE;
- [ ] no production demo fallback;
- [ ] finance summary by currency;
- [ ] localization.

## Tests/CI

- [ ] PostgreSQL concurrency;
- [ ] Redis/outbox retry;
- [ ] provider tests;
- [ ] UI tests;
- [ ] full E2E;
- [ ] OpenAPI sync;
- [ ] all builds green;
- [ ] staging rehearsal documented.

---

# 24. Финальная бизнес-гарантия

После выполнения этого ТЗ система должна обеспечивать следующий сценарий:

```text
Партнёр создаёт code в partner portal
→ получает случайную canonical share URL
→ customer открывает ссылку
→ одноразовый transfer безопасно переносит attribution на customer host
→ URL очищается
→ customer перезагружает страницу
→ проходит OAuth/email/passkey auth
→ backend atomic claim создаёт правильную scoped binding
→ quote/order фиксирует immutable winner и contract snapshot
→ payment completed создаёт durable outbox event
→ worker создаёт ровно один earning в правильной currency
→ hold/statement/payout отображаются в нужном workspace
→ refund/dispute формирует корректную корректировку
```

Ни один из следующих факторов не должен изменить или потерять результат:

- удаление query;
- reload;
- новая вкладка;
- auth redirect;
- повтор webhook;
- network retry;
- изменение code после order;
- изменение tier/config после order;
- одновременный claim;
- несколько currencies;
- refund/chargeback.

Система может считаться реализованной на 100% только после прохождения полного production-like E2E с SQL assertions для:

```text
partner_attribution_sessions
attribution_touchpoints
customer_commercial_bindings
order_attribution_results
earning_events
earning_holds
partner_statements
settlement_adjustments
```
