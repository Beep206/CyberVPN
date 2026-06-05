# CYBA-452 Карта test data

Дата: 2026-06-04
Владелец: `qa-lead-flow-mapper`
Статус gate: `GO - local-stage synthetic QA`

## Правила работы с test data

- Хранить только role names, state labels и fixture IDs, если они sanitized.
- Не хранить JWT, cookies, refresh tokens, passwords, `.env` values, payment secrets, customer PII, OAuth codes или real Telegram `initData`.
- Использовать только synthetic users и sandbox payment/provider states.
- Если evidence содержит sensitive data, отредактировать его до attachment/comment/report.

Context7 docs checked: N/A - manual UI/business-flow finding.

## Матрица обязательных аккаунтов

| Поверхность | Role/state | Для каких flows нужно | Статус | Owner/action |
| --- | --- | --- | --- | --- |
| Client | Анонимный посетитель | Marketing, pricing, legal, download, auth entry, dashboard redirect | Ready | Use `http://127.0.0.1:13000`. |
| Client | Зарегистрированный пользователь, email не verified | Registration, verify, resend/blocked dashboard behavior | Blocked/not-tested unless fixture discovered | No credentials in evidence. |
| Client | Verified user без subscription | Login, dashboard empty states, pricing/checkout entry, support, settings | Ready | Synthetic customer web active user exists in protected secret file. |
| Client | Active subscriber | Servers/devices/subscriptions/wallet/service access | Blocked/not-tested | Non-production VPN/service entitlement was not approved; mark as not-tested unless safe fixture is confirmed. |
| Client | Expired/cancelled subscriber | Renewal, entitlement loss, support/payment history | Blocked/not-tested | Use only synthetic states if discoverable without secret leakage. |
| Client | 2FA pending/enabled | 2FA complete/pending same-origin routes и login recovery | Ready for customer TOTP state | Synthetic customer web TOTP user exists in protected secret file. |
| Client | Passkey enrolled/fresh auth required | Settings/security/passkey checks в scope | Blocked/not-tested unless fixture discovered | Safe passkey fixture not listed in operator handoff. |
| Client Mini App | Telegram test user | Mini App home/plans/payments/wallet/referral/profile | Blocked/not-tested | No real Telegram operation or real `initData` evidence. |
| Partner | Анонимный storefront visitor | Storefront, legal docs, support, checkout entry | Partial | No stage1 container; local-dev/source-level QA only. |
| Partner | Applicant | Partner application/onboarding | Blocked/not-tested unless fixture discovered | Use only synthetic local-stage data. |
| Partner | Workspace owner | Dashboard, programs, campaigns, codes, analytics, finance, team, settings | Ready if partner local-dev preview is started | Partner workspace `cyba451-s1-partner` with owner role exists. |
| Partner | Workspace member/manager | RBAC comparison, team-limited state | Ready if partner local-dev preview is started | Partner roles `manager`, `finance`, `analyst` exist. |
| Partner | Finance/compliance-limited member | Finance, cases, compliance, reporting boundary checks | Partial | Finance/analyst roles exist; real payment operations remain prohibited. |
| Partner | Suspended/disabled workspace | Disabled states, storefront and dashboard restrictions | Blocked/not-tested | No suspended workspace state listed. |
| Admin | Admin operator | Dashboard, support, customers, commerce, growth, infrastructure, security | Ready | Synthetic admin realm `admin`/`operator` users exist. |
| Admin | Support-only operator | Support/customer read and mutation boundaries | Ready | Synthetic `support` user exists. |
| Admin | Finance-only operator | Payments, withdrawals, wallets, settlement read-only checks | Ready for read-only/safe checks | Synthetic `finance` user exists; no payment capture/refund/payout. |
| Admin | Security/review operator | Sessions, two-factor, passkeys, review queue, anti-phishing | Partial | Use `owner/super_admin`, `admin`, or `operator` only for non-destructive checks. |
| Admin | Read-only/auditor | Audit log/governance visibility без mutation | Ready | Synthetic `viewer` user exists. |

## Матрица обязательных integration/test states

| Integration/state | Для каких flows нужно | Разрешённое QA behavior | Статус | Owner/action |
| --- | --- | --- | --- | --- |
| Payment sandbox/mock | Checkout, payment history, wallet, partner finance, admin commerce | Только sandbox/mock; без capture/refund/payout execution | Blocked/not-tested unless safe fixture discovered | Pricing seed exists; real payment operations remain prohibited. |
| Failed payment | Error handling and retry states | Только synthetic failure state | Blocked/not-tested | No failure fixture listed. |
| Refunded/cancelled payment | History and admin/partner reconciliation | Только read-only synthetic state | Blocked/not-tested | No refund/cancel fixture listed; no real refund operations. |
| Email sandbox | Verify, reset password, magic link | Только test inbox/mail catcher | Blocked/not-tested | No mailbox path listed. |
| OAuth test provider | OAuth start/callback and account linking | Только test provider или mocked callback | Blocked/not-tested | No provider path listed. |
| Telegram test bot | Telegram link, Mini App, partner bot integration | Только test bot; без real `initData` в evidence | Blocked/not-tested | No real Telegram operations. |
| Remnawave sandbox/mock | Service access, server/device states, provisioning boundaries | Только non-production; без production VPN changes | Not-tested | Requires separate explicit approval. |
| Support tickets | Client support/admin support flows | Только synthetic tickets | Blocked/not-tested unless seed discovered | Use only synthetic tickets if present. |
| Audit logs | Governance/admin trace validation | Только read-only synthetic log rows | Partial | Admin viewer exists; only sanitized read-only evidence. |
| Analytics/reporting | Dashboard analytics, partner reporting, admin growth reporting | Только redacted aggregate/synthetic data | Partial | Use synthetic aggregate/read-only evidence only. |

## Minimum data set для `GO`

Gate может перейти в `GO` только после выполнения всех условий:

- хотя бы один anonymous path на каждой web surface reachable;
- есть хотя бы один authenticated client user для verified/no-subscription state;
- есть хотя бы один subscribed client или explicit `not testable` decision для service access/VPN paths;
- есть хотя бы один partner owner workspace;
- есть хотя бы один admin operator;
- payment/email/Telegram/OAuth/Remnawave либо sandbox-ready, либо явно marked blocked/not-tested с owner/action;
- credentials переданы только через approved secret channels, не через Markdown/screenshots.

## Текущее решение

`GO - local-stage synthetic QA`.

Operator handoff confirms protected synthetic credentials and role/state map outside git at `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`. This artifact intentionally does not include credential values. Child QA may proceed in approved local-stage scope and must mark unsupported integrations/states as `blocked/not-tested` with owner/action instead of using production data.
