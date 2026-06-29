# Техническое задание v7.4  
# Финальное устранение RSC/CORS redirect в личном кабинете и стабилизация production routing

**Проект:** CyberVPN  
**Версия ТЗ:** v7.4  
**Статус:** требуется к выполнению  
**Причина:** после v7.3/v7.3.1 проблема RSC/CORS в личном кабинете всё ещё воспроизводится: RSC-запросы с `my.cyber-vpn.net` на `/rewards/*` и `/messages` получают redirect на `cyber-vpn.net`, из-за чего браузер блокирует navigation/fetch как cross-origin preflight redirect.

---

## 1. Симптом production-проблемы

В браузере в личном кабинете видны ошибки вида:

```text
Access to fetch at 'https://cyber-vpn.net/en-EN'
redirected from 'https://my.cyber-vpn.net/en-EN/rewards/notifications?_rsc=...'
from origin 'https://my.cyber-vpn.net' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
Redirect is not allowed for a preflight request.
```

Затронутые routes:

```text
/en-EN/rewards
/en-EN/rewards/referral
/en-EN/rewards/gifts
/en-EN/rewards/invites
/en-EN/rewards/codes
/en-EN/rewards/notifications
/en-EN/messages
```

Фактический недопустимый переход:

```text
https://my.cyber-vpn.net/en-EN/rewards/*?_rsc=...
→ https://cyber-vpn.net/en-EN
```

Это ломает переходы внутри личного кабинета.

---

## 2. Текущая причина в коде

В текущем `frontend/src/proxy.ts` есть:

```ts
const MANDATORY_PUBLIC_ALLOWED_PREFIXES = ['/miniapp'] as const;
const MANDATORY_CABINET_ALLOWED_PREFIXES = ['/miniapp'] as const;
const MANDATORY_OPERATIONAL_PATH_PREFIXES = ['/runtime'] as const;
```

При нормализации runtime capabilities используется:

```ts
cabinetAllowedPrefixes: withMandatoryPathPrefixes(
  normalizeSafePathList(
    siteRecord.cabinet_allowed_prefixes,
    fallback.cabinetAllowedPrefixes,
  ),
  MANDATORY_CABINET_ALLOWED_PREFIXES,
)
```

Если внешний `/api/v1/client/capabilities` возвращает неполный или stale список `cabinet_allowed_prefixes`, frontend гарантированно добавляет только `/miniapp`, но не добавляет обязательные cabinet routes:

```text
/dashboard
/subscriptions
/payment-history
/referral
/rewards
/rewards/referral
/rewards/gifts
/rewards/invites
/rewards/codes
/rewards/notifications
/messages
/wallet
/settings
/support
/servers
/onboarding
/monitoring
/analytics
/users
/partner
```

В результате proxy может считать `/rewards/*` или `/messages` marketing route на cabinet host и редиректить его на public host.

---

## 3. Цель доработки

Сделать невозможным cross-origin redirect из `my.cyber-vpn.net` на `cyber-vpn.net` для всех RSC/internal navigation requests и для всех обязательных cabinet routes.

После выполнения:

```text
https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=...
```

не должен возвращать:

```text
30x Location: https://cyber-vpn.net/...
```

Допустимо:

```text
200
204
404
```

Недопустимо:

```text
301 / 302 / 307 / 308 на cyber-vpn.net
```

---

## 4. Frontend proxy: обязательные исправления

### 4.1. Сделать полный mandatory cabinet allowlist

Файл:

```text
frontend/src/proxy.ts
```

Заменить:

```ts
const MANDATORY_CABINET_ALLOWED_PREFIXES = ['/miniapp'] as const;
```

на:

```ts
const MANDATORY_CABINET_ALLOWED_PREFIXES = CABINET_ALLOWED_PREFIXES;
```

или на явный полный список:

```ts
const MANDATORY_CABINET_ALLOWED_PREFIXES = [
  '/miniapp',
  '/dashboard',
  '/subscriptions',
  '/payment-history',
  '/referral',
  '/rewards',
  '/rewards/referral',
  '/rewards/gifts',
  '/rewards/invites',
  '/rewards/codes',
  '/rewards/notifications',
  '/messages',
  '/wallet',
  '/settings',
  '/support',
  '/servers',
  '/onboarding',
  '/monitoring',
  '/analytics',
  '/users',
  '/partner',
] as const;
```

Рекомендуемый вариант:

```ts
const MANDATORY_CABINET_ALLOWED_PREFIXES = CABINET_ALLOWED_PREFIXES;
```

чтобы не держать два рассинхронизирующихся списка.

---

### 4.2. Мержить backend payload с fallback, а не заменять fallback

Сейчас `normalizeSafePathList(siteRecord.cabinet_allowed_prefixes, fallback.cabinetAllowedPrefixes)` возвращает payload, если он непустой, и тем самым может выбросить fallback.

Нужно изменить на helper:

```ts
function mergeSafePathLists(
  fallback: readonly string[],
  payload: unknown,
  mandatory: readonly string[],
): readonly string[] {
  const payloadList = normalizeSafePathList(payload, []);
  return withMandatoryPathPrefixes(
    [
      ...fallback,
      ...payloadList,
    ],
    mandatory,
  );
}
```

Использовать:

```ts
cabinetAllowedPrefixes: mergeSafePathLists(
  fallback.cabinetAllowedPrefixes,
  siteRecord.cabinet_allowed_prefixes,
  MANDATORY_CABINET_ALLOWED_PREFIXES,
),
```

Аналогично рекомендуется сделать для:

```ts
allowedPathPrefixes
operationalPathPrefixes
```

но P0-блокер — именно `cabinetAllowedPrefixes`.

---

### 4.3. Запретить cross-origin redirect для internal navigation на cabinet host

В `buildCabinetOnlyRedirect(...)`, внутри ветки:

```ts
if (isCabinetHost) {
  ...
}
```

добавить hard guard перед любым redirect на public host:

```ts
if (isCabinetHost && isNextInternalNavigationRequest(request)) {
  return new NextResponse(null, { status: 404 });
}
```

Но правильнее — вернуть `404` только если route не разрешён:

```ts
if (isCabinetHost) {
  if (isAllowedByRuntimePrefix(unlocalizedPathname, snapshot.cabinetAllowedPrefixes)) {
    return null;
  }

  if (isNextInternalNavigationRequest(request)) {
    return new NextResponse(null, { status: 404 });
  }

  ...
}
```

Это гарантирует, что даже при сломанном allowlist RSC/preflight не уйдёт на другой origin.

---

### 4.4. Добавить dedicated guard для cabinet route segments

Даже если `cabinetAllowedPrefixes` неполный, route segment `rewards` или `messages` является cabinet route.

Добавить:

```ts
if (isCabinetHost && isCabinetRouteSegment(routeSegment)) {
  return null;
}
```

или более строго:

```ts
if (
  isCabinetHost
  && isCabinetRouteSegment(routeSegment)
  && !isAllowedByRuntimePrefix(unlocalizedPathname, snapshot.legalPathPrefixes)
) {
  return null;
}
```

Рекомендация: использовать это как дополнительную страховку после allowlist.

---

## 5. Shared route list

Файл:

```text
frontend/src/shared/lib/cabinet-routes.ts
```

Проверить, что список содержит все маршруты личного кабинета:

```ts
export const CABINET_ROUTE_SEGMENTS = [
  'analytics',
  'dashboard',
  'delete-account',
  'messages',
  'monitoring',
  'onboarding',
  'partner',
  'payment-history',
  'referral',
  'rewards',
  'servers',
  'settings',
  'subscriptions',
  'support',
  'users',
  'wallet',
] as const;
```

Для `miniapp` принять продуктовый выбор:

- если Mini App canonical на public host `cyber-vpn.net`, не добавлять `miniapp` в `CABINET_ROUTE_SEGMENTS`;
- если Mini App разрешён и на cabinet host, добавить отдельные тесты, что `my.cyber-vpn.net/ru-RU/miniapp` не уходит на public/dashboard.

---

## 6. Caddy / edge hardening

### 6.1. Container-edge Caddy

Файл:

```text
infra/deploy/stage1/Caddyfile.stage1.snippet
```

На `my.cyber-vpn.net` добавить явный `handle` для cabinet routes перед `@public_routes`:

```caddy
@cabinet_routes path_regexp cabinet_routes ^/(?:(?:[a-z]{2}-[A-Z]{2}|zh-Hant)/)?(?:analytics|dashboard|monitoring|payment-history|referral|rewards|messages|servers|settings|subscriptions|support|users|wallet|onboarding|partner)(?:/.*)?$
handle @cabinet_routes {
    reverse_proxy cybervpn-frontend:3000 {
        header_up Host {host}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Port 443
    }
}
```

Цель: Caddy должен явно держать cabinet routes на `my.cyber-vpn.net`.

---

### 6.2. System-edge Caddy

Файл:

```text
infra/deploy/stage1/Caddyfile.system-stage1.snippet
```

Аналогично добавить `@cabinet_routes` на `my.cyber-vpn.net` перед `@public_routes`:

```caddy
@cabinet_routes path_regexp cabinet_routes ^/(?:(?:[a-z]{2}-[A-Z]{2}|zh-Hant)/)?(?:analytics|dashboard|monitoring|payment-history|referral|rewards|messages|servers|settings|subscriptions|support|users|wallet|onboarding|partner)(?:/.*)?$
handle @cabinet_routes {
    reverse_proxy http://127.0.0.1:13000 {
        header_up Host {host}
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Port 443
    }
}
```

---

## 7. Tests

### 7.1. Unit tests для `frontend/src/proxy.ts`

Добавить/обновить тесты:

#### Test 1 — stale capabilities не ломает rewards

Mock capabilities:

```json
{
  "site": {
    "customer_site_mode": "cabinet_only",
    "public_hosts": ["cyber-vpn.net"],
    "cabinet_hosts": ["my.cyber-vpn.net"],
    "cabinet_allowed_prefixes": ["/miniapp"]
  }
}
```

Request:

```text
https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=test
RSC: 1
Accept: text/x-component
```

Expected:

```text
not redirect to cyber-vpn.net
status !== 30x
```

#### Test 2 — `/messages` protected

Request:

```text
https://my.cyber-vpn.net/en-EN/messages?_rsc=test
```

Expected:

```text
not redirect to cyber-vpn.net
```

#### Test 3 — normal browser navigation to cabinet route

Request:

```text
https://my.cyber-vpn.net/en-EN/rewards/invites
```

Expected:

```text
allow NextResponse.next()
```

#### Test 4 — unknown marketing route on cabinet host

Request:

```text
https://my.cyber-vpn.net/en-EN/features
```

Expected:

```text
redirect to https://cyber-vpn.net/en-EN
```

#### Test 5 — internal unknown route on cabinet host

Request:

```text
https://my.cyber-vpn.net/en-EN/features?_rsc=test
RSC: 1
```

Expected:

```text
404
no Location header
```

---

### 7.2. Smoke script update

Файл:

```text
scripts/smoke/customer_site_rsc_routes.sh
```

Расширить проверки:

1. Проверять не только `http_code == 30*`, но и наличие любого `Location: https://cyber-vpn.net`.
2. Проверять `OPTIONS` preflight:

```bash
curl -sS -o /dev/null -D "$headers_file" -w '%{http_code}' \
  -X OPTIONS \
  -H 'Origin: https://my.cyber-vpn.net' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: rsc,next-router-state-tree' \
  "$url"
```

Expected:

```text
no 30x
no Location: https://cyber-vpn.net
```

---

## 8. Production deploy requirements

### 8.1. Use correct production target

Production application target must be `prod-app-1 / 45.87.41.146`.

Do not deploy to:

```text
95.82.233.131
cybervpn-h
home/lab host
```

unless explicitly requested.

---

### 8.2. Source sync mode

Use one of:

```bash
STAGE1_SOURCE_SYNC_MODE=git-archive
```

or:

```bash
STAGE1_SOURCE_SYNC_MODE=runtime-archive
```

Avoid accidental stale local working tree sync unless needed.

---

### 8.3. Mandatory public smoke after deploy

After deploy, collect evidence:

```bash
curl -I https://cyber-vpn.net/ru-RU/miniapp
curl -I https://cyber-vpn.net/ru-RU/miniapp/home
curl -s https://cyber-vpn.net/runtime/fingerprint
curl -s https://api.cyber-vpn.net/api/v1/runtime/fingerprint
```

Expected:

```text
miniapp routes: 200 or valid Next response, no redirect to dashboard
fingerprints: same release/git_sha/origin_marker
```

---

### 8.4. Mandatory RSC smoke after deploy

Run:

```bash
HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh
```

Additionally run manual checks:

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

Must not contain:

```text
HTTP/1.1 301
HTTP/1.1 302
HTTP/1.1 307
HTTP/1.1 308
Location: https://cyber-vpn.net/...
```

---

## 9. Cloudflare / browser cache

After deploy:

1. Purge Cloudflare cache for:
   ```text
   cyber-vpn.net/*
   my.cyber-vpn.net/*
   api.cyber-vpn.net/*
   ```
2. Check that browser loads a new JS chunk.
3. Verify `/runtime/fingerprint` from browser network panel.
4. Ask tester to hard refresh or use incognito only after edge purge.

---

## 10. Acceptance criteria

The task is accepted only if:

1. `frontend/src/proxy.ts` has full mandatory cabinet prefixes.
2. Stale capabilities with only `/miniapp` cannot break `/rewards` and `/messages`.
3. RSC requests from `my.cyber-vpn.net` never redirect to `cyber-vpn.net`.
4. Preflight `OPTIONS` for RSC routes never redirects to `cyber-vpn.net`.
5. `my.cyber-vpn.net/en-EN/rewards/invites` opens without CORS errors.
6. `my.cyber-vpn.net/en-EN/messages` opens without CORS errors.
7. Mini App still opens on `https://cyber-vpn.net/ru-RU/miniapp`.
8. Telegram Bot `/start` still returns pending onboarding / Mini App button for new users.
9. Deploy evidence contains external public smoke and RSC smoke.
10. Runtime fingerprints match across public/frontend/backend paths.

---

## 11. Rollback

If hotfix breaks routing:

1. Temporarily set:
   ```json
   customer_site.runtime.mode = "full_site"
   ```
2. Purge Cloudflare cache.
3. Re-run RSC smoke.
4. Keep `/miniapp` allowed.
5. Re-enable `cabinet_only` only after full RSC smoke is green.

---

## 12. Notes

This ТЗ does not change:

- invite campaign logic;
- Premium Smart RU lifetime grants;
- Telegram Bot registration mode;
- payment logic;
- Remnawave provisioning.

It only fixes the remaining production routing/RSC/CORS class of bugs.
