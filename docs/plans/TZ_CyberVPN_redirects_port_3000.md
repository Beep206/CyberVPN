# Техническое задание
## Устранение утечки внутренних портов `3000/3001/3002` в production-редиректы и исправление навигации CyberVPN

**Репозиторий:** `Beep206/CyberVPN`
**Ветка:** `main`
**Контрольный снимок аудита:** `de490b4191f61d506aeeb3366eec653570e80b57`
**Дата подготовки:** `2026-06-19`
**Приоритет:** `P1`
**Тип работ:** bugfix + routing hardening + auth UX + regression tests
**Затрагиваемые приложения:** `frontend`, `admin`, `partner`
**Backend:** проверка контракта logout; изменение только при обнаружении несоответствия
**Инфраструктура:** изменение внутренних upstream-портов не требуется

---

## 1. Назначение документа

Документ описывает полный объём работ для устранения следующих дефектов:

1. В production-переадресации попадает внутренний порт Next.js/Docker, например:
   - `https://my.cyber-vpn.net:3000/...`;
   - `https://admin.cyber-vpn.net:3000/...`;
   - `https://partner.cyber-vpn.net:3000/...`.
2. После выхода из пользовательского аккаунта выполняется переход через относительный `/`, что запускает дополнительный server redirect и может приводить к утечке внутреннего порта.
3. Кнопка `back_to_home` и логотип на страницах авторизации используют `href="/"`, поэтому на домене кабинета ведут не на публичный сайт, а на корень текущего origin.
4. Аналогичный риск присутствует в redirect-ветках `frontend`, `admin` и `partner`, использующих `request.nextUrl.clone()`.
5. Текущие unit-тесты частично закрепляют ошибочное поведение и ожидают перенос listener-порта во внешний `Location`.
6. Отсутствует обязательный production-like regression test, проверяющий работу Next.js за reverse proxy.

Документ предназначен для самостоятельной реализации, code review, тестирования и production-приёмки.

---

## 2. Термины

| Термин | Значение |
|---|---|
| External origin | Внешний origin, который видит браузер: схема, hostname и внешний порт |
| Runtime origin | Внутренний адрес приложения, например `http://cybervpn-frontend:3000` |
| Canonical origin | Официальный production origin конкретной поверхности |
| Public surface | Публичный сайт `https://cyber-vpn.net` |
| Cabinet surface | Пользовательский кабинет `https://my.cyber-vpn.net` |
| Admin surface | Административная панель `https://admin.cyber-vpn.net` |
| Partner surface | Партнёрский портал или storefront |
| Listener port | Порт, на котором Next.js слушает внутри контейнера |
| Production-like request | Запрос с внутренним `request.nextUrl`, но с внешними proxy-заголовками |

---

## 3. Зафиксированная проблема

### 3.1. Утечка внутреннего порта

В proxy выполняется следующий общий паттерн:

```ts
const redirectUrl = request.nextUrl.clone();

redirectUrl.protocol = 'https:';
redirectUrl.hostname = SOME_PRODUCTION_HOST;
redirectUrl.pathname = '/target';

return NextResponse.redirect(redirectUrl);
```

При этом поле `port` не очищается.

Если Next.js получил внутренний runtime URL:

```text
http://cybervpn-frontend:3000/
```

после замены только `protocol`, `hostname` и `pathname` получается:

```text
https://my.cyber-vpn.net:3000/en-EN/dashboard
```

Внутренний порт становится частью публичного заголовка:

```http
Location: https://my.cyber-vpn.net:3000/en-EN/dashboard
```

### 3.2. Logout запускает проблемный переход

Текущая логика в `frontend/src/features/header/user-menu.tsx`:

```ts
const logoutAttempt = logout();
queryClient.clear();
router.replace('/');
router.refresh();
```

Проблемы:

- переход начинается до завершения server logout;
- используется неоднозначный `/`;
- на `my.cyber-vpn.net` это корень кабинета, а не публичный сайт;
- корень кабинета обрабатывается proxy и перенаправляется на dashboard;
- параллельно выполняются `replace`, `refresh`, очистка store и запрос logout;
- возникает race condition между cookie revocation, RSC/router cache и навигацией;
- не определён явный конечный route после logout.

### 3.3. `back_to_home` не ведёт на публичный home

В `frontend/src/app/[locale]/(auth)/layout.tsx` две ссылки используют:

```tsx
<Link href="/">
```

Это относится к:

- кнопке `back_to_home`;
- логотипу CyberVPN.

На странице:

```text
https://my.cyber-vpn.net/ru-RU/login
```

такая ссылка ведёт на:

```text
https://my.cyber-vpn.net/
```

Ожидаемый результат:

```text
https://cyber-vpn.net/ru-RU
```

### 3.4. Ошибочное поведение закреплено тестами

В `frontend/src/__tests__/proxy.test.ts` имеются ожидания вида:

```text
https://my.cyber-vpn.net:9001/...
```

То есть тест считает сохранение runtime/listener-порта правильным результатом. Такой тест не защищает production-сценарий за reverse proxy.

---

## 4. Цели

После выполнения работ система должна:

1. Никогда не возвращать внутренние адреса и порты в пользовательских `Location`.
2. Корректно строить абсолютные URL за Caddy/reverse proxy.
3. Сохранять локальную разработку с портами `3000`, `3001`, `3002`, `3004`, `9001`, когда запрос действительно локальный.
4. Выполнять logout без промежуточного перехода на `/`.
5. Дожидаться server logout перед финальной навигацией.
6. После logout переводить пользователя на локализованную страницу login.
7. Вести `back_to_home` и логотип на локализованную главную страницу публичного сайта.
8. Не создавать open redirect и Host Header Injection.
9. Покрыть production-like сценарии unit/regression-тестами.
10. Сохранить существующую route policy, locale policy, query string и redirect status, если в настоящем ТЗ явно не указано обратное.

---

## 5. Не входит в объём работ

В рамках задачи не требуется:

- удалять `cybervpn-frontend:3000` из Caddy;
- менять внутренние Docker-порты;
- публиковать Next.js контейнеры напрямую в интернет;
- удалять `localhost:3000` из dev-конфигурации и unit-тестов;
- переписывать всю систему маршрутизации;
- менять правила локализации `next-intl`;
- менять SEO canonical URL, кроме переиспользования существующих констант;
- добавлять новый monorepo package только ради небольшого URL helper;
- менять бизнес-логику OAuth;
- менять redirect status с `307` на `301/308`, если это отдельно не согласовано;
- выполнять широкую переработку authentication architecture.

---

## 6. Исходные файлы и зоны риска

### 6.1. Обязательный scope

| Файл | Текущая проблема | Требуемое действие |
|---|---|---|
| `frontend/src/proxy.ts` | Cross-domain redirects строятся через `request.nextUrl.clone()` | Перестроить формирование redirect URL |
| `frontend/src/__tests__/proxy.test.ts` | Ожидается перенос runtime-порта | Исправить и расширить тесты |
| `frontend/src/features/header/user-menu.tsx` | Logout не awaited, переход на `/`, `router.refresh()` | Переписать logout flow |
| `frontend/src/app/[locale]/(auth)/layout.tsx` | `back_to_home` и logo используют `href="/"` | Использовать canonical public home URL |
| `admin/src/proxy.ts` | Same-origin redirects строятся из runtime URL | Использовать корректный external/canonical origin |
| `admin/src/__tests__/proxy.test.ts` | Нет production-like proxy tests | Добавить |
| `partner/src/proxy.ts` | Redirects наследуют runtime origin и port | Исправить с учётом portal/storefront |
| `partner/src/__tests__/proxy.test.ts` | Нет production-like tests для internal listener | Добавить |

### 6.2. Файлы для проверки и возможного переиспользования

| Файл | Назначение |
|---|---|
| `frontend/src/features/auth/lib/request-origin.ts` | Уже читает `x-forwarded-proto`, `x-forwarded-host`, `host` |
| `admin/src/features/auth/lib/request-origin.ts` | Аналогичный helper |
| `partner/src/features/auth/lib/request-origin.ts` | Аналогичный helper |
| `frontend/src/shared/lib/seo-route-policy.ts` | Содержит `SITE_URL = https://cyber-vpn.net` |
| `admin/src/shared/lib/seo-route-policy.ts` | Содержит production/dev `SITE_URL` |
| `partner/src/features/storefront-shell/lib/runtime.ts` | Определяет portal/storefront host и canonicalHost |
| `infra/deploy/stage1/Caddyfile.stage1.snippet` | Передаёт внешние proxy-заголовки |
| `frontend/next.config.ts` | Содержит разрешённые dev origins |
| `frontend/src/app/api/analytics/allowed-origin.ts` | Содержит допустимый localhost для dev |
| `frontend/src/lib/api/client.ts` | Глобальная 401-навигация и login redirect |
| `frontend/src/stores/auth-store.ts` | Локальная очистка auth state и server logout |

### 6.3. Файлы, в которых порты являются легитимными

Следующие упоминания не должны удаляться автоматически:

```text
reverse_proxy cybervpn-frontend:3000
reverse_proxy cybervpn-admin:3000
reverse_proxy cybervpn-partner:3000
localhost:3000
localhost:3001
localhost:3002
127.0.0.1:...
```

Они допустимы в:

- Docker/Caddy upstream;
- локальном dev;
- test fixtures;
- README;
- `allowedDevOrigins`;
- локальном analytics allowlist.

Критерий дефекта — не наличие строки `3000`, а попадание внутреннего порта в пользовательский production URL или HTTP `Location`.

---

## 7. Архитектурное решение

### 7.1. Основной принцип

Публичный redirect URL запрещено строить путём частичной мутации внутреннего `request.nextUrl`.

Запрещённый паттерн:

```ts
const target = request.nextUrl.clone();
target.hostname = 'my.cyber-vpn.net';
target.protocol = 'https:';
```

Обязательный паттерн для canonical cross-domain redirect:

```ts
const target = new URL(request.nextUrl.pathname, CABINET_ORIGIN);
target.search = request.nextUrl.search;
```

### 7.2. Разделение типов redirect

Необходимо различать два типа:

#### A. Canonical cross-domain redirect

Примеры:

```text
cyber-vpn.net/dashboard -> my.cyber-vpn.net/dashboard
my.cyber-vpn.net/pricing -> cyber-vpn.net/pricing
admin.cyber-vpn.org -> admin.cyber-vpn.net
```

Для него target origin должен браться только из доверенной константы или проверенной конфигурации.

#### B. Same-surface redirect

Примеры:

```text
/admin/en-EN -> /admin/en-EN/login
partner portal root -> partner portal login
storefront workspace route -> storefront home
```

Для него origin строится из проверенного external request origin либо canonical surface origin. Нельзя слепо отражать произвольный `Host`/`X-Forwarded-Host`.

---

## 8. Требования к URL helper

### 8.1. Рекомендуемое размещение

Не создавать новый workspace package. Создать app-local helper с одинаковым контрактом:

```text
frontend/src/shared/lib/redirect-url.ts
admin/src/shared/lib/redirect-url.ts
partner/src/shared/lib/redirect-url.ts
```

Допускается переиспользовать существующий helper, если:

- он перенесён в нейтральный shared-слой;
- все импорты обновлены;
- не возникает конфликт с существующим `shared/lib/request-origin.ts`;
- добавлены отдельные unit-тесты.

### 8.2. Обязательные функции

Рекомендуемый интерфейс:

```ts
import type { NextRequest } from 'next/server';

type RedirectUrlOptions = {
  pathname?: string;
  preserveSearch?: boolean;
};

export function buildCanonicalRedirectUrl(
  request: NextRequest,
  canonicalOrigin: string,
  options?: RedirectUrlOptions,
): URL;

export function buildExternalRequestRedirectUrl(
  request: NextRequest,
  fallbackOrigin: string,
  options?: RedirectUrlOptions & {
    allowedHosts?: ReadonlySet<string>;
  },
): URL;
```

Точные имена могут отличаться, но контракт должен быть эквивалентным.

### 8.3. `buildCanonicalRedirectUrl`

Функция должна:

1. Валидировать `canonicalOrigin`.
2. Разрешать только `http:` и `https:`.
3. Запрещать credentials в origin.
4. Создавать новый `URL`, а не клонировать runtime URL.
5. Использовать указанный `pathname` или текущий pathname.
6. По умолчанию сохранять `request.nextUrl.search`.
7. Никогда не переносить runtime port.
8. Не переносить hash: HTTP request не содержит browser fragment.
9. Не позволять pathname заменить origin через строку вида `//evil.example`.
10. Нормализовать pathname до абсолютного внутреннего пути, начинающегося с `/`.

Пример защиты:

```ts
function normalizeRedirectPathname(pathname: string): string {
  if (!pathname.startsWith('/') || pathname.startsWith('//')) {
    throw new Error('Redirect pathname must be an internal absolute path');
  }

  return pathname;
}
```

### 8.4. `buildExternalRequestRedirectUrl`

Функция должна читать первое значение из:

```text
x-forwarded-proto
x-forwarded-host
host
```

Требования:

- учитывать comma-separated proxy chain;
- разрешать только `http` и `https`;
- валидировать authority через `URL`;
- запрещать username/password;
- запрещать CR/LF;
- в production не использовать внутренние service names как публичный host;
- для неизвестного host использовать безопасный `fallbackOrigin`;
- локальные порты сохранять только для локальных hosts;
- default ports `80` и `443` не должны появляться явно;
- при наличии allowlist target host должен входить в неё.

### 8.5. Защита от open redirect

Нельзя реализовывать:

```ts
const origin = `${request.headers.get('x-forwarded-proto')}://${request.headers.get('x-forwarded-host')}`;
return NextResponse.redirect(new URL(path, origin));
```

без проверки host.

Обязательные негативные тесты:

```text
X-Forwarded-Host: evil.example
X-Forwarded-Host: good.example@evil.example
X-Forwarded-Host: good.example/evil
X-Forwarded-Proto: javascript
X-Forwarded-Host: value\r\nLocation: https://evil.example
```

---

## 9. Canonical origins

### 9.1. Frontend

Использовать:

```ts
const PUBLIC_ORIGIN = 'https://cyber-vpn.net';
const CABINET_ORIGIN = 'https://my.cyber-vpn.net';
const ADMIN_ORIGIN = 'https://admin.cyber-vpn.net';
```

`PUBLIC_ORIGIN` желательно получить из существующего `SITE_URL`.

Для cabinet origin создать единую константу в нейтральном shared-модуле, чтобы proxy и UI не дублировали домен.

Рекомендуемый файл:

```text
frontend/src/shared/lib/surface-origins.ts
```

Пример:

```ts
export const PUBLIC_ORIGIN = 'https://cyber-vpn.net';
export const CABINET_ORIGIN = 'https://my.cyber-vpn.net';
export const ADMIN_ORIGIN = 'https://admin.cyber-vpn.net';
```

### 9.2. Admin

Использовать существующий `SITE_URL` из:

```text
admin/src/shared/lib/seo-route-policy.ts
```

Production fallback уже должен быть:

```text
https://admin.cyber-vpn.net
```

Local development должен продолжать поддерживать:

```text
http://localhost:3001
```

### 9.3. Partner

Нельзя жёстко свести все storefront-запросы к одному host без учёта конфигурации.

Правила:

- portal production origin определяется конфигурацией portal;
- storefront origin определяется `surfaceContext.canonicalHost`;
- известный configured storefront host сохраняется;
- неизвестный host не должен отражаться в `Location`;
- неизвестный storefront host должен использовать безопасный default canonical storefront host;
- local hosts `localhost`, `127.0.0.1`, `portal.localhost`, `storefront.localhost` сохраняют локальный порт.

При необходимости добавить в `partner/src/features/storefront-shell/lib/runtime.ts` экспортируемую функцию:

```ts
export function getCanonicalPartnerSurfaceHost(
  context: PartnerSurfaceContext,
): string;
```

---

## 10. Изменение `frontend/src/proxy.ts`

### 10.1. Общие требования

После изменения:

- в redirect-ветках не должно оставаться частичной мутации internal `request.nextUrl`;
- query string должен сохраняться там, где он сохранялся раньше;
- route matching не должен измениться;
- locale policy не должна измениться;
- redirect status должен остаться прежним;
- Caddy headers должны считаться boundary внешнего запроса, но cross-domain target берётся из canonical constants.

### 10.2. Redirect matrix

#### F-PROXY-01: admin mirror

Вход:

```text
Host: admin.cyber-vpn.org
Path: /ru-RU/dashboard?tab=ops
Runtime origin: http://cybervpn-frontend:3000
```

Ожидается:

```text
https://admin.cyber-vpn.net/ru-RU/dashboard?tab=ops
```

Запрещено:

```text
https://admin.cyber-vpn.net:3000/...
```

#### F-PROXY-02: public route -> cabinet

Вход:

```text
https://cyber-vpn.net/ru-RU/dashboard?tab=ops
```

Ожидается:

```text
https://my.cyber-vpn.net/ru-RU/dashboard?tab=ops
```

#### F-PROXY-03: public www route -> cabinet

Вход:

```text
https://www.cyber-vpn.net/en-EN/settings/security
```

Ожидается:

```text
https://my.cyber-vpn.net/en-EN/settings/security
```

#### F-PROXY-04: cabinet root

Вход:

```text
https://my.cyber-vpn.net/
```

Ожидается:

```text
https://my.cyber-vpn.net/en-EN/dashboard
```

Если в корневом URL был query string, сохранить его, чтобы не менять текущую семантику:

```text
https://my.cyber-vpn.net/?source=notification
->
https://my.cyber-vpn.net/en-EN/dashboard?source=notification
```

#### F-PROXY-05: cabinet public route -> public

Вход:

```text
https://my.cyber-vpn.net/ru-RU/pricing?currency=RUB
```

Ожидается:

```text
https://cyber-vpn.net/ru-RU/pricing?currency=RUB
```

#### F-PROXY-06: no redirect

Маркетинговый route на публичном host должен продолжить обработку через `intlMiddleware`:

```text
https://cyber-vpn.net/ru-RU/pricing
```

Dashboard route на cabinet host также должен пройти без cross-domain redirect:

```text
https://my.cyber-vpn.net/ru-RU/dashboard
```

### 10.3. Дополнительное исправление определения hostname

Существующая функция нормализации host должна:

- корректно удалять порт только для route classification;
- не использовать очищенный hostname для формирования полного redirect origin;
- корректно обрабатывать trailing dot;
- корректно обрабатывать comma-separated forwarded values.

Host classification и URL construction должны быть разделены.

---

## 11. Исправление logout во frontend

### 11.1. Целевое поведение

После нажатия `Sign out`:

1. Меню закрывается.
2. Кнопка блокируется от повторного нажатия.
3. Выполняется `logout()`.
4. Завершается server request logout.
5. Очищается React Query cache.
6. Выполняется полная browser navigation на локализованный login:
   - `/ru-RU/login`;
   - `/en-EN/login`;
   - соответствующая активная locale.
7. Переход на `/` не выполняется.
8. `router.refresh()` не выполняется.
9. History entry заменяется, чтобы Back не возвращал пользователя к защищённой странице как к текущей записи.

### 11.2. Рекомендуемая реализация

Компонент должен получить locale:

```ts
const locale = useLocale();
```

Рекомендуемый flow:

```ts
const [isLoggingOut, setIsLoggingOut] = useState(false);

const handleLogout = async () => {
  if (isLoggingOut) {
    return;
  }

  setIsOpen(false);
  setIsLoggingOut(true);

  try {
    await logout();
  } catch (error: unknown) {
    console.log('[UserMenu] Server logout request failed', {
      errorName: error instanceof Error ? error.name : 'UnknownError',
    });
    console.trace('[UserMenu] Logout failure navigation trace');
  } finally {
    queryClient.clear();
    window.location.replace(`/${locale}/login`);
  }
};
```

Это пример контракта, а не требование дословно скопировать код.

### 11.3. Требования к ошибке logout

Нельзя логировать:

- access token;
- refresh token;
- cookies;
- email;
- user ID;
- полный Axios request config;
- полный response body, если он может содержать PII.

При ошибке server revoke:

- локальный state остаётся очищенным;
- пользователь всё равно выводится из текущего protected UI;
- выполняется переход на login;
- ошибка отправляется в существующий observability pipeline, если такой механизм уже подключён;
- backend contract отдельно проверяется: logout response обязан очищать httpOnly cookies.

### 11.4. Backend logout contract

Проверить, что `POST /api/v1/auth/logout`:

- возвращает успешный ответ при валидной сессии;
- удаляет access cookie;
- удаляет refresh cookie;
- удаляет cookies с теми же `path`, `domain`, `sameSite`, `secure`, с которыми они были установлены;
- не выполняет HTTP redirect;
- корректно обрабатывает повторный logout;
- не оставляет активной сессию после успешного ответа.

Если backend уже соответствует требованиям, backend-код не менять — добавить или актуализировать тест.

### 11.5. Запрещённые варианты

```ts
logout();
router.replace('/');
```

```ts
void logout();
window.location.href = '/';
```

```ts
await logout();
router.push('/');
router.refresh();
```

---

## 12. Исправление `back_to_home` и logo

### 12.1. Целевой URL

Для locale `ru-RU`:

```text
https://cyber-vpn.net/ru-RU
```

Для locale `en-EN`:

```text
https://cyber-vpn.net/en-EN
```

### 12.2. Обязательные элементы

Исправить обе ссылки в:

```text
frontend/src/app/[locale]/(auth)/layout.tsx
```

Элементы:

- `back_to_home`;
- центральный logo `CyberVPN home`.

### 12.3. Реализация

Переиспользовать `SITE_URL` или helper `toAbsoluteLocalizedUrl`.

Предпочтительный вариант:

```ts
const publicHomeHref = new URL(`/${locale}`, SITE_URL).toString();
```

Для cross-origin перехода использовать обычный `<a>`:

```tsx
<a href={publicHomeHref} aria-label="Back to home">
```

Причина:

- переход является document navigation между origin;
- Next client router не нужен;
- prefetch между разными origin не требуется;
- поведение становится однозначным.

### 12.4. Требования

- locale сохраняется;
- query parameters auth-страницы на home не переносятся;
- `target="_blank"` не использовать;
- `rel` не требуется, так как переход в том же окне;
- visual styles и accessibility attributes сохранить;
- существующие закомментированные строки не удалять;
- `MiniAppNavGuard` не ломать;
- Telegram Mini App behavior проверить отдельно.

---

## 13. Изменение `admin/src/proxy.ts`

### 13.1. Redirect-ветки

Исправить:

1. unsupported locale -> default locale;
2. localized root -> localized login.

### 13.2. Production-like поведение

Вход:

```text
Runtime URL: http://cybervpn-admin:3000/en-EN
Host: admin.cyber-vpn.net
X-Forwarded-Host: admin.cyber-vpn.net
X-Forwarded-Proto: https
X-Forwarded-Port: 443
```

Ожидается:

```text
https://admin.cyber-vpn.net/en-EN/login
```

### 13.3. Local behavior

Вход:

```text
http://localhost:3001/en-EN
```

Ожидается:

```text
http://localhost:3001/en-EN/login
```

Local port должен сохраняться.

### 13.4. Query policy

Сохранить существующее поведение:

- при root -> login query очищается;
- при unsupported locale remainder сохраняется;
- нельзя случайно переносить OAuth/2FA query в route, где раньше он очищался.

---

## 14. Изменение `partner/src/proxy.ts`

### 14.1. Redirect-ветки

Исправить URL construction для:

1. unsupported locale normalization;
2. retired legacy admin route;
3. portal localized root -> login;
4. storefront host + portal workspace route -> storefront root;
5. portal host + storefront public route -> portal login.

404-ветку не менять.

### 14.2. Portal production request

Вход:

```text
Runtime URL: http://cybervpn-partner:3000/en-EN
X-Forwarded-Host: partner.cyber-vpn.net
X-Forwarded-Proto: https
```

Ожидается:

```text
https://partner.cyber-vpn.net/en-EN/login
```

### 14.3. Storefront production request

Для configured storefront host:

```text
X-Forwarded-Host: storefront.cyber-vpn.net
```

redirect должен оставаться на его canonical storefront origin без `:3000`.

### 14.4. Custom storefront domains

Если custom domain официально присутствует в конфигурации storefront hosts:

- сохранить этот domain;
- использовать `https` в production;
- не добавлять внутренний port.

Если host не распознан:

- не отражать его напрямую;
- использовать `surfaceContext.canonicalHost`;
- не создавать open redirect;
- добавить тест на unknown host.

### 14.5. Local storefront

Должны продолжать работать:

```text
http://storefront.localhost:3002
http://portal.localhost:3002
http://localhost:3002
```

---

## 15. Тестирование URL helper

Создать unit tests для каждого фактически используемого helper или общий набор table-driven tests.

### 15.1. Положительные кейсы

1. Canonical origin не наследует runtime port.
2. Pathname сохраняется.
3. Query string сохраняется при `preserveSearch: true`.
4. Query очищается при `preserveSearch: false`.
5. `x-forwarded-host` с comma-separated chain берёт первое значение.
6. `x-forwarded-proto` с comma-separated chain берёт первое значение.
7. `https` + port `443` нормализуется без явного `:443`.
8. `http` + port `80` нормализуется без явного `:80`.
9. Localhost сохраняет нестандартный port.
10. `127.0.0.1` сохраняет нестандартный port.
11. Configured partner storefront host разрешён.
12. Unknown production host использует fallback/canonical host.

### 15.2. Негативные кейсы

Helper должен отклонять или безопасно fallback-ить:

```text
javascript://example.com
https://user:password@example.com
//evil.example/path
evil.example/path
example.com\r\nLocation: https://evil.example
example.com, evil.example
good.example@evil.example
```

Проверить, что первый comma-separated value обрабатывается только после строгой нормализации.

---

## 16. Frontend proxy tests

Обновить:

```text
frontend/src/__tests__/proxy.test.ts
```

### 16.1. Обязательный production-like fixture

```ts
function createProxiedRequest(
  path: string,
  options: {
    runtimeOrigin: string;
    externalHost: string;
    externalProto?: 'http' | 'https';
    externalPort?: string;
  },
): NextRequest;
```

Пример:

```ts
const request = new NextRequest(
  'http://cybervpn-frontend:3000/ru-RU/dashboard?tab=ops',
  {
    headers: {
      host: 'cyber-vpn.net',
      'x-forwarded-host': 'cyber-vpn.net',
      'x-forwarded-proto': 'https',
      'x-forwarded-port': '443',
    },
  },
);
```

### 16.2. Обязательные assertions

Для каждого production redirect:

```ts
expect(location).toBe(EXACT_EXPECTED_URL);
expect(location).not.toContain(':3000');
expect(location).not.toContain('localhost');
expect(location).not.toContain('127.0.0.1');
expect(location).not.toContain('cybervpn-frontend');
```

### 16.3. Исправление старых тестов

Тесты, ожидающие:

```text
https://my.cyber-vpn.net:9001/...
```

должны быть изменены.

Для production hostname нестандартный listener port переносить нельзя.

Отдельный local test может ожидать port только при local external host:

```text
http://localhost:9001/...
```

---

## 17. Admin proxy tests

Обновить:

```text
admin/src/__tests__/proxy.test.ts
```

Обязательные кейсы:

- internal runtime `cybervpn-admin:3000` + production forwarded headers;
- localized root;
- unsupported locale;
- search clearing;
- localhost:3001 сохраняется;
- malicious forwarded host не отражается;
- `Location` не содержит internal service name.

---

## 18. Partner proxy tests

Обновить:

```text
partner/src/__tests__/proxy.test.ts
```

Обязательные кейсы:

- internal runtime `cybervpn-partner:3000`;
- portal root -> portal login;
- configured storefront host;
- unknown storefront host -> canonical fallback;
- local `storefront.localhost:3002`;
- local `portal.localhost:3002`;
- legacy route search clearing;
- workspace/storefront route isolation;
- malicious forwarded host;
- отсутствие `:3000` в production `Location`.

---

## 19. UI tests для logout

Добавить тест рядом с `UserMenu` по принятой в проекте структуре.

Обязательные проверки:

1. `logout` вызывается один раз.
2. Повторный click во время pending не создаёт второй запрос.
3. Меню закрывается.
4. Кнопка disabled во время logout.
5. `queryClient.clear()` вызывается.
6. `window.location.replace()` вызывается с локализованным login.
7. `router.replace('/')` отсутствует.
8. `router.refresh()` отсутствует.
9. При reject выполняется безопасное логирование.
10. При reject в лог не попадают токены/PII.
11. После reject пользователь всё равно покидает protected UI.
12. Locale `ru-RU` и `en-EN` проверяются отдельно.

Для мокирования `window.location.replace` использовать безопасный test setup, совместимый с текущим Vitest/JSDOM.

---

## 20. UI tests для auth layout

Добавить server component/unit test либо вынести построение URL в чистую функцию и протестировать её.

Проверки:

```text
locale=ru-RU -> https://cyber-vpn.net/ru-RU
locale=en-EN -> https://cyber-vpn.net/en-EN
```

Проверить обе ссылки:

- `Back to home`;
- `CyberVPN home`.

Обе ссылки:

- не содержат `my.cyber-vpn.net`;
- не содержат `:3000`;
- не равны `/`.

---

## 21. Repository-wide аудит

Перед завершением задачи выполнить:

```powershell
git grep -n "request.nextUrl.clone()" -- frontend admin partner
git grep -n "NextResponse.redirect" -- frontend/src admin/src partner/src
git grep -n "router.replace('/')" -- frontend admin partner
git grep -n 'href="/"' -- frontend/src admin/src partner/src
git grep -n -E "localhost:(3000|3001|3002)|127\.0\.0\.1:(3000|3001|3002)" -- frontend/src admin/src partner/src
```

Каждое найденное совпадение классифицировать:

- production defect;
- safe local/test usage;
- documentation;
- infrastructure upstream;
- unrelated relative navigation.

Не заменять совпадения массово без анализа контекста.

### 21.1. Дополнительный аудит redirect constructors

Проверить:

```text
new URL(..., request.url)
new URL(..., request.nextUrl)
request.nextUrl.clone()
window.location.href
window.location.replace
router.push
router.replace
redirect()
permanentRedirect()
NextResponse.redirect()
```

Особое внимание:

- route handlers OAuth;
- 2FA handlers;
- global Axios 401 interceptor;
- auth guards;
- legacy route retirement;
- storefront surface routing.

---

## 22. Диагностическое логирование

### 22.1. Временный redirect debug

Допускается временное логирование только в local/staging и только за feature flag:

```text
REDIRECT_DEBUG=true
```

Пример:

```ts
if (process.env.REDIRECT_DEBUG === 'true') {
  console.log('[redirect-debug]', {
    runtimeOrigin: request.nextUrl.origin,
    host: request.headers.get('host'),
    forwardedHost: request.headers.get('x-forwarded-host'),
    forwardedProto: request.headers.get('x-forwarded-proto'),
    targetOrigin: target.origin,
    targetPathname: target.pathname,
  });

  console.trace('[redirect-debug] redirect construction trace');
}
```

### 22.2. Запрещено логировать

- cookies;
- Authorization;
- OAuth `code`;
- OAuth `state`;
- magic-link token;
- password reset token;
- полный query string;
- user identifiers;
- email;
- IP без существующей политики sanitization.

Перед production deploy debug flag должен быть выключен.

---

## 23. Проверка Caddy и proxy headers

Файл:

```text
infra/deploy/stage1/Caddyfile.stage1.snippet
```

Должен продолжать передавать:

```caddy
header_up Host {host}
header_up X-Forwarded-Host {host}
header_up X-Forwarded-Proto https
header_up X-Forwarded-Port 443
```

Внутренние upstream остаются:

```caddy
reverse_proxy cybervpn-frontend:3000
reverse_proxy cybervpn-admin:3000
reverse_proxy cybervpn-partner:3000
```

### 23.1. Запрещённое инфраструктурное исправление

Нельзя пытаться устранить bug заменой:

```text
cybervpn-frontend:3000
```

на публичный домен.

Это нарушит service discovery и не решит неправильное построение `Location`.

---

## 24. Команды проверки на Windows PowerShell

Корневые package scripts используют POSIX-форму `NODE_ENV=test`. В чистом PowerShell предпочтительно запускать Vitest напрямую.

### 24.1. Подготовка i18n

```powershell
npm run prepare:i18n -w frontend
npm run prepare:i18n -w admin
npm run prepare:i18n -w partner
```

### 24.2. Точечные frontend tests

```powershell
$env:NODE_ENV = "test"
npm exec --workspace frontend -- vitest run src/__tests__/proxy.test.ts
Remove-Item Env:NODE_ENV
```

### 24.3. Admin tests

```powershell
$env:NODE_ENV = "test"
npm exec --workspace admin -- vitest run src/__tests__/proxy.test.ts
Remove-Item Env:NODE_ENV
```

### 24.4. Partner tests

```powershell
$env:NODE_ENV = "test"
npm exec --workspace partner -- vitest run src/__tests__/proxy.test.ts
Remove-Item Env:NODE_ENV
```

### 24.5. Полные проверки

```powershell
npm run lint -w frontend
npm run lint -w admin
npm run lint -w partner

npm run build -w frontend
npm run build -w admin
npm run build -w partner
```

Для полного Vitest suite в PowerShell:

```powershell
$env:NODE_ENV = "test"
npm exec --workspace frontend -- vitest run
npm exec --workspace admin -- vitest run
npm exec --workspace partner -- vitest run
Remove-Item Env:NODE_ENV
```

---

## 25. Production/staging smoke tests

### 25.1. Проверка redirect headers через `curl.exe`

```powershell
curl.exe -sS -D - -o NUL --max-redirs 0 "https://cyber-vpn.net/ru-RU/dashboard?tab=ops"
curl.exe -sS -D - -o NUL --max-redirs 0 "https://my.cyber-vpn.net/"
curl.exe -sS -D - -o NUL --max-redirs 0 "https://my.cyber-vpn.net/ru-RU/pricing?currency=RUB"
curl.exe -sS -D - -o NUL --max-redirs 0 "https://admin.cyber-vpn.org/ru-RU/dashboard"
```

Ожидаемые `Location`:

```text
https://my.cyber-vpn.net/ru-RU/dashboard?tab=ops
https://my.cyber-vpn.net/en-EN/dashboard
https://cyber-vpn.net/ru-RU/pricing?currency=RUB
https://admin.cyber-vpn.net/ru-RU/dashboard
```

### 25.2. Автоматическая проверка запрещённых значений

```powershell
$urls = @(
  "https://cyber-vpn.net/ru-RU/dashboard?tab=ops",
  "https://my.cyber-vpn.net/",
  "https://my.cyber-vpn.net/ru-RU/pricing?currency=RUB",
  "https://admin.cyber-vpn.org/ru-RU/dashboard"
)

$forbiddenPattern = '(?i)(localhost|127\.0\.0\.1|cybervpn-(frontend|admin|partner)|:(3000|3001|3002)(?:/|$))'

foreach ($url in $urls) {
  $headers = curl.exe -sS -D - -o NUL --max-redirs 0 $url 2>&1
  $location = $headers | Select-String -Pattern '^Location:' -CaseSensitive:$false

  Write-Host "`n$url"
  Write-Host $location

  if ($location -match $forbiddenPattern) {
    throw "Internal origin or port leaked into redirect: $location"
  }
}
```

### 25.3. Полная redirect chain

```powershell
curl.exe -sS -L -D redirect-chain.txt -o NUL "https://cyber-vpn.net/ru-RU/dashboard"
Select-String -Path redirect-chain.txt -Pattern "^Location:" -CaseSensitive:$false
```

В цепочке не должно быть:

```text
:3000
:3001
:3002
localhost
127.0.0.1
cybervpn-frontend
cybervpn-admin
cybervpn-partner
```

---

## 26. Ручные browser scenarios

### 26.1. Customer logout

Для `ru-RU` и `en-EN`:

1. Авторизоваться в кабинете.
2. Открыть dropdown пользователя.
3. Нажать `Sign out`.
4. Убедиться, что запрос `/api/v1/auth/logout` отправлен один раз.
5. Убедиться, что запрос завершился до document navigation.
6. Проверить конечный URL:
   - `https://my.cyber-vpn.net/ru-RU/login`;
   - либо соответствующая фактическая внешняя auth surface без internal port.
7. Нажать Back.
8. Protected content не должен стать доступным.
9. Прямо открыть `/ru-RU/dashboard`.
10. AuthGuard должен вернуть на login.
11. В Application/Cookies проверить отсутствие auth cookies после успешного logout.

### 26.2. Back to home

Проверить на:

- login;
- register;
- forgot password;
- reset password;
- magic link;
- OAuth callback/error;
- verify;
- Telegram link.

На public и cabinet host, где route доступен.

Результат:

```text
https://cyber-vpn.net/{locale}
```

### 26.3. Logo

Повторить предыдущую проверку для центрального логотипа.

### 26.4. Partner

Проверить:

- portal root;
- storefront root;
- workspace route на storefront;
- storefront public route на portal;
- configured custom storefront domain;
- unknown host в безопасной тестовой среде.

### 26.5. Admin

Проверить:

- localized root;
- unsupported locale;
- login;
- logout;
- refresh после logout.

---

## 27. Security requirements

1. Не доверять произвольному `Host` для cross-domain target.
2. Не доверять произвольному `X-Forwarded-Host` без proxy boundary/allowlist.
3. Не допускать protocol injection.
4. Не допускать CRLF injection.
5. Не допускать URL credentials.
6. Не переносить OAuth query в debug logs.
7. Не переносить internal service names во внешний URL.
8. Не использовать query parameter как полный redirect origin.
9. Существующий `return_to`/`redirect` должен оставаться internal-path-only.
10. Redirect helper должен иметь unit tests на open redirect.
11. Partner custom domains должны проходить через конфигурацию или canonicalHost.
12. Logout должен реально очищать server cookies, а не только Zustand state.

---

## 28. Observability requirements

После deploy отслеживать:

- количество 3xx по frontend/admin/partner;
- рост redirect loops;
- 4xx/5xx на auth routes;
- ошибки `ERR_CONNECTION_REFUSED` на `:3000`;
- ошибки CSP/mixed content;
- logout failures;
- повторные session restore после logout;
- жалобы на custom partner domains;
- Sentry navigation errors.

Рекомендуется добавить отдельный synthetic probe, проверяющий `Location` на запрещённый pattern.

Пример правила:

```text
Fail if Location contains:
localhost
127.0.0.1
cybervpn-frontend
cybervpn-admin
cybervpn-partner
:3000
:3001
:3002
```

---

## 29. Порядок реализации

### Этап 1. Воспроизведение

- [ ] Зафиксировать текущие ошибочные `Location`.
- [ ] Сохранить curl/browser evidence.
- [ ] Проверить фактические `Host`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Forwarded-Port`.
- [ ] Убедиться, что internal runtime origin действительно содержит `:3000`.

### Этап 2. URL helper

- [ ] Создать helper.
- [ ] Добавить validation.
- [ ] Добавить unit tests.
- [ ] Проверить local и production-like режимы.

### Этап 3. Frontend proxy

- [ ] Переписать 4 redirect-ветки.
- [ ] Не менять route sets.
- [ ] Исправить proxy tests.
- [ ] Добавить malicious-host tests.

### Этап 4. Frontend auth navigation

- [ ] Переписать logout flow.
- [ ] Добавить pending state.
- [ ] Убрать переход на `/`.
- [ ] Убрать `router.refresh()`.
- [ ] Добавить UI tests.
- [ ] Проверить backend cookie clearing.

### Этап 5. Auth layout

- [ ] Исправить `back_to_home`.
- [ ] Исправить logo.
- [ ] Сохранить locale.
- [ ] Добавить tests.

### Этап 6. Admin proxy

- [ ] Переписать redirect URL construction.
- [ ] Добавить production-like tests.
- [ ] Сохранить local port.

### Этап 7. Partner proxy

- [ ] Переписать redirect URL construction.
- [ ] Учесть portal/storefront/canonicalHost.
- [ ] Добавить custom/unknown host tests.
- [ ] Сохранить local ports.

### Этап 8. Полный аудит

- [ ] Выполнить `git grep`.
- [ ] Классифицировать совпадения.
- [ ] Проверить OAuth/2FA redirects.
- [ ] Проверить глобальную 401-навигацию.
- [ ] Проверить отсутствие новых absolute localhost URLs.

### Этап 9. CI и build

- [ ] Frontend lint/test/build.
- [ ] Admin lint/test/build.
- [ ] Partner lint/test/build.
- [ ] Backend logout tests при необходимости.
- [ ] Production-like smoke.

### Этап 10. Deploy и приёмка

- [ ] Deploy всех изменённых Next.js images.
- [ ] Проверить redirect headers.
- [ ] Проверить browser flows.
- [ ] Проверить Sentry/logs.
- [ ] Зафиксировать evidence.

---

## 30. Критерии приёмки

### AC-01

Ни один production `Location` не содержит:

```text
:3000
:3001
:3002
localhost
127.0.0.1
cybervpn-frontend
cybervpn-admin
cybervpn-partner
```

### AC-02

Переход:

```text
https://cyber-vpn.net/ru-RU/dashboard
```

возвращает:

```text
Location: https://my.cyber-vpn.net/ru-RU/dashboard
```

### AC-03

Переход:

```text
https://my.cyber-vpn.net/ru-RU/pricing
```

возвращает:

```text
Location: https://cyber-vpn.net/ru-RU/pricing
```

### AC-04

Корень кабинета ведёт на localized dashboard без internal port.

### AC-05

Admin localized root ведёт на localized login без internal port.

### AC-06

Partner portal/storefront redirects не содержат internal port.

### AC-07

Local development продолжает работать на своих портах.

### AC-08

Logout:

- вызывает server endpoint;
- не вызывает переход на `/`;
- не вызывает `router.refresh()`;
- приводит на localized login;
- не создаёт duplicate request;
- очищает client cache;
- после успешного ответа удаляет auth cookies.

### AC-09

Back browser после logout не восстанавливает доступ к protected UI.

### AC-10

`back_to_home` с любой auth-страницы ведёт на:

```text
https://cyber-vpn.net/{locale}
```

### AC-11

Logo на auth-странице ведёт на тот же public localized home.

### AC-12

Query string сохраняется только в тех redirect-ветках, где он сохранялся до исправления.

### AC-13

Все новые негативные security tests проходят.

### AC-14

Frontend/admin/partner lint, tests и build проходят.

### AC-15

Внутренние Caddy upstream `:3000` не удалены и продолжают работать.

---

## 31. Definition of Done

Задача считается завершённой, когда:

- [ ] Код соответствует этому ТЗ.
- [ ] Все обязательные файлы обработаны.
- [ ] Нет unsafe partial mutation `request.nextUrl` в рассматриваемых redirect-ветках.
- [ ] Добавлен reusable URL helper.
- [ ] Добавлена защита от Host Header Injection/open redirect.
- [ ] Исправлен logout.
- [ ] Исправлены `back_to_home` и logo.
- [ ] Исправлены frontend tests.
- [ ] Добавлены admin production-like tests.
- [ ] Добавлены partner production-like tests.
- [ ] Выполнен repository-wide audit.
- [ ] Существующие закомментированные строки кода не удалены без причины.
- [ ] Все diagnostics очищены либо выключены feature flag.
- [ ] Создано QA evidence с HTTP headers и browser screenshots.
- [ ] Production smoke не обнаруживает `:3000/3001/3002`.
- [ ] Rollback plan проверен.
- [ ] Code review отдельно проверил security и partner custom domains.

---

## 32. Rollback plan

Rollback требуется при:

- redirect loop;
- неверной locale;
- недоступности login;
- поломке custom storefront domains;
- logout, оставляющем пользователя в protected UI;
- ошибках build/runtime;
- росте auth 4xx/5xx.

Порядок:

1. Вернуть предыдущие images frontend/admin/partner.
2. Не изменять Caddy upstream.
3. Повторить smoke старой версии.
4. Сохранить проблемные headers и logs.
5. Исправить helper/tests до повторного deploy.

Нельзя выполнять частичный rollback только одного приложения, если общий routing contract уже изменён и зависит от согласованной версии других surfaces.

---

## 33. Рекомендованная структура commit history

1. `test(routing): add production-like redirect regression coverage`
2. `fix(frontend): build canonical redirects without internal listener ports`
3. `fix(auth): make logout deterministic and locale-aware`
4. `fix(auth): route auth home links to canonical public origin`
5. `fix(admin): sanitize proxy redirect origins`
6. `fix(partner): preserve canonical surface origins in proxy redirects`
7. `test(routing): add host-injection and custom-domain coverage`
8. `docs(qa): record redirect and logout verification evidence`

Перед merge допускается squash согласно принятой политике репозитория.

---

## 34. Финальная проверочная матрица

| Surface | Scenario | Expected host | Expected port |
|---|---|---:|---:|
| Public | dashboard route | `my.cyber-vpn.net` | none |
| Public www | settings route | `my.cyber-vpn.net` | none |
| Cabinet | root | `my.cyber-vpn.net` | none |
| Cabinet | pricing | `cyber-vpn.net` | none |
| Auth on cabinet | back_to_home | `cyber-vpn.net` | none |
| Auth on cabinet | logo | `cyber-vpn.net` | none |
| Customer | logout | current external auth host | none |
| Admin mirror | any route | `admin.cyber-vpn.net` | none |
| Admin | localized root | configured admin host | none |
| Partner portal | localized root | configured portal host | none |
| Partner storefront | workspace route | canonical storefront host | none |
| Local frontend | root/navigation | `localhost` | local port allowed |
| Local admin | root/navigation | `localhost` | `3001` allowed |
| Local partner | root/navigation | local partner host | `3002/3004` allowed |

---

## 35. Итоговое техническое решение

Ключевой результат задачи:

- internal listener URL используется только для внутренней обработки запроса;
- browser-facing URL всегда строится заново из доверенного external/canonical origin;
- cross-domain navigation имеет явный target;
- logout имеет детерминированный порядок операций;
- local dev ports сохраняются только в local environment;
- тесты моделируют реальный reverse proxy, а не только прямой localhost request.
