# CYBA-452 Готовность environment

Дата: 2026-06-04
Владелец: `qa-lead-flow-mapper`
Статус gate: `GO - local-stage synthetic QA`

## Назначение

Подтвердить, что environment безопасен и достаточен для manual QA audit по [CYBA-451](/CYBA/issues/CYBA-451). Это readiness gate, а не test execution report.

## Факты repo/workspace

| Область | Evidence | Статус |
| --- | --- | --- |
| Monorepo workspaces | Root `package.json` содержит `admin`, `frontend`, `partner`, `apps/*`, `services/*`, `packages/*`. | Ready |
| Client app command | `npm run dev` или `npm run dev -w frontend`; client README указывает `http://localhost:3000`. | Ready, только local |
| Admin app command | `npm run dev:admin`; admin README указывает `http://localhost:3001`. | Ready, только local |
| Partner app command | `npm run dev:partner`; partner README указывает `http://localhost:3002`. | Ready, только local |
| Backend API template | `backend/.env.example` документирует `API_PORT=8000`, `DATABASE_URL`, `REDIS_URL`, Remnawave, auth, payment, CORS, OAuth, Telegram и metrics settings. | Template ready |
| Next.js proxy convention | `frontend/src/proxy.ts`, `admin/src/proxy.ts` и `partner/src/proxy.ts` присутствуют. | Ready |

Context7 docs checked: `/vercel/next.js/v16.2.2` через `ctx7 docs`; проверены Next.js 16 `proxy.ts` convention и App Router dynamic segments. MCP Context7 недоступен из-за monthly quota exceeded.

## Non-production checklist безопасности

| Gate | Обязательное условие | Статус | Owner/action |
| --- | --- | --- | --- |
| Environment classification | Явно local/staging/dedicated QA, не production | Ready | Operator verified local stage1 synthetic package. |
| Backend data source | Только synthetic/sandbox/test DB | Ready | Operator verified synthetic package and backend smoke without exposing credentials. |
| Redis/cache | Только test cache, без production sessions | Ready for scope | No production session evidence is used; QA must not store cookies/tokens. |
| Remnawave | Только sandbox/mock/non-production target | Not-tested | Remnawave/provisioning remains out of scope unless explicitly approved separately. |
| Payments | Только sandbox/mock; без real capture, refund, payout, settlement execution | Limited | Pricing catalog seed is available; real payment operations remain prohibited and payment flows must be sandbox/mock/read-only or marked not-tested. |
| Email | Только sandbox/mail catcher/test mailbox | Blocked/not-tested unless fixture discovered | No secret or mailbox content may be pasted into evidence. |
| Telegram | Только test bot/sandbox path; без real user `initData` в evidence | Blocked/not-tested | No real Telegram operations or real `initData` evidence. |
| OAuth | Test provider credentials или mocked callbacks only | Blocked/not-tested | Use only approved test provider/mocked callbacks if available. |
| Observability | Sentry/PostHog/log evidence redaction rules активны | Ready as policy | Store sanitized screenshots/notes only; no tokens, cookies, HAR secrets, customer data, or production PII. |
| Production guard | Без production secrets, customer data, payment data, destructive admin operations | Ready как policy | QA lead enforces; Board approval required to change. |

## Local verification state

Initial readiness run did not start browser QA because the gate was `NO-GO`. Later operator handoffs superseded that state:

- `2026-06-04T15:48:51Z`: partial local-stage QA approved for public/read-only/redirect/a11y scope.
- `2026-06-04T16:04:49Z`: stage1 synthetic QA package available with protected credentials outside git.
- `2026-06-04T16:11:05Z`: operator verified readiness gate is `GO` for local-stage synthetic QA.

Новые безопасные inputs:

- client frontend: `http://127.0.0.1:13000`;
- admin panel: `http://127.0.0.1:13001`;
- backend API: `http://127.0.0.1:18080`;
- partner portal: no deployed stage1 container; local-dev/source-level QA only if a safe dev preview is started;
- synthetic credentials path: `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`, not read into this artifact and not safe to paste into comments/evidence.

## Решение по environment readiness

`GO - local-stage synthetic QA`.

Manual QA can proceed inside the approved synthetic/local-stage boundaries. Any flow needing production data, real payment/Telegram operation, destructive admin action, or Remnawave/provisioning remains blocked until separate approval.
