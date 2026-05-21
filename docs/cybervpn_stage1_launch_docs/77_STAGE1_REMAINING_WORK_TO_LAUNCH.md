> CyberVPN Stage 1 Launch Readiness
> Date: 2026-05-05
> Target launch: S1 - Controlled Public Beta
> Scope: what remains before real beta users can safely register, pay or receive trial, get VPN access and be supported.

# Что осталось до запуска S1 Controlled Public Beta

## Executive Summary

Запуск S1 пока нельзя считать готовым к живым пользователям. Большая часть локальной реализации и локальных evidence уже проделана, но это именно local/dev proof. Для запуска нужны реальные staging/production evidence, payment credentials, Remnawave staging/prod, DNS/TLS, backup/restore, rollback и observability. Legal/text/public-copy pack закрыт owner approval в `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; связанные mailbox/provider/cookie/PII proofs остаются operational evidence, а не юридическими текстовыми blockers.

Главная рекомендация: не пытаться включать всё сразу. Для S1 нужен один управляемый B2C path:

```text
public site / Telegram
-> registration/login
-> trial OR one proven payment path
-> Remnawave provisioning
-> QR/subscription URL/config delivery
-> user connects
-> support/admin can recover the case
```

Все partner, mobile store, desktop, Android TV, browser extension, Helix/Verta/Beep, payouts, full GitOps/Talos/Kubernetes и growth mechanics должны оставаться выключенными до следующих этапов.

## Latest Rented Production Snapshot - 2026-05-21

Evidence:

```text
docs/evidence/releases/stage1-rented-prod-09-telegram-miniapp-live-smoke-20260520T072553Z.md
docs/evidence/releases/stage1-rented-prod-08-controlled-runtime-enablement-20260520T070701Z.md
docs/evidence/releases/stage1-rented-prod-09a-owner-telegram-miniapp-auth-hotfix-20260520T074800Z.md
docs/evidence/releases/stage1-rented-prod-09b-miniapp-route-guard-hotfix-20260520T080000Z.md
docs/evidence/releases/stage1-rented-prod-09c-telegram-sdk-hotfix-20260520T081500Z.md
docs/evidence/releases/stage1-rented-prod-09d-miniapp-auth-gate-theme-20260520T083000Z.md
docs/evidence/releases/stage1-rented-prod-09e-backend-telegram-token-reload-20260520T085339Z.md
docs/evidence/releases/stage1-rented-prod-09f-telegram-miniapp-owner-bootstrap-20260520T090407Z.md
docs/evidence/releases/stage1-rented-prod-09g-miniapp-customer-session-react31-20260520T121643Z.md
docs/evidence/releases/stage1-rented-prod-09h-miniapp-ru-l10n-20260520T132348Z.md
docs/evidence/releases/stage1-rented-prod-09i-edge-http3-reset-fix-20260520T134851Z.md
docs/evidence/releases/stage1-rented-prod-09j-edge-http3-quic-restore-20260520T135210Z.md
docs/evidence/releases/stage1-rented-prod-10-payment-path-preflight-20260520T140517Z.md
docs/evidence/releases/stage1-rented-prod-10b-cryptopay-key-webhook-closure-20260520T144900Z.md
docs/evidence/releases/stage1-rented-prod-10c-telegram-stars-enable-20260520T150500Z.md
docs/evidence/releases/stage1-rented-prod-11-observability-stabilization-20260520T162926Z.md
docs/evidence/releases/stage1-rented-prod-11a-external-probe-relay-20260520T164632Z.md
docs/evidence/releases/stage1-rented-prod-11b-node-only-and-direct-home-prod-app-20260520T170051Z.md
docs/evidence/releases/stage1-rented-prod-11c-direct-home-prod-app-network-path-20260520T172432Z.md
docs/evidence/releases/stage1-rented-prod-11d-cloudflare-user-path-probes-20260520T175619Z.md
docs/evidence/releases/stage1-rented-prod-12-catalog-support-beta-gate-20260520T180458Z.md
docs/evidence/releases/stage1-rented-prod-13-first-controlled-cohort-trial-watch-20260520T184156Z.md
docs/evidence/releases/stage1-home-observability-swap-tuning-20260520T191045Z.md
docs/evidence/releases/stage1-rented-prod-14-owner-device-cohort2-preflight-20260520T191226Z.md
docs/evidence/releases/stage1-rented-prod-14a-owner-device-confirmation-cohort2-list-20260521T061114Z.md
docs/evidence/releases/stage1-rented-prod-14b-owner-real-device-retest-cohort2-invite-20260521T062040Z.md
docs/evidence/releases/stage1-stabilization-20260520.md
```

Current operational decision:

```text
GO for Telegram Bot/Mini App infrastructure readiness.
GO for owner/internal Telegram Mini App smoke status after 09G/09H/09J; owner reported the Mini App opens and works.
GO for controlled internal/owner trial smoke and small manually controlled trial cohort.
GO for visible S1 catalog across web, Mini App and Telegram Bot.
GO for owner/internal Telegram trial config delivery and real client connect proof after `STAGE1-RENT-13`.
GO for cohort-2 preparation after owner real-device validation.
NO-GO for cohort-2 invitations until a 1-3 user cohort-2 list is approved.
NO-GO for opening public B2C registration.
NO-GO for paid beta users.
NO-GO for external paid Telegram cohort until real payment/provisioning proof exists.
```

Next ordered step:

```text
STAGE1-RENT-15: Cohort-2 Trial Invite Execution And Support Watch.
```

What is healthy now:

- rented `prod-app-1` runtime is up: frontend, admin, backend, worker, scheduler, Telegram bot, PostgreSQL, Valkey, Remnawave and exporters are healthy;
- rented `prod-vpn-node-1` VLESS/XHTTP node and real client connect proof exist from `STAGE1-RENT-07`;
- `https://api.cyber-vpn.net/health` returns `200`;
- `https://cyber-vpn.net/` redirects to `/en-EN` and returns `200`;
- `https://admin.cyber-vpn.net/` redirects to `/ru-RU/login` and returns `200`;
- trial provisioning is enabled in the running backend with `STAGE1_TRIAL_PROVISIONING_ENABLED=true`;
- production Telegram bot token is accepted by Telegram API and `getMe` resolves `C_y_b_e_r_VPN_Bot`;
- `https://api.cyber-vpn.net/webhook/telegram` is configured as the Telegram webhook with `pending_update_count=0` and no last error in `getWebhookInfo`;
- public webhook requests without Telegram secret header are rejected with `401`;
- Telegram commands are configured: `start`, `menu`, `connect`, `plans`, `trial`, `support`, `paysupport`;
- Telegram default menu button opens `https://cyber-vpn.net/ru-RU/miniapp`;
- Mini App public page returns `200`;
- Mini App frontend auth hotfix is deployed in image `cybervpn/cybervpn-frontend:stage1-rent09a-miniapp-auth-20260520T074800Z`;
- Mini App route-guard hotfix is deployed in image `cybervpn/cybervpn-frontend:stage1-rent09b-miniapp-route-20260520T080000Z`;
- Mini App Telegram SDK hotfix is deployed in image `cybervpn/cybervpn-frontend:stage1-rent09c-telegram-sdk-20260520T081500Z`, and deployed HTML includes `https://telegram.org/js/telegram-web-app.js`;
- Mini App auth-gate/theme hotfix is deployed in image `cybervpn/cybervpn-frontend:stage1-rent09d-miniapp-auth-gate-20260520T083000Z`; `/miniapp/*` routes no longer render the normal web guest profile while Telegram init data is missing, and Mini App panels/nav no longer use light gray Telegram background fallbacks;
- backend was recreated after token fingerprint mismatch evidence; running backend now uses the same Telegram bot token fingerprint as the Telegram bot runtime, so the previous Mini App HMAC failure should be closed pending owner retest;
- Mini App customer-session and React error `#31` hotfix is deployed in images `cybervpn/cybervpn-backend:stage1-rent09g-miniapp-customer-session-20260520t121643z` and `cybervpn/cybervpn-frontend:stage1-rent09g-miniapp-customer-session-20260520t121643z`;
- backend Telegram Mini App auth now issues customer/mobile scoped tokens for `/api/v1/miniapp/*`; redacted internal runtime smoke shows `POST /api/v1/auth/telegram/miniapp -> 200`, `/api/v1/miniapp/bootstrap -> 200`, and `/api/v1/miniapp/config -> 404` for an account without an active config;
- temporary owner bootstrap allowlist from `09F` has been removed from runtime secrets after owner account creation;
- public registration remains paused with `REGISTRATION_ENABLED=false`;
- generic/CryptoBot payments, add-ons, referrals, promo codes, gift codes, checkout discounts, autoprolongation and Helix are disabled; Telegram Stars is runtime-enabled only for Telegram Bot/Mini App and still lacks real purchase/provisioning evidence;
- Crypto Pay provider auth and signed synthetic webhook proof exist, but generic/CryptoBot paid checkout remains disabled until real checkout -> provider callback -> provisioning evidence is captured;
- S1 production plan catalog is seeded: Basic, Plus, Pro and Max are visible for 30/90/180/365 days across `web`, `miniapp` and `telegram_bot`;
- minimum S1 support/storefront/merchant records are seeded and active: `support@cyber-vpn.net`, `refund@cyber-vpn.net`, `noreply@cyber-vpn.net`, `cyber-vpn.net` storefront, `CYBERVPN` billing descriptor;
- Telegram Stars runtime gate is open for Telegram-only payment flow, but real Stars purchase/provisioning proof is not complete;
- home observability stack is running and Alertmanager Telegram/email delivery is proven; production VPN node TCP probes for `de-1.cyber-vpn.org:443` and `:8443` are green;
- `prod-vpn-node-1` is restored to node-only policy: no app/API/admin probe relay, no extra Prometheus exporter, no support/payment/backend/observability workload on the VPN node;
- direct home Prometheus public-web blackbox probes to `prod-app-1` still time out: ICMP and TCP handshake work, MikroTik transmits post-handshake payload to WAN, but that payload is lost before it reaches `prod-app-1`;
- `STAGE1-RENT-11C` has RouterOS SSH evidence: route/NAT/FastTrack inspection does not show a local router blocker; the remaining fault domain is upstream ISP path or JustHost/provider anti-DDoS/TCP validation for the home public IP on `80/443`;
- `STAGE1-RENT-11D` switches S1 `.net` public hostnames to Cloudflare-proxied DNS and closes public endpoint user-path monitoring: all `blackbox-stage1-public-web` targets report `probe_success=1` and HTTP `200` from home Prometheus;
- `STAGE1-RENT-12` rechecked observability after production catalog/support seed: Stage 1 firing alerts are `0`, public user-path probes remain green, and VPN-node TCP probes remain green;
- `STAGE1-RENT-13` hotfixed Telegram/Mini App trial provisioning surfaces and Telegram Bot/Mini App config delivery, then proved owner/internal trial active state, Remnawave link, subscription URL, protected VLESS config delivery and real Xray client connect through `de-1.cyber-vpn.org`;
- home observability swap warnings were closed by tuning GitLab memory/concurrency and controlled restarts of GitLab/Sentry services; firing alerts are empty after scrape;
- `STAGE1-RENT-14` preflight proved rented production runtime healthy, owner trial/config server-side state valid, public endpoint/VPN-node probes green and Stage 1-specific firing alerts `0`;
- `STAGE1-RENT-14A` found and hotfixed the remaining Mini App bootstrap usage lookup path so the owner Telegram-linked user now authenticates, bootstraps and receives Remnawave-generated config on production with HTTP `200`;
- `STAGE1-RENT-14B` closed owner real-device validation: owner received the config through the Telegram Bot/Mini App flow, imported it into a VPN client, connected successfully and confirmed public exit through `77.90.13.29` in Germany;
- pre-enable production backups were captured for CyberVPN PostgreSQL and Remnawave PostgreSQL;
- pause runbooks exist on `prod-app-1` for registration, payments/growth and trial provisioning.

Remaining launch blockers after `STAGE1-RENT-14B`:

- B2C invite-only is not proven across every public registration surface. Current `REGISTRATION_INVITE_REQUIRED=true` does not cover all mobile/Telegram/Mini App/magic-link/OAuth new-user entrypoints, so global public registration must remain paused until this is fixed or beta users are onboarded manually.
- Paid beta remains blocked until one provider has real credentials, webhook signature/final-status/idempotency/provisioning/reconciliation evidence.
- Public endpoint monitoring authority is now Cloudflare-proxied user-path monitoring. The direct home -> origin provider/upstream issue remains open as a known infra issue, but it is no longer the active public user-path monitoring blocker. Do not reuse the VPN node as a relay.
- Provider/upstream direct-origin closure remains open for later hardening: use provider ticket/whitelist or a separate external origin probe location if direct origin monitoring is required.
- Paid Telegram Stars remains blocked until a real Stars purchase -> charge ID -> provisioning -> `/paysupport`/refund/reconciliation proof is captured.
- Canonical service identity / entitlement / device credential rows are not yet populated by the Telegram trial path; current S1 trial delivery relies on `mobile_users.remnawave_uuid` and `mobile_users.subscription_url`. Track this as S1 hardening before larger cohort scale.

## Latest Stabilization Snapshot - 2026-05-11

Evidence: `docs/evidence/releases/stage1-stabilization-20260511.md`

Current operational decision:

```text
CONTINUE internal smoke / pre-beta stabilization.
NO-GO for external beta cohort expansion.
```

What is healthy now:

- public web, admin login, API health and `.org` redirects respond with expected `200`/`301`;
- backend, worker, scheduler, Telegram bot, PostgreSQL, Valkey, Remnawave and lab node containers are healthy;
- Prometheus sees core S1 targets up;
- Telegram webhook is configured, pending updates are `0`, and last error is absent;
- app PostgreSQL and Valkey are healthy;
- payment/orphan queues are empty because paid flow remains disabled;
- backup/restore evidence from `STAGE1-PUB-14` exists for the current no-cost runtime.

New/confirmed launch blockers:

- `S1-STAB-20260511-001`: no rented/always-on production VPN node is proven; only `stage1-lab-home-node` exists.
- `S1-STAB-20260511-002`: paid path remains disabled and no provider proof exists for a paid cohort.
- `S1-STAB-20260511-003`: Loki/Caddy logs include sensitive request-header material for GitLab runner polling; redact headers and decide whether to rotate runner token before widening beta or sharing log exports.
- `S1-STAB-20260511-004`: GitLab is at memory limit and host swap alerts are firing.
- `S1-STAB-20260511-005`: support/refund mailbox DNS remains unproven; no MX/DMARC output for `cyber-vpn.net` / `cyber-vpn.org`.
- `S1-STAB-20260511-006`: closed on rented production by `STAGE1-RENT-12`; S1 plan catalog and support profile are seeded and verified.
- `S1-STAB-20260511-007`: backend direct `/ready` returns `404`; either expose readiness or keep `/healthz`/`/health` as the documented probe contract.

## Status Legend

| Status | Meaning |
|---|---|
| Local done | Реализация/тест/evidence выполнены локально, но это не production proof |
| Remaining no-cost | Можно продолжать без оплаты серверов, локально или документационно |
| External required | Нужны домены, provider accounts, public endpoints, staging/prod infra или managed services |
| Go-live blocker | Без этого Controlled Public Beta запускать нельзя |

## 1. Governance, Freeze and Release Control

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Re-run dirty worktree/scope map before RC | Completed for 2026-05-09 snapshot; repeat again if worktree changes | Текущий worktree широкий; нельзя случайно включить experimental/native/partner/Helix код в S1 runtime | `S1-REL-002` repeated in `22_STAGE1_REL_002_DIRTY_WORKTREE_SCOPE_MAP.md`; follow-up `S1-INFRA-007` current-tree secrets findings are locally resolved, but RC still needs a fresh scope map after additional implementation changes |
| Release notes template | Local done | На RC/live tag должно быть понятно, что изменилось и что откатывать | `S1-REL-005` закрыт локально в `78_STAGE1_REL_005_RELEASE_NOTES_TEMPLATE_EVIDENCE.md`; перед каждым RC/live нужно заполнить шаблон реальными evidence |
| Immutable tag deployment | Go-live blocker | Floating `main` недопустим для beta launch | Deploy только по immutable commit SHA/tag: `stage1-beta-rc.N`, затем `stage1-beta-live.N` |
| Go/no-go authority confirmation | Remaining no-cost | При incident нужен один человек, который может остановить регистрацию/payments/trial/provisioning | Уточнить, что `@Sasha_Beep` сохраняет stop authority, и записать в release checklist |

## 2. Infrastructure, DNS, TLS and Secrets

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Production topology spec | Local done; external proof remains | Топология должна быть зафиксирована до staging/prod, иначе DNS, secrets, backups and ingress будут проектироваться на догадках | `S1-INFRA-001` закрыт локально в `120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md`: Simple Controlled Hybrid Container Topology, placement, public/private ingress, data authority and home-lab boundary are documented; next proof is real staging/prod deployment |
| Staging environment contract | Local done; external proof remains | Staging должен быть отдельным от production до того, как мы начнём тратить деньги на хостинг и provider setup | `S1-INFRA-002` закрыт локально в `121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md`: separate DB/Valkey/Remnawave/bot/sandbox payments/no-prod-credentials/evidence checklist зафиксированы |
| Production environment contract | Local done; external proof remains | Production должен быть deployable без staging credentials/state до покупки/подключения реальных external services | `S1-INFRA-003` закрыт локально в `122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md`: no-staging-credentials boundary, production ingress/preflight/kill-switch checklist and external production evidence list зафиксированы |
| Real staging environment | External required / blocker | Local Docker и local contract не заменяют staging с public callbacks, real TLS, bot webhook, provider sandbox | Поднять минимальный external staging раньше production: backend, frontend/admin, worker, bot, DB, Redis/Valkey, Remnawave staging |
| Real production environment | External required / blocker | S1 users должны попадать не в dev/local/staging окружение | Использовать contract из `122`: managed PostgreSQL, private Valkey, containers, private Remnawave API, protected public ingress, immutable tag/SHA deploy and kill switches |
| DNS/TLS contract | Local done; external proof remains | Домены выбраны, но full live DNS/TLS ещё нельзя доказать без DNS provider/origin access | `S1-INFRA-004` закрыт локально и revalidated 2026-05-09 в `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`: `.net` primary, `.org` redirects, admin mirror, API/webhooks/OAuth, `/status`, TLS and evidence commands зафиксированы |
| Live DNS/TLS evidence | External required / blocker | Домены должны реально резолвиться, иметь валидный TLS, правильные redirects and protected admin | No-cost probes показывают только partial apex DNS/TLS for `.net`/`.org`; подтвердить `www.cyber-vpn.net`, `api.cyber-vpn.net`, `admin.cyber-vpn.net`, redirects, `/status`, admin protection, webhook/OAuth no-challenge |
| Protected ingress contract | Local done; external proof remains | Admin/backend нельзя оставлять публичными без защиты | `S1-INFRA-005` закрыт локально и revalidated 2026-05-09 в `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`: direct-public backend/admin exposure forbidden, admin protected before login, private services stay private, webhook/OAuth no-challenge paths preserved |
| Live protected ingress evidence | External required / blocker | Локальный contract не доказывает реальные firewall/edge/reverse-proxy правила | No-cost probes show this is still open: `api`/`admin` hosts do not resolve, customer-domain admin route probes did not complete, webhook/OAuth no-challenge not proven. Attach edge route inventory, redacted reverse-proxy config, origin firewall/security-group proof, admin Access/IP allowlist/private VPN proof and webhook/OAuth no-challenge probes |
| Edge WAF/rate limiting | Local done; external proof remains | Backend rate limits есть, но публичный edge должен фильтровать scanner/abuse traffic и не ломать webhook/OAuth flows | Local Cloudflare/equivalent baseline закрыт в `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`; перед go-live приложить DNS/TLS/WAF/rate-limit/Security Events proof and webhook no-challenge evidence |
| Production secret store evidence | External required / blocker | Локальная secrets policy есть, но production storage не доказан | Хранить production secrets вне repo; разделить backend/bot/worker/frontend/admin/payment/Remnawave secrets |
| Remote history/token rotation decision | Go-live blocker | Local secret scan/purge есть, но remote history/rotation decision должен быть закрыт до RC | Перед RC зафиксировать owner decision: rewrite remote history или risk-accept + rotate affected tokens where applicable |
| Frontend bundle/env scan | Local done | Любой `NEXT_PUBLIC_*` может утечь в client bundle | `S1-FE-010` закрыт локально в `80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md`; повторить на RC/staging/production artifact до go-live |

## 3. Database, First Admin and Durable State

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Clean migrations on staging/prod DB | External required / blocker | Local clean DB migration уже доказан, но managed staging/prod DB может отличаться | Повторить `S1-BE-001` на staging managed PostgreSQL и production preflight |
| First admin bootstrap on staging/prod | External required / blocker | Local bootstrap есть, но первый production admin ещё не доказан | One-time protected bootstrap, role `owner/super_admin`, mandatory 2FA, audit event, bootstrap disabled after use |
| Seed minimum production data | Completed on rented production; repeat on rebuild | Без тарифов/config/profile IDs нельзя проверить покупку/provisioning | `STAGE1-RENT-12` seeded 28 subscription plan rows, 2 add-ons kept disabled by runtime flag, 16 public active plan entries and the minimum support/storefront/merchant records; repeat the seed after any production DB rebuild |
| Durable queue/retry persistence | Go-live blocker | Redis/Valkey не должен быть source of truth for critical jobs | Critical payment/provisioning jobs должны восстанавливаться из PostgreSQL |

## 4. Auth, Registration and Account Linking

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Registration toggle deployed proof | Go-live blocker | Local `S1-AUTH-001` is complete in `113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md`; staging/prod proof still needed | Проверить emergency kill switch для registration/trial/payments/provisioning on deployed HTTPS surface |
| Email/password live flow | External required | Локальные тесты не доказывают real domain/cookie/TLS/session behavior | Прогнать browser E2E на staging: register/login/logout/session expiry |
| Magic link/OTP with real email provider | Local done; external evidence still required | Local `S1-AUTH-003` is complete in `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md`, but local dispatcher tests do not prove real deliverability, sender-domain reputation or deployed cookie behavior | В S1 включать только после mailbox/provider/sender-domain/deployed HTTPS evidence; otherwise keep passwordless flow hidden or gated |
| OAuth Google/GitHub callbacks | Local gate done; external evidence still required | Local `S1-AUTH-006` is complete in `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md`, but OAuth still depends on real provider apps, callbacks, secrets and browser proof | Включать только Google/GitHub after provider/callback evidence; остальные providers hidden/disabled |
| Telegram/email/OAuth linking deployed proof | External required | Local no-silent-merge policy есть, но нужен real Telegram initData/client evidence | Прогнать Telegram start -> web login -> linked account conflict scenarios |
| Delete/export request procedure | Remaining no-cost + later evidence | Privacy/rights flows нельзя оставлять только UI текстом | Для S1 допустим manual support process, но он должен быть documented, tested and auditable |

## 5. Payments and Billing

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Choose first live payment path | Go-live blocker for paid beta | Нельзя одновременно доводить 6 providers до production proof | Выбрать один primary path для S1 paid beta. Остальные держать disabled until evidence |
| Provider accounts and access setup | Partially closed for Crypto Pay | Crypto Pay production token now validates against `getMe`; остальные providers не доказаны | For S1 paid beta keep only Crypto Pay as first candidate; leave PayRam/NOWPayments/YooKassa/Digiseller/Stars disabled until their own provider evidence exists |
| Real provider final statuses | External required / blocker | Локальная mapping таблица не доказывает provider behavior | Для enabled provider приложить real callback/API samples: success, pending, fail/cancel/expired |
| Webhook signature/authenticity live proof | Partially closed for Crypto Pay synthetic proof | Valid signed synthetic Crypto Pay webhook returns 200 and is stored in `webhook_logs`; real provider callback still not captured | Enable Crypto Pay webhooks in app settings, then prove a real provider callback from a real invoice before public paid beta |
| Durable webhook idempotency | Go-live blocker | Duplicate webhook не должен продлевать subscription или создать второй provisioning job | Back keys with DB/Redis uniqueness, test duplicate callback on staging |
| Payment -> provisioning failure recovery | Go-live blocker | Пользователь оплатил, но Remnawave/API упал: это главный launch risk | Paid state сохраняется, retry job создаётся, support queue/alert срабатывает |
| Orphan payment support queue | Go-live blocker | Owner rule: no orphan/paid-but-no-access older than 24h | 15m alert, 1h P1, 24h P0; real admin/support queue evidence |
| Refund/dispute process | Local done; provider evidence still required | Local `S1-PAY-009` role gate/runbook exists, but provider refund evidence is not live proof | Use `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` as local contract; before enabling a provider, prove manual finance approval, audit retrieval, provider-specific refund/support and reconciliation |
| Reconciliation job | Local done; provider/admin/alert evidence still required | Provider state и internal state могут расходиться | Use `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md`; before paid beta, attach real provider samples, deployed manual review queue and alert delivery |
| PayRam readiness | Local done; provider evidence still required | Local `S1-PAY-013` proves PayRam `FILLED`/underpaid/overpaid/cancelled status behavior, `API-Key` guard, idempotency and enablement blockers, but no real PayRam instance/account/callback/refund proof exists | Use `109_STAGE1_PAY_013_PAYRAM_READINESS_EVIDENCE.md`; keep PayRam disabled until real PayRam account, credentials, callback/status-poll, refund/reconciliation and payment->Remnawave provisioning evidence exists |
| NOWPayments readiness | Local done; provider evidence still required | Local `S1-PAY-014` proves NOWPayments `finished`/partial/wrong-asset/refund status behavior, `x-nowpayments-sig` HMAC guard, idempotency and enablement blockers, but no real NOWPayments account/IPN/refund proof exists | Use `110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md`; keep NOWPayments disabled until real account, credentials, IPN/status-poll, refund/reconciliation and payment->Remnawave provisioning evidence exists |
| Russia payment path | Recommend defer if not legally ready | YooKassa/Digiseller требуют seller/fiscal/legal clarity | Для S1 first beta лучше не блокировать весь запуск Russia path; включать отдельно after evidence |

## 6. Remnawave and VPN Provisioning

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Remnawave staging | External required / blocker | Local Remnawave/node smoke есть, но не заменяет staging | Separate staging instance, test nodes/providers, disposable data, same production contract |
| Remnawave production | External required / blocker | Users cannot rely on local/dev control-plane | Dedicated production Remnawave control-plane, private/internal API, separate from staging |
| Staging/prod profiles/inbounds/nodes | External required / blocker | Protocol allowlist local, но реальные profiles/inbounds not proven | Prove `vless-reality-raw` default and `vless-reality-xhttp` alternate with real node evidence |
| Trial provisioning real evidence | External required / blocker | Local mockable trial proof is not enough | Staging: create trial user -> Remnawave user/profile/expiry/traffic/device evidence |
| Paid provisioning real evidence | External required / blocker | Payment -> VPN ready is the core S1 flow | Staging paid webhook -> create/extend Remnawave access -> user receives config |
| Retry/outage real evidence | External required / blocker | Remnawave outages must not lose paid users | Simulate Remnawave unavailable -> retry -> success; prove alert and support state |
| Expiry/grace durable worker | Go-live blocker | Owner approved 72h grace, but durable schedule must be proven | PostgreSQL-backed candidates, worker lock/claim, trial disables at expiry, paid disables after grace |
| Usage/traffic display | Required or explicitly unavailable | Wrong usage data creates support load and trust issue | Either implement accurate Remnawave usage sync or mark usage unavailable in S1 |
| Node/region inventory | Local done; provider/node evidence still required | Marketing and UI must not promise unavailable locations | `S1-VPN-010` closed locally in `86_STAGE1_VPN_010_NODE_REGION_INVENTORY_EVIDENCE.md`; show only regions with real staging/prod Remnawave node evidence |
| Torrent/P2P/TOR node policy | Local done; plugin/provider evidence still required | AUP says provider/node policy can restrict P2P; owner also requested TOR be considered if Remnawave supports it | `S1-VPN-011` closed locally in `87_STAGE1_VPN_011_TORRENT_TOR_NODE_POLICY_EVIDENCE.md`; no native Remnawave TOR blocker addon found in current official docs, TOR control remains disabled until separate evidence |

## 7. Frontend Customer Experience

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Marketing critical pages review | Completed locally / deployed proof remains | Public pages must not have placeholders or unsupported claims | Local content audit/build proof is in `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`; repeat on staging/RC with screenshots, `.net` primary and `.org` mirror/redirect proof |
| Dashboard state coverage | Completed locally / deployed proof remains | User must understand trial, active, grace, expired, payment failed, provisioning failed | Local UI/model tests, EN screenshot and build proof are in `99_STAGE1_FE_002_DASHBOARD_STATES_EVIDENCE.md`; repeat with deployed staging/RC real backend/provider/Remnawave states |
| Config delivery UI | Completed locally / deployed proof remains | Main value: QR/subscription URL/config | Local UI/model tests and build proof are in `100_STAGE1_FE_003_CONFIG_DELIVERY_UI_EVIDENCE.md`; repeat with deployed staging/RC real Remnawave payload and VPN client import evidence |
| Devices page | Completed locally / deployed proof remains | Пользователь должен видеть активные устройства, лимит тарифа и безопасно отзывать устаревшие сессии | Local model/UI tests and build proof are in `101_STAGE1_FE_004_DEVICES_PAGE_EVIDENCE.md`; repeat on staging/RC with real backend sessions, entitlement `device_limit` and device enforcement proof |
| Wallet page | Completed locally / deployed proof remains | Пользователь должен видеть безопасную историю платежей без raw provider data | Local UI/API tests and build proof are in `102_STAGE1_FE_005_WALLET_PAGE_EVIDENCE.md`; repeat on staging/RC with real provider payment records, authenticated customer scope and final artifact scan |
| Referral/promo/gift UI gating | Completed locally / deployed proof remains | Public growth UI must stay hidden/paused in S1 unless a later evidence gate is approved | Local flag, route, Mini App and checkout-code tests/build proof are in `103_STAGE1_FE_006_GROWTH_UI_GATES_EVIDENCE.md`; repeat on staging/RC with deployed screenshots and final public env/artifact scan |
| Hide operator/admin surfaces | Completed locally / deployed proof remains | обычный user не должен видеть monitoring/analytics/operator tools | Local route policy, direct route and server-surface tests/build proof are in `104_STAGE1_FE_007_OPERATOR_SURFACE_AUDIT_EVIDENCE.md`; repeat on staging/RC with browser transcripts/screenshots |
| Platform guides | Completed locally / deployed proof remains | Support load will spike without clear connect instructions | Local public `/devices` guide coverage now includes iOS, Android, Windows, macOS, Linux and Telegram Mini App in `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`; repeat with deployed screenshots and real Remnawave/client import proof before go-live |
| Critical-path i18n | Local done; deployed proof remains | 39 locales exist, but S1 can launch only with honest locale posture | `106_STAGE1_FE_009_I18N_CRITICAL_PATH_EVIDENCE.md` proves fallback-complete critical paths for all enabled locales and direct EN/RU review; secondary locales remain fallback-supported, not fully translated |

## 8. Telegram Bot and Mini App

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| BotFather staging/prod evidence | External required | Local bot command/menu proof не доказывает real Telegram bot | getMe, webhook, commands, menu button and domain evidence |
| Telegram Mini App real initData | External required | Web UI screenshots are not enough | Verify Telegram client opens Mini App, auth/linking works, expired/paid/trial states render |
| Telegram Stars if enabled | Runtime gate enabled; catalog seeded; real purchase evidence still required | Owner allowed Stars only for Telegram after evidence; `STAGE1-RENT-10C` opened Stars without opening generic/CryptoBot checkout | `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md` proves local XTR/pre-checkout/success/refund contract; `stage1-rented-prod-10c-telegram-stars-enable-20260520T150500Z.md` proves runtime gate and `createInvoiceLink` smoke; `STAGE1-RENT-12` proves the public S1 catalog. Still required: approved XTR purchase amount policy, real Stars payment, charge ID, `/paysupport`, refundStarPayment/reconciliation and provisioning evidence |
| Notifications delivery | External required | Expiry/payment/provisioning notifications are support-critical | Real client screenshots and queue delivery proof |
| Bot rate limiting with deployed Redis | External required | Telegram spam can create support/payment abuse | Prove Redis-backed limits and fail-closed behavior |
| AI support escalation to real queue | External required | Local deterministic triage exists, but support must receive cases | Prove support queue/admin visibility and human SLA acknowledgement |

## 9. Admin, Support and Operations

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Deployed admin domain protection | External required / blocker | Local host guard exists, but real DNS/TLS/ingress not proven | `admin.cyber-vpn.org` redirect to `admin.cyber-vpn.net`; admin behind protected ingress |
| RBAC persona proof | External required | Local FastAPI dependencies pass, but UI/persona proof needed | Owner/support/operator/finance screenshots or API transcripts |
| Admin 2FA browser/API evidence | Local done; deployed proof remains blocker | Local `S1-AUTH-004` is complete in `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md`, but local tests do not prove target-domain browser/API persona behavior | Before go-live, prove login/admin API blocked without TOTP, valid TOTP-enabled admin passes and audit/persona evidence exists |
| Privileged audit log deployed proof | External required / blocker | Manual grants/refunds/credential regen must be attributable | Audit log sample for grant, extend, disable, regenerate, refund/support actions |
| Payment attempts/admin support view | External required | Support must debug paid-but-no-access safely | Safe view: no raw provider payloads, no payment URLs, no secrets |
| Manual subscription ops | External required | Required recovery path when provider/provisioning fails | Role-gated manual grant/extend/disable with audit and owner approval path |
| Mailbox proof | External required | Public contacts must work | Prove `support@`, `refund@`, `privacy@`, `abuse@` as applicable |
| Human SLA test | External required | Runbook is not enough | Test escalation: user report -> support -> ops/finance/owner within S1 SLA |

## 10. Legal, Privacy and Abuse

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| No-logs claim validation | Owner-approved legal/text closure | Privacy copy is bounded and owner accepted the S1 no-absolute-overpromise wording stance | Keep operational logging/Remnawave/Sentry proof under security/observability before expanding public claims |
| Public seller display/jurisdiction | Owner-approved legal/text closure | Owner selected individual founder/owner and accepted keeping sensitive personal/tax/banking data outside repo | Provider/legal-public details, if required externally, must be handled outside repo and attached only as redacted operational evidence |
| Final legal review | Owner-approved legal/text closure | Owner instructed that texts, terms and legal information are completed for S1 | Use `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` as the S1 legal/text approval record |
| Abuse complaint runbook | Owner-approved legal/text closure | S1 abuse intake/action boundary is accepted | Deployed `abuse@` mailbox/admin enforcement proof remains support/ops evidence |
| Law enforcement request policy | Owner-approved legal/text closure | S1 intake, verification, minimum disclosure and owner/audit boundary is accepted | Live support escalation proof remains support/ops evidence |
| GDPR/delete/export procedure | Completed locally / deployed proof remains | S1 manual support/privacy request procedure is accepted; local backend/frontend request path and support escalation are covered | `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md` closes local route/runbook proof; deployed `privacy@` mailbox, support queue, identity verification and human SLA evidence remain required |
| Cookie browser inventory | External required | Cookie Policy local candidate exists, but actual browser cookies must match | Capture browser DevTools/curl `Set-Cookie` for public/auth/OAuth/logout/admin/Mini App |
| Consent evidence if non-essential analytics enabled | Conditional blocker | GA4/PostHog/marketing pixels require consent/default-off evidence where applicable | Keep non-essential analytics disabled for S1 unless consent UI is implemented and tested |

## 11. Observability, Monitoring and Alerts

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Sentry projects/config | Completed locally and revalidated 2026-05-09 / external live proof remains | Local config contract exists for frontend/admin/backend/bot/worker; live projects must show real events, but local env has no Sentry URL/token/org/project/DSNs/releases and no `sentry-cli` | Provision live Sentry projects, inject redacted DSNs, upload sourcemaps for web/admin and capture one safe test event per surface |
| PII scrubbing proof | Completed locally and revalidated 2026-05-09 / live proof remains | Local Sentry/log redaction evidence exists for S1-sensitive cookies, auth headers, config URLs, OAuth/TOTP, Telegram and payment values; local env has no Sentry URL/token/org/project/DSNs/releases and no `sentry-cli` | Attach live Sentry org scrubber settings, prevent-IP proof, safe test events, replay masking proof and deployed backend log samples before go-live |
| Metrics/dashboards | Completed locally and revalidated 2026-05-09 / deployed evidence still required | Local dashboard/rule contract exists in `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md`; local env has no Prometheus/Grafana endpoints or tokens, and launch still requires deployed Grafana screenshots and live target proof | Keep S1 dashboard as primary launch board; attach live screenshots, target-up proof and synthetic paid-but-no-access sample before go-live |
| Alert delivery | Completed locally and revalidated 2026-05-09; live delivery go-live blocker | Incidents must reach humans | Local rules/routes are in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`; validator/tooling/contract tests pass. Live test still requires Alertmanager delivery to Telegram channel `-5173727789` and backup email `backup@cyber-vpn.net` |
| Paid-but-no-access alert | Local rules done; live delivery go-live blocker for paid beta | This is the highest trust-breaking failure mode | Local rules cover 15m, P1 at 1h, P0/blocker at 24h; live delivery and support queue evidence remain |
| Status page decision | Recommended | Users need basic incident visibility | For S1, a simple public or semi-public `/status` is enough if maintained |

## 12. Backup, Restore and Disaster Recovery

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| PostgreSQL backups | Local proof completed and revalidated / external blocker remains | Subscription/payment/support state is durable source of truth | Local `.dump` proof exists and was revalidated on 2026-05-09 in `92_STAGE1_QA_003_LOCAL_BACKUP_EVIDENCE.md`; still configure daily encrypted managed backups, 14-day retention, off-host storage and pre-deploy backup |
| Restore drill | Local proof completed and revalidated / go-live blocker for managed target remains | Backup without restore proof is not evidence | Local clean restore proof exists and was revalidated on 2026-05-09 in `93_STAGE1_QA_004_RESTORE_DRILL_EVIDENCE.md`; repeat on staging/prod or accepted managed DB target and record production RPO/RTO |
| Remnawave backup/export/rebuild | Go-live blocker | VPN access state must be recoverable | Export/rebuild strategy for profiles/users/nodes; document what can be reconstructed from backend DB |
| Redis/Valkey non-durable rule | Already decided, needs implementation proof | Critical jobs cannot disappear with Redis loss | PostgreSQL remains recovery source for payments/provisioning |
| Secret rotation runbook proof | Required before RC | If secret leaks or JWT key is compromised, response must be known | JWT/TOTP/OAuth/payment/Remnawave rotation runbooks with owner approval path |

## 13. QA, Security and Evidence Pack

### Что осталось

| Item | Status | Почему нужно | Рекомендация |
|---|---|---|---|
| Critical E2E | Completed locally / go-live blocker for deployed proof | S1 must prove complete user journey | Local no-cost gate passed in `88_STAGE1_QA_001_CRITICAL_E2E_LOCAL_EVIDENCE.md`; repeat against staging/prod HTTPS, real Remnawave and real support/admin personas before go-live |
| Paid E2E | Go-live blocker for paid beta | Real money path must not rely on mocks | Provider success -> webhook -> subscription -> provisioning -> user config -> admin payment view |
| Failure E2E | Go-live blocker | Failures happen on launch day | Payment failed, paid-but-no-access, provisioning failure, expired/grace, Remnawave down |
| Dependency audits | High/critical threshold passes after `S1-AUTH-007` lockfile refresh | High/critical vulnerabilities should not ship | `S1-AUTH-007` repeat used safe `npm --prefix frontend audit fix --package-lock-only`; frontend production and full audit now pass for high/critical, while moderate Next/PostCSS remains tracked because npm's force fix proposes a breaking Next.js downgrade |
| Secrets scan before RC | Local current-tree pass / repeat before RC | Many generated/untracked files exist | `S1-INFRA-007` was revalidated on 2026-05-09: accepted baseline is redacted and baseline-enforced scan returns `no leaks found`. Repeat after more implementation changes and before RC/live tags |
| Edge WAF/rate-limit proof | Local baseline done / deployed proof blocker | Edge rules without Security Events/rate-limit transcripts are only intent, not evidence | Use `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`; capture real custom block, auth/admin/trial/support rate-limit, payment webhook no-challenge and Telegram webhook no-challenge proof |
| Evidence pack assembly | Completed locally / final pack incomplete until external evidence | Go/no-go must be evidence-driven | Local index and category structure exist in `91_STAGE1_REL_007_EVIDENCE_PACK_INDEX.md` and `evidence_pack/stage1/`; fill missing provider/staging/prod/backup/observability/go-live slots before launch |
| Rollback dry-run | Completed locally / repeat before go-live | Rollback must be a proven command/procedure | Local release-pointer rollback and runtime rollback controls passed in `90_STAGE1_REL_006_ROLLBACK_DRY_RUN_EVIDENCE.md`; repeat against staging/prod final RC artifacts and hosting |

## 14. Things To Keep Disabled for S1

| Area | S1 decision | Recommendation |
|---|---|---|
| Partner portal/payouts | Out of S1 | Stage 3 after B2C proof |
| Referral/promo/gift public flows | Disabled by default | Keep hidden; manual audited support grants only |
| Add-ons | Disabled by default | Enable later with pricing/support/refund evidence |
| Mobile store release | Out of S1 | Stage 4 |
| Desktop/Android TV/browser extension | Out of S1 | Stage 5 or later |
| Helix/Verta/Beep production | Out of S1 | Stage 6 private transport beta after security/legal review |
| Full Talos/Kubernetes/GitOps | Not a S1 blocker | Stage 7 when scale justifies it |
| Auto-prolongation | Not promised in S1 | Manual renewal + reminders only until recurring billing evidence exists |

## 15. Recommended Execution Order From Here

### A. Continue no-cost/local work now

1. Continue with `S1-BE-003` route-boundary review/revalidation after the 2026-05-09 clean migration and first-admin bootstrap rechecks.
2. Keep provider-account evidence as external-account work: `S1-PAY-001`...`S1-PAY-003`, `S1-PAY-011`, `S1-PAY-013`...`S1-PAY-016` are locally documented/guarded, but real provider credentials, callback samples, invoices, refunds/reconciliation and payment-to-provisioning proof are still required before enabling any paid rail.
3. Keep remaining Remnawave plugin/node evidence as staging/prod work: real node plugin config, Torrent Blocker reports/stats, webhook signature, admin/support persona, alert delivery and rollback proof.
4. Repeat frontend marketing screenshots/domain proof only after staging/RC deploy; local `S1-FE-001` content audit is completed in `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`.

### B. Unlock staging with minimal external cost

1. Create staging stack with separate DB/Valkey/Remnawave/bot/payment test mode.
2. Configure staging DNS/TLS and Telegram webhook.
3. Run `S1-BE-003` on staging: prove public/internal/admin/user API route boundary, admin/internal protection, Swagger public-off behavior and webhook/OAuth callback exposure before user/payment/VPN smoke.
4. Repeat clean migrations and first admin bootstrap on staging: `S1-BE-001`, `S1-BE-002`.
5. Run `S1-AUTH-*` staging auth flows: email/password, magic link/OTP, Telegram linking, admin 2FA and OAuth if enabled.
6. Keep `S1-VPN-001`, `S1-VPN-003`, `S1-VPN-004` evidence current if runtime tags or Remnawave settings change; rented production trial/client-connect proof is recorded in `docs/evidence/releases/stage1-rented-prod-07-backend-trial-client-connect-20260520T065023Z.md`.
7. Test one provider sandbox path end-to-end, first candidate `S1-PAY-002` CryptoBot.

### C. Prepare production only after staging passes

1. Provision production managed PostgreSQL and private Valkey.
2. Deploy production backend/worker/bot/frontend/admin containers.
3. Deploy production Remnawave and at least minimal real node inventory.
4. Configure DNS/TLS for `.net` primary customer/admin/API surfaces and `.org` VPN node/subscription surfaces only.
5. Run backup/restore and rollback drills.

### D. Paid beta gate

1. Enable exactly one proven live payment path first.
2. Keep all other providers disabled until their provider evidence exists.
3. Prove paid success, duplicate webhook, payment failure, refund/support, reconciliation and paid-but-no-access alert.

### E. Go-live candidate

1. Re-run `S1-REL-002` dirty worktree scope map.
2. Create `stage1-beta-rc.N` tag.
3. Run all acceptance gates.
4. Assemble final evidence pack.
5. Owner signs go/no-go.
6. Launch to controlled beta cohort, not full public traffic.

## 16. Minimum Go/No-Go Rule

S1 Controlled Public Beta can launch only when all of this is true:

- at least one real user can register/login;
- local email/password register/verify/login/refresh/logout evidence exists in `114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md`, and deployed HTTPS/browser proof is attached before go-live;
- local magic link/OTP evidence exists in `115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md`, and real email-provider/deployed HTTPS proof is attached before enabling passwordless login;
- local admin 2FA evidence exists in `116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md`, and deployed admin browser/API persona proof is attached before go-live;
- local OAuth provider-scope evidence exists in `117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md`, and real Google/GitHub provider callback/browser proof is attached before enabling OAuth login publicly;
- local edge WAF/rate-limit baseline exists in `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`, and real DNS/TLS/WAF/rate-limit/security-event proof is attached before go-live;
- local production topology spec exists in `120_STAGE1_INFRA_001_PRODUCTION_TOPOLOGY_EVIDENCE.md`, local production environment contract exists in `122_STAGE1_INFRA_003_PRODUCTION_ENVIRONMENT_EVIDENCE.md`, local DNS/TLS contract exists in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`, local protected ingress contract exists in `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md`, and real staging/prod deployment, DNS/TLS and protected ingress proof is attached before go-live;
- local staging environment contract exists in `121_STAGE1_INFRA_002_STAGING_ENVIRONMENT_EVIDENCE.md`, and real external staging health/evidence proof is attached before first rollout;
- trial provisioning works on real Remnawave and has a fresh redacted client-connect proof;
- at least one live payment path is proven if paid beta is enabled;
- paid-but-no-access cannot remain unresolved over 24h without owner/support escalation;
- admin/support can see payment, subscription and provisioning state safely;
- local backup/restore is proven, and managed staging/prod backup/restore is proven before real go-live;
- rollback is proven;
- alert delivery is proven;
- legal/text pack owner approval exists in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`;
- no high/critical known security issues remain unhandled;
- launch candidate is an immutable tag/commit, not floating `main`.

## Next Recommended Task

The current ordered local/revalidation chain completed on 2026-05-09:

1. `S1-BE-003` - completed locally/revalidated in the first owner-requested batch.
2. `S1-REL-002` - completed locally/revalidated in the first owner-requested batch.
3. `S1-INFRA-002` - local contract completed/revalidated; real external staging still required.
4. `S1-INFRA-004` - local contract and no-cost probes completed/revalidated; required live DNS/TLS subdomain evidence still open.
5. `S1-BE-001` - completed locally/revalidated on disposable PostgreSQL 17.7.
6. `S1-BE-002` - completed locally/revalidated: protected first-admin bootstrap and repeat-lock proof.
7. `S1-BE-003` - completed locally/revalidated again: route boundary remains `needs-review=0`.
8. `S1-AUTH-001` - completed locally/revalidated: registration kill switch and auth regression pass.
9. `S1-AUTH-002` - completed locally/revalidated: email/password flow pass.
10. `S1-AUTH-003` - completed locally/revalidated: magic link/OTP flow pass.
11. `S1-AUTH-004` - completed locally/revalidated: admin 2FA gate and lifecycle pass.
12. `S1-AUTH-006` - completed locally/revalidated: Google/GitHub-only OAuth scope pass.
13. `S1-AUTH-007` - completed locally/revalidated: privacy delete/export request path pass.
14. `S1-VPN-001` - local control-plane smoke completed; real external staging Remnawave remains required.
15. `S1-VPN-003` - completed locally/revalidated: S1 protocol allowlist pass.
16. `S1-VPN-004` - completed locally/revalidated and proven on rented production: trial activation, Remnawave provisioning, real VLESS links and Xray client-connect pass.
17. `S1-PAY-002` - completed locally/revalidated: CryptoBot sandbox/testnet runtime contract pass; real testnet credentials and callback samples remain required.
18. `S1-QA-003` - completed locally/revalidated: fresh local `.dump` backup created and listed.
19. `S1-QA-004` - completed locally/revalidated: fresh restore drill passed and disposable DB removed.
20. `S1-INFRA-005` - completed locally/revalidated: protected-ingress contract pass; live API/admin ingress evidence remains required.
21. `S1-INFRA-008` - completed locally/revalidated: edge WAF/rate-limit baseline contract pass; live edge/DNS/TLS/security-event evidence remains required.
22. `S1-OBS-001` - completed locally/revalidated: Sentry critical project/config contract pass; live Sentry org/project/DSN/test-event/source-map evidence remains required.
23. `S1-OBS-002` - completed locally/revalidated: Sentry/log PII scrubbing pass; live Sentry scrubber/prevent-IP/replay/event/log proof remains required.
24. `S1-OBS-003` - completed locally/revalidated: Prometheus/Grafana dashboard/rule and worker metric contract pass; live dashboard/target/metric sample proof remains required.
25. `S1-OBS-004` - completed locally/revalidated: Alertmanager Telegram/email routing and S1 alert-rule contract pass; live Telegram/email delivery proof remains required.
26. `S1-REL-006` - completed locally/revalidated: rollback dry-run and runtime rollback controls pass; real staging/prod rollback on RC artifacts remains required.
27. `S1-FE-010` - completed locally/revalidated: production frontend build and bundle/env scan pass; deployed RC/CDN artifact scan remains required.
28. `S1-QA-002` - completed locally/revalidated: dependency audit and local image scan pass; final RC image/artifact scans remain required.
29. `S1-REL-002` - completed locally/revalidated: dirty worktree inventory updated; broad worktree still blocks RC until final owner-approved scope map.
30. `S1-REL-007` - completed locally/revalidated: evidence pack structure and links pass; final evidence pack snapshot remains required before go/no-go.
31. `stage1-beta-rc.N` - eligibility checked in `129_STAGE1_STEP_31_RC_TAG_EVIDENCE.md`; real `stage1-beta-rc.1` tag was not created because release branch is missing and the worktree is dirty.
32. `Owner go/no-go` - prepared in `130_STAGE1_STEP_32_OWNER_GO_NO_GO_EVIDENCE.md`; recommended decision is `NO-GO_FOR_CONTROLLED_BETA_LAUNCH` and owner signature remains required.

Next ordered step: owner must sign or override the go/no-go decision before `33. Controlled beta cohort launch`.

## 17. Rented Production Runtime Update - 2026-05-21

The rented Stage 1 runtime has advanced beyond the older local go/no-go snapshot. Current operating status:

1. `STAGE1-RENT-14B` proved owner real-device VPN connectivity through Telegram Bot/Mini App config delivery and the production VPN node.
2. `STAGE1-RENT-14C` fixed a Mini App stale-session restore issue that could show a misleading no-subscription state even though backend state still had an active trial, Remnawave UUID and subscription URL.
3. The active customer-facing frontend image is `cybervpn/cybervpn-frontend:stage1-rent14c-miniapp-session-restore-20260521t063728z`.
4. Backend, bot, worker, scheduler, Remnawave and VPN node were not changed by the 14C hotfix.
5. Next launch blocker before cohort-2 expansion: owner must close/reopen the Telegram Mini App and confirm that session restore shows the active trial/config correctly on a real device.

Next ordered rented-runtime step:

```text
STAGE1-RENT-14C owner real-device retest confirmation
then STAGE1-RENT-15: Cohort-2 Trial Invite Execution And Support Watch
```

## 18. STAGE1-RENT-15 Status - 2026-05-21

`STAGE1-RENT-15` has started.

Completed:

1. Issued 3 controlled beta invite codes to the owner Telegram-linked mobile account.
2. Set each code to 7 free days.
3. Set 72-hour expiry: 2026-05-24 11:54:13 UTC.
4. Wrote audit event `s1_controlled_beta_invites_issued`.
5. Verified production invite count: `total_invites=3`, `active_invites=3`.
6. Verified rented production containers remained healthy.
7. Verified public endpoint probes and VPN-node TCP probes remained green.
8. Verified home Prometheus firing alerts were `0`.

Still required:

1. Owner selects and sends the codes to 1-3 real cohort-2 users.
2. First invited user completes Telegram Bot/Mini App entry.
3. First invited user activates trial or redeems invite code.
4. Support watches provisioning/config/client-connect.
5. Evidence is recorded in `STAGE1-RENT-15A`.

Next ordered rented-runtime step:

```text
STAGE1-RENT-15A: First Invited User Trial/Invite Flow Evidence
```
