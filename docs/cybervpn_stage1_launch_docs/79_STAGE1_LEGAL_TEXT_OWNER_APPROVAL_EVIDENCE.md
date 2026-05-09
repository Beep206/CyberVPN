> CyberVPN Stage 1 Evidence
> Date: 2026-05-05
> IDs: S1-LEGAL-001, S1-LEGAL-002, S1-LEGAL-003, S1-LEGAL-004, S1-LEGAL-005, S1-LEGAL-006, S1-LEGAL-007, S1-LEGAL-008, S1-LEGAL-009
> Scope: owner-approved legal/text/public-copy closure for S1 Controlled Public Beta.

# Stage 1 Legal/Text Owner Approval Evidence

## Owner decision

Owner instruction on 2026-05-05:

```text
Все что связано с текстами, условиями и юридической информацией закрыть. Считать это выполненным.
```

This evidence closes the Stage 1 legal/text/public-copy workstream for owner approval purposes. It does not commit sensitive personal identity, tax, banking, payment credential or provider dashboard details to the repository.

## Closure boundary

Closed by this decision:

- public Terms of Service wording;
- public Privacy Policy wording;
- public Acceptable Use Policy wording;
- public Refund Policy wording;
- public Cookie Policy wording;
- S1 no-logs/privacy wording stance;
- law-enforcement request response boundaries;
- abuse complaint response boundaries;
- S1 manual GDPR/data export/delete support procedure;
- owner/legal approval of support templates and public legal copy.

Still required outside this legal/text closure:

- deployed DNS/TLS/redirect evidence;
- real mailbox delivery evidence for published contact addresses;
- real payment provider account, callback, signature, refund and reconciliation evidence;
- deployed cookie/browser inventory and observability PII scrubbing evidence;
- staging/prod Remnawave, backup/restore, rollback and alert evidence;
- pre-RC scope map and security/dependency scans.

These remaining items are operational, security, provider or infrastructure evidence. They are not legal-copy drafting blockers.

## Closed legal items

| ID | Item | S1 owner-approved result | Remaining non-text evidence, if applicable |
|---|---|---|---|
| S1-LEGAL-001 | Terms of Service | Approved for S1 using the existing conservative Terms candidate and `individual founder/owner` seller category. Sensitive public identity details stay outside the repo. | Provider account ownership and public payment behavior evidence remain under payment/provider gates. |
| S1-LEGAL-002 | Privacy Policy | Approved for S1 using the existing bounded Privacy Policy candidate, data-category disclosure and `privacy@cyber-vpn.net` contact. | Deployed mailbox proof, processor/provider evidence and observability PII proof remain operational evidence. |
| S1-LEGAL-003 | Acceptable Use Policy | Approved for S1 with spam, malware, automated login abuse, scraping/abuse and bounded torrent/node/provider language. | Deployed abuse mailbox and enforcement/audit proof remain support/admin evidence. |
| S1-LEGAL-004 | Refund Policy | Approved for S1 as a manual, provider-bounded refund review process with no automatic or guaranteed refund promise. | Real provider refund behavior, finance/admin workflow and mailbox proof remain provider/support evidence. |
| S1-LEGAL-005 | Cookie Policy | Approved for S1 with strictly necessary storage disclosed and non-essential tracking disabled unless separately approved and evidenced. | Deployed browser cookie inventory, Set-Cookie proof, consent and PII evidence remain observability/security evidence. |
| S1-LEGAL-006 | No-logs claim validation | Approved S1 wording stance: no absolute no-logs overpromise; disclose account, payment, device, support, security and operational metadata where used; do not claim browsing-content/activity storage. | Actual deployed logging/Remnawave/node/Sentry proof remains security/observability evidence before public claims are expanded. |
| S1-LEGAL-007 | Law enforcement request policy | Approved S1 response boundary: intake through support/owner path, verify request, disclose only data that exists and is legally/owner-approved, never disclose secrets/config URLs/admin access, keep audit trail. | Live mailbox/support escalation proof remains support/ops evidence. |
| S1-LEGAL-008 | Abuse complaint runbook | Approved S1 boundary: intake through support/abuse route, collect safe identifiers/evidence, route to owner/ops, avoid exposing user secrets, audit any suspension/manual action. | Deployed abuse queue/admin enforcement proof remains support/admin evidence. |
| S1-LEGAL-009 | GDPR export/delete process | Approved S1 manual procedure: user requests data export/delete through support/privacy contact; support verifies account ownership, owner approves sensitive cases, actions are time-bound and auditable. | Automated self-service export/delete can be deferred; deployed support workflow proof remains support/ops evidence. |

## Public-copy rules accepted for S1

- Do not promise automatic renewal in S1.
- Do not promise universal torrent/P2P availability.
- Do not promise a fixed uptime/SLA unless separately evidenced.
- Do not expose private legal identity, tax, banking or payment credential data in the repo.
- Do not publish raw VPN subscription URLs, QR codes or config files in support/admin logs.
- Keep partner, payout, native app, Helix/Verta/Beep and public growth mechanics copy disabled unless a later stage approves them.

## Evidence status

This document is the owner-approval evidence for legal/text/public-copy closure. The next implementation item after this closure is `S1-FE-010` unless the owner chooses to reorder the remaining work.
