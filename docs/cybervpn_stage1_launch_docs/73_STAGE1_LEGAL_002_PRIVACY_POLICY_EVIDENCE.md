> CyberVPN Launch Program
> Stage: S1 Controlled Public Beta
> Task: S1-LEGAL-002
> Date: 2026-05-05
> Status: owner-approved for S1 legal/text closure in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`

# S1-LEGAL-002 Privacy Policy Evidence

## Result

`S1-LEGAL-002` is closed for local implementation evidence and S1 owner-approved legal/text closure.

The public Privacy Policy and privacy summary copy have been changed from placeholder/overbroad wording into a conservative S1 Controlled Public Beta privacy candidate. Owner-approved S1 legal/text closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`. Public go-live still requires non-text evidence such as mailbox delivery, provider/processor deployment evidence, observability PII scrubbing and release gates.

## Owner Decisions Used

| Decision | Applied rule |
|---|---|
| `DEC-S1-011` | Legal seller is `individual founder/owner`; sensitive identity/tax/banking details remain outside the repository. |
| `DEC-S1-010` | Payment accounts belong to legal seller/project owner; finance/ops access is limited and audited. |
| `DEC-S1-015` | S1 PostgreSQL backups are encrypted, off-host and retained 14 days; Redis/Valkey is not a durable source of truth. |
| `DEC-S1-019` | S1 identity paths include email/password, Telegram linking, magic link/OTP and OAuth for Google/GitHub. |

## Files Updated

| File | Change |
|---|---|
| `frontend/messages/en-EN/privacy-policy.json` | Replaced placeholder/absolute privacy copy with S1 Privacy Policy candidate. |
| `frontend/messages/ru-RU/privacy-policy.json` | Replaced placeholder/absolute privacy copy with S1 Privacy Policy candidate in Russian. |
| `frontend/messages/*/privacy-policy.json` | Non-EN/RU locales temporarily use the conservative English fallback to avoid publishing unsafe translated legacy copy. |
| `frontend/messages/en-EN/Privacy.json` | Replaced marketing-style privacy summary with bounded S1 privacy readiness summary. |
| `frontend/messages/ru-RU/Privacy.json` | Replaced marketing-style privacy summary with bounded S1 privacy readiness summary in Russian. |
| `frontend/messages/*/Privacy.json` | Non-EN/RU locales temporarily use the conservative English fallback for `/privacy`. |
| `frontend/messages/*/delete-account.json` | Updated privacy contact from `privacy@cybervpn.app` to `privacy@cyber-vpn.net`. |
| `frontend/src/app/[locale]/(marketing)/privacy-policy/page.tsx` | Removed hardcoded `privacy@cybervpn.app`; page now renders translated S1 privacy contact. |
| `frontend/src/app/[locale]/(marketing)/delete-account/delete-account-client.tsx` | Mailto now uses translated privacy contact instead of hardcoded legacy domain. |
| `frontend/src/i18n/messages/generated/*.json` | Regenerated locale bundles through `npm run prepare:i18n`. |
| `frontend/src/shared/lib/__tests__/stage1-privacy-policy-copy.test.ts` | Added guard tests for privacy categories, retention criteria, contacts and unsafe phrase regression. |
| `frontend/package.json`, `frontend/package-lock.json`, `package-lock.json` | Forward-upgraded frontend `axios` to `1.16.0` after `npm audit --audit-level=high` reported a high advisory during S1-LEGAL-002 security checks. |

## Privacy Candidate Rules

| Area | S1 rule |
|---|---|
| Controller/seller category | Uses `individual founder/owner`; sensitive personal, tax, banking and credential details remain outside the repository. |
| Privacy contact | Uses `privacy@cyber-vpn.net`; mailbox delivery evidence remains operational evidence. |
| Data categories | States account/authentication, Telegram/OAuth, payment, subscription/wallet, provisioning, support, security, audit, notification, webhook and observability data. |
| IP/user-agent | Explicitly states IP address and user-agent may exist in auth/security/session logs. |
| Remnawave | States Remnawave references/subscription URL/provisioning state may be processed. |
| No-logs wording | Bounded: no final audited no-logs claim until backend, Remnawave, VPN node, support, provider and observability evidence is validated. |
| Retention criteria | States active-account retention, payment/provider/legal criteria, support target of 90 days, deletion target of 30 days with exceptions, and 14-day PostgreSQL backup retention. |
| Providers/processors | Lists approved S1 provider categories and selected providers, with enablement gated by credentials, webhook/status evidence and PII controls. |
| Security claims | Replaces absolute claims with evidence-bound controls: hashing, selected encryption, 2FA/RBAC/audit, private DB/Valkey/Remnawave API and HTTPS ingress. |

## External Drafting Guardrails

These official sources were used only as risk guardrails, not as legal approval:

- GDPR Article 13 lists information that may need to be provided when collecting personal data from users: https://eur-lex.europa.eu/eli/reg/2016/679/art_13/oj/eng
- EDPB transparency guidance explains that privacy information must be concise, transparent, intelligible and easy to access: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-transparency-under-regulation-2016679_en
- FTC advertising guidance says claims must be truthful, non-misleading and supported by evidence: https://www.ftc.gov/business-guidance/advertising-marketing

## Local Checks

| Check | Result |
|---|---|
| `npm run test:run -- src/shared/lib/__tests__/stage1-privacy-policy-copy.test.ts` | Pass: 3 tests. |
| `npm run lint -- src/shared/lib/__tests__/stage1-privacy-policy-copy.test.ts 'src/app/[locale]/(marketing)/privacy-policy/page.tsx' 'src/app/[locale]/(marketing)/delete-account/delete-account-client.tsx'` | Pass. |
| `npm audit --audit-level=high` from repo root and `frontend` | Pass for high severity after `axios` forward-upgrade; existing moderate `next/postcss` advisory remains tracked in `TD-S1-SEC-001` because the suggested auto-fix is a breaking Next downgrade. |
| Privacy unsafe phrase guard | Pass for `privacy-policy.json`, `Privacy.json` and `delete-account.json` source messages. |
| i18n bundle generation | Pass: 39 generated locale bundles. |

## Remaining Go-Live Blockers

These are still blockers before any public paid beta:

1. Approve final public controller/seller display name outside the repository.
2. Approve final jurisdiction/country and whether a public legal address is required.
3. Prove `privacy@cyber-vpn.net` mailbox delivery and ownership before publishing it as final.
4. Align Privacy Policy with final Terms, AUP, Refund Policy, Cookie Policy and data retention policy.
5. Replace provider/processor candidate wording with real enabled provider evidence.
6. Validate no-logs wording against backend logs, Remnawave, VPN node logs, payment providers, support tooling and observability.
7. Decide whether non-English Privacy Policy pages are published as English fallback or receive reviewed translations.
8. Confirm actual analytics/observability configuration and PII scrubbing before publishing analytics wording.

## Follow-Up Debt

| Debt | Reason |
|---|---|
| Non-EN/RU privacy fallback | Safer than publishing old unsafe localized privacy copy, but not final localization. |
| Privacy mailbox evidence | `privacy@cyber-vpn.net` is the candidate public contact; delivery proof remains required. |
| Final processor list | Candidate lists approved S1 provider categories; live provider enablement evidence is still open. |
| No-logs validation | Copy is bounded, but final public claim requires architecture and deployment evidence. |
