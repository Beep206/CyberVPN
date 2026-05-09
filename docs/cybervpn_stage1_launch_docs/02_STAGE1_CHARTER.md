> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Charter — Controlled Public Beta

## Название этапа

**S1 — Controlled Public Beta / управляемая публичная beta CyberVPN.**

## Цель этапа

Доказать, что CyberVPN способен обслужить ранних B2C-пользователей по полному customer journey:

`visit -> register/login -> trial or pay -> provision VPN access -> receive QR/subscription URL/config file -> connect -> receive support if needed`.

Stage 1 не обязан доказывать всю экосистему. Он должен доказать только жизнеспособность основного B2C-контура.

## Почему это не full public release

Полный публичный релиз требует зрелости payments, legal, observability, support, DR, abuse handling и production operations. В текущих ответах часть этих областей не определена или не подтверждена. Поэтому Stage 1 должен иметь ограничители:

- kill switch для public registration;
- kill switch для trial;
- kill switch для payments;
- kill switch для referral/promo/gift;
- возможность временно отключить отдельный payment provider;
- возможность перевести provisioning в retry/support state;
- возможность остановить публичное привлечение без выключения сервиса для уже активных пользователей.

## Предварительный scope Stage 1

### Product scope

В Stage 1 входит:

- Marketing site с базовыми страницами: pricing, features, devices, download/help, privacy, terms, status.
- Регистрация и вход: email/password, login/password, magic link/OTP, Telegram Bot/Mini App link. OAuth в S1 ограничен Google и GitHub и включается только при готовых credentials, callback URLs и account-linking evidence. Остальные OAuth providers disabled/default-off.
- Открытая регистрация с возможностью мгновенно выключить через feature flag/env/system config.
- Trial: **3 дня / 1 устройство / доступен всем**, если anti-abuse и kill switch готовы.
- Тарифы: публичные и приватные, месячный/квартальный/годовой варианты, без lifetime.
- Цена: базово USD; локальная валюта на сайте как display conversion с округлением вверх. Billing source of truth должен оставаться единым.
- Payment flow: approved S1 provider set включает PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, YooKassa for users from Russia. Каждый provider feature-flagged и включается только после account/credentials/webhook/status/refund/reconciliation evidence; documentation-derived placeholder mappings из `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` должны быть заменены real callback evidence перед enablement; минимум один live payment path обязателен для paid beta.
- VPN provisioning через Remnawave как authoritative backend.
- Выдача пользователю QR-code, subscription URL и config file.
- Devices page.
- Wallet/payment history как user-facing payment state, без включения partner payout logic.
- Referral/promo/gift disabled-by-default: `REFERRAL_ENABLED=false`, public referral/promo/gift UI hidden/gated, no rewards, no payouts, no gift purchase, no checkout discounts from codes. Manual audited support grants разрешены.
- Telegram Bot/Mini App как ранний основной канал вместе с сайтом.
- Admin panel для owner/support/ops/finance с RBAC, 2FA, audit log и ограниченным доступом.
- Support через Telegram/email/web tickets/bot; core emails: `support@cyber-vpn.net` and `refund@cyber-vpn.net`; ИИ-агент как первая линия допустим только при escalation path.
- Status page для пользователей и internal monitoring отдельно.

### Technical scope

В Stage 1 входит:

- Backend API `/api/v1`.
- Frontend customer cabinet.
- Telegram Bot/Mini App.
- Worker/scheduler для provisioning retries, payment reconciliation, subscription expiry/renewal, notifications, cleanup.
- PostgreSQL.
- Redis/Valkey или эквивалент для очередей/cache/rate limit.
- Remnawave staging и production.
- Admin workspace.
- Sentry, Prometheus/Grafana или эквивалентный observability stack для critical flows.
- Backups и restore drill.
- Secret management.
- CORS/cookies/rate limits/CSRF assessment/Swagger disabled in production.

## Out of scope Stage 1

Следующие направления не должны быть обязательной частью Stage 1:

- Partner portal как публичный продукт.
- Partner payouts.
- Reseller storefronts.
- Native mobile app store release.
- Desktop client как production-required path.
- Android TV app.
- Browser extension.
- Helix/Verta/Beep as production/default transport.
- Advanced growth reporting.
- A/B testing.
- Full Kubernetes/Talos/GitOps migration, если она задерживает B2C beta.
- RevenueCat/mobile billing.
- Heavy traffic abuse automation, кроме базовых abuse controls и AUP.

## Success criteria Stage 1

Stage 1 считается успешным, если выполнены все условия:

1. Пользователь может зарегистрироваться или войти через утверждённый auth flow.
2. Пользователь может получить trial 3 дня / 1 устройство.
3. Пользователь может оплатить тариф через минимум один production-ready payment path.
4. Payment webhook обрабатывается идемпотентно.
5. После успешной оплаты или trial доступ в Remnawave создаётся автоматически.
6. При недоступности Remnawave payment state не теряется, provisioning попадает в retry/support state.
7. Пользователь получает QR-code, subscription URL и config file.
8. Пользователь может открыть инструкции по подключению для основных платформ.
9. Support может увидеть статус подписки/payment/provisioning без доступа к секретам.
10. Admin privileged actions пишутся в audit log.
11. Есть backup и подтверждённый restore drill.
12. Есть rollback plan.
13. Critical alerts работают и доставляются в Telegram channel `-5173727789` и `backup@cyber-vpn.net`.
14. Legal pages не содержат placeholders.
15. Public registration/payments/trial/referral можно отключить без redeploy или через подтверждённую emergency procedure.
16. Grace period для paid subscriptions соответствует owner decision: 72 hours.
17. First-week beta metrics соответствуют DEC-S1-013: 95%+ successful `trial/pay -> VPN ready`, median provisioning <=60s, p95 <=5min, zero unresolved paid-but-no-access/orphan payments older than 24h.

## Hard blockers

Stage 1 нельзя вводить в эксплуатацию, если есть хотя бы один blocker:

- Нет staging environment.
- Нет отдельного Remnawave staging/prod.
- Нет payment provider credentials для выбранного Stage 1 payment path.
- Для включаемого provider нет real callback/status evidence вместо documentation-derived placeholder mapping.
- Не реализована или не доказана webhook idempotency.
- Не доказан provisioning success/failure/retry.
- Не настроены secrets и нет secrets scan.
- Нет staging/prod DB migration evidence на чистой базе.
- Нет staging/prod first-admin bootstrap and admin login/2FA evidence.
- Нет admin 2FA/RBAC/audit evidence for target environment.
- Нет backup restore drill.
- Нет rollback notes.
- Нет dirty worktree launch-critical/excluded scope map перед RC tag.
- Public pages содержат placeholder `[Your Company Address]` или аналогичные заглушки.
- Public no-logs/privacy claim выходит за рамки owner-approved S1 wording stance in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` или противоречит deployed logging/observability evidence.

## Known issues, допустимые для Stage 1

Допустимые known issues, если они задокументированы и не ломают core flow:

- UI polish.
- Неполное покрытие 38 языков по второстепенным страницам при условии, что critical flows переведены.
- Partner portal disabled.
- Native clients disabled.
- Helix disabled/default-off.
- PostHog минимален или disabled, если это не мешает operational metrics.
- A/B testing disabled.
- OAuth providers other than Google/GitHub disabled, если есть working primary auth and Telegram identity/linking.

## Governance

До реализации Stage 1 должны быть утверждены:

- Stage 1 Charter.
- Product requirements.
- Technical specification.
- Payment provider readiness matrix.
- Remnawave provisioning runbook.
- Admin/support permissions matrix.
- Legal/support operations pack, including owner-approved legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- Acceptance gates.
- Go-live and rollback runbook.
- Risk register.
- Approved decision log.
- Operational inputs and evidence checklist.
- Technical debt register.

Любое изменение scope после утверждения оформляется как change request с влиянием на сроки, риски и acceptance gates.
