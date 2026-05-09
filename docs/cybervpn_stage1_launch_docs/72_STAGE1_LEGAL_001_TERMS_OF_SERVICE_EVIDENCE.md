> CyberVPN Launch Program
> Stage: S1 Controlled Public Beta
> Task: S1-LEGAL-001
> Date: 2026-05-05
> Status: owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`

# S1-LEGAL-001 Terms of Service Evidence

## Result

`S1-LEGAL-001` is closed for local implementation evidence and S1 owner-approved legal/text closure.

The public Terms copy has been changed from stylized/fantasy wording into a conservative S1 Controlled Public Beta Terms candidate. Owner-approved S1 legal/text closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`. Public go-live still requires non-text evidence such as payment provider behavior, deployed support/mailbox proof, observability and release gates.

## Owner Decisions Used

| Decision | Applied rule |
|---|---|
| `DEC-S1-011` | Legal seller is `individual founder/owner`; concrete public display details remain outside the repository until approved. |
| `DEC-S1-010` | Payment accounts belong to legal seller/project owner; refunds/reconciliation are audited and role-limited. |
| `DEC-S1-020` | S1 does not promise automatic renewal; manual renewal and expiry reminders only if tested. |
| `DEC-S1-018` | Referral/promo/gift flows disabled by default; no public rewards or checkout discounts in S1 Terms. |

## Files Updated

| File | Change |
|---|---|
| `frontend/messages/en-EN/Terms.json` | Replaced old fantasy/legal copy with S1 Terms candidate. |
| `frontend/messages/ru-RU/Terms.json` | Replaced old fantasy/legal copy with S1 Terms candidate in Russian. |
| `frontend/messages/*/Terms.json` | Non-EN/RU locales use the conservative English fallback to avoid publishing unsafe translated legacy copy; owner accepts this S1 legal/text localization stance. |
| `frontend/src/i18n/messages/generated/*.json` | Regenerated locale bundles through `npm run prepare:i18n`. |
| `frontend/src/shared/lib/__tests__/stage1-terms-copy.test.ts` | Added guard tests for S1 Terms content and unsafe phrase regression. |

## Terms Candidate Rules

The S1 Terms candidate now states or avoids the following:

| Area | S1 rule |
|---|---|
| Service status | CyberVPN is a Controlled Public Beta VPN service. |
| Seller | Uses `individual founder/owner` as the owner-approved seller category; no sensitive personal, tax, banking or credential details are committed. |
| Seller details | Sensitive personal, tax, banking and credential details stay outside the repository; owner accepts this S1 public-copy boundary. |
| Support contacts | Uses `support@cyber-vpn.net` and `refund@cyber-vpn.net`. |
| Renewal | No automatic renewal promise, no saved recurring payment method promise, no "renews automatically" wording. |
| Payment/refund | Refunds depend on final Refund Policy, provider status and support/finance review. |
| Provisioning | Mentions Remnawave as the provisioning control plane without exposing internal details. |
| Availability | No hard public SLA or `99.9%` uptime promise in Terms. |
| Abuse | Prohibits spam, malware, account-stuffing abuse, scraping, sanctions evasion and unlawful activity. |
| Minors | Requires the user to be legally able to enter the agreement and not be a minor where service use is restricted. |
| Secrets/sensitive data | Tells users not to send passwords, 2FA codes, CVV/CVC, raw subscription URLs, QR codes or config files to support. |
| Termination | Allows suspension/termination for abuse, fraud, unpaid/expired access, security risk or legal/compliance reasons, while avoiding arbitrary "without explanation" language. |

## External Drafting Guardrails

These official sources were used only as risk guardrails, not as legal approval:

- FTC advertising guidance says advertising claims must be truthful, non-misleading and evidence-based: https://www.ftc.gov/business-guidance/advertising-marketing
- GDPR Article 13 identifies information that may be required when personal data is collected from users: https://eur-lex.europa.eu/eli/reg/2016/679/art_13/oj/eng
- European Commission digital contract guidance describes digital content/service consumer-protection concepts, including remedies/refunds where applicable: https://commission.europa.eu/business-economy-euro/doing-business-eu/contract-rules/digital-contracts/digital-contract-rules_en

## Local Checks

| Check | Result |
|---|---|
| `npm run test:run -- src/shared/lib/__tests__/stage1-terms-copy.test.ts` | Pass: 3 tests. |
| `npm run lint -- src/shared/lib/__tests__/stage1-terms-copy.test.ts` | Pass. |
| Terms unsafe phrase guard | Pass for all `frontend/messages/*/Terms.json`. |
| i18n bundle generation | Pass: 39 generated locale bundles. |

## Remaining Non-Text Go-Live Evidence

These are still required before public paid beta, but they are not legal-copy drafting blockers:

1. Align enabled provider payment/refund behavior with real provider evidence.
2. Prove deployed support/refund mailbox and support/admin workflow.
3. Verify public marketing/status availability claims under frontend/content gates before publishing affected surfaces.

## Follow-Up Debt

| Debt | Reason |
|---|---|
| Non-EN/RU Terms fallback | Owner accepts this S1 legal/text localization stance; improved reviewed translations can be done later. |
| Marketing/status `99.9/99.99` claims outside Terms | Closed locally under `S1-FE-001`: unsupported public uptime/availability claim patterns were removed and audited in `107_STAGE1_FE_001_MARKETING_CRITICAL_PAGES_EVIDENCE.md`; repeat on deployed RC before public launch. |
