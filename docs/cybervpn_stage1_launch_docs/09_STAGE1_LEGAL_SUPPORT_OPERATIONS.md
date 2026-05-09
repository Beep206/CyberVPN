> CyberVPN Launch Program  
> Версия: 0.1-draft  
> Дата подготовки: 2026-05-02  
> Основание: ответы на CyberVPN Launch Questionnaire от 2026-04-25.  
> Статус: draft для оценки владельцем проекта. Не является финальным разрешением на разработку или запуск.


# Stage 1 Legal, Support and Operations Requirements

## Purpose

Stage 1 is public-facing, even if controlled. Therefore legal, privacy and support readiness are launch-critical. This document defines the minimum required pack.

## Legal documents required before public beta

| ID | Document | Stage 1 status | Minimum requirement |
|---|---|---|---|
| S1-LEGAL-001 | Terms of Service | Owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Identify seller category, service, billing, restrictions and termination without committing sensitive identity/tax/banking data |
| S1-LEGAL-002 | Privacy Policy | Owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Remove public placeholders, disclose data categories, retention criteria and privacy contact |
| S1-LEGAL-003 | Acceptable Use Policy | Owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Prohibit spam, malware, account-stuffing abuse, scraping/abuse and clarify bounded torrent/node/provider rules |
| S1-LEGAL-004 | Refund Policy | Owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Match S1 manual refund/support process and avoid automatic/guaranteed refund promises |
| S1-LEGAL-005 | Cookie Policy | Owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Disclose actual cookies/storage/analytics stance and default-off non-essential tracking rule |
| S1-LEGAL-006 | No-logs Policy Explanation | Owner-approved for S1 wording stance in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Avoid absolute no-logs overpromise; disclose operational metadata where used |
| S1-LEGAL-007 | Law Enforcement Request Policy | Owner-approved for S1 response boundary in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Define intake, verification, minimum disclosure and audit trail |
| S1-LEGAL-008 | Abuse Complaint Runbook | Owner-approved for S1 response boundary in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | Define complaint intake, safe evidence handling and owner/ops escalation |
| S1-LEGAL-009 | GDPR Export/Delete Procedure | Owner-approved for S1 manual procedure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` | User can request/export/delete through support/privacy route; automation may be deferred |

## Owner legal/payment decisions

- Legal seller for S1: individual founder/owner.
- Payment provider accounts belong to the legal seller/project owner.
- Payment operations require finance/ops backup `@Sasha_Beep`, limited technical access, audited refunds/reconciliation and approved secret storage.
- Approved payment provider set: PayRam, NOWPayments, CryptoBot, Telegram Stars for Telegram, Digiseller for users from Russia, YooKassa for users from Russia.
- Each provider-specific refund/support statement must match the actual provider behavior before that provider is enabled.
- Public legal/text/copy approval for S1 is closed by owner decision in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
- Sensitive identity, banking, tax and payment credential details must not be committed to the repository.

## Owner legal/text closure decision

Owner decided on 2026-05-05 that all text, terms and legal-information work is closed for S1. This makes `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md` the active owner-approval record for `S1-LEGAL-001`...`S1-LEGAL-009`.

The closure does not replace operational evidence: real mailboxes, deployed browser cookie inventory, provider refund behavior, alerting, support/admin workflow, Remnawave evidence and observability PII proof remain tracked in their own workstreams.

## Terms of Service S1 candidate

Local S1 Terms candidate evidence exists in `72_STAGE1_LEGAL_001_TERMS_OF_SERVICE_EVIDENCE.md`.

The candidate removes unsafe stylized legal language from the public Terms page, avoids automatic-renewal and uptime/SLA promises, references manual renewal, support and refund contacts, and states the owner-approved `individual founder/owner` seller category without committing sensitive identity, banking, tax or credential details.

This Terms text is owner-approved for S1 legal/text closure. Provider-aligned payment/refund behavior remains a provider/support evidence requirement before a payment provider is enabled.

## Privacy Policy S1 candidate

Local S1 Privacy Policy candidate evidence exists in `73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`.

The candidate removes `[Your Company Address]`, legacy `privacy@cybervpn.app`, absolute no-logs claims, RAM-disk claims and unsupported end-to-end/security claims from the public privacy surfaces. It states S1 data categories, retention criteria, privacy contact `privacy@cyber-vpn.net`, provider categories and no-logs validation limits.

This Privacy Policy text is owner-approved for S1 legal/text closure. Provider/processor, mailbox delivery, deployed logging and observability PII evidence remain operational/security evidence requirements.

## Acceptable Use Policy S1 candidate

Local S1 Acceptable Use Policy candidate evidence exists in `74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md`.

The candidate adds a public `/acceptable-use` page, footer legal link, all-locale i18n coverage and copy tests. It prohibits spam, phishing, account-stuffing abuse, malware/ransomware, DDoS/flooding, scraping/automation abuse, illegal content, exploitation of minors, rights abuse, sanctions/provider-rule violations, unauthorized resale/config sharing and public proxy/open relay/server workloads through personal accounts.

Torrent/P2P copy is intentionally bounded: CyberVPN does not promise torrent/P2P availability on every node, and node/provider/jurisdiction rules can be stricter than the public AUP.

This AUP text is owner-approved for S1 legal/text closure. `abuse@cyber-vpn.net` delivery proof, node/provider torrent evidence and deployed support/admin enforcement proof remain operational evidence requirements.

## Refund Policy S1 candidate

Local S1 Refund Policy candidate evidence exists in `75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md`.

The candidate adds a public `/refund-policy` page, footer legal link, all-locale i18n coverage and copy tests. It defines S1 refunds as a manual request/review process through `refund@cyber-vpn.net` or approved Telegram/support flow. It avoids automatic or guaranteed refund promises and requires payment status, provider rules, provisioning state, support evidence and abuse checks before approval or denial.

Provider posture is intentionally evidence-bound:

- PayRam and CryptoBot/Crypto Pay require manual crypto refund/transfer/check workflows unless later provider automation is proven.
- NOWPayments requires merchant-side refund responsibility review and provider validation for wrong-asset/wrong-network/minimum-amount cases.
- Telegram Stars requires stored `telegram_payment_charge_id`, `/paysupport` support and proven `refundStarPayment` behavior.
- Digiseller follows purchase/dispute and invoice-state evidence.
- YooKassa can support full/partial refunds for successful payments where the payment method supports it, but requires idempotency, fiscal/receipt alignment and finance approval.

This Refund Policy text is owner-approved for S1 legal/text closure. `refund@cyber-vpn.net` delivery proof, provider-specific refund evidence and deployed support/admin refund workflow proof remain provider/support evidence requirements.

## Cookie Policy S1 candidate

Local S1 Cookie Policy candidate evidence exists in `76_STAGE1_LEGAL_005_COOKIE_POLICY_EVIDENCE.md`.

The candidate adds a public `/cookie-policy` page, footer legal link, all-locale i18n coverage and copy tests. It discloses locale/routing storage, web auth cookies, short-lived OAuth/Magic link/OTP/2FA cookies, CSRF origin/referer protection, Sentry/Web Vitals/internal analytics, Telegram Mini App runtime data and provider-side storage boundaries.

The S1 rule is conservative: strictly necessary storage can support login, security, checkout return handling, language routing, support and VPN provisioning, while GA4, PostHog, marketing pixels, advertising retargeting, profiling and other non-essential storage are disabled unless separately approved, consented where required and evidenced.

This Cookie Policy text is owner-approved for S1 legal/text closure. Deployed browser cookie inventory, redacted `Set-Cookie` proof, consent proof for non-essential storage and observability PII evidence remain security/observability evidence requirements.

## Legal hard blockers

Public beta must not launch if:

- Privacy Policy contains `[Your Company Address]` or similar placeholders.
- Seller/legal entity is not identified where required by the payment/legal model.
- Refund Policy contradicts actual provider behavior or promises automatic/guaranteed refunds without evidence.
- Cookie/analytics behavior is not disclosed or deployed browser inventory/`Set-Cookie` evidence contradicts the Cookie Policy.
- No-logs claim contradicts actual data collection/logging.
- AUP does not prohibit obvious abuse or makes unsupported torrent/P2P availability claims.

## Data categories to document

At minimum, Privacy Policy/Data Retention must address:

- Email.
- Login/username/display name.
- Telegram ID/username where used.
- OAuth account identifiers.
- Sessions and auth/security events.
- Payment metadata and provider transaction identifiers.
- Subscription/wallet state.
- Device credentials/config delivery state.
- Usage/traffic data if displayed.
- IP/user-agent fields if stored by auth/security logs.
- Support ticket data.
- Backups.
- Analytics events.

Do not claim not to collect a category if code/logs/providers actually collect it.

## No-logs validation

No-logs wording must be precise. Recommended Stage 1 rule:

- Do not store browsing content.
- Do not store raw browsing activity.
- Do not expose raw VPN config links in logs/support.
- Be explicit if operational metadata such as account, payment, device, quota, support and security logs is stored.
- Be explicit whether Remnawave/node logs are disabled, minimized or retained for security/operations.

## Support channels

Stage 1 support channels:

- Telegram.
- Email: `support@cyber-vpn.net`.
- Refund/payment email: `refund@cyber-vpn.net`.
- Privacy email candidate: `privacy@cyber-vpn.net`; delivery evidence required before publishing as final.
- Web tickets.
- Bot / AI first line.

Operational alert channels:

- Private Telegram alert channel: `-5173727789`.
- Backup alert email: `backup@cyber-vpn.net`.
- Optional aliases under `cyber-vpn.net`: `alerts@`, `ops@`, `security@`, `privacy@`, `abuse@`.

AI first line is acceptable only if:

- It can create/escalate tickets.
- It does not hallucinate billing/provisioning state.
- It does not expose secrets/config links unnecessarily.
- It has scripted answers for critical cases.

## S1 support ticket path

Local implementation evidence exists in `69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`.

| Intake path | Stage 1 routing |
|---|---|
| Telegram Bot | `/support <question>` and `/paysupport <question>` first-line triage can create backend support staff-note escalation |
| Telegram Mini App | Routed as `telegram_mini_app` in the shared support-ticket contract; live UX evidence still required |
| Web ticket/contact | `/contact` uses the official support profile and `support@cyber-vpn.net` handoff; deployed delivery proof still required |
| Support email | `support@cyber-vpn.net` for general support, paid-no-access and VPN/connectivity issues |
| Refund/payment email | `refund@cyber-vpn.net` for refund, failed payment and provider reconciliation issues |
| Admin manual | Admin/support can create safe internal notes/references when handling user reports |

Ticket references must be safe to paste into support/admin logs. User-provided summaries must redact VPN config URLs, HTTP URLs, email addresses, Telegram bot-token-like values and long secret-like values before storage.

SLA baseline:

- P0: acknowledgement <=15 minutes.
- P1: acknowledgement <=60 minutes.
- P2/P3 and all beta customer first responses: <=12 hours.

## Support roles

| Role | Allowed | Not allowed |
|---|---|---|
| AI first line | Basic troubleshooting, collect safe identifiers, create ticket | Refund approvals, raw secrets, account merges, credential regeneration unless strictly controlled |
| Support | View user/subscription/payment status, create escalation, trigger safe retry if permitted | See provider secrets/OAuth tokens/TOTP secrets/raw sensitive logs |
| Finance | Payment/refund/dispute review | VPN credentials unless needed |
| Ops | Provisioning/node/Remnawave incidents | Unnecessary payment secrets |
| Owner | Emergency decisions and privileged operations | Must still be audited |

## Launch-week responsible handles

| Responsibility | Assigned handle | Evidence required |
|---|---|---|
| Primary on-call/support owner | `@Sasha_Beep` | P0/P1 alert acknowledgement test |
| Backup on-call/support owner | `@Sasha_Beep` | Backup alert route test |
| First admin bootstrap owner | `@Sasha_Beep` | Redacted bootstrap + audit evidence |
| Finance/ops backup | `@Sasha_Beep` | Refund/reconciliation access matrix |

Single-person coverage is acceptable for S1 only if the go-live decision explicitly accepts the risk. A separate backup should be assigned before S2.

## Required support templates

### Template SUP-S1-001 — Failed payment

```text
Мы видим, что оплата не завершилась или ожидает подтверждения. Проверьте статус платежа в кабинете или Telegram Mini App. Если деньги списались, отправьте ID платежа, дату, способ оплаты или скрин без номера карты, CVV/CVC, QR-кода, subscription URL и config. Мы сверим статус у провайдера и обновим доступ только после подтверждения платежа.
```

Queue: `s1_payment_finance_review`.
Contact: `refund@cyber-vpn.net`.
Do not request: password, 2FA/TOTP code, full card number, CVV/CVC, raw QR code, raw subscription URL, raw config file, seed/private key.

### Template SUP-S1-002 — Paid but no access

```text
Оплата найдена или проверяется. Если платеж подтвержден, доступ должен быть выдан автоматически. Если доступ не появился, мы проверим payment status, provisioning status и Remnawave-состояние, затем повторим выдачу доступа или передадим заявку технической команде. Не отправляйте публично QR-код, subscription URL или config file.
```

Queue: `s1_paid_no_access_review`.
Contact: `support@cyber-vpn.net`.
Do not request: password, 2FA/TOTP code, full card number, CVV/CVC, raw QR code, raw subscription URL, raw config file, seed/private key.

### Template SUP-S1-003 — VPN does not connect

```text
Проверьте срок подписки, лимит устройств, правильную инструкцию для вашей платформы и что используется актуальный QR/subscription URL/config. Если подключение все равно не работает, отправьте платформу, приложение/клиент, страну подключения, примерное время ошибки и скрин сообщения без QR-кода, subscription URL и config file.
```

Queue: `s1_vpn_connectivity_support`.
Contact: `support@cyber-vpn.net`.
Do not request: password, 2FA/TOTP code, full card number, CVV/CVC, raw QR code, raw subscription URL, raw config file, seed/private key.

### Template SUP-S1-004 — Expired subscription

```text
Подписка истекла или находится в grace period. Для восстановления доступа продлите тариф в кабинете или Telegram Mini App. В Stage 1 мы не обещаем автоматическое списание или автопродление: продление выполняется вручную пользователем. Если оплата уже была выполнена, отправьте ID платежа или дату оплаты, и мы проверим статус.
```

Queue: `s1_customer_support`.
Contact: `support@cyber-vpn.net`.
Do not request: password, 2FA/TOTP code, full card number, CVV/CVC, raw QR code, raw subscription URL, raw config file, seed/private key.

### Template SUP-S1-005 — Refund request

```text
Мы приняли запрос на возврат. Для проверки укажите ID платежа, дату оплаты, способ оплаты и причину обращения. Решение зависит от статуса платежа, использованного провайдера и финальной Refund Policy. Не отправляйте номер карты, CVV/CVC, пароль, QR-код, subscription URL или config file. До проверки мы не обещаем автоматический или гарантированный возврат.
```

Queue: `s1_payment_finance_review`.
Contact: `refund@cyber-vpn.net`.
Do not request: password, 2FA/TOTP code, full card number, CVV/CVC, raw QR code, raw subscription URL, raw config file, seed/private key.

## Support escalation process

```text
AI/bot first line
  -> Support triage
    -> Finance for payment/refund/dispute
    -> Ops for Remnawave/provisioning/node outage
    -> Owner for account merge/legal/abuse/emergency kill switch
```

Escalation must create a ticket, staff note or audit trail. The local machine-readable rule catalog is implemented in `backend/src/presentation/api/shared/stage1_support_escalation.py` and evidenced in `71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`.

S1 owners and alert destinations:

| Item | Value |
|---|---|
| Primary on-call/support owner | `@Sasha_Beep` |
| Backup on-call/support owner | `@Sasha_Beep` |
| Private Telegram alert channel | `-5173727789` |
| Backup alert email | `backup@cyber-vpn.net` |
| Support email | `support@cyber-vpn.net` |
| Refund/support email | `refund@cyber-vpn.net` |

Single-person coverage remains an S1 risk until explicitly accepted in the go-live record or split to a separate backup.

## Typical incidents and owner path

| Incident / trigger | Path | Target | Priority | Queue | SLA / rule |
|---|---|---|---|---|---|
| General support | AI/bot -> Support | Support | P3 | `s1_customer_support` | First response <=12h |
| Payment failed | AI/bot -> Support -> Finance | Finance | P1 | `s1_payment_finance_review` | Ack <=1h; verify provider final status |
| Refund request | AI/bot -> Support -> Finance | Finance | P1 | `s1_payment_finance_review` | Ack <=1h; no guaranteed refund promise |
| Paid but no access | AI/bot -> Support -> Ops | Ops | P1 | `s1_paid_no_access_review` | Ack <=1h; verify payment/provisioning/Remnawave |
| Paid but no access older than 24h | Support -> Ops -> Owner | Owner | P0 | `s1_paid_no_access_review` | Ack <=15m; must resolve or pause affected flow |
| Provisioning failure | Support -> Ops | Ops | P1 | `s1_paid_no_access_review` | Ack <=1h; retry/manual recovery after safe verification |
| Remnawave/node outage | Support -> Ops -> Owner | Ops | P0 | `s1_ops_incident` | Ack <=15m; kill switch allowed |
| VPN connectivity incident | AI/bot -> Support -> Ops | Ops | P2 | `s1_vpn_connectivity_support` | First response <=12h; ops if node/protocol issue suspected |
| Expired subscription stuck | AI/bot -> Support | Support | P2 | `s1_customer_support` | First response <=12h; no autoprolongation promise |
| Account access conflict | AI/bot -> Support -> Owner | Owner | P1 | `s1_owner_account_access` | Ack <=1h; no silent account merge |
| Legal/abuse request | Support -> Owner | Owner | P0 | `s1_owner_legal_abuse` | Ack <=15m; preserve audit trail |
| Emergency kill switch | Ops -> Owner | Owner | P0 | `s1_owner_emergency` | Ack <=15m; owner can pause registration/payments/trial/provisioning or initiate rollback |

Support must not request passwords, 2FA/TOTP codes, full card numbers, CVV/CVC, raw QR codes, raw subscription URLs, raw config files, provider secrets, bot tokens or private keys.

## Operational minimums

Before beta:

- Support mailbox/chat/channel created.
- Ticket intake path tested.
- Admin/support view tested.
- Support cannot view secrets.
- Escalation path exists.
- Status page ready.
- Incident note template ready.
- On-call/ops role identified.
- Payment reconciliation owner identified.
- Backup/restore owner identified.

## Abuse policy minimum

AUP must prohibit:

- spam;
- malware;
- account-stuffing abuse;
- scraping/abuse;
- attacks against third parties;
- illegal activity;
- excessive abuse of network resources where applicable;
- torrent traffic on nodes where torrent blocking is required.

If torrent traffic is blocked only on certain nodes, the policy must not claim global behavior unless true.

## Refund/dispute operations

Refunds/disputes must be role-gated and audit-logged. The local S1 implementation evidence is recorded in `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md`.

S1 role boundary:

- customer can submit a refund request for their own order;
- support can intake and escalate refund/dispute cases;
- finance, admin, super-admin and owner/super-admin can review refunds and reconcile dispute state;
- support, operator and viewer must not approve refunds or mutate dispute financial state;
- provider-side execution remains disabled until provider-specific refund/support/reconciliation evidence exists.

Minimum states:

- refund requested;
- under review;
- approved;
- rejected;
- refunded;
- provider failed;
- dispute opened;
- dispute resolved.

Refund support must not require users to post sensitive payment data in public chats.

## Launch support readiness checklist

- Failed payment template ready.
- Paid but no access template ready.
- VPN does not connect template ready.
- Refund template ready.
- Expired subscription template ready.
- Remnawave unavailable support instruction ready.
- Support escalation tested.
- Admin/support permissions tested.
- Support privacy restrictions tested.
- Status page message templates ready.
