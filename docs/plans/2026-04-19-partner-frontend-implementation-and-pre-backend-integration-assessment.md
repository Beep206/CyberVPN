# CyberVPN Partner Frontend Implementation And Pre-Backend Integration Assessment

**Date:** 2026-04-19  
**Status:** implementation status and integration readiness assessment  
**Purpose:** зафиксировать, что уже построено в отдельном `partner` frontend-приложении, какие backend contracts уже существуют, какие части портала уже реально готовы к подключению, какие части всё ещё остаются scaffold/local-state слоем, и в каком порядке правильно идти в полноценную backend integration.

---

## 1. Role Of This Document

Этот документ нужен не для product-design и не для phase planning как таковых.

Он выполняет четыре прикладные задачи:

1. даёт цельную картину по уже реализованному `partner` frontend;
2. фиксирует фактическое состояние перед живой интеграцией с backend;
3. отделяет уже готовые canonical integration points от временных scaffold-слоёв;
4. задаёт честный integration baseline для следующих implementation задач.

Документ не заменяет:

- `2026-04-18-partner-portal-prd.md`
- `2026-04-18-partner-portal-ia-and-menu-map.md`
- `2026-04-18-partner-portal-status-and-visibility-matrix.md`
- `2026-04-18-partner-portal-role-matrix.md`
- `2026-04-18-partner-portal-lane-capability-matrix.md`
- `2026-04-18-partner-portal-onboarding-workflow-spec.md`
- `2026-04-18-partner-portal-application-review-and-approval-policy.md`
- `2026-04-18-partner-portal-surface-policy-matrix.md`
- `2026-04-18-partner-portal-phase-and-workboard-decomposition.md`
- `2026-04-19-partner-platform-full-execution-summary-and-plan-status.md`

Он sits between documentation and execution reality.

---

## 2. Input Materials Used For This Assessment

Оценка ниже собрана по трём слоям.

### 2.1 Partner Platform And Portal Documents

- `docs/plans/2026-04-17-partner-platform-spec-package-index.md`
- `docs/plans/2026-04-17-partner-platform-target-state-architecture.md`
- `docs/plans/2026-04-17-partner-platform-rulebook.md`
- `docs/plans/2026-04-17-partner-platform-api-specification-package.md`
- `docs/plans/2026-04-17-analytics-and-reporting-spec.md`
- `docs/plans/2026-04-18-partner-portal-prd.md`
- `docs/plans/2026-04-18-partner-portal-ia-and-menu-map.md`
- `docs/plans/2026-04-18-partner-portal-role-matrix.md`
- `docs/plans/2026-04-18-partner-portal-status-and-visibility-matrix.md`
- `docs/plans/2026-04-18-partner-portal-lane-capability-matrix.md`
- `docs/plans/2026-04-18-partner-portal-onboarding-workflow-spec.md`
- `docs/plans/2026-04-18-partner-portal-application-review-and-approval-policy.md`
- `docs/plans/2026-04-18-partner-portal-surface-policy-matrix.md`
- `docs/plans/2026-04-18-partner-portal-phase-and-workboard-decomposition.md`
- `docs/plans/2026-04-18-partner-portal-traceability-matrix.md`
- `docs/plans/2026-04-19-partner-platform-full-execution-summary-and-plan-status.md`

### 2.2 Frontend Partner App

Основной inspected scope:

- `partner/src/app/[locale]/(dashboard)/*`
- `partner/src/features/partner-shell/*`
- `partner/src/features/partner-portal-state/*`
- `partner/src/features/partner-onboarding/*`
- `partner/src/features/partner-commercial/*`
- `partner/src/features/partner-compliance/*`
- `partner/src/features/partner-operations/*`
- `partner/src/features/partner-reporting/*`
- `partner/src/features/partner-integrations/*`
- `partner/src/features/partner-reseller/*`
- `partner/src/lib/api/partner-portal.ts`

### 2.3 Backend Partner And Auth Domains

Основной inspected scope:

- `backend/src/presentation/api/v1/partners/routes.py`
- `backend/src/presentation/api/v1/partner_payout_accounts/routes.py`
- `backend/src/presentation/api/v1/policy_acceptance/routes.py`
- `backend/src/presentation/api/v1/notifications/routes.py`
- `backend/src/presentation/api/v1/reporting/routes.py`
- `backend/src/presentation/dependencies/partner_workspace.py`
- `backend/src/presentation/dependencies/auth.py`
- `backend/src/application/use_cases/auth_realms/resolve_realm.py`
- `backend/src/domain/entities/auth_realm.py`
- `backend/src/infrastructure/database/models/admin_user_model.py`

---

## 3. Executive Conclusion

Мой главный вывод после повторной оценки такой:

`partner` frontend как отдельное приложение уже построен на правильной архитектурной основе и в целом соответствует portal package. Это уже не affiliate-cabinet, а отдельный partner workspace surface.

Но readiness у этого приложения неоднородный.

### 3.1 Что уже действительно хорошо

- отдельное `partner` приложение существует как самостоятельный workspace;
- canonical partner IA перенесена в приложение;
- menu, route visibility, release rings, status bands и lane-aware restrictions уже встроены в shell;
- значительная часть operational portal surface уже умеет читать canonical backend data;
- часть важных partner actions уже реально wired на backend routes;
- backend по partner-workspace domain оказался богаче, чем выглядело по ранним UI assumptions.

### 3.2 Что пока нельзя считать закрытым

- self-serve applicant onboarding пока не интегрирован end-to-end;
- `application`, `organization`, `settings`, `team`, `legal`, `notifications` всё ещё не доведены до полного canonical backend-backed состояния;
- partner realm separation есть в backend design, но её надо подтвердить реальным host/realm wiring;
- frontend access gate пока слишком мягкий и должен опираться на backend realm/session/permissions, а не на FE role heuristic.

### 3.3 Итоговая оценка готовности

Если разделять readiness по контурам:

- **frontend shell readiness:** высокая
- **operational surface readiness:** выше средней
- **self-serve onboarding readiness:** средняя или ниже средней
- **backend partner domain readiness:** высокая для post-approval workspace flows
- **realm/session integration certainty:** средняя, требует верификации

Итоговый practical verdict:

можно и нужно переходить к backend integration, но правильный старт не с добавления новых страниц, а с перевода существующих portal surfaces с local/scaffold state на backend source of truth.

---

## 4. Target Product Model That The Frontend Already Aligns To

После document pass и implementation cycles `partner` app уже выровнен под правильную модель:

- отдельный `partner realm`
- отдельный `partner workspace`
- governed onboarding, а не instant activation
- state-aware portal surface
- lane-aware portal surface
- role-aware portal surface
- release-ring-aware rollout
- separate partner reporting, finance, compliance, integrations, reseller scope

Это критично, потому что новый фронтенд уже не мыслит себя расширением consumer dashboard и не пытается повторять старый `frontend/(dashboard)/partner`.

В этом смысле product direction выбрана правильно.

---

## 5. What Was Built In The Partner Frontend

Ниже не план, а фактический implementation inventory.

## 5.1 Separate App And Workspace Bootstrap

Отдельное приложение `partner/` уже существует и не является route group внутри `frontend` или `admin`.

Что это значит practically:

- отдельный workspace;
- отдельный `package.json`;
- отдельный build/lint/dev surface;
- собственный route tree;
- собственный shell;
- собственные messages;
- отдельная точка будущего partner-host rollout.

Это фундаментально правильно для дальнейшей integration, потому что portal surface не будет конкурировать с consumer semantics.

---

## 5.2 Canonical Portal Route Surface

В `partner` уже заведено canonical top-level route family:

- `/dashboard`
- `/application`
- `/organization`
- `/team`
- `/programs`
- `/legal`
- `/codes`
- `/campaigns`
- `/conversions`
- `/analytics`
- `/finance`
- `/compliance`
- `/integrations`
- `/cases`
- `/notifications`
- `/settings`
- `/reseller`

Canonical registry уже зафиксирован в:

- `partner/src/features/partner-shell/config/section-registry.ts`

Это важно, потому что route truth уже совпадает с portal package, а не с admin IA и не с legacy referral semantics.

---

## 5.3 Phase-By-Phase Frontend Buildout

Ниже зафиксировано, что было фактически сделано по внутренним portal phases.

### PP0. App Bootstrap And Canonical Shell

В рамках `PP0` было сделано:

- separate partner app bootstrap;
- canonical section registry;
- partner-native sidebar and mobile navigation;
- удаление публичной зависимости от admin-shaped route space;
- перевод shell на partner IA;
- базовый status-aware route model.

Итог:

у приложения появился правильный каркас, на который уже можно было насаживать governed workspace portal.

### PP1. Identity And Application Foundation

В рамках `PP1` были собраны:

- public auth routes;
- staged application foundation;
- foundation screens для `application`;
- starter-profile слой для `organization`;
- foundation security/settings слой.

Но здесь важно не путать:

это был foundation UI slice, а не fully canonical onboarding contract.

### PP2. Applicant UX And Requested-Info Loop

В рамках `PP2` были добавлены:

- applicant-safe dashboard behavior;
- cases/review area;
- notifications surface;
- status-aware pending/blocked UX;
- visibility logic для applicant/probation/active scenarios.

Итог:

pending workspace больше не выглядит как пустой кабинет.

### PP3. Workspace Core

В рамках `PP3` были собраны:

- `team`
- `programs`
- `legal`
- role-aware gating
- launch role set modeling

Это довело non-commercial workspace core до usable состояния на уровне shell и UX.

### PP4. Commercial Foundation

В рамках `PP4` были собраны:

- `codes`
- `campaigns`
- `compliance`
- lane-aware commercial gating

Это уже не просто route placeholders, а работающий commercial layer с разной логикой для Creator, Performance и Reseller.

### PP5. Reporting, Finance, Cases

В рамках `PP5` были собраны:

- `analytics`
- `finance`
- richer `cases`
- dashboard reporting/finance summary

Этот слой сделал portal финансово и operationally полезным.

### PP6. Advanced Operational Surfaces

В рамках `PP6` были собраны:

- `conversions`
- `integrations`
- `reseller`

Это продвинуло портал к target-state platform model.

### PP7. Hardening And Release Gating

В рамках `PP7` были собраны:

- release-ring-aware runtime behavior;
- unified route gating;
- status/role/lane/release-ring alignment;
- расширенное regression coverage;
- hardening shell before live backend wiring.

Итог:

frontend уже не просто показывает страницы, а моделирует rollout-safe portal behavior.

---

## 5.4 Partner Frontend Architecture That Exists Today

Текущий `partner` frontend состоит из трёх слоёв.

### Layer A. Canonical Shell And Section Registry

Основные задачи:

- route truth;
- menu truth;
- release ring truth;
- section metadata;
- phase targeting;
- route labels and hints.

Ключевой файл:

- `partner/src/features/partner-shell/config/section-registry.ts`

### Layer B. Portal State And Visibility Policy

Основные задачи:

- workspace status model;
- role model;
- lane model;
- readiness overlays;
- visibility bands;
- route block reasons;
- route visibility mapping.

Ключевые файлы:

- `partner/src/features/partner-portal-state/lib/portal-state.ts`
- `partner/src/features/partner-portal-state/lib/portal-visibility.ts`

Здесь уже зафиксированы:

- `workspace_status`
- `finance_readiness`
- `compliance_readiness`
- `technical_readiness`
- `governance_state`
- `lane_membership_status`
- `notification kinds`
- `case kinds`
- `legal document statuses`
- `release rings`

Это соответствует product docs и предотвращает смешение status objects.

### Layer C. Runtime State From Backend Contracts

Основные задачи:

- загрузка active workspace;
- загрузка partner-workspace operational slices;
- маппинг permission-aware backend data в portal UI state;
- fallback в local state только там, где canonical workspace ещё не активен.

Ключевые файлы:

- `partner/src/lib/api/partner-portal.ts`
- `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts`
- `partner/src/features/partner-portal-state/lib/runtime-state.ts`

Это уже реальный integration bridge, а не чистый mock layer.

---

## 5.5 What The Frontend Already Does Well

На текущем этапе сильные стороны `partner` app такие.

### A. Correct Information Architecture

Frontend больше не shaped around:

- consumer referral
- partner-cabinet minimalism
- admin leftovers as public IA

Он shaped around:

- workspace lifecycle
- commercial operations
- finance/reporting
- compliance/governance
- reseller/performance specialization

### B. Proper Visibility Logic

В приложении уже работает visibility matrix для состояний:

- pre-submit
- review
- probation
- active
- constrained
- terminal

И это отдельный плюс, потому что menu access уже не закодирован случайными if-ами в компонентах.

### C. Release Ring Awareness

Frontend умеет удерживать части surface через rollout-gating, что критично для постепенного запуска.

### D. Lane Awareness

Creator, Performance и Reseller не сливаются в одну абстрактную роль.

### E. Backend-Friendly Runtime Model

Новый frontend уже построен так, что его можно постепенно пересаживать на canonical backend data, не переписывая IA с нуля.

---

## 6. What Is Already Connected To Canonical Backend Contracts

Это ключевой вывод повторной оценки.

Новый `partner` frontend уже частично интегрирован с backend. Не формально, а по-настоящему.

## 6.1 Canonical Partner Portal API Client Already Exists

Файл:

- `partner/src/lib/api/partner-portal.ts`

Он уже знает, как ходить за:

- `listMyWorkspaces`
- `getWorkspace`
- `getWorkspacePrograms`
- `listWorkspaceCodes`
- `listWorkspaceStatements`
- `listWorkspaceConversionRecords`
- `getWorkspaceConversionExplainability`
- `listWorkspaceAnalyticsMetrics`
- `listWorkspaceReportExports`
- `scheduleWorkspaceReportExport`
- `listWorkspaceReviewRequests`
- `respondToWorkspaceReviewRequest`
- `listWorkspaceTrafficDeclarations`
- `submitWorkspaceTrafficDeclaration`
- `submitWorkspaceCreativeApproval`
- `listWorkspaceCases`
- `respondToWorkspaceCase`
- `markWorkspaceCaseReadyForOps`
- `listWorkspaceIntegrationCredentials`
- `listWorkspaceIntegrationDeliveryLogs`
- `getWorkspacePostbackReadiness`
- `listWorkspacePayoutAccounts`
- `getPayoutAccountEligibility`

Это означает, что integration base в приложении уже существует.

---

## 6.2 Runtime Query Layer Already Pulls Canonical Data

Файл:

- `partner/src/features/partner-portal-state/lib/use-partner-portal-runtime-state.ts`

Он уже подтягивает:

- active workspace;
- workspace itself;
- codes;
- statements;
- payout accounts;
- conversion records;
- analytics metrics;
- report exports;
- review requests;
- cases;
- integration credentials;
- integration delivery logs;
- traffic declarations;
- workspace programs;
- notification preferences.

То есть operational read surface уже частично сидит на backend truth.

---

## 6.3 Runtime Mapping Already Respects Backend Permission Model

Файл:

- `partner/src/features/partner-portal-state/lib/runtime-state.ts`

Он уже учитывает:

- `workspace_read`
- `codes_read`
- `earnings_read`
- `payouts_read`
- `traffic_read`
- `integrations_read`

И уже собирает из backend response:

- finance statements
- payout accounts
- conversion records
- analytics metrics
- exports
- review requests
- cases
- integration credentials
- traffic declarations
- team members
- codes

Причём это permission-aware mapping, а не слепой merge.

---

## 6.4 Some Real Write Actions Are Already Live-Wired

Это особенно важно, потому что приложение уже делает не только reads.

### Compliance

Файл:

- `partner/src/features/partner-compliance/components/compliance-center-page.tsx`

Уже wired:

- traffic declaration submission
- creative approval submission

### Reporting

Файл:

- `partner/src/features/partner-reporting/components/analytics-exports-page.tsx`

Уже wired:

- scheduling report exports

### Cases And Review Loop

Файл:

- `partner/src/features/partner-portal-state/components/partner-cases-page.tsx`

Уже wired:

- response to review requests
- response to cases
- mark case ready for ops

Это означает, что frontend уже не просто симулирует behavior. Некоторые action rails уже реально готовы к backend usage.

---

## 7. What Still Remains Local, Scaffolded, Or Simulated

Вот где проходит главный integration seam.

## 7.1 Application Foundation Is Still Local Draft

Файл:

- `partner/src/features/partner-onboarding/components/application-foundation-page.tsx`

Сейчас:

- draft грузится локально;
- draft сохраняется локально;
- readiness mark идёт через local draft state;
- submit-like behavior пока не превращён в canonical backend application workflow.

Итог:

`application` сегодня является хорошим UI foundation, но не real governed onboarding contract.

---

## 7.2 Organization Is Still A Starter Profile Layer

Файл:

- `partner/src/features/partner-onboarding/components/organization-starter-page.tsx`

Сейчас:

- данные читаются из local draft;
- данные сохраняются локально;
- canonical workspace переводит экран в read-only mode;
- real organization persistence на backend contract пока не реализована.

Итог:

это starter UX, а не финальный organization system of record.

---

## 7.3 Settings Still Use Foundation Storage

Файлы:

- `partner/src/features/partner-settings/components/settings-foundation-page.tsx`
- `partner/src/lib/api/profile.ts`

Важно:

- `settings` пока живут на local storage draft;
- `profileApi` сам помечает текущий `/users/me/profile` как placeholder;
- persistence profile/settings ещё не может считаться production truth для portal.

Итог:

settings surface есть, но backend-backed account/workspace settings ещё не закрыты.

---

## 7.4 Team Is Still Not Fully Canonicalized

Файл:

- `partner/src/features/partner-workspace/components/team-access-page.tsx`

Сейчас:

- экран опирается на local portal state;
- real member-management action rail ещё не доведён до full workspace-membership UI integration;
- backend route для member add уже существует, но этот экран ещё не является финальной canonical membership surface.

---

## 7.5 Legal Is Still Not Wired To Real Policy Acceptance History

Файл:

- `partner/src/features/partner-legal/components/legal-documents-page.tsx`

Сейчас:

- экран показывает legal/document model из local portal state;
- acceptance history и real policy acceptance log ещё не тянутся из canonical backend acceptance surface;
- partner-facing legal acceptance flow ещё не переведён в real backend-owned document lifecycle.

---

## 7.6 Notifications Page Is Not A Real Partner Inbox Yet

Файл:

- `partner/src/features/partner-portal-state/components/partner-notifications-page.tsx`

Сейчас:

- список уведомлений живёт в local portal state;
- mark-as-read идёт через local store;
- backend confirmed only notification preferences API, а не полноценный inbox/feed route.

Итог:

`notifications` пока является portal UX placeholder, а не real notification center.

---

## 7.7 Dashboard Still Exposes Simulation Controls

Файл:

- `partner/src/features/partner-portal-state/components/partner-dashboard-page.tsx`

Сейчас:

- scenario selector остаётся в приложении;
- workspace role simulation остаётся в приложении;
- canonical workspace presence отключает часть simulation behavior, но сам слой всё ещё присутствует.

Это хороший engineering tool, но перед production backend rollout его нужно аккуратно удержать или убрать из public runtime behavior.

---

## 7.8 Frontend Access Gate Is Too Soft

Файл:

- `partner/src/features/auth/lib/partner-access.ts`

Сейчас:

- portal access считается разрешённым для любого non-empty `role`.

Это означает:

frontend сам по себе ещё не является надёжным guard layer и должен полностью опираться на backend realm/session/workspace permissions.

---

## 8. Backend Re-Assessment After Reviewing Real Code

Это вторая главная часть документа.

Повторная оценка backend показывает, что он уже во многом готов под partner portal.

## 8.1 Backend Already Has A Rich Canonical Partner-Workspace API

Ключевой файл:

- `backend/src/presentation/api/v1/partners/routes.py`

Что там уже есть для partner-facing workspace surface:

- list my workspaces;
- get workspace;
- get workspace programs;
- list workspace codes;
- list workspace statements;
- list workspace conversion records;
- get conversion explainability;
- list workspace analytics metrics;
- list workspace report exports;
- schedule workspace report export;
- list workspace integration credentials;
- rotate integration credential;
- list integration delivery logs;
- get postback readiness;
- list review requests;
- respond to review request;
- list traffic declarations;
- submit traffic declaration;
- submit creative approval;
- list cases;
- respond to case;
- mark case ready for ops;
- add workspace member.

Это означает, что backend уже думает категориями `partner workspace portal`, а не только `legacy partner code dashboard`.

---

## 8.2 Workspace Permission Model Is Real

Ключевой файл:

- `backend/src/presentation/dependencies/partner_workspace.py`

Что уже есть:

- membership resolution;
- role-based permission keys;
- active-membership checks;
- internal admin override;
- permission-scoped access dependency.

Это хороший признак, потому что portal можно строить поверх real workspace permission model, а не выдумывать свой access layer на frontend.

---

## 8.3 Payout Domain Is Already Real

Ключевой файл:

- `backend/src/presentation/api/v1/partner_payout_accounts/routes.py`

Что уже есть:

- create payout account;
- list payout accounts;
- get payout account;
- eligibility check;
- make default;
- admin verify/suspend/archive flows.

Это означает, что finance onboarding может опираться на реальные contract points уже сейчас.

---

## 8.4 Policy Acceptance Domain Already Exists

Ключевой файл:

- `backend/src/presentation/api/v1/policy_acceptance/routes.py`

Что уже есть:

- create policy acceptance;
- list my policy acceptance;
- admin review of policy acceptance records.

Это хороший сигнал для будущего `legal` surface.

---

## 8.5 Reporting Layer Already Exists In Backend Form

Related files:

- `backend/src/presentation/api/v1/partners/routes.py`
- `backend/src/presentation/api/v1/reporting/routes.py`

То есть:

- partner statements;
- conversion records;
- explainability;
- analytics metrics;
- exports;
- reporting token model

уже присутствуют в backend slice.

---

## 8.6 Notifications Are Only Partially Backed

Ключевой файл:

- `backend/src/presentation/api/v1/notifications/routes.py`

Что confirmed:

- notification preferences read/update

Что не confirmed как canonical partner route:

- полноценный notification inbox/feed;
- partner-facing notification event list;
- read-state lifecycle for partner portal notifications.

Именно поэтому `notifications` во фронтенде пока выглядит как placeholder surface.

---

## 9. Auth And Realm Model Assessment

Это самый важный integration seam.

## 9.1 Separate Partner Realm Exists In The Backend Domain

Ключевой файл:

- `backend/src/domain/entities/auth_realm.py`

В default realm set уже есть:

- `customer`
- `partner`
- `admin`
- `service`

У `partner` есть собственные:

- `realm_key`
- `realm_type`
- `audience`
- `cookie_namespace`

Архитектурно это правильно.

---

## 9.2 Partner Principal Model Also Exists

Ключевые файлы:

- `backend/src/presentation/dependencies/auth.py`
- `backend/src/infrastructure/database/models/admin_user_model.py`

Что видно:

- partner principal today sits on `AdminUserModel`;
- `AdminUserModel` already has `auth_realm_id`;
- `get_current_principal_actor` distinguishes partner realm and falls back to `PARTNER_OPERATOR` principal class when realm type is `partner`.

Это не идеальная long-term semantics, но для integration bootstrap это уже рабочая база.

---

## 9.3 Main Risk: Realm Resolution Depends On Host/Header Mapping

Ключевой файл:

- `backend/src/application/use_cases/auth_realms/resolve_realm.py`

Порядок resolution сейчас такой:

1. explicit auth realm header
2. host or forwarded host
3. fallback default realm by inferred realm type

Это означает:

partner realm separation в runtime будет корректной только если partner host реально промаплен на partner realm.

Именно здесь находится основной integration risk.

Это не bug statement, а verified architectural dependency.

До подтверждения live host-to-realm wiring нельзя считать auth/session contour fully closed.

---

## 10. Readiness Matrix By Surface

Ниже practical readiness view.

| Surface | Frontend status | Backend status | Integration verdict | Main note |
|---|---|---|---|---|
| Shell and navigation | strong | n/a | ready | canonical route model уже собран |
| Dashboard | partial-to-strong | strong | ready with cleanup | runtime-backed, но simulation слой ещё присутствует |
| Auth/session | partial | strong in design | needs verification | realm/host mapping must be proven |
| Workspace discovery | strong | strong | ready | canonical workspaces API already exists |
| Application onboarding | partial | partial | not ready end-to-end | no canonical self-serve applicant flow yet |
| Organization | partial | partial | not ready | starter profile exists, canonical persistence not closed |
| Team | partial | medium-to-strong | needs wiring | backend members domain exists, UI still local-driven |
| Programs | strong | strong | ready | good candidate for live integration |
| Legal | partial | medium-to-strong | needs wiring | policy acceptance exists, UI still local-driven |
| Codes | strong | strong | ready | canonical route exists on both sides |
| Campaigns | medium | medium | ready for staged integration | can deepen gradually |
| Compliance | strong | strong | ready | write actions already wired |
| Cases/review loop | strong | strong | ready | write actions already wired |
| Analytics | strong | strong | ready | runtime + exports already wired |
| Finance | medium-to-strong | strong | ready for staged integration | payout onboarding domain exists |
| Conversions | strong | strong | ready | canonical conversion + explainability backend exists |
| Integrations | medium-to-strong | strong | ready for staged integration | credentials/logs/postback readiness exist |
| Notifications | partial | weak-to-medium | needs backend feed contract | prefs exist, feed not confirmed |
| Settings/profile | partial | weak | not ready | profile persistence still placeholder |
| Reseller | medium | medium-to-strong | staged rollout only | should stay gated by lane and release ring |

---

## 11. What This Means In Practice

Если смотреть честно, сейчас ситуация такая:

frontend partner portal уже достаточно зрелый, чтобы:

- подключать реальные partner workspaces;
- тянуть программы, коды, аналитку, кейсы, compliance, integrations, payouts;
- строить live runtime state поверх backend truth;
- переходить от portal simulation к canonical state.

Но он ещё недостаточно зрелый, чтобы без дополнительных backend/contract шагов считать готовыми:

- public apply;
- full applicant workflow;
- final organization profile persistence;
- full legal acceptance UX;
- real notification center;
- final settings/profile persistence.

Это и есть граница between “frontend built” and “frontend fully integrated”.

---

## 12. Main Risks And Seams Before Full Integration

Ниже те места, которые действительно надо закрыть, а не cosmetic issues.

## 12.1 No Canonical Self-Serve Application Contract Yet

Portal docs требуют self-serve application with governed activation.

Текущее состояние:

- frontend foundation есть;
- admin workspace bootstrap route есть;
- partner-facing self-serve application contract в inspected backend scope не обнаружен.

Это главный продуктовый шов.

---

## 12.2 Realm And Session Wiring Must Be Proven In Runtime

Нельзя считать integration завершённой, пока не доказано, что:

- partner host резолвится в `partner` realm;
- partner tokens получают правильный audience;
- partner cookies/namespace не конфликтуют с admin/customer;
- `partner` app реально аутентифицируется как partner surface.

---

## 12.3 Several Core Sections Still Depend On Local State

Это касается:

- `application`
- `organization`
- `settings`
- `team`
- `legal`
- `notifications`

До перевода этих разделов на canonical APIs broad-activation делать нельзя.

---

## 12.4 Settings/Profile Backend Is Not A Reliable Source Of Truth Yet

Current profile client сам говорит, что persistence placeholder.

Это означает, что user/account/workspace settings ещё нельзя принимать за production-grade contract.

---

## 12.5 Frontend Access Check Must Not Remain The Final Guard

Текущий `partner-access.ts` годится как temporary shell gate, но не как security boundary.

Final access truth должен быть таким:

- realm
- session audience
- workspace membership
- permission keys
- route/surface policy

---

## 13. Recommended Integration Order

Вот порядок, который считаю правильным после повторной оценки.

## Step 1. Prove Realm And Session Truth

Подтвердить end-to-end:

- partner host to auth realm mapping;
- login/session on partner host;
- correct audience and realm validation;
- correct cookie namespace;
- partner-workspace access for authenticated partner operator.

Это должен быть первый live integration slice.

## Step 2. Make Workspace Runtime The Single Source Of Truth

Подключить canonical workspace payload к:

- dashboard
- sidebar
- route guards
- status visibility
- release ring gating
- capability resolution

Часть этого уже сделана, но теперь надо считать её primary path, а не hybrid convenience layer.

## Step 3. Replace Local Applicant Foundation With Real Backend Workflow

Нужно закрыть:

- create workspace or apply flow;
- staged application persistence;
- submit for review;
- needs-info loop;
- review state updates;
- requested documents/evidence handling.

Это главный next product-integration block.

## Step 4. Canonicalize Core Workspace Sections

Перевести на backend truth:

- organization
- team
- legal
- settings
- notifications

Только после этого portal станет реально operating surface, а не partially simulated shell.

## Step 5. Deepen Already Ready Operational Areas

После закрытия source-of-truth seam можно углублять:

- payout account create/default flows
- integration credential rotation
- explainability drill-downs
- report export scheduling UX
- richer cases/disputes
- reseller-specific controls

---

## 14. What Should Not Be Done Next

Есть несколько неверных ходов, которых надо избежать.

### A. Не надо возвращаться к legacy `frontend` partner/referral model

Старый слой в `frontend/src/lib/api/partner.ts` и related screens слишком узкий и не соответствует новому portal model.

### B. Не надо пытаться закрыть onboarding только фронтендом

Self-serve application тут backend-shaped problem.

### C. Не надо строить дальше новые advanced pages поверх local simulated state

Это увеличит техдолг и усложнит backend cutover.

### D. Не надо воспринимать красивый UI readiness как production integration readiness

Главный remaining issue сейчас не в дизайне и не в menu, а в source-of-truth.

---

## 15. Honest Final Assessment

Если формулировать предельно прямо:

я уже собрал полноценный `partner` frontend как отдельное приложение с правильной portal architecture, canonical IA, state-aware shell, lane-aware behavior, role-aware visibility и release-ring-aware rollout model.

И это хороший результат.

Но после повторной оценки с кодом backend стало ясно:

основная задача следующего этапа не “достроить ещё один экран”, а перевести портал из hybrid state model в canonical backend-owned runtime model.

Готовность на сегодня можно описать так:

- как frontend platform foundation партнёрка построена хорошо;
- как operational portal для post-approval workspace она уже близка к реальной интеграции;
- как end-to-end self-serve governed onboarding surface она пока не закрыта;
- как fully backend-backed portal она ещё находится в переходном состоянии.

Мой практический verdict:

структурно проект идёт в правильном направлении, переделывать архитектуру не нужно, но перед broad integration и тем более перед broad activation нужно закрыть четыре вещи:

1. realm/session truth  
2. applicant workflow contracts  
3. canonicalization of still-local sections  
4. real settings/legal/notification source of truth

После этого `partner` app можно будет считать не просто построенным фронтендом партнёрки, а полноценным integrated partner portal.

---

## 16. Recommended Next Workstream

Самый логичный следующий workstream после этого документа:

**Partner Backend Integration Backbone**

Состав:

1. partner realm host verification  
2. partner session and workspace bootstrap payload  
3. canonical application workflow API wiring  
4. organization/team/legal/settings canonicalization  
5. notification feed and review/case event consistency  

Это правильнее, чем открывать новый portal UI phase.

---

## 17. Final One-Line Summary

`partner` frontend уже построен как отдельный, зрелый и архитектурно правильный workspace portal, но следующий решающий шаг теперь находится на границе frontend and backend truth: нужно не расширять simulation, а добивать canonical integration.
