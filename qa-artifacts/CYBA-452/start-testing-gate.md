# CYBA-452 Gate старта тестирования

Дата: 2026-06-04
Владелец: `qa-lead-flow-mapper`
Решение: `GO - local-stage synthetic QA`

## Цель gate

Решить, можно ли начинать manual QA для child work по [CYBA-451](/CYBA/issues/CYBA-451):

- [CYBA-456](/CYBA/issues/CYBA-456) client frontend flows;
- [CYBA-457](/CYBA/issues/CYBA-457) partner portal flows;
- [CYBA-458](/CYBA/issues/CYBA-458) admin panel flows;
- [CYBA-459](/CYBA/issues/CYBA-459) security and RBAC boundaries;
- [CYBA-460](/CYBA/issues/CYBA-460) accessibility, i18n and responsive review;
- [CYBA-461](/CYBA/issues/CYBA-461) final evidence summary.

Context7 docs checked: `/vercel/next.js/v16.2.2` через `ctx7 docs` для Next.js 16 `proxy.ts` и App Router route discovery. Остальные gate items: manual UI/business-flow readiness findings.

## Проверенные inputs

- Root `package.json` workspace scripts и workspace list.
- `frontend/package.json`, `admin/package.json`, `partner/package.json`.
- `frontend/README.md`, `admin/README.md`, `partner/README.md`.
- `backend/.env.example` template only; real `.env` values не читались.
- Next.js route files в `frontend/src/app`, `partner/src/app`, `admin/src/app`.
- `src/proxy.ts` presence в `frontend`, `partner`, `admin`.
- Current issue state для [CYBA-452](/CYBA/issues/CYBA-452) и blocked child issues.

## GO/NO-GO критерии

| Критерий | Что требуется для старта manual QA | Текущий результат |
| --- | --- | --- |
| Approved non-production URLs | Client, partner, admin, backend/API подтверждены как local/staging/dedicated QA и не production-backed | `GO`, partner `partial` local-dev/source-level |
| Synthetic account map | Client, partner, admin roles и key states доступны через approved channels | `GO` for listed synthetic roles/states |
| Integration safety | Payments, email, Telegram, OAuth, Remnawave являются sandbox/mock или explicitly blocked/not-tested | `GO` with unsupported integrations marked `blocked/not-tested`; Remnawave requires separate approval |
| Evidence redaction policy | Evidence/redaction rules задокументированы | `GO` |
| Route scope | Route inventory есть для client, partner, admin | `GO` |
| Dependency child tasks | Child manual QA tasks остаются blocked, пока gate не пройден | `GO` |
| Production safety | Без production testing, production data, destructive operations, env edits, code fixes, dependency changes | `GO` |

## Resolved gate inputs

| Input | Evidence | Result |
| --- | --- | --- |
| Non-production URLs | Operator approved `http://127.0.0.1:13000`, `http://127.0.0.1:13001`, `http://127.0.0.1:18080`; partner local-dev/source-level only. | Resolved for local-stage scope |
| Synthetic account credentials/states | Protected file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env` exists outside git with `0600` mode per operator handoff. | Resolved without credential disclosure |
| Backend/API data source | Operator smoke: admin and partner 2FA completion 200, customer login 200, disabled customer 401. | Resolved for synthetic stage1 |
| Payment/Telegram/destructive safety | Operator safety limits prohibit production customer/payment data, real payment/Telegram operations, destructive admin actions. | Resolved as constrained scope |
| Remnawave/provisioning | Not approved. | Explicitly not-tested until separate approval |

## Обязательный handoff перед child QA

После разблокировки этого gate владельцы child QA должны получить:

- confirmed URL table;
- account/role/state map без credentials в Markdown;
- integration mode table с sandbox/mock/not-tested decisions;
- severity and evidence bar:
  - каждый bug содержит exact repro steps, expected result, actual result, environment, user role/state, severity и sanitized evidence;
  - P0/P1 findings содержат screenshot или stronger evidence;
  - security/RBAC details остаются внутри issue и escalated to SecurityEngineer;
  - product gaps и blocked/not-tested areas отделены от bugs.

## Текущее решение

`GO - local-stage synthetic QA`.

Manual QA may start or resume in the approved synthetic/local-stage scope. Child issues must keep production data, real payment/Telegram operations, destructive admin actions, and Remnawave/provisioning out of scope, and must record unsupported areas as `blocked/not-tested` with owner/action.
