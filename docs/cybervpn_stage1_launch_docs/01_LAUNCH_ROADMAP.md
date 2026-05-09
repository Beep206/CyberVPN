> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# CyberVPN Launch Roadmap

## Цель roadmap

Roadmap задаёт последовательность запуска всей платформы CyberVPN: от управляемой beta до полноценного публичного релиза, партнёрской платформы, мобильных/desktop клиентов и дополнительных private transport направлений.

План рассчитан на горизонт **6 месяцев** до full public launch. Даты внутри этапов должны уточняться после утверждения infrastructure/payment/legal решений.

## Основной принцип

CyberVPN нельзя запускать как единый “big bang”, потому что в проекте одновременно присутствуют B2C, Telegram, payments, Remnawave provisioning, admin, partner, native apps, Helix/private transports, GitOps/platform foundation, observability и legal/privacy контур. Поэтому запуск дробится на этапы с отдельными gates и rollback-готовностью.

## Этапы запуска

### S0 — Documentation & Decision Freeze

Это текущий подготовительный этап.

Цель: зафиксировать документы, scope, blockers, decision log, acceptance gates, технические требования и правила реализации.

Входит:

- документы запуска;
- Stage 1 Charter;
- PRD;
- Technical Spec;
- Implementation Backlog;
- Acceptance Gates;
- Go-Live Runbook;
- Risk Register;
- Review Checklist;
- фиксация hard blockers;
- выбор production domain;
- выбор payment provider;
- выбор production topology;
- решение по Remnawave staging/prod;
- legal seller;
- support/on-call;
- launch candidate branch/tag.

Не входит:

- активная реализация кода;
- выкатывание в production;
- добавление новых фич.

Exit criteria: документы Stage 1 утверждены, ключевые решения закрыты.

### S1 — Controlled Public Beta

Это Этап 1, который сейчас готовится.

Цель: доказать базовый B2C-поток.

Главный поток:

```text
сайт / Telegram
-> регистрация / логин
-> trial или оплата
-> provisioning через Remnawave
-> выдача QR / subscription URL / config
-> подключение пользователя
-> support/admin контроль
```

Входит:

- публичный сайт;
- web-кабинет;
- Telegram Bot;
- Telegram Mini App;
- trial;
- минимум один live payment path;
- Remnawave provisioning;
- worker/scheduler;
- базовая админка;
- support flow;
- monitoring;
- rollback;
- backup;
- evidence gates.

Не входит:

- partner payouts;
- полноценный partner portal;
- mobile app release;
- desktop app release;
- Android TV release;
- browser extension;
- Helix/Verta/Beep production;
- Kubernetes/Talos/GitOps как обязательный blocker.

Exit criteria: реальные beta-пользователи могут зарегистрироваться, оплатить или получить trial, получить VPN-доступ, подключиться, а support/admin могут сопровождать процесс.

### S2 — Public Release 1.0

Это первый полноценный публичный B2C-релиз.

Цель: превратить controlled beta в нормальный публичный запуск без узкого invite-bottleneck.

Входит:

- стабилизированные функции S1;
- финальные тарифы;
- стабильная регистрация;
- production-ready платежи;
- больше payment methods;
- финальный legal pack;
- production observability;
- публичный или полупубличный status page;
- нормальные support-процессы;
- улучшенные onboarding-инструкции;
- понятные refund/payment/subscription flows.

Не входит как обязательная часть:

- partner payouts;
- mobile store release;
- desktop/TV release;
- Helix как массовая функция.

Exit criteria: CyberVPN можно открыто продавать B2C-пользователям.

### S3 — Partner / Reseller Platform

Цель: включить партнёрский и reseller-рост.

Входит:

- partner portal;
- storefronts;
- referral partners;
- reseller flows;
- payout process;
- anti-fraud;
- partner reporting;
- manual/controlled settlements;
- partner support process.

Не входит:

- обязательный mobile release;
- Helix как массовая фича;
- enterprise-hardening.

Exit criteria: партнёры могут приводить пользователей, начисления считаются корректно, выплаты контролируются, fraud-сценарии обработаны.

### S4 — Mobile Store Beta / Release

Цель: вывести продукт в native mobile-канал.

Входит:

- iOS app;
- Android app;
- Apple Developer Account;
- Google Play Console;
- mobile billing strategy;
- RevenueCat или альтернативная стратегия;
- mobile onboarding;
- app store review readiness;
- mobile support guides;
- mobile crash/error monitoring.

Не входит:

- desktop как обязательный канал;
- Android TV как обязательный канал;
- Helix как default transport.

Exit criteria: мобильное приложение проходит beta/store criteria и готово к реальным пользователям.

### S5 — Desktop / Android TV / Device Expansion

Цель: расширить CyberVPN на дополнительные устройства.

Входит:

- desktop client beta;
- Windows/macOS/Linux flows;
- auto-update mechanism;
- Android TV;
- troubleshooting guides;
- device management;
- support/admin visibility по устройствам;
- platform-specific diagnostics.

Не входит:

- Helix как default transport;
- enterprise-scale platform migration как обязательное условие.

Exit criteria: пользователи могут использовать CyberVPN не только через web/Telegram/mobile, но и через desktop/TV-устройства с поддерживаемыми инструкциями и support-процессами.

### S6 — Helix / Verta / Beep Private Transport Beta

Цель: проверить private transport направления как отдельный технологический слой.

Входит:

- Helix beta;
- Verta beta;
- Beep beta;
- security review;
- privacy review;
- legal review;
- canary rollout;
- ограниченный доступ;
- отдельные kill switches;
- отдельный мониторинг;
- отдельные beta-пользователи.

Не входит:

- массовый rollout без аудита;
- включение private transport по умолчанию для всех;
- позиционирование как основной transport до доказанной стабильности.

Exit criteria: private transport проходит beta, security/legal gates и может быть рекомендован для расширения или production rollout.

### S7 — Platform Scale & Enterprise Hardening

Это этап “полная зрелость платформы”.

Цель: довести CyberVPN до состояния масштабируемой, управляемой, операционно зрелой платформы.

Входит:

- GitOps/Talos/Kubernetes там, где это действительно оправдано;
- OpenBao maturity;
- зрелое secrets management;
- advanced observability;
- disaster recovery drills;
- regular restore tests;
- enterprise policies;
- mature RBAC;
- audit trails;
- abuse operations;
- incident response;
- production governance;
- cost controls;
- scaling strategy;
- platform automation.

Exit criteria: CyberVPN готов не только “работать”, но и масштабироваться: больше пользователей, партнёров, устройств, серверов, платёжных путей и операционной нагрузки.

## Почему Stage 1 = Controlled Public Beta

Из owner answers видно, что бизнес хочет full public launch, но фактическая готовность всё равно требует сначала управляемый этап:

- Production domains выбраны (`cyber-vpn.net`, mirror `cyber-vpn.org`), но нужны DNS/TLS/CORS/cookie/OAuth/webhook evidence.
- Admin domains выбраны (`admin.cyber-vpn.net`, mirror `admin.cyber-vpn.org`), но нужны protection/2FA/RBAC/audit evidence.
- Production topology выбрана как Simple Controlled Hybrid Container Topology, но нужен deploy diagram, ingress list, secrets inventory и rollback proof.
- Provider set выбран, documentation-derived status mappings записаны, но PayRam/NOWPayments/CryptoBot/Telegram Stars/Digiseller/YooKassa требуют accounts, credentials, real callback samples, webhook/idempotency/status/refund/reconciliation evidence.
- Legal seller выбран как individual founder/owner, а legal/text/public-copy pack закрыт owner approval in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; mailbox/provider/cookie/PII evidence remains operational.
- Remnawave staging/prod выбраны как separate instances, но нужны smoke/provisioning/backup evidence.
- On-call/support, alert contacts and first admin bootstrap owner записаны в operational pack; local bootstrap evidence exists, but target-environment alert/support/bootstrap evidence is still required; primary and backup currently same handle and need S1 risk acceptance or separate backup.
- Local clean DB migration evidence exists, but staging/managed PostgreSQL migration evidence is still required before go-live.
- Есть широкий dirty worktree, который требует launch-critical/excluded scope map перед tag.

Controlled Public Beta позволяет запускать открытый B2C-поток, но с kill switches, ограниченным rollout, evidence requirements и возможностью остановить регистрацию/платежи/trial/referral без потери контроля.

## Общая последовательность для каждого этапа

Каждый этап проходит одинаковый lifecycle:

1. **Stage Charter** — что запускаем, зачем, кто принимает решение.
2. **Product Requirements** — пользовательские сценарии и продуктовые правила.
3. **Technical Specification** — архитектура, компоненты, конфигурации, интеграции.
4. **Risk Register** — blockers, mitigations, owner, status.
5. **Implementation Backlog** — задачи только с requirement IDs.
6. **Acceptance Gates** — тесты, evidence, критерии готовности.
7. **Runbooks** — deploy, rollback, incident handling, support.
8. **Implementation Review** — проверка фактической реализации против документов.
9. **Go/No-Go** — решение о вводе.
10. **Stabilization** — post-launch период, incidents, retro, следующий этап.

## Запрещённый подход

Нельзя запускать Stage 1, если:

- Документы не утверждены.
- Нет staging evidence по auth/payment/provisioning.
- Платёжные webhook’и не проверены на idempotency.
- Remnawave provisioning не проверен при success/failure/retry.
- Нет rollback плана.
- Нет backup restore drill.
- Production secrets хранятся неуправляемо или могут попасть в repo/frontend bundle.
- Админка доступна без RBAC/2FA/audit/IP protection или эквивалентной защиты.
- Legal pages содержат placeholders.
- Support не имеет сценариев для “оплатил, но доступа нет” и “VPN не подключается”.

## Предварительная целевая модель на 6 месяцев

| Месяц | Цель | Результат |
|---|---|---|
| 1 | S0 + S1 documents + infra/payment/legal decisions | Утверждён Stage 1 package, закрыты hard blockers |
| 2 | Stage 1 implementation + staging | End-to-end flow работает на staging |
| 3 | Controlled Public Beta | Первая управляемая beta с пользователями и support loop |
| 4 | Stabilization + Public Release 1.0 preparation | Устранены beta blockers, готовится S2 |
| 5 | S2 public release + partner prep | Публичный B2C релиз, partner docs/specs готовы |
| 6 | S3 partner launch или mobile beta, по фактическим метрикам | Расширение роста или native channels |

## Decision log, который должен быть закрыт до Stage 1 implementation

| ID | Решение | Почему важно | Рекомендуемое действие |
|---|---|---|---|
| D-S1-001 | Основной production domain | CORS, cookies, TLS, OAuth, Telegram callbacks | Утверждено: `cyber-vpn.net` + mirror `cyber-vpn.org`; local DNS/TLS contract in `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`; live DNS/TLS evidence still required |
| D-S1-002 | Production topology | Deploy, backups, monitoring, cost | Утверждено: Simple Controlled Hybrid Container Topology for S1 |
| D-S1-003 | Secret management | Безопасность production | OpenBao или documented interim secrets policy |
| D-S1-004 | Primary payment provider | Нельзя тестировать payments без аккаунтов | Утвержден provider set: PayRam, NOWPayments, CryptoBot, Telegram Stars, Digiseller, YooKassa; включать только после evidence |
| D-S1-005 | Payment statuses/orphan policy | Риск потери оплаченных пользователей | Baseline зафиксирован в `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`; replace placeholders with real provider evidence |
| D-S1-006 | Remnawave staging/prod placement | Provisioning является core flow | Утверждено: separate staging/prod Remnawave; собрать smoke/provisioning/backup evidence |
| D-S1-007 | Legal seller/legal pack | Public launch blocker | Утверждено: individual founder/owner; финализировать ToS, Privacy, AUP, Refund, Cookie |
| D-S1-008 | First admin bootstrap | Admin operations | Утверждена one-time bootstrap policy; owner `@Sasha_Beep`; собрать evidence |
| D-S1-009 | On-call/support owner | Incidents | Утверждена support/on-call policy; primary/backup `@Sasha_Beep`, alerts `-5173727789` + `backup@cyber-vpn.net`; собрать delivery evidence |
| D-S1-010 | Launch candidate branch/tag | Release governance | Утверждено: `release/stage1-controlled-public-beta`, `stage1-beta-rc.N`, `stage1-beta-live.N` |
