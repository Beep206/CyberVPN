# CyberVPN Monorepo: ответы на discovery-вопросы по Sentry

Ниже ответы только по тому, что удалось подтвердить по реальному коду, конфигам, workflow и документации в репозитории. Если в репозитории нет надёжного подтверждения, я пишу `не знаю`.

## 1. Организация Sentry и governance

1. **Вопрос:** Где будет жить Sentry: Sentry Cloud или self-hosted?
   **Ответ:** self-hosted

2. **Вопрос:** Уже есть готовая Sentry organization, или её ещё нужно создавать?
   **Ответ:** не знаю.

3. **Вопрос:** Кто будет org owner/admin с правом управлять проектами, токенами и alerting?
   **Ответ:** не знаю.

4. **Вопрос:** Нужны ли отдельные teams внутри Sentry: web, backend, mobile, desktop, platform/control-plane?
   **Ответ:** не знаю.

5. **Вопрос:** Есть ли требования по data residency, например только EU?
   **Ответ:** не знаю.

6. **Вопрос:** Нужны ли сразу интеграции со Slack, Telegram, Jira, GitHub, PagerDuty или стартуем минимально?
   **Ответ:** не знаю.

7. **Вопрос:** Есть ли ограничения по количеству Sentry projects, budgets, quotas, replay volume, tracing volume?
   **Ответ:** не знаю.

8. **Вопрос:** Кто будет отвечать за lifecycle secrets: `SENTRY_AUTH_TOKEN`, DSN, org/project config?
   **Ответ:** не знаю. По коду видно только места хранения/использования: GitHub Actions secrets/vars (`.github/workflows/*.yml`), runtime env vars и platform-секреты через OpenBao/Ansible Vault в `infra/`.

## 2. Фактическая карта runtime и деплоя

9. **Вопрос:** Какие из перечисленных surface уже реально крутятся в production прямо сейчас?
   **Ответ:** не знаю. По репозиторию видно production-ориентированные конфиги/домены/релизные workflow для `frontend`, `admin`, `partner`, `backend`, `services/task-worker`, `cybervpn_mobile`, `apps/desktop-client`, `apps/android-tv`, но сам факт живого production-трафика код не доказывает.

10. **Вопрос:** Какие из них есть только в staging/dev или ещё не обслуживают живой трафик?
   **Ответ:** `services/node-fleet-controller` по своему `README.md` явно описан как foundation/pre-production сервис и "intentionally not a live-complete controller yet". Для остальных точный статус живого трафика по коду не подтверждён.

11. **Вопрос:** Для каждой surface один deployable artifact, или внутри есть несколько независимых runtime-юнитов?
   **Ответ:** Частично видно по коду. `frontend`, `admin`, `partner` выглядят как отдельные deployable Next.js app. `backend` и `services/task-worker` уже разведены как отдельные runtime/artifact. `apps/desktop-client` имеет renderer + native `src-tauri`. `cybervpn_mobile` собирается под Android и iOS. У `services/node-fleet-controller` есть HTTP app + workflow/NATS/OpenTofu/OpenBao-интеграции, но это один сервис.

12. **Вопрос:** Где хостятся `frontend`, `admin`, `partner`: Vercel, Docker/Kubernetes, свои Node-серверы?
   **Ответ:** не знаю. По коду видны публичные домены `vpn.ozoxy.ru`, `admin.ozoxy.ru`, `partner.ozoxy.ru`, но платформа хостинга напрямую не подтверждена.

13. **Вопрос:** Где хостятся `backend` и Python services: Docker Compose, Kubernetes, systemd, bare metal?
   **Ответ:** По репозиторию есть два подтверждённых слоя. Локально они запускаются через `infra/docker-compose.yml`. Целевая платформа для `backend` и `services/task-worker` выглядит как Kubernetes/GitOps: см. `docs/plans/2026-04-21-platform-workload-delivery.md`, `infra/terraform/live/staging/control-plane/`, `infra/platform-gitops/`.

14. **Вопрос:** `apps/desktop-client` всегда релизится как единый пакет renderer + native, или возможны рассинхроны по версиям?
   **Ответ:** По текущему коду это единый Tauri-пакет: есть общий `package.json`, `src-tauri/Cargo.toml`, один workflow `.github/workflows/desktop-release.yml`, который собирает единый релиз по матрице OS. Теоретические рассинхроны по версиям кодом не описаны.

15. **Вопрос:** У mobile есть обе платформы в реальном scope: Android и iOS?
   **Ответ:** Да. В `cybervpn_mobile` есть Android Gradle-проект, iOS `Runner.xcodeproj`, Fastlane для iOS, и Flutter app для обеих платформ.

16. **Вопрос:** У Android TV есть отдельный production rollout или пока только internal/beta pipeline?
   **Ответ:** не знаю. По коду видно отдельный release workflow `.github/workflows/android-tv-release.yml`, который собирает APK/AAB и GitHub Release, но store-track rollout не найден.

## 3. Environment contract и release model

17. **Вопрос:** Подтверждаем ли единый словарь environment: `development`, `staging`, `production`?
   **Ответ:** Не полностью. `backend`, `services/task-worker`, `services/telegram-bot` используют `development/staging/production`, а `cybervpn_mobile` использует `dev/staging/prod`. Единого словаря на весь монорепозиторий в коде нет.

18. **Вопрос:** Есть ли ещё environment-ы, которые нужно видеть в Sentry: `preview`, `qa`, `beta`, `demo`, `canary`?
   **Ответ:** Частично. В коде встречаются `internal`/`beta` как release/distribution-контекст у mobile/desktop пайплайнов, но как единый Sentry environment contract это не оформлено. `preview`, `qa`, `demo`, `canary` как общий стандарт не подтверждены.

19. **Вопрос:** Что будет источником истины для `environment` в каждом runtime: env vars, CI, deploy platform, mobile flavor, app build config?
   **Ответ:** По текущему коду это разное.
   Web: сейчас `process.env.NODE_ENV` в `src/instrumentation-client.ts`.
   Backend/worker/bot/controller: env vars через `BaseSettings`.
   Mobile: flavor и `--dart-define` (`API_ENV`, `SENTRY_DSN`).
   Desktop/Android TV: Sentry environment ещё не реализован.

20. **Вопрос:** Что будет источником истины для `release`: git SHA, semver tag, build number, image tag?
   **Ответ:** Единого ответа в коде нет. Сейчас по поверхностям видны разные источники: mobile использует app version + build number, desktop и Android TV собираются от git tag/release workflow, backend/worker в delivery-доках привязаны к image/chart version и commit-driven CI.

21. **Вопрос:** Для backend и worker на одном commit нужен общий release или отдельный release per runtime artifact?
   **Ответ:** По коду они уже живут как отдельные runtime artifact: `backend` и `services/task-worker` собираются и деплоятся отдельно. Значит, текущая структура скорее предполагает отдельные release per artifact.

22. **Вопрос:** Для web-apps релиз должен считаться от git SHA или от semver/versioning схемы продукта?
   **Ответ:** не знаю. В текущем web-коде явная release-схема Sentry не зафиксирована.

23. **Вопрос:** Где именно release должен финализироваться: на этапе build, на этапе deploy, после smoke-check?
   **Ответ:** не знаю.

24. **Вопрос:** Нужны ли deploy markers отдельно для `staging` и `production` у каждой surface?
   **Ответ:** не знаю. В репозитории нет уже принятой Sentry release/deploy-marker схемы.

25. **Вопрос:** Нужен ли отдельный тег `deployment_ring` вроде `canary`, `ring0`, `ring1`, `full`?
   **Ответ:** не знаю. В репозитории встречается термин `release_ring` в staging smoke workflow, но общий Sentry tag contract не описан.

26. **Вопрос:** Нужно ли хранить в release ещё и build metadata, например `<surface>@<semver>+<build>` для user-facing apps?
   **Ответ:** не знаю. По коду для mobile и desktop уже есть версии и build numbers, но единый release metadata contract для Sentry не оформлен.

## 4. Privacy, PII и правила scrub

27. **Вопрос:** Подтверждаем ли стратегию minimal PII по умолчанию для всех SDK, аналогично mobile?
   **Ответ:** Нет, глобально это не подтверждено. Явно и жёстко это реализовано только в `cybervpn_mobile` через `sendDefaultPii = false`, `beforeSend` и `beforeBreadcrumb`.

28. **Вопрос:** Какой user context допустим глобально: только внутренний `user.id`, hashed id, tenant id, subscription id?
   **Ответ:** Глобального стандарта в коде нет. Явно подтверждён только mobile-вариант: `SentryUser(id: user.id)` в `lib/core/analytics/sentry_user_sync_provider.dart`.

29. **Вопрос:** Нужно ли полностью отключать отправку IP address, email, username почти везде?
   **Ответ:** Для mobile это уже фактически так. Для остальных runtime общий policy в коде не найден.

30. **Вопрос:** Есть ли список endpoint-категорий, для которых body/query/header всегда должны редактироваться без исключений?
   **Ответ:** Централизованного списка не найдено. По коду явно чувствительными выглядят auth/payment/webhook/admin/provisioning flow, но общего scrub-catalog в репозитории нет.

31. **Вопрос:** Нужно ли глобально запрещать отправку `Authorization`, `Cookie`, `Set-Cookie`, JWT, Telegram payloads, Remnawave/OpenBao tokens, payment secrets?
   **Ответ:** Как глобальное правило это не зафиксировано. Частичные санитайзеры есть в mobile и в frontend observability слоях `admin`/`partner`, но централизованного org/project policy в коде нет.

32. **Вопрос:** Нужны ли централизованные server-side scrubbing rules на уровне org/project сразу в первой волне?
   **Ответ:** не знаю.

33. **Вопрос:** Разрешён ли Session Replay только для web, или есть ограничения ещё и по конкретным ролям/страницам/формам?
   **Ответ:** По коду Session Replay сейчас включается только в web apps через `@sentry/nextjs`. Ограничений по ролям/страницам/формам я не нашёл.

34. **Вопрос:** Нужна ли allowlist-стратегия для headers/tags/context вместо blacklist-подхода?
   **Ответ:** не знаю. В коде нет единой глобальной стратегии.

35. **Вопрос:** Нужно ли запрещать вложения, сырые payload dumps и large context blobs во всех runtime?
   **Ответ:** не знаю.

36. **Вопрос:** Есть ли compliance/юридические ограничения по retention и доступу к данным внутри Sentry?
   **Ответ:** не знаю.

## 5. Web: `frontend`, `admin`, `partner`

37. **Вопрос:** Все три web-приложения полностью на App Router, или где-то есть legacy `pages/` / `pages/api`?
   **Ответ:** По исходникам все три приложения выглядят как App Router. Legacy `pages/`/`pages/api` в исходном коде не найдены.

38. **Вопрос:** Используются ли Edge Runtime, Route Handlers, Server Actions, streaming SSR в production?
   **Ответ:** Route Handlers точно используются: в каждом web app есть `src/app/api/**/route.ts`. Явных source-level подтверждений `export const runtime = 'edge'`, `use server` или отдельной streaming-специфики я не нашёл.

39. **Вопрос:** Есть ли уже `src/proxy.ts` или его ещё предстоит вводить под tunneling/edge-исключения?
   **Ответ:** Да, `src/proxy.ts` уже есть во всех трёх приложениях: `frontend`, `admin`, `partner`.

40. **Вопрос:** Нужен ли Sentry tunnel/proxy из-за adblock/corporate filtering, или идём без него?
   **Ответ:** не знаю. По текущему коду Sentry tunnel не реализован.

41. **Вопрос:** Все три web-app должны иметь отдельные Sentry projects, или часть из них уже создана и надо лишь довести конфиг?
   **Ответ:** не знаю. По коду видно раздельное конфигурирование каждого app и отдельные `.env.example`, но факт существования Sentry projects не подтверждён.

42. **Вопрос:** Какой окончательный источник `environment` в web: `NEXT_PUBLIC_APP_ENV`, `APP_ENV`, что-то ещё?
   **Ответ:** Сейчас в Sentry-конфиге web используется `process.env.NODE_ENV`.

43. **Вопрос:** Какой окончательный источник server-side `SENTRY_DSN` и client-side `NEXT_PUBLIC_SENTRY_DSN`?
   **Ответ:** Сейчас по коду так и есть. Client-side: `NEXT_PUBLIC_SENTRY_DSN` в `src/instrumentation-client.ts`. Server-side/edge: `SENTRY_DSN` в `sentry.server.config.ts` и `sentry.edge.config.ts`.

44. **Вопрос:** Нужно ли жёстко развести public DSN и server DSN по разным секретам/переменным?
   **Ответ:** По текущему коду они уже разведены по разным переменным: `NEXT_PUBLIC_SENTRY_DSN` и `SENTRY_DSN`. Требование "жёстко" как governance-policy в репозитории не описано.

45. **Вопрос:** Какие sample rates нужны для web по средам: `tracesSampleRate`, `replaysSessionSampleRate`, `replaysOnErrorSampleRate`, profiling?
   **Ответ:** Текущие значения в коде такие.
   `tracesSampleRate`: `0.2` в production, `1.0` вне production.
   `replaysSessionSampleRate`: `0.1`.
   `replaysOnErrorSampleRate`: `1.0`.
   Profiling в web-конфиге не найден.

46. **Вопрос:** Нужно ли выровнять custom runtime-layer из `admin`/`partner` и перенести его как общий паттерн в `frontend`?
   **Ответ:** По коду видно несоответствие: у `admin` и `partner` есть развитый `frontend-observability` слой, у `frontend` такого слоя нет. Значит, технически выравнивание действительно нужно, если цель — единый паттерн.

47. **Вопрос:** Нужна ли корреляция Sentry ↔ PostHog по безопасному идентификатору пользователя/сессии?
   **Ответ:** не знаю. Явной уже реализованной корреляции Sentry ↔ PostHog в коде не найдено.

48. **Вопрос:** Какие web-flow считаются incident-grade: auth, payments, checkout, provisioning, mini app, admin actions, workspace flows?
   **Ответ:** не знаю как policy. По коду явно присутствуют и выглядят критичными auth/2FA/OAuth flow, mini app/runtime analytics, admin/partner actions, provisioning/runtime telemetry, product events и часть payment-related surface.

49. **Вопрос:** Какие client errors надо игнорировать как шум: adblock/network aborts, extensions, hydration mismatch noise, cancelled navigations?
   **Ответ:** не знаю. Явных `ignoreErrors`/`denyUrls`/`beforeSend` фильтров для web в Sentry-конфиге не найдено.

50. **Вопрос:** Нужно ли отдельно мониторить server actions / route handlers как критические backend-like операции внутри web apps?
   **Ответ:** Route Handlers точно есть и они выглядят как критические backend-like операции. Server Actions в исходниках я не подтвердил.

51. **Вопрос:** Source maps уже генерируются так, как нужно для загрузки в Sentry, или pipeline надо перестраивать?
   **Ответ:** Частично подготовлено. Все три web app используют `withSentryConfig(...)`, `widenClientFileUpload: true` и `SENTRY_AUTH_TOKEN`-зависимую сборку. Но единый подтверждённый artifact-upload pipeline по всем web apps я не нашёл.

52. **Вопрос:** Есть ли ограничения безопасности на hidden source maps или их upload в CI?
   **Ответ:** не знаю.

53. **Вопрос:** Нужен ли user feedback dialog/widget на web, или сейчас он не входит в scope?
   **Ответ:** не знаю. По коду user feedback dialog/widget не реализован.

54. **Вопрос:** Нужно ли выставлять ownership/routing по `frontend`, `admin`, `partner` отдельно уже на уровне issue rules?
   **Ответ:** не знаю. В репозитории нет Sentry ownership/routing правил.

## 6. Backend: `backend`

55. **Вопрос:** Как именно запускается backend: `uvicorn`, `gunicorn+uvicorn`, k8s deployment, несколько pod/replica?
   **Ответ:** По приложению backend запускается через `uvicorn` (`backend/src/main.py`). Локально он есть в Docker Compose. Для целевого окружения в репозитории есть Kubernetes/GitOps-структура, но конкретное число pod/replica я не подтверждал.

56. **Вопрос:** Нужен ли tracing для DB, Redis, внешних HTTP-клиентов, webhooks и payment-интеграций?
   **Ответ:** не знаю как окончательное решение. По коду видно, что backend уже ориентирован на observability: есть OpenTelemetry bootstrap, HTTP-инструментирование и явные интеграционные домены для DB/Redis/HTTP/webhooks/payments.

57. **Вопрос:** Есть ли уже request id / correlation id, который надо пробрасывать в Sentry tags/context?
   **Ответ:** Да. В backend есть `RequestIDMiddleware`, заголовок `X-Request-ID`, contextvar и прокидка `request_id` в logging/exception handling.

58. **Вопрос:** Какие типы исключений должны идти в Sentry как error, а какие лучше снижать до warning/info или игнорировать?
   **Ответ:** Точная Sentry severity policy не найдена. Но по коду видно, что часть исключений уже считается штатным бизнес-потоком: `UserNotFoundError`, `PaymentNotFoundError`, `InvalidCredentialsError`, `InvalidTokenError`, `SubscriptionExpiredError`, `TrafficLimitExceededError` и т.д.

59. **Вопрос:** Нужны ли стандартные backend-теги: `endpoint`, `realm`, `payment_provider`, `webhook_source`, `security_flow`?
   **Ответ:** не знаю как утверждённый стандарт. По коду такие измерения уже встречаются или явно доступны: `endpoint`, `realm`, `request_id`, `trace_id`, payment/webhook/security домены.

60. **Вопрос:** Нужно ли отдельное правило scrub для auth/payment/admin/webhook endpoints?
   **Ответ:** не знаю. Централизованного backend scrub policy в коде нет.

61. **Вопрос:** Есть ли domain-specific exceptions, которые ты уже считаешь нормальным бизнес-потоком, а не инцидентом?
   **Ответ:** Да. Это видно по выделенным exception handlers для auth/payment/subscription/not-found/permission-related ошибок.

62. **Вопрос:** Нужен ли post-deploy smoke event/health-check для backend после старта контейнера?
   **Ответ:** не знаю. Sentry-specific smoke event для backend в репозитории не найден.

63. **Вопрос:** Нужно ли связывать backend Sentry event с Loki/Tempo через `trace_id`, `request_id`, `sentry_event_id`?
   **Ответ:** не знаю как policy. По коду уже есть `trace_id` и `request_id`, значит техническая база для корреляции существует.

64. **Вопрос:** Есть ли отдельные cron-like/background задачи внутри backend, которые не живут в TaskIQ, но тоже требуют покрытия?
   **Ответ:** не знаю. Явного отдельного cron-пула внутри `backend` не нашёл.

## 7. Worker: `services/task-worker`

65. **Вопрос:** Какой broker/transport у TaskIQ: Redis, RabbitMQ, NATS, другое?
   **Ответ:** Redis. В `services/task-worker/src/broker.py` используется `RedisStreamBroker` и `RedisAsyncResultBackend`.

66. **Вопрос:** Есть ли несколько очередей, приоритетов или scheduler lanes, которые надо тегировать?
   **Ответ:** Частично. Явно есть несколько scheduler source и несколько категорий scheduled tasks (`monitoring`, `payments`, `notifications`, `sync`, `reports`, `helix` и т.д.). Явную карту queue names/priorities я не подтвердил.

67. **Вопрос:** Какой минимальный стандартный набор тегов нужен для worker: `task_name`, `queue`, `retry`, `schedule`, `trigger_source`, `tenant/domain`?
   **Ответ:** не знаю как утверждённый стандарт. По коду минимум логично и подтверждаемо доступны `task_name`, category/schedule, retry-context и domain task group.

68. **Вопрос:** Какие task failures считаются нормальными retryable-case и не должны сразу поднимать шум?
   **Ответ:** По коду подтверждаются rate-limit/retry сценарии для Telegram и внешних интеграций. Полный шумовой policy для worker не найден.

69. **Вопрос:** Нужна ли отдельная sampling policy для частых задач и high-volume ошибок?
   **Ответ:** не знаю. Отдельной sampling policy для worker в коде нет.

70. **Вопрос:** Нужно ли пробрасывать связь с исходным API request/job id, если задача была порождена backend-вызовом?
   **Ответ:** не знаю как policy. По репозиторию request/trace ID уже существуют в backend observability, но явной сквозной связки backend → worker Sentry я не нашёл.

71. **Вопрос:** Какие категории задач наиболее критичны: payments, notifications, sync, reports, monitoring, reconciliation?
   **Ответ:** По коду именно такие категории и присутствуют: `payments`, `notifications`, `sync`, `reports`, `monitoring`, плюс `analytics`, `cleanup`, `helix`.

72. **Вопрос:** Нужен ли отдельный smoke-test path для worker в CI/CD или достаточно runtime event на startup/first task?
   **Ответ:** не знаю. Sentry-specific smoke path для worker не найден.

## 8. Telegram bot: `services/telegram-bot`

73. **Вопрос:** Бот работает через webhook, polling или режим зависит от environment?
   **Ответ:** Режим зависит от конфигурации. В коде поддерживаются `polling` и `webhook`; в `main.py` прямо указано, что polling используется по умолчанию/в development, webhook — в production.

74. **Вопрос:** Будут ли отдельные bot tokens для `development`, `staging`, `production`?
   **Ответ:** не знаю. В коде есть один `bot_token` в settings, а стратегия разведения по env не зафиксирована.

75. **Вопрос:** Какой user context допустим для бота: внутренний `user.id`, hashed Telegram ID, tenant, subscription id?
   **Ответ:** не знаю. Sentry user-context policy для бота в коде отсутствует.

76. **Вопрос:** Какие bot-flow критичны: payment, referral, config delivery, subscription lifecycle, admin actions?
   **Ответ:** По `README.md` и структуре сервиса явно присутствуют payment, referral, config delivery/QR, subscription lifecycle и admin actions.

77. **Вопрос:** Нужно ли связывать события бота с backend API событиями через correlation id / custom tags?
   **Ответ:** не знаю. Явной уже реализованной корреляции не найдено.

78. **Вопрос:** Какие bot errors считаются шумом и должны фильтроваться: invalid input, expired callback, user cancelled flow, Telegram 429/5xx retries?
   **Ответ:** Частично видно `Telegram 429`/retry и not-found/invalid-response категории. Полный policy по шуму не найден.

79. **Вопрос:** Нужны ли отдельные теги `handler`, `bot_mode`, `payment_provider`, `flow_step`?
   **Ответ:** не знаю как утверждённый стандарт. По коду такие измерения технически доступны: `bot_mode` есть в settings, flow/handler/payment домены в коде бота присутствуют.

80. **Вопрос:** Бот деплоится в одном pipeline с backend или как отдельный runtime с отдельным релизным циклом?
   **Ответ:** По структуре репозитория это отдельный runtime. В локальном Compose он отдельный сервис. Общий production pipeline с backend по коду не подтверждён.

81. **Вопрос:** Есть ли в боте обработка файлов/документов/конфигов, где privacy нужно ужесточать отдельно?
   **Ответ:** Да. В описании бота есть delivery конфигов и QR-кодов, значит privacy для payloads/документов здесь действительно нужна.

82. **Вопрос:** Нужен ли webhook/polling smoke-test с тестовым событием после деплоя?
   **Ответ:** не знаю. Такой smoke-test в репозитории не найден.

## 9. Node fleet controller и Rust control-plane

83. **Вопрос:** `services/node-fleet-controller` уже обслуживает реальный lifecycle в production или пока pre-production foundation?
   **Ответ:** Пока pre-production foundation. Это прямо описано в `services/node-fleet-controller/README.md`.

84. **Вопрос:** Какие операции controller должны иметь явные теги: `reconcile`, `plan`, `apply`, `publish`, `audit_write`, `secret_fetch`?
   **Ответ:** По коду и README у controller точно есть домены `request submission`, `baseline`, `operator commands`, `reconciliation`, workflow execution, audit и secret/bootstrap-интеграции через OpenBao. Значит как минимум `reconcile`, `apply`, `audit_write`, `secret_fetch` подтверждаются предметно.

85. **Вопрос:** Для controller нужны только request traces, или ещё и long-running workflow spans/transactions?
   **Ответ:** не знаю как policy. По коду у него есть не только HTTP, но и `WorkflowEngine`, значит long-running workflow spans здесь выглядят естественными.

86. **Вопрос:** Какие идентификаторы безопасно использовать в tags: `node_id`, `workspace_id`, `tenant_id`, `operation_type`, `workflow_stage`?
   **Ответ:** По коду точно подтверждаются `request_id`, `correlation_id`, `node_id` и типы операций/workflow stage. `workspace_id`/`tenant_id` как общий safe-tag contract не подтверждён.

87. **Вопрос:** Для `services/helix-adapter` на первом этапе нужен только error/crash coverage или сразу включаем performance/tracing?
   **Ответ:** не знаю. В текущем коде Sentry там нет, но сервис уже использует `tracing` и имеет `/healthz`, `/readyz`, `/metrics`.

88. **Вопрос:** Для `services/helix-node` нужна ли стратегия offline buffering/late delivery, если daemon живёт в нестабильной сети?
   **Ответ:** не знаю. По коду Sentry/offline buffering для `helix-node` не реализован.

89. **Вопрос:** `helix-node` запускается в вашей инфраструктуре, на клиентских нодах, или в гибридной модели?
   **Ответ:** не знаю. По архитектурному смыслу это node daemon для внешнего fleet, но жёстко финальная модель развертывания кодом не зафиксирована.

90. **Вопрос:** Для Rust surfaces every panic/crash должен считаться incident-grade, или сначала идём через capture + triage без жёсткого paging?
   **Ответ:** не знаю.

91. **Вопрос:** Бинарники Rust сейчас собираются с debug info, который можно использовать для symbol upload, или релизный pipeline strip-ит всё слишком рано?
   **Ответ:** Частично. Для `apps/desktop-client/src-tauri` в `Cargo.toml` release-профиль явно содержит `strip = true`, то есть там symbols без отдельной политики не сохранятся автоматически. Для `services/helix-adapter` и `services/helix-node` этого по просмотренным файлам я не подтвердил.

92. **Вопрос:** Нужно ли сразу продумать native symbol handling policy для `helix-adapter` и `helix-node`, или это отдельная волна после базовой SDK-интеграции?
   **Ответ:** не знаю.

## 10. Mobile: `cybervpn_mobile`

93. **Вопрос:** Подтверждаешь ли, что mobile scope — это Android + iOS в одном Flutter приложении?
   **Ответ:** Да. Это один Flutter app с Android и iOS платформами.

94. **Вопрос:** Один Sentry project для mobile достаточен, или нужны отдельные проекты/DSN по платформам?
   **Ответ:** не знаю как целевое решение. По текущему коду mobile использует единый `SENTRY_DSN`, то есть сейчас заложена модель одного DSN на Flutter app.

95. **Вопрос:** Какие flavors реально существуют: `dev`, `staging`, `prod`, `internal`, `beta`?
   **Ответ:** Реально подтверждены `dev`, `staging`, `prod` в Android Gradle и CI. `internal`/`beta` встречаются как distribution/release контекст, но не как основной runtime flavor приложения.

96. **Вопрос:** Что будет canonical release string для mobile: версия из `pubspec` + build number из CI/store?
   **Ответ:** не знаю как утверждённый формат. По коду доступны все ингредиенты: версия приложения, Android `versionCode`/`versionName`, iOS build metadata и `BUILD_NUMBER` из CI.

97. **Вопрос:** Нужны ли performance traces/profiling на mobile, или на первом этапе ограничиваемся crashes/errors + network spans?
   **Ответ:** По текущему коду mobile уже включает performance tracing: `enableAutoPerformanceTracing = true`, `enableUserInteractionTracing = true`, `tracesSampleRate` настроен. Это уже больше, чем только crashes/errors.

98. **Вопрос:** Есть ли native Android/iOS плагины или platform channels, для которых надо отдельно продумать symbol upload и native crash visibility?
   **Ответ:** Да, в проекте есть native Android/iOS слой и platform-specific integration. Но отдельная policy по native symbols в репозитории явно не оформлена.

99. **Вопрос:** Какой safe user context допустим на mobile кроме `user.id`, или остаёмся только на нём?
   **Ответ:** По текущему коду подтверждён только `user.id`.

100. **Вопрос:** Нужен ли отдельный QA smoke-scenario, чтобы до выкладки проверять release/artifact linkage в Sentry?
   **Ответ:** не знаю. Явного smoke-сценария для проверки linkage в Sentry не найдено.

101. **Вопрос:** В staging/test builds mobile должен реально отправлять события в отдельный project/environment или они должны быть выключены?
   **Ответ:** не знаю. В коде это как policy не зафиксировано.

102. **Вопрос:** Нужно ли выровнять upload Dart debug files между `ci.yml` и `mobile-release.yml` в один общий reusable flow?
   **Ответ:** Да, по текущему коду есть несоответствие: `ci.yml` содержит upload Dart debug symbols в Sentry, а `mobile-release.yml` этого общего шага не повторяет как reusable flow.

## 11. Desktop и Android TV

103. **Вопрос:** Для `apps/desktop-client` какие target OS входят в scope: Windows, macOS, Linux?
   **Ответ:** Все три. В `.github/workflows/desktop-release.yml` есть Windows, Linux и две macOS-цели.

104. **Вопрос:** Renderer и native layer будут иметь два отдельных Sentry project с разными DSN?
   **Ответ:** не знаю. Sentry для desktop пока не интегрирован.

105. **Вопрос:** При этом release name у renderer и native должен быть общий, чтобы их можно было сопоставлять между собой?
   **Ответ:** не знаю.

106. **Вопрос:** Нужна ли корреляция renderer-event ↔ native-event через `installation_id`, `device_id`, `release`, custom correlation id?
   **Ответ:** не знаю. Явной схемы `installation_id`/`device_id` для Sentry я не нашёл.

107. **Вопрос:** Какие desktop-flow критичны: auth, updater, deep-link, tray, VPN connect/disconnect, config import, crash on startup?
   **Ответ:** По коду явно присутствуют и выглядят критичными updater, deep-link, tray, connect/disconnect, startup cleanup/recovery, remote control и diagnostic flow.

108. **Вопрос:** Нужны ли source maps для renderer и отдельно native symbols для Tauri/Rust уже в первой реализации?
   **Ответ:** не знаю как утверждённое решение. По текущему коду ни source maps upload, ни native symbol upload для desktop не реализованы.

109. **Вопрос:** Desktop-client сейчас имеет один релизный pipeline или по OS идут разные workflow/jobs с разными артефактами?
   **Ответ:** Один release workflow с матрицей OS и разными артефактами по платформам.

110. **Вопрос:** Нужен ли offline event caching для desktop при нестабильной сети?
   **Ответ:** не знаю. По коду Sentry caching/offline queue для desktop не найден.

111. **Вопрос:** Для `apps/android-tv` уже есть production track или пока internal/beta rollout?
   **Ответ:** не знаю. По коду есть release workflow и выпуск артефактов, но не найден Play Store rollout pipeline.

112. **Вопрос:** На Android TV Sentry будет единственным crash-инструментом, или надо учитывать coexistence с Firebase Crashlytics/другими системами?
   **Ответ:** не знаю. Firebase Crashlytics в просмотренных файлах Android TV не найден.

113. **Вопрос:** Какие safe tags/context нужны для Android TV: `platform`, `app_version`, `build_number`, `device_class`, `household/tenant`, `session_type`?
   **Ответ:** не знаю как policy. По коду точно доступны `app_version`/`build_number` из Android-конфига; остальные safe tags не оформлены.

114. **Вопрос:** Нужны ли на TV сразу ANR coverage, performance traces и release health, или начинаем только с crash/error + mappings?
   **Ответ:** не знаю.

## 12. Alerting, ownership, CI/CD и operational model

115. **Вопрос:** Кто владелец triage по каждой surface: web, backend, worker, bot, mobile, desktop, control-plane?
   **Ответ:** не знаю.

116. **Вопрос:** Нужен ли auto-assignment issues по teams/CODEOWNERS/path ownership?
   **Ответ:** не знаю. `CODEOWNERS` в репозитории я не нашёл.

117. **Вопрос:** Какие каналы оповещения нужны с первого дня: Slack, email, Telegram, PagerDuty, Jira?
   **Ответ:** не знаю.

118. **Вопрос:** Какие сигналы считаются incident-grade: new prod issue, regression, spike, crash-free sessions drop, payment failures, auth failures?
   **Ответ:** не знаю. Формализованного incident policy для Sentry в репозитории нет.

119. **Вопрос:** Какие alert rules нужны отдельно для `staging`, чтобы не утонуть в шуме?
   **Ответ:** не знаю.

120. **Вопрос:** Нужны ли готовые Sentry dashboards/queries по surface, environment, release уже в первой итерации?
   **Ответ:** не знаю. Sentry dashboards/queries в репозитории не описаны.

121. **Вопрос:** Где сейчас хранятся secrets для CI/runtime: GitHub Actions secrets, Vault, Doppler, Kubernetes secrets, другое?
   **Ответ:** По коду подтверждаются GitHub Actions secrets/vars, env files для локалки и platform secret-management через OpenBao/Ansible Vault/Kubernetes Secret цепочку в `infra/`.

122. **Вопрос:** Есть ли reusable GitHub Actions/workflows, куда логично вынести `sentry-cli`, release creation, deploy markers, artifact upload?
   **Ответ:** Отдельного reusable Sentry workflow я не нашёл. Логически точкой выноса могут быть существующие GitHub Actions workflows, но сейчас это не выделено.

123. **Вопрос:** Нужно ли автоматически проверять в CI, что source maps / debug files / mappings реально прикрепились к правильному release?
   **Ответ:** не знаю. Такой автоматической проверки в репозитории не найдено.

124. **Вопрос:** Нужен ли обязательный post-deploy smoke event для каждой production surface?
   **Ответ:** не знаю. По коду обязательного Sentry smoke-event стандарта нет.

125. **Вопрос:** Есть ли environment-ы, где Sentry должен быть полностью выключен: local dev, tests, ephemeral previews?
   **Ответ:** По коду это частично уже так. Во многих runtime Sentry активируется только при наличии DSN, а локальные/test конфиги часто идут без него. Но общий формальный policy на весь монорепозиторий не найден.

126. **Вопрос:** Нужны ли автотесты на интеграцию Sentry: unit smoke, integration assertions, e2e verification release/env injection?
   **Ответ:** По коду частичное покрытие уже есть: web-тесты на sentry config, backend integration tests на observability/request-id, mobile privacy/env tests. Полного e2e verification стандарта по всем surface нет.

127. **Вопрос:** Нужен ли отдельный документ/матрица по ownership + privacy + tags + alerting как часть rollout?
   **Ответ:** не знаю как решение. Отдельной такой матрицы в исходном репозитории я не нашёл.

128. **Вопрос:** Что ты хочешь получить от меня после твоих ответов: архитектурный план, список Sentry projects, env schema, кодовые патчи, CI/CD патчи, privacy policy, rollout roadmap, DoD checklist?
   **Ответ:** не знаю. Этот ответ невозможно вывести из кода.

## Практические рекомендации по пунктам, где по коду ответа нет

Ниже уже не факты из репозитория, а мои рекомендации под ваш текущий стек, монорепо и расклад по surface.

### 1. Организация Sentry и governance

2. **Рекомендация:** Если отдельной organization ещё нет, я бы сразу заводил одну выделенную Sentry organization под продукт, а не смешивал её с другими проектами.
   **Почему:** У вас уже много runtime-поверхностей, и дальше станет только сложнее. Отдельная org сразу даёт чистые правила доступа, понятные quotas, единый naming и проще rollout по всем приложениям.

3. **Рекомендация:** Держать минимум двух human-admin и один service account для CI.
   **Почему:** Это снимает bus factor и не завязывает выпуск релизов на одного человека. CI-токен должен жить отдельно от пользовательских admin-доступов.

4. **Рекомендация:** Не дробить на слишком много teams. Для этого проекта я бы начал с 4 команд: `web`, `core`, `client-apps`, `platform`.
   **Почему:** Это совпадает с реальными эксплуатационными границами. `web` покрывает `frontend/admin/partner`, `core` покрывает `backend/task-worker/telegram-bot`, `client-apps` покрывает `mobile/desktop/android-tv`, `platform` покрывает `node-fleet-controller/helix-*`.

5. **Рекомендация:** Если остаётесь на Sentry Cloud, я бы выбирал EU-регион хранения данных.
   **Почему:** У вас есть auth, payments, Telegram и subscription-домены. Для такого стека лучше сразу минимизировать future legal/privacy риски и не переносить данные между регионами без необходимости.

6. **Рекомендация:** Стартовать минимально: GitHub + email + один операционный чат. Для вашего проекта логичнее всего GitHub и Telegram-канал/чат для critical prod alert.
   **Почему:** Полный набор Slack/Jira/PagerDuty на первой волне только размажет rollout. Сначала нужен надёжный triage и понятный critical path, а не тяжёлая интеграционная матрица.

7. **Рекомендация:** Сразу задать budgets и volume guardrails, особенно для web replay и tracing.
   **Почему:** У вас есть public web, mobile и потенциально шумные worker/control-plane surface. Без лимитов вы быстро получите либо неожиданные расходы, либо бесполезный шум.

8. **Рекомендация:** Ownership за `SENTRY_AUTH_TOKEN`, org/project config и DSN я бы отдал platform/infra owner, а прикладным командам оставил только потребление секретов.
   **Почему:** Секреты и org-level настройки лучше централизовать. Иначе вы очень быстро получите рассинхрон env naming, разные sample rates и случайные утечки конфигурации.

### 2. Фактическая карта runtime и деплоя

9. **Рекомендация:** Для первой волны я бы считал production-scope такими: `frontend`, `admin`, `partner`, `backend`, `services/task-worker`, `services/telegram-bot`, `cybervpn_mobile`. `desktop-client` и `android-tv` вынес бы во вторую волну, `node-fleet-controller` и `helix-*` в третью.
   **Почему:** Первая группа даёт основной пользовательский и денежный путь. Desktop/TV пока менее подтверждены по зрелости, а control-plane ещё не выглядит как fully-live слой.

12. **Рекомендация:** Держать `frontend`, `admin`, `partner` на одном и том же deployment-моделе и release-контракте; с учётом текущего репозитория я бы целился в единый Docker/GitOps/Kubernetes path.
   **Почему:** Для Sentry главное не конкретная платформа, а единообразие release/environment/deploy-marker. Разные платформы для трёх web app дадут три разных operational contract и лишнюю сложность.

16. **Рекомендация:** Для `apps/android-tv` я бы начинал только с internal/beta rollout, без production track.
   **Почему:** В коде пока нет явной crash-observability цепочки и store rollout discipline. Сначала нужно поставить базовую телеметрию, потом уже открывать production audience.

### 3. Environment contract и release model

22. **Рекомендация:** Для web canonical release я бы делал от git SHA с префиксом surface, например `frontend@<sha>`, `admin@<sha>`, `partner@<sha>`.
   **Почему:** Web у вас деплоится часто и независимо. Для source maps и rollback git SHA надёжнее и дешевле в сопровождении, чем semver для каждого Next.js app.

23. **Рекомендация:** Release создавать на build-этапе, artifact upload делать там же, а финализировать и ставить deploy marker только после успешного deploy и smoke-check.
   **Почему:** Тогда release в Sentry соответствует реальному выкату, а не просто факту сборки. Это уменьшает ложные regression и упрощает incident review.

24. **Рекомендация:** Да, отдельные deploy markers для `staging` и `production` нужны у каждой production-grade surface.
   **Почему:** Иначе вы не сможете нормально отличать "сломали на staging" от "сломали на бою" и быстро связывать issue со временем выката.

25. **Рекомендация:** Ввести `deployment_ring`, но не делать его обязательным для всех. Использовать там, где rollout реально поэтапный: mobile, desktop, android-tv и, возможно, часть web.
   **Почему:** Глобальный тег без реальных ring deployment превращается в мусор. Но на phased rollout поверхностях он очень полезен.

26. **Рекомендация:** Для user-facing app хранить release как `<surface>@<version>+<build>`, а для web/backend worker оставить `<surface>@<sha>`.
   **Почему:** Для mobile/desktop/TV пользователи и сторы живут версиями и build number. Для web/server runtime важнее точная привязка к коммиту.

### 4. Privacy, PII и правила scrub

32. **Рекомендация:** Да, org/project-level server-side scrubbing rules я бы закладывал сразу в первой волне.
   **Почему:** У вас слишком много surface и слишком много чувствительных доменов, чтобы надеяться только на client-side дисциплину в каждом SDK.

34. **Рекомендация:** Делать allowlist-подход для headers/tags/context, а не blacklist.
   **Почему:** В проекте уже есть auth, payment, Telegram, OpenBao, токены и конфиги. Blacklist почти всегда пропускает что-то новое; allowlist проще держать безопасным.

35. **Рекомендация:** Запретить attachments, raw payload dumps и large context blobs по умолчанию. Разрешать только точечно и осознанно.
   **Почему:** Это лучший баланс для privacy, стоимости и стабильного triage. Большие payload часто дают мало ценности, но резко повышают риск утечки данных.

36. **Рекомендация:** Держать минимальную retention и доступ по least-privilege. Практически я бы начал с короткой retention для staging и умеренной для production.
   **Почему:** Сейчас проекту важнее оперативная диагностика, чем исторический архив за многие месяцы. Это уменьшает риски и не мешает rollout.

### 5. Web: `frontend`, `admin`, `partner`

40. **Рекомендация:** Для public web (`frontend` и, вероятно, `partner`) я бы включил Sentry tunnel; для `admin` можно оставить прямую отправку на первом этапе.
   **Почему:** У consumer-аудитории VPN-продукта доля adblock/privacy tooling обычно выше средней. Без tunnel вы потеряете часть client-side событий именно там, где они нужны.

41. **Рекомендация:** Делать три отдельных Sentry project: `web-frontend`, `web-admin`, `web-partner`.
   **Почему:** У приложений разный пользователь, разный шум и разный owner. Смешивание их в один project быстро ломает triage и ownership.

47. **Рекомендация:** Да, безопасную корреляцию Sentry ↔ PostHog я бы добавлял. Брать только внутренний `user.id` или его hash, без email/username.
   **Почему:** Так вы сможете сопоставлять product-события и incidents без лишнего PII. Для growth/admin/partner flow это особенно полезно.

48. **Рекомендация:** В incident-grade для web я бы включил auth, signup, payment/checkout, subscription/provisioning, admin mutations и partner workspace mutations.
   **Почему:** Именно эти цепочки влияют на деньги, доступ пользователя и управляющие действия. Product analytics и декоративные UI-ошибки туда лучше не включать.

49. **Рекомендация:** Шумом я бы считал extension errors, adblock/network aborts, cancelled navigation, известные benign hydration/client noise. Но не фильтровал бы auth/payment/API failures.
   **Почему:** Иначе public web начнёт засыпать issue-трекер мусором и скроет реальные регрессии.

52. **Рекомендация:** Использовать hidden source maps и загружать их только через CI. Публичные `.map` не отдавать.
   **Почему:** Это стандартный компромисс между нормальной дебаг-диагностикой и безопасностью фронтенда.

53. **Рекомендация:** User feedback dialog на первой волне не включать. Вернуться к нему после стабилизации alerting и privacy.
   **Почему:** Сначала нужно получить чистую machine-observability. Иначе вы добавите ручной шум и вопросы по PII до того, как выровняете базовый pipeline.

54. **Рекомендация:** Да, ownership/routing rules для `frontend`, `admin`, `partner` нужно разводить отдельно с первого дня.
   **Почему:** Даже при одной web-команде это ускоряет triage и предотвращает "непонятно чья ошибка" между пользовательским, админским и партнёрским интерфейсом.

### 6. Backend: `backend`

56. **Рекомендация:** Да, для backend я бы включал tracing для DB, Redis, внешних HTTP-клиентов, webhook и payment-интеграций.
   **Почему:** Backend у вас центральный orchestration point. Без этих спанов вы увидите только факт ошибки, но не поймёте, где реально ломается критический путь.

59. **Рекомендация:** Для backend я бы стандартизировал теги `endpoint_template`, `request_id`, `realm`, `payment_provider`, `webhook_source`, `security_flow`.
   **Почему:** Это минимальный набор, который даёт полезную фильтрацию в инцидентах без лишней детализации и без опасного PII.

60. **Рекомендация:** Да, отдельные scrub-правила для auth/payment/admin/webhook endpoints я бы делал обязательно.
   **Почему:** Эти зоны содержат самые дорогие и самые чувствительные данные. Их нельзя отдавать на общих основаниях.

62. **Рекомендация:** Для backend я бы сделал post-deploy smoke event и простой synthetic health transaction.
   **Почему:** Это быстро показывает, что release/env linkage и DSN действительно работают после деплоя, а не только на локальной сборке.

63. **Рекомендация:** Да, связывать backend Sentry event с Loki/Tempo нужно через `trace_id` и `request_id`, а `sentry_event_id` логировать в structured logs.
   **Почему:** Тогда расследование не упирается в один инструмент. Вы сможете прыгать из Sentry в логи и трассы за секунды.

64. **Рекомендация:** Любой background/cron-подобный код я бы выносил в TaskIQ; если оставить что-то в backend, то только с отдельной явной Sentry-инструментацией.
   **Почему:** Иначе backend смешает request-path и background-path, а retries/ownership станут нечёткими.

### 7. Worker: `services/task-worker`

67. **Рекомендация:** Для worker я бы стандартизировал теги `task_name`, `task_group`, `queue`, `retry_count`, `trigger_source`, `request_id/job_id`, `realm_or_tenant` если это безопасно.
   **Почему:** Без этого worker-ошибки быстро превращаются в плоский шум, особенно когда задач много и они разнотипные.

69. **Рекомендация:** Да, отдельная sampling policy worker нужна. Для частых housekeeping задач делать низкий sampling, а для `payments`, `reconciliation`, `provisioning` и важных sync-задач оставлять высокий.
   **Почему:** Worker почти всегда становится самым шумным runtime. Без градации вы либо платите слишком много, либо теряете важные сигналы.

70. **Рекомендация:** Да, связь с исходным backend request/job id я бы делал обязательной.
   **Почему:** Для асинхронных ошибок корневая причина почти всегда находится в вызове, который породил задачу.

72. **Рекомендация:** Для worker я бы добавил две вещи: startup heartbeat и synthetic canary-task после деплоя.
   **Почему:** Это проверит не только процесс, но и реальный путь broker → worker → task execution → Sentry.

### 8. Telegram bot: `services/telegram-bot`

74. **Рекомендация:** Да, отдельные bot token на `development`, `staging`, `production` обязательны.
   **Почему:** Telegram-интеграции слишком легко перепутать между средами. Один токен на всё почти гарантированно приведёт к cross-env инцидентам.

75. **Рекомендация:** В Sentry для бота я бы хранил только `internal_user_id`, hash от `telegram_user_id`, `subscription_id` и безопасный `tenant/realm` при необходимости.
   **Почему:** Этого хватает для корреляции, но вы не тащите в Sentry raw Telegram identifiers и лишний пользовательский контекст.

77. **Рекомендация:** Да, бот и backend нужно связывать через `correlation_id`/`request_id` и общие flow tags.
   **Почему:** У вас subscription/payment/config delivery завязаны на оба runtime. Без корреляции инцидент будет распадаться на две несвязанные половины.

79. **Рекомендация:** Для бота я бы ввёл теги `handler`, `bot_mode`, `flow_step`, `payment_provider`, `update_type`.
   **Почему:** Эти измерения дают максимум пользы для triage и почти не несут privacy-риска.

82. **Рекомендация:** Да, после деплоя бота нужен smoke-check. Для webhook — синтетический update в staging, для production — хотя бы health ping и canary flow.
   **Почему:** Бот часто "поднимается", но реально ломается на первом апдейте. Это нужно ловить сразу.

### 9. Node fleet controller и Rust control-plane

85. **Рекомендация:** Для controller я бы сразу проектировал не только request traces, но и long-running workflow transactions/spans.
   **Почему:** У вас там orchestration и reconciliation. Простые HTTP traces не покажут реальную картину длительных control-plane операций.

87. **Рекомендация:** Для `helix-adapter` в первой волне я бы делал errors + базовый request tracing + несколько критических кастомных spans вокруг Remnawave/OpenBao/signing.
   **Почему:** Полная deep-tracing интеграция сразу может быть дорогой, а без базовых спанов вы не поймёте, где ломается цепочка.

88. **Рекомендация:** Для `helix-node` я бы закладывал bounded offline buffering с локальной очередью и TTL.
   **Почему:** Это daemon в потенциально нестабильной сети. Без буфера вы потеряете как раз те события, которые нужны при сетевых сбоях.

89. **Рекомендация:** Я бы проектировал `helix-node` как управляемый инфраструктурный агент в гибридной модели, а не как "клиентское приложение".
   **Почему:** Тогда теги, release policy и privacy contract можно строить вокруг узла и control-plane, а не вокруг end-user устройства.

90. **Рекомендация:** Every panic/crash в production Rust surface я бы считал incident-grade, но paging включал бы не на единичный event, а на повторяемость/всплеск.
   **Почему:** Так вы не пропустите серьёзные падения и одновременно избежите pager fatigue на старте rollout.

92. **Рекомендация:** Native symbol policy для `helix-adapter` и `helix-node` нужно спроектировать сразу, но внедрять сразу после базовой SDK-интеграции как вторую под-волну.
   **Почему:** Если отложить это слишком далеко, потом придётся ломать release pipeline задним числом. Но и тормозить базовую error-интеграцию из-за symbols не стоит.

### 10. Mobile: `cybervpn_mobile`

94. **Рекомендация:** Для Flutter mobile я бы начинал с одного Sentry project и одного DSN на приложение.
   **Почему:** У вас общий код, общие user flow и уже единый `SENTRY_DSN` в коде. Разделять по платформам стоит только если дальше резко разойдутся объём и характер native crash.

96. **Рекомендация:** Canonical mobile release я бы делал как `cybervpn-mobile@<pubspec-version>+<build-number>`.
   **Почему:** Это одновременно понятно команде, CI и пользователям сторовых сборок; плюс так легче матчить release с debug symbols и rollout.

100. **Рекомендация:** Да, у mobile нужен отдельный QA smoke-сценарий на internal/staging build.
   **Почему:** Mobile сильнее других поверхностей зависит от правильной склейки release, dSYM/ProGuard/Dart debug files и store/build metadata.

101. **Рекомендация:** Staging/internal сборки должны отправлять события в отдельный environment и, при большом объёме, лучше даже в отдельный project. Local/test сборки лучше выключать.
   **Почему:** Так вы проверите интеграцию по-настоящему, но не загрязните production шумом.

### 11. Desktop и Android TV

104. **Рекомендация:** Для desktop я бы делал два проекта: `desktop-renderer` и `desktop-native`.
   **Почему:** У них разный тип ошибок, разный pipeline артефактов и разная техника символикации. В одном проекте это будет неудобно сопровождать.

105. **Рекомендация:** При этом release name у renderer и native должен быть общий по базе, например `desktop@<version>+<build>`, а слой различать тегом `runtime_layer`.
   **Почему:** Так вы сохраняете сопоставимость между двумя уровнями и не теряете удобство фильтрации.

106. **Рекомендация:** Да, корреляция renderer ↔ native нужна. Я бы использовал `installation_id`, `release`, `session_id`/`launch_id` и безопасный correlation id между IPC-вызовами.
   **Почему:** У Tauri-подобного клиента проблемы часто переходят из JS-слоя в native и обратно. Без склейки инцидент будет распадаться.

108. **Рекомендация:** Для desktop я бы включал и source maps для renderer, и native symbols уже в первой реализации.
   **Почему:** Desktop без символикации даёт очень мало практической пользы: вы увидите факт падения, но не сможете быстро его починить.

110. **Рекомендация:** Да, для desktop нужен bounded offline event cache.
   **Почему:** Это VPN-клиент, а значит нестабильная сеть — нормальный режим работы, а не крайний случай.

111. **Рекомендация:** Для Android TV я бы шёл только через internal/beta rollout до стабилизации crash pipeline.
   **Почему:** TV-поверхность обычно медленнее в итерациях и болезненнее в продовых откатах. Сначала нужна уверенность в observability.

112. **Рекомендация:** На Android TV я бы начинал с Sentry как единственного crash-инструмента.
   **Почему:** Для этого монорепо важнее единая observability-модель, чем параллельное ведение Sentry и Crashlytics. Двойная система слишком рано усложнит triage.

113. **Рекомендация:** Для Android TV я бы оставил теги `platform=android-tv`, `app_version`, `build_number`, `device_class`, `session_type` и только при реальной необходимости — безопасный tenant/household identifier в hash-виде.
   **Почему:** Это достаточно для диагностики без излишнего пользовательского контекста.

114. **Рекомендация:** На первой волне для Android TV я бы делал crash/error + mappings + release health, а ANR/performance tracing вынес бы во вторую волну.
   **Почему:** Так проще быстрее получить рабочий baseline и не утонуть в настройке сразу всех сигналов.

### 12. Alerting, ownership, CI/CD и operational model

115. **Рекомендация:** Владельцев triage я бы закрепил так: `web` → `frontend/admin/partner`, `core` → `backend/task-worker/telegram-bot`, `client-apps` → `mobile/desktop/android-tv`, `platform` → `node-fleet-controller/helix-*`.
   **Почему:** Это совпадает с эксплуатационными границами и даёт понятный on-call ownership без избыточной дробности.

116. **Рекомендация:** Да, auto-assignment по teams/CODEOWNERS/path ownership нужен.
   **Почему:** При таком количестве surface ручной triage быстро станет bottleneck и будет регулярно терять время.

117. **Рекомендация:** На первый день я бы включил GitHub integration, email и один продовый ops-канал. Если у команды операционный контур живёт в Telegram, то именно Telegram для critical alerts.
   **Почему:** Это минимально достаточный набор. Он не перегружает процесс, но уже делает alerts рабочими.

118. **Рекомендация:** Incident-grade сигналами я бы считал: new regression в `production`, error spike на auth/payment/provisioning, crash-free drop на mobile/desktop, падения control-plane Rust surface и сбои bot payment/subscription flow.
   **Почему:** Это именно те сигналы, которые бьют по деньгам, доступности и управлению платформой.

119. **Рекомендация:** Для `staging` я бы оставил только release-blocking alerts: regressions, smoke-failure, error spike на критичных flow.
   **Почему:** Если включить staging слишком широко, команда перестанет верить alerting вообще.

120. **Рекомендация:** Да, в первой итерации нужны хотя бы базовые Sentry dashboards/saved queries: обзор по surface, overview по production release и отдельные critical-flow views.
   **Почему:** Без обзорных экранов rollout превращается в ручной просмотр issue list, а это плохо масштабируется.

123. **Рекомендация:** Да, CI должен автоматически проверять, что source maps/debug files/mappings привязались к нужному release.
   **Почему:** Иначе вы узнаете о сломанной символикации только в момент инцидента, когда исправлять уже поздно.

124. **Рекомендация:** Да, обязательный post-deploy smoke event нужен для всех production-grade surface, а минимум для `backend`, `worker`, `bot`, `web`, `mobile release validation`.
   **Почему:** Это самый дешёвый способ доказать, что интеграция жива не только на build-стадии, но и после реального выката.

127. **Рекомендация:** Да, отдельный rollout-документ/матрица по ownership + privacy + tags + alerting обязателен.
   **Почему:** У вас уже не "один SDK в одном сервисе", а большая программа внедрения на монорепо. Без такой матрицы решения начнут расходиться по surface.

128. **Рекомендация:** Следующим шагом я бы просил у себя же подготовить 6 артефактов в таком порядке: `архитектурный план`, `список Sentry projects`, `env schema`, `privacy/tags contract`, `CI/CD patch plan`, `rollout roadmap + DoD`.
   **Почему:** Это правильный порядок. Сначала проектируем целевую модель, потом фиксируем naming/policy, и только затем идём в код и пайплайны.
