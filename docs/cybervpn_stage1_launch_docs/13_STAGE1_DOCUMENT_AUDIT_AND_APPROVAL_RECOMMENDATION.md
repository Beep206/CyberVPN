> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Статус: review artifact перед утверждением Stage 1. Не является разрешением на production go-live.

# Stage 1 Document Audit and Approval Recommendation

## Краткий вывод

Комплект `docs/cybervpn_stage1_launch_docs` достаточно хорошо описывает правильный формат первого запуска: **Controlled Public Beta CyberVPN**, управляемая публичная beta для B2C-контура. Это правильнее, чем полный публичный релиз, потому что проект имеет широкий launch surface: сайт, кабинет, Telegram Bot/Mini App, платежи, worker, Remnawave, админка, support, legal, observability и rollback.

Текущий пакет **можно использовать как основу для утверждения Stage 1**: owner answers по `DEC-S1-001`...`DEC-S1-020` записаны, operational values добавлены, а placeholders вынесены в техдолг. При этом пакет **не является разрешением на production go-live**, пока blockers не будут закрыты evidence или явно приняты как blocking dependencies с владельцами, due date и backlog ID.

## Рекомендация по статусу

| Область | Рекомендованный статус | Причина |
|---|---|---|
| Формат запуска | Approve with changes | Controlled Public Beta B2C соответствует рискам проекта |
| Scope Stage 1 | Approve with changes | Scope в целом верный, но часть функций нужно явно выключить default-off |
| Документы как baseline | Approve with evidence gates | Owner decisions записаны; placeholders и evidence gaps вынесены в `18`/`19` |
| Переход к реализации | Allowed after G0 entry criteria | Нужны accepted `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`, `19_STAGE1_TECH_DEBT_REGISTER.md` и launch scope map |
| Production go-live | Blocked | Нет live Remnawave/payment/domain/backup/rollback/observability evidence подтверждений; legal/text approval закрыт отдельно |

## Что в документах уже хорошо

1. Stage 1 явно определён как **Controlled Public Beta**, а не как full public launch.
2. Scope ограничен B2C-контуром и не тянет в первый запуск партнёрские выплаты, native app store release, Helix production и полный GitOps/Talos как обязательство.
3. Есть единая цепочка ценности: `register/login -> trial/pay -> provision VPN access -> QR/subscription URL/config -> connect -> support`.
4. `06_STAGE1_IMPLEMENTATION_BACKLOG.md` даёт task IDs, по которым можно вести реализацию без размывания scope.
5. `07_STAGE1_ACCEPTANCE_GATES.md` и `08_STAGE1_GO_LIVE_RUNBOOK.md` требуют evidence, rollback и kill switches.
6. `10_STAGE1_RISK_REGISTER.md` честно фиксирует launch blockers, а не прячет их как “known issues”.
7. Legal/support/operations вынесены отдельно, что важно для публичной beta VPN-продукта.

## Главные слабые места пакета

| Проблема | Где видно | Почему это blocker |
|---|---|---|
| Owner answers записаны, но часть evidence отсутствует | `11_STAGE1_REVIEW_CHECKLIST.md`, `17_STAGE1_APPROVED_DECISION_LOG.md` | Решения больше не должны приниматься скрыто в коде; теперь нужно закрывать evidence gates |
| Production/staging Remnawave не подтверждены evidence | `10_STAGE1_RISK_REGISTER.md`, `04_STAGE1_TECHNICAL_SPEC.md` | Нельзя проверить provisioning end-to-end |
| Payment provider set выбран, но accounts/credentials/evidence отсутствуют | `10_STAGE1_RISK_REGISTER.md`, `06_STAGE1_IMPLEMENTATION_BACKLOG.md` | Нельзя доказать paid beta, webhooks, refunds, reconciliation |
| Production topology выбрана, но deploy/rollback evidence отсутствует | `04_STAGE1_TECHNICAL_SPEC.md`, `10_STAGE1_RISK_REGISTER.md` | Нельзя безопасно проектировать secrets, DNS, backups, ingress, rollback |
| Основной и admin domains выбраны; local DNS/TLS и protected ingress contracts есть, live evidence отсутствует | `04_STAGE1_TECHNICAL_SPEC.md`, `123_STAGE1_INFRA_004_DNS_TLS_EVIDENCE.md`, `124_STAGE1_INFRA_005_PROTECTED_INGRESS_EVIDENCE.md` | Нельзя финализировать OAuth callbacks, CORS, cookies, webhooks, TLS и admin exposure без live DNS/TLS/redirect/admin-protection/edge/firewall proof |
| Legal/text pack owner-approved | `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`, `09_STAGE1_LEGAL_SUPPORT_OPERATIONS.md` | Legal/copy drafting no longer blocks S1; mailbox/provider/cookie/PII evidence remains in ops/security/provider gates |
| Payment statuses/orphan policy утверждены как baseline, но не доказаны provider evidence | `04_STAGE1_TECHNICAL_SPEC.md`, `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`, `19_STAGE1_TECH_DEBT_REGISTER.md` | Documentation-derived mapping нельзя включать в production без real callbacks/tests |
| Webhook idempotency не доказана | `07_STAGE1_ACCEPTANCE_GATES.md`, `08_STAGE1_GO_LIVE_RUNBOOK.md` | Duplicate webhook может создать двойную выдачу доступа или двойную wallet transaction |
| Clean DB migrations locally proven, staging/prod evidence отсутствует | `10_STAGE1_RISK_REGISTER.md`, `28_STAGE1_BE_001_CLEAN_DB_MIGRATION_EVIDENCE.md` | Staging/prod deploy может сломаться на пустой базе без повторного managed DB proof |
| First admin bootstrap locally proven, staging/prod/browser evidence отсутствует | `17_STAGE1_APPROVED_DECISION_LOG.md`, `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md`, `29_STAGE1_BE_002_FIRST_ADMIN_BOOTSTRAP_EVIDENCE.md` | Нельзя считать production admin готовым без target-environment transcript, admin login/2FA proof and backup recovery proof |
| Dirty worktree широкий | `git status`, `10_STAGE1_RISK_REGISTER.md` | Launch-critical код смешан с experimental изменениями |
| Backup/rollback/observability evidence отсутствуют | `07_STAGE1_ACCEPTANCE_GATES.md`, `08_STAGE1_GO_LIVE_RUNBOOK.md` | Go-live будет недоказуемым |

## Оценка по документам

| Документ | Оценка | Что нужно перед утверждением |
|---|---|---|
| `00_INDEX.md` | Хорошая карта комплекта | Поддерживать ссылки на `18` и `19` |
| `01_LAUNCH_ROADMAP.md` | Верная этапизация | Уточнить, что S1 является B2C beta, а не “почти 1.0” |
| `02_STAGE1_CHARTER.md` | Сильный baseline | Синхронизировать trial/payment/domain/legal решения с owner answers |
| `03_STAGE1_PRD_USER_FLOWS.md` | Достаточно полный PRD | Проверить, какие страницы будут скрыты default-off: referral, promo, analytics, monitoring |
| `04_STAGE1_TECHNICAL_SPEC.md` | Хорошая техническая рамка | Provider mappings заменить real callback evidence перед включением провайдеров |
| `05_STAGE1_DOCUMENT_REVIEW_PROTOCOL.md` | Полезный governance | Привязать к G0 approval и decision log |
| `06_STAGE1_IMPLEMENTATION_BACKLOG.md` | Подходит для реализации по ID | Не начинать задачи без owner decisions и evidence criteria |
| `07_STAGE1_ACCEPTANCE_GATES.md` | Правильный evidence-first подход | Добавить ссылки на конкретные evidence artifacts после выполнения |
| `08_STAGE1_GO_LIVE_RUNBOOK.md` | Нужный runbook | Заполнить реальные kill switch commands и evidence output |
| `09_STAGE1_LEGAL_SUPPORT_OPERATIONS.md` | Верно фиксирует legal/support risks | Legal/text approval закрыт; поддерживать operational evidence для mailboxes, provider behavior, cookie inventory and PII proof |
| `10_STAGE1_RISK_REGISTER.md` | Реалистичный risk baseline | Обновлять после каждого закрытого blocker |
| `11_STAGE1_REVIEW_CHECKLIST.md` | Owner answers внесены | Использовать как review checklist и сверять against `17_STAGE1_APPROVED_DECISION_LOG.md` |
| `12_STAGE1_DECISION_LOG_TEMPLATE.md` | Полезен | Использовать для всех изменений после approval |
| `17_STAGE1_APPROVED_DECISION_LOG.md` | Новый источник правды по owner decisions | Использовать как active decision log для реализации |
| `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` | Новый evidence/input checklist | Использовать для payment mappings, contacts, topology, observability, Remnawave and scope map |
| `19_STAGE1_TECH_DEBT_REGISTER.md` | Новый реестр placeholders | Закрывать перед go-live или явно переносить на S2+ |

## Критерий “документы можно утверждать”

Документы можно утверждать как Stage 1 baseline только если:

1. В `11_STAGE1_REVIEW_CHECKLIST.md` заполнены owner answers по `DEC-S1-001`...`DEC-S1-020`.
2. По каждому critical blocker есть одно из двух состояний: `Closed with evidence` или `Accepted as blocking dependency with owner and due date`.
3. Scope зафиксирован как B2C Controlled Public Beta.
4. Default-off список функций утверждён: partner payouts, partner public portal, native app store release, Helix/Verta/Beep production, referral/promo/gift, OAuth providers except Google/GitHub/Telegram identity, and any payment provider without real evidence.
5. Реализация начинается строго по IDs из `06_STAGE1_IMPLEMENTATION_BACKLOG.md`.

## Что нельзя делать после утверждения документов

1. Нельзя добавлять payment provider, OAuth provider, public domain, topology или Remnawave mode без decision log.
2. Нельзя считать задачу P0 закрытой без evidence artifact.
3. Нельзя смешивать launch-critical и experimental changes в одном release branch без явной карты включения/исключения.
4. Нельзя обещать paid beta, если нет production-ready payment path.
5. Нельзя расширять no-logs/privacy claims за рамки owner-approved S1 wording stance без deployed logging, analytics and provider metadata evidence.

## Рекомендуемое решение

Утвердить направление **Controlled Public Beta CyberVPN / B2C contour** со статусом: **Approved for S1 implementation planning after G0, blocked for production go-live until evidence gates pass**.

Следующий шаг: принять `18_STAGE1_OPERATIONAL_INPUTS_AND_EVIDENCE.md` и `19_STAGE1_TECH_DEBT_REGISTER.md`, затем выполнить entry criteria из `16_STAGE1_IMPLEMENTATION_ENTRY_CRITERIA.md` и открывать реализацию строго по IDs из `06_STAGE1_IMPLEMENTATION_BACKLOG.md`.
