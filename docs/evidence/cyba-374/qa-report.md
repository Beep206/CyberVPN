# CYBA-374 QA report: important notifications

Среда: local workspace `ai/cyba-244/w15-final-package`, commit `0b509f6`, `2026-06-01` UTC.

Итог после retest: **PASS**.

Первичный прогон CYBA-374 был **FAIL** из-за mobile visual blocker: `NotificationCenterDropdown` на `390x844` уходил за левый край viewport и обрезал important notification title/body. Блокер был вынесен в `CYBA-385`; после завершения `CYBA-385` выполнен focused retest customer notification UI.

## Проверенный Scope

- Backend REST contracts для customer/admin notifications: recipient scoping, dismiss/read/sync, realtime fallback и rate-limit buckets.
- Customer notification dropdown на desktop/mobile с synthetic authenticated state и mocked `/api/v1` data.
- Admin broadcast operations: desktop preview и support-role read-only state.
- Task-worker durable outbox fanout: duplicate/idempotent processing, retry/dead-letter path.
- Retest после `CYBA-385`: customer mobile notification viewport clipping regression и сохранение desktop behavior.

Production deploy, production secrets, production customer/payment data, external Telegram/email/FCM/APNs delivery, VPN provisioning и Remnawave adapters не использовались.

Context7 docs checked: N/A — QA verification only; no code/config/library behavior was changed.

## Выполненные команды

- `REMNAWAVE_TOKEN=local-remnawave-token REMNAWAVE_API_TOKEN=local-remnawave-token CRYPTOBOT_TOKEN=local-cryptobot-token JWT_SECRET=0123456789abcdef0123456789abcdef .venv/bin/python -m pytest --no-cov tests/integration/test_messaging_api.py tests/security/test_stage1_rate_limit_policy.py tests/unit/infrastructure/test_messaging_realtime_gateway.py -q` in `backend` -> `52 passed in 30.34s`.
- `NODE_ENV=test ../node_modules/.bin/vitest run src/lib/api/__tests__/messaging.test.ts src/features/messaging/components/__tests__/CustomerMessagingClient.test.tsx` in `frontend` -> `2 files / 12 tests passed`.
- `NODE_ENV=test ../node_modules/.bin/vitest run src/lib/api/__tests__/messaging-admin.test.ts src/shared/lib/__tests__/admin-rbac.test.ts src/features/messaging/components/__tests__/messaging-console.test.tsx` in `admin` -> failed because direct runner skipped jest-dom setup (`Invalid Chai property: toBeInTheDocument`); rerun with workspace script below passed.
- `npm run test:run -w admin -- src/lib/api/__tests__/messaging-admin.test.ts src/shared/lib/__tests__/admin-rbac.test.ts src/features/messaging/components/__tests__/messaging-console.test.tsx` -> `3 files / 15 tests passed`.
- `REMNAWAVE_API_TOKEN=test-token .venv/bin/python -m pytest --no-cov tests/unit/tasks/test_messaging_outbox.py -q` in `services/task-worker` -> `5 passed in 1.08s`.
- `env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 npm run dev -w frontend` и `env NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 PORT=9101 npm run dev -w admin` для browser evidence.
- Inline Playwright smoke against `http://localhost:9001/en-EN/messages` and `http://localhost:9101/en-EN/messaging` with `DEV_BYPASS_AUTH=true` and synthetic route mocks for auth, capabilities, notifications, conversations, realtime sync, and admin broadcast operations -> screenshots saved.
- Retest after `CYBA-385`: `npm run test:run -w frontend -- src/features/messaging/components/__tests__/CustomerMessagingClient.test.tsx` -> `1 file / 6 tests passed`.
- Retest after `CYBA-385`: `NEXT_TELEMETRY_DISABLED=1 DEV_BYPASS_AUTH=true nohup npm run dev -w frontend > /tmp/cyba-374-frontend.log 2>&1 &` и inline Playwright against `http://localhost:9001/en-EN/messages` at `390x844` and `1440x900` with synthetic notification/realtime fallback mocks -> screenshots saved.

## Артефакты

- `docs/evidence/cyba-374/screenshots/customer-notification-desktop.png`
- `docs/evidence/cyba-374/screenshots/customer-notification-mobile.png`
- `docs/evidence/cyba-374/screenshots/admin-broadcast-preview-desktop.png`
- `docs/evidence/cyba-374/screenshots/admin-broadcast-support-readonly-mobile.png`
- `docs/evidence/cyba-374/screenshots/customer-notification-mobile-retest.png`
- `docs/evidence/cyba-374/screenshots/customer-notification-desktop-retest.png`

## Ожидаемое vs фактическое

Ожидалось:

- Customer notification dropdown полностью остаётся внутри desktop и mobile viewport.
- Notification title/body, severity, read/dismiss controls, refresh/open actions остаются видимыми и доступными для tap/click.
- Admin broadcast panel позволяет admin preview explicit-recipient campaign и показывает recipient count.
- Support role может просматривать messaging, но не может создавать notification broadcasts.
- REST/realtime/worker/security paths проходят focused regression checks.

Фактически:

- Backend, admin tests, frontend component/API tests, worker tests и admin browser smoke прошли.
- Initial customer desktop dropdown был usable.
- Initial customer mobile dropdown был clipped off left edge of viewport; это заблокировало release QA и было отправлено в `CYBA-385`.
- Retest after `CYBA-385` passed on `390x844`: dialog box `x=16`, `width=358`, right edge `374 <= 390`; title, body, mark-read control и dismiss control внутри viewport.
- Retest after `CYBA-385` passed on `1440x900`: dialog box `x=544.140625`, `width=384`, right edge `928.140625 <= 1440`; title, body, mark-read control и dismiss control внутри viewport.

## Дефекты

- `CYBA-385` исправил mobile viewport clipping blocker. Focused retest подтверждает, что дефект resolved.
- Новых blocking defects в этом retest не найдено.

## Остаточный риск

- Browser tests использовали synthetic route mocks и development auth bypass; они подтверждают UI behavior без production data, но не заменяют проверку full deployed environment.
- Full workspace build/typecheck не перезапускался во время retest, потому что heartbeat использовал smallest focused verification для закрытого blocker.
- Browser retest logged local `403` responses from `/api/analytics/web-vitals` and `/api/analytics/traffic`; notification, conversations, capabilities, customer-subscriptions и realtime fallback mocks завершились успешно, а analytics responses не повлияли на verified notification UI.
