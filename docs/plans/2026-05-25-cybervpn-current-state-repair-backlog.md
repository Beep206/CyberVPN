# CyberVPN current-state repair backlog

Дата: 2026-05-25

Цель документа: зафиксировать текущие дефекты S2/S3 runtime и разбить их на стабильные порядковые задачи `FIX-XXX`, которые выполняются до следующего production deploy. После закрытия всех `FIX` делаем один контролируемый деплой и smoke-проверку.

## Рабочие правила

1. Перед любыми production DB-изменениями делаем короткий redacted snapshot/evidence.
2. Пользовательские тестовые аккаунты можно чистить только явно перечисленные в этом документе.
3. Сначала закрываются security/auth/runtime blockers, затем UI/SEO, затем финальная проверка.
4. GitLab остаётся first remote, GitHub mirror. Пуш после фиксов: сначала GitLab `main`, затем GitHub `main`.
5. Deploy выполняется только после прохождения всего списка или отдельного owner approval на частичный hotfix.
6. Секреты, токены, 2FA seed, SMTP/API keys и admin-реквизиты в этот документ не записываются.

## Batch status

| Batch | Status | Evidence |
|---|---|---|
| Batch A: `FIX-001` - `FIX-005` | Completed | `docs/evidence/releases/current-state-fix-batch-a-20260525.md` |
| Batch B: `FIX-006` - `FIX-018` | Completed | `docs/evidence/releases/fix-batch-b-20260525T185152Z.md` |
| Batch C: `FIX-019` - `FIX-032` | Completed | `docs/evidence/releases/fix-batch-c-20260525T204632Z.md` |

## Порядок выполнения

| ID | Блок | Что исправляем | Где искать | Acceptance evidence |
|---|---|---|---|---|
| FIX-001 | Preflight | Сделать production evidence перед ремонтом: git SHA, compose status, DB backup marker, текущие user/subscription snapshots по тестовым аккаунтам без секретов. | prod-app-1, PostgreSQL, docs/evidence | Есть redacted evidence до мутаций. |
| FIX-002 | Test data | Удалить или полностью освободить `veephtc@gmail.com`, чтобы можно было повторно пройти регистрацию с email verification. | backend DB: users/auth identities/OTP/sessions | Повторная регистрация не получает `Username already exists`. |
| FIX-003 | Test data | Обновить `@Sasha_Beep`: активная 2 GB trial-подписка, инвайты доступны для повторной проверки. | backend DB, subscriptions, invites, Remnawave user mapping | В Mini App/боте видна активная trial-подписка и свежие инвайты. |
| FIX-004 | Test data | Убрать активную подписку у `@Sasha_Beep_KZ`, чтобы повторить invite redemption flow. | backend DB, subscriptions, entitlements | Пользователь снова может получить доступ через invite code. |
| FIX-005 | Test data | Сохранить короткий after-reset snapshot без PII сверх handle/email из задачи. | docs/evidence | Видно, что reset выполнен и не затронул посторонних пользователей. |
| FIX-006 | Domain | Подготовить `my.cyber-vpn.net` как канонический домен личного кабинета. | Cloudflare DNS/TLS, app ingress | `https://my.cyber-vpn.net` открывает cabinet без TLS/redirect ошибок. |
| FIX-007 | Domain | Развести route contract: публичный сайт на `cyber-vpn.net`, личный кабинет на `my.cyber-vpn.net`, API cookies/sessions работают корректно между доменами. | frontend routing, backend CORS/cookie settings, nginx/Caddy | Авторизация не теряется при переходе в личный кабинет. |
| FIX-008 | Domain | Добавить redirect policy для старых dashboard/profile/settings routes с `cyber-vpn.net` на `my.cyber-vpn.net`, где это безопасно. | frontend proxy/edge config | Старые ссылки не ломаются, но пользователь оказывается в cabinet domain. |
| FIX-009 | Public header | Если пользователь авторизован, заменить `Войти/Создать аккаунт` на user profile dropdown и кнопку уведомлений. | `frontend/src/widgets/public-terminal-header-controls.tsx`, `frontend/src/features/header/user-menu.tsx` | Header публичных страниц показывает профиль авторизованному пользователю. |
| FIX-010 | Notifications | Кнопка уведомлений видна рядом с профилем, но в S2/S3 пока disabled/read-only без mock-уведомлений. | `frontend/src/features/notifications/notification-dropdown.tsx` | Нет фейковых `System Logs`, кнопка не вводит в заблуждение. |
| FIX-011 | Theme | Починить светлую тему на `download`, `features`, `pricing`, `network` и остальных marketing routes. | `frontend/src/app/[locale]/(marketing)`, shared UI/theme CSS | В светлой теме нет чёрных прямоугольников, нечитаемого текста и мерцания. |
| FIX-012 | Telegram links | Заменить все ссылки/упоминания Telegram bot на `https://t.me/C_y_b_e_r_VPN_Bot`. | frontend/admin/messages/docs grep по `CyberVPN_Bot`, `t.me/` | Все CTA ведут на правильного бота. |
| FIX-013 | Home SEO | Переделать секцию `GLOBAL MONITORED NETWORK`: дать полезную SEO/пользовательскую информацию о VLESS Reality, XHTTP, Germany node, мониторинге доступности, privacy posture без технического мусора. | landing widgets/messages | Секция стала полезной и индексируемой, без пустого decorative copy. |
| FIX-014 | Currency UI | Рядом с выбором языка добавить selector валюты в модальном окне. | `LanguageSelector` или новый `CurrencySelector` | Пользователь может явно выбрать валюту из header. |
| FIX-015 | Currency detection | Для нового пользователя определять язык и валюту по locale/browser. Сейчас в проекте 39 локалей, включая `zh-Hant`. | `frontend/src/i18n/config.ts`, middleware/proxy/client preference | Первый визит получает разумную locale/currency пару. |
| FIX-016 | Currency persistence | Если пользователь меняет валюту, сохранять её постоянно в браузере. | localStorage/cookie preference layer | После reload/новой сессии выбранная валюта сохраняется. |
| FIX-017 | Pricing currency | Показывать цены на `/pricing` и duplicated pricing blocks в выбранной/определённой валюте. | pricing catalog/widgets/messages | `pricing` меняет валюту без смены языка и без payment contract breakage. |
| FIX-018 | Remnawave notifications | Восстановить production Remnawave Telegram notifications в `CryptoVPN_Notification` (`Chat ID: -1003864406389`) для panel/node events. | Remnawave env/admin config, Telegram bot token/config | В группе приходят события `panel_started`, node created/restored/down без секретов. |
| FIX-019 | Mobile menu | Добавить левую header-кнопку menu icon с dropdown/drawer для мобильных устройств. В меню только важные пункты: главная, цены, скачать, сеть, помощь, кабинет. | public header/navigation components | Mobile navigation доступна одной кнопкой и не перегружена. |
| FIX-020 | Desktop menu | Для desktop оставить верхнее меню только с важными public links: цены, скачать, сеть, возможности/помощь. | public header/navigation components | Header на desktop не перегружен и не конфликтует с profile/currency/language. |
| FIX-021 | Home pricing | На главной после hero-блока `PUBLIC VPN ACCESS. POWERED BY VLESS REALITY` продублировать pricing block из `/pricing`. | marketing home/pricing widgets | Пользователь видит тарифы до глубокого scroll и может перейти к checkout. |
| FIX-022 | Register performance | Убрать лаг 3D-сцены при focus password на `/register`, не меняя визуально саму анимацию. | auth layout, 3D scene boundary, `CyberInput` | Focus в поле пароля не вызывает заметный FPS drop. |
| FIX-023 | OAuth layout | Не выделять Telegram отдельно. Сделать 3 равные кнопки в один ряд: Google, GitHub, Telegram. | `SocialAuthButtons.tsx` | Порядок и визуальный вес: Google, GitHub, Telegram. |
| FIX-024 | Register spacing | Добавить нормальный отступ над label `Email адрес`, чтобы он не прилипал к OAuth-кнопкам. | register page/Auth components | Форма выглядит компактно, но без визуальных слипаний. |
| FIX-025 | Email validation | Добавить современную email validation: native browser hints, server-side source of truth, trim spaces, понятная ошибка после blur/input. Не использовать чрезмерно строгий regex. | auth frontend + backend validation if needed | Неверный email показывает понятную ошибку до submit; валидные реальные адреса не режутся. |
| FIX-026 | Password validation | Улучшить password validation в регистрации: live feedback, minimum length policy, предупреждение о русском layout/кириллице, запрет submit при нарушении policy. | auth frontend/backend schemas | Пользователь сразу понимает, почему пароль не подходит. |
| FIX-027 | Change password validation | Применить ту же password policy и UX к смене пароля в кабинете. | `ChangePasswordModal.tsx`, backend security API | Регистрация и смена пароля ведут себя одинаково. |
| FIX-028 | Register compact legal | Сделать блок согласий компактнее: Terms/Privacy и marketing consent без огромных вертикальных отступов. | register page/Auth components/messages | Соглашения занимают меньше места, кликабельность не потеряна. |
| FIX-029 | Register compact footer | Сделать компактнее отступ между `Создать аккаунт` и `Уже есть аккаунт? Войти`. | register page/Auth components | Auth card стал ниже без потери читаемости. |
| FIX-030 | OTP delivery report | Зафиксировать текущий OTP delivery contract: production initial OTP через Resend, resend через Brevo только если настроен, иначе Resend; local dev через 3 SMTP/Mailpit сервера. Проверить runtime env. | `services/task-worker/src/tasks/email/send_otp.py`, prod env | Документально понятно, какие провайдеры реально используются сейчас. |
| FIX-031 | OTP UX/performance | На OTP-странице сразу фокусировать первое поле и убрать лаг 3D-сцены при focus OTP. | `OtpVerificationForm.tsx`, `CyberOtpInput.tsx`, auth layout | OTP field активен сразу; focus не просаживает 3D. |
| FIX-032 | Email activation link | В email verification письме добавить ссылку активации аккаунта, кроме кода OTP. Backend/frontend должны поддерживать переход по ссылке. | backend auth registration/email dispatcher/task-worker template/frontend route | Аккаунт можно подтвердить и кодом, и ссылкой из письма. |
| FIX-033 | S2 cabinet completeness | Проверить и довести S2-функции в личном кабинете: referral link, promo code redeem, gift code/purchase entrypoint, trial activation, renewal/autoprolongation status/cancel где включено. | customer cabinet, subscriptions, referral, wallet, settings | В кабинете доступны все S2 commerce/growth actions, которые включены в runtime flags. |
| FIX-034 | Partial data UX | Прояснить блок `ЧАСТИЧНЫЕ ДАННЫЕ`: сейчас это означает, что часть React Query ресурсов кабинета упала и UI показывает деградированный snapshot. Сделать список failed resources и понятный retry. | `CustomerCabinetDashboard.tsx`, `dashboard.json` | Пользователь видит, какие ресурсы не загрузились, а не просто число `6`. |
| FIX-035 | Logout | Исправить logout: после `Sign Out` auth state, query cache, cookies/session status должны сбрасываться сразу. | auth store, API logout, query client, route guards | Пользователь выходит мгновенно, без минуты активной сессии в UI. |
| FIX-036 | 2FA enforcement | После включения 2FA следующий login обязан требовать TOTP. Проверить email/password, Telegram, bot link, magic link/OAuth. | backend auth use cases, frontend 2FA pending route | 2FA нельзя обойти ни одним auth flow. |
| FIX-037 | Settings language | В настройках кабинета язык должен быть dropdown/select, а не свободный ввод. | settings cabinet/profile preferences | Выбор языка валиден и соответствует `locales`. |
| FIX-038 | Settings timezone | В настройках кабинета часовой пояс должен быть dropdown/select по IANA timezone list. | settings cabinet/profile preferences | Нельзя сохранить невалидный timezone. |
| FIX-039 | Telegram external account flow | Починить `telegram-link`: `Я подтвердил вход в Telegram` должен проверять статус magic link, `Попробовать снова` должен запускать новый flow, linking не должен терять сессию. | `telegram-link-client.tsx`, oauth Telegram magic link endpoints, bot handler | Пользователь может привязать Telegram из кабинета без ошибки восстановления сессии. |
| FIX-040 | 2FA recovery flow | Описать и при необходимости реализовать recovery: backup codes, regenerate codes after reauth, support-assisted reset only with audit and identity verification. | 2FA backend/frontend/support docs | Пользователь понимает, что делать при потере 2FA; support не сбрасывает 2FA без audit. |
| FIX-041 | Admin customers access | Починить admin bug: `owner-admin@cyber-vpn.net` с 2FA не должен вылетать из раздела клиенты с `Доступ запрещён. Требуется аккаунт администратора.` | admin RBAC/session guard, backend admin dependencies, token realm | Owner/admin открывает клиентов, API возвращает 200, audit фиксирует доступ. |
| FIX-042 | Admin auth performance | Убрать лаг 3D-сцены при focus email/password в admin login, не меняя визуально фон. | admin auth components/layout | Поля admin login вводятся без FPS drop. |
| FIX-043 | Test pack | Добавить/обновить тесты на email/password validation, OTP link, 2FA enforcement, logout, Telegram linking, currency preference, public header auth state. | frontend/backend/admin tests | Локально проходит targeted test pack. |
| FIX-044 | Build and scan | Прогнать build/lint/typecheck для изменённых workspaces, проверить bundle/env scan на отсутствие секретов. | frontend/admin/backend/task-worker | Build green, секреты не попали в клиентский bundle. |
| FIX-045 | Deploy and smoke | После всех FIX: push GitLab -> GitHub, deploy production, smoke checklist по public site, `my`, registration, OTP email, Telegram bot, cabinet, admin customers, Remnawave notifications. | prod-app-1, Cloudflare, GitLab/GitHub | Production smoke green, evidence сохранён. |

## Best-practice decisions for validation

### Email

Для email validation не используем один “идеальный” regex. Правильный contract:

- frontend: `type="email"`, `inputMode="email"`, trim пробелов, понятная ошибка после blur/input;
- backend: нормализует и валидирует синтаксис, проверяет уникальность с учётом незавершённой регистрации;
- реальное владение адресом подтверждается OTP или activation link;
- если пользователь уже существует, но не завершил verification, flow должен вести в resend/OTP, а не блокировать тупым `Username already exists`.

### Password

Password UX должен быть строгим там, где это полезно, но не ломать password managers:

- разрешаем paste/autofill/password managers;
- предупреждаем о русской раскладке/кириллице сразу;
- если CyberVPN выбирает ASCII-only policy, submit блокируется понятной причиной, а ввод не “съедается” молча;
- minimum length и backend policy являются источником истины;
- одна и та же policy используется в регистрации и смене пароля;
- 2FA не является заменой сильного пароля, а дополнительным фактором.

Источники для реализации:

- NIST SP 800-63B-4: https://pages.nist.gov/800-63-4/sp800-63b.html
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP Input Validation Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- MDN Constraint Validation: https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Constraint_validation

## Объяснение спорных текущих состояний

### `ЧАСТИЧНЫЕ ДАННЫЕ`

Сейчас личный кабинет агрегирует несколько backend resources через независимые React Query запросы: profile, entitlement, usage, wallet, referral, notification counters, notification list, service state, trial. Если часть запросов падает, UI не скрывает весь кабинет, а показывает degraded snapshot. Это правильно по устойчивости, но плохо объяснено пользователю. `FIX-034` должен показать конкретные failed resources и retry по каждому/всем.

### OTP delivery сейчас

По коду task-worker:

- production initial OTP: Resend;
- production resend OTP: Brevo, если `BREVO_API_KEY` настроен; иначе fallback на Resend;
- local/dev mode: SMTP через Mailpit cluster, по умолчанию 3 SMTP endpoint;
- magic link письма уже поддерживаются отдельной задачей, но registration verification letter должен явно получить activation link в `FIX-032`.

Runtime env на production нужно подтвердить в `FIX-030`, не выводя API keys в evidence.

### 2FA recovery

Безопасный recovery flow не должен быть “напишите в поддержку, и мы выключим 2FA”. Нужны backup codes или support-assisted reset с проверкой личности, owner/operator approval и audit log. Если backup codes уже частично есть в UI, нужно проверить, что они реально сохраняются, одноразово показываются и принимаются backend.

## Рекомендуемые батчи

1. Batch A: `FIX-001` - `FIX-005` production test data reset.
2. Batch B: `FIX-006` - `FIX-018` public site/domain/header/theme/currency/notifications.
3. Batch C: `FIX-019` - `FIX-032` auth, registration, OTP, password, 3D performance.
4. Batch D: `FIX-033` - `FIX-040` user cabinet S2 completeness, logout, 2FA, Telegram linking.
5. Batch E: `FIX-041` - `FIX-042` admin access and admin auth performance.
6. Batch F: `FIX-043` - `FIX-045` tests, build, push, deploy, smoke.

## Launch blocker classification

Hard blockers before deploy:

- `FIX-002` because registration retest is blocked.
- `FIX-006` - `FIX-008` because cabinet domain changes affect auth/session safety.
- `FIX-025` - `FIX-032` because registration/email/OTP are public release critical.
- `FIX-035` - `FIX-036` because logout and 2FA enforcement are security-critical.
- `FIX-041` because admin customer operations are required for support.

Can ship in the same deploy but not as independent blockers:

- `FIX-013`, `FIX-016`, `FIX-017`, `FIX-019`, `FIX-020`, `FIX-021`, `FIX-034`.

Do not deploy until `FIX-043` - `FIX-045` are completed or explicitly waived by owner.
