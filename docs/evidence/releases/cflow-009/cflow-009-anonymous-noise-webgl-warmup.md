# CFLOW-009 — Anonymous Console/API Noise Cleanup + Auth First-Focus WebGL Warm-Up

Дата: 2026-05-29  
Scope: frontend/customer web, Mini App public runtime telemetry, auth 3D scene.

## Цель

Убрать лишний браузерный шум для анонимных пользователей и снизить риск первого лага при фокусе на auth-полях без изменения основного auth-контракта защищённых страниц.

## Baseline

Production probe до фикса показал:

- Public pages: видимые `401 /api/v1/auth/session` и последующий `401 /api/v1/auth/refresh` для гостей.
- `my.cyber-vpn.net` auth/Mini App pages: `403 /api/analytics/web-vitals` и `403 /api/analytics/traffic`.
- `/ru-RU/features`: `500 /scanlines.svg`.
- Auth focus probe: исходный selector не находил поле из-за отсутствия `name="email"` на актуальных auth inputs; warm-up guard проверен статически и будет перепроверен post-deploy.

## Изменения

- Добавлен `GET /api/auth/optional-session`:
  - серверно проверяет backend session по cookies;
  - для гостя возвращает `200 null`, не показывая браузеру backend `401`;
  - использует `connection()` для demand runtime в Next.js Cache Components режиме;
  - сохраняет `Cache-Control: no-store`.
- `AuthSessionBootstrap` переведён на optional-session route:
  - guest public pages больше не запускают refresh-loop;
  - authenticated user по-прежнему восстанавливается в Zustand store;
  - OAuth result analytics сохраняется только если user реально восстановлен.
- Analytics origin-check вынесен в общий allowlist:
  - разрешены `cyber-vpn.net`, `my.cyber-vpn.net`, `admin.cyber-vpn.net`, `partner.cyber-vpn.net`, `.org` node/subscription domain и local dev origins;
  - foreign origin остаётся `403`.
- Добавлен `frontend/public/scanlines.svg`.
- Auth 3D scene:
  - сохранён `frameloop="demand"` на время фокуса input/select/textarea;
  - добавлен pre-warm через `useThree().invalidate()` на первые 2 RAF после фокуса;
  - добавлены `pointerdown`/`Tab` listeners, чтобы переключать режим до/сразу после первого фокуса.

## Локальная верификация

- `npm run test:run --workspace frontend -- src/app/api/analytics/web-vitals/route.test.ts src/app/api/analytics/traffic/route.test.ts src/app/api/analytics/miniapp-runtime/route.test.ts src/app/api/analytics/reporting/route.test.ts src/app/api/auth/optional-session/route.test.ts src/3d/__tests__/performance-baseline.test.ts`  
  Result: 6 files passed, 27 tests passed.
- `npm run lint --workspace frontend`  
  Result: passed.
- `npm run build --workspace frontend`  
  Result: passed; `/api/auth/optional-session` is dynamic on demand.
- `git diff --check`  
  Result: passed.
- `npm audit --audit-level=high --workspace frontend`  
  Result: passed for high/critical threshold. Current audit output still reports known moderate `next/postcss` advisory where suggested auto-fix would downgrade Next.js, so no downgrade was applied.
- Static changed-file scan for obvious secret/dangerous browser patterns  
  Result: no findings.

## Post-Deploy Smoke

Заполнить после production deploy:

- `https://cyber-vpn.net/ru-RU`: no visible anonymous `401 /auth/session` + `401 /auth/refresh`.
- `https://cyber-vpn.net/ru-RU/pricing`: no visible anonymous auth refresh noise.
- `https://cyber-vpn.net/ru-RU/features`: no `500 /scanlines.svg`.
- `https://my.cyber-vpn.net/ru-RU/login`: no `403 /api/analytics/*`.
- `https://my.cyber-vpn.net/ru-RU/register`: no `403 /api/analytics/*`.
- `https://my.cyber-vpn.net/ru-RU/miniapp/home`: no analytics `403`; Mini App viewport remains usable.
- Auth first focus: no obvious user-visible WebGL hitch on first email/password/OTP focus.

## Residual Risk

- Browser/headless WebGL may still print software-renderer warnings in CI/headless; this is not customer runtime API noise.
- Optional session intentionally does not replace protected-page session enforcement; dashboard/customer API auth still relies on backend auth endpoints.
