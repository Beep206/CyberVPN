> CyberVPN Stage 1 Evidence
> ID: S1-LEGAL-003
> Date: 2026-05-05
> Scope: local legal-copy candidate, frontend/i18n guardrails and owner-approved S1 legal/text closure.

# S1-LEGAL-003 Acceptable Use Policy Evidence

## Result

`S1-LEGAL-003` is completed locally for implementation readiness and S1 owner-approved legal/text closure.

The repository now contains a Stage 1 Acceptable Use Policy candidate for Controlled Public Beta. Owner-approved S1 legal/text closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`. Abuse mailbox proof, node/provider torrent evidence and support/admin enforcement proof remain operational evidence.

## Implemented surfaces

| Surface | Result |
|---|---|
| Public route | Added `/acceptable-use` under the localized marketing app |
| i18n namespace | Added `AcceptableUse` and generated bundles for 39 locales |
| Primary copy | English and Russian S1 candidate copy added |
| Secondary locales | English fallback copy added to avoid unsafe or missing legal text |
| Footer | Added legal footer link to `/acceptable-use` |
| Tests | Added `stage1-acceptable-use-copy.test.ts` |

## Policy coverage

The S1 candidate states that CyberVPN may not be used for:

- spam and unsolicited bulk messaging;
- phishing, impersonation, scams and credential theft;
- account-stuffing abuse, password spraying and brute force account checking;
- malware, ransomware, botnets, command-and-control systems and exploit kits;
- DDoS, flooding, intrusion attempts, port scanning and network reconnaissance;
- abusive scraping, crawling, automation and rate-limit abuse;
- illegal content, child sexual abuse material, exploitation of minors and terrorist content;
- rights abuse, counterfeit activity and copyright/trademark infringement where a valid complaint or provider requirement applies;
- sanctions/export/payment-provider/hosting-provider rule violations;
- unauthorized resale, sharing or public posting of accounts, configs, QR codes or subscription URLs;
- public proxies, open relays, exit nodes, hosting services, crypto-mining and server workloads through a personal account.

## Torrent/P2P and node policy

The candidate deliberately avoids promising that torrent/P2P traffic is available everywhere.

S1 rule:

- torrent/P2P may be blocked, throttled or restricted by node;
- node/provider/jurisdiction rules can be stricter than the public AUP;
- final go-live needs node/provider torrent policy evidence before any public claim about torrent/P2P availability.

## Abuse reporting and enforcement

The candidate references:

- `abuse@cyber-vpn.net` for abuse reports;
- `support@cyber-vpn.net` for ordinary account, billing, trial and connection issues;
- warning, rate limiting, throttling, provisioning block, credential revocation, trial disablement, suspension, termination or renewal refusal as possible enforcement actions;
- manual review/support escalation for paid-but-no-access and abuse-related cases.

## External guardrails checked

These sources were used as non-legal implementation guardrails for the abuse categories and user-protection posture:

- European Commission Digital Services Act overview: https://digital-strategy.ec.europa.eu/en/policies/digital-services-act
- FTC phishing guidance: https://www.ftc.gov/business-guidance/small-businesses/cybersecurity/phishing
- CISA/FBI/NSA/MS-ISAC StopRansomware guide: https://www.cisa.gov/sites/default/files/2023-06/stopransomware_guide_508c_0.pdf
- CISA/FBI/MS-ISAC DDoS guidance: https://www.cisa.gov/sites/default/files/2024-03/understanding-and-responding-to-distributed-denial-of-service-attacks_508c.pdf

These sources do not replace legal review.

## Commands executed

```bash
npm run prepare:i18n
npm run test:run -- stage1-acceptable-use-copy
npm run test:run -- stage1-acceptable-use-copy stage1-privacy-policy-copy stage1-terms-copy
npm run lint -- 'src/app/[locale]/(marketing)/acceptable-use/page.tsx' src/widgets/footer.tsx src/i18n/client-namespaces.ts src/shared/lib/__tests__/stage1-acceptable-use-copy.test.ts
npm audit --audit-level=high
```

## Verification summary

| Check | Result |
|---|---|
| i18n bundle generation | Passed; 39 locale bundles generated |
| AUP copy tests | Passed; 4 tests passed |
| Legal-copy regression pack | Passed; 3 files and 10 tests across AUP, Privacy and Terms |
| Targeted ESLint | Passed |
| Frontend high-severity audit gate | Passed; only existing moderate Next/PostCSS advisory remains |
| Root high-severity audit gate | Passed; only existing moderate Next/PostCSS advisory remains |

## Remaining go-live blockers

| Blocker | Required before public beta |
|---|---|
| Final legal review | Owner/legal approval of AUP together with Terms, Privacy, Refund and Cookie Policy |
| Abuse mailbox proof | Prove delivery and ownership for `abuse@cyber-vpn.net` |
| Node/provider torrent policy | Attach provider/node evidence before claiming torrent/P2P availability |
| Enforcement evidence | Prove support/admin abuse handling, audit trail and escalation workflow in deployed environment |
| Localization | Decide whether English fallback is acceptable for S1 or provide reviewed translations |

## Files changed

| File / path | Purpose |
|---|---|
| `frontend/src/app/[locale]/(marketing)/acceptable-use/page.tsx` | Public localized AUP page |
| `frontend/messages/*/AcceptableUse.json` | AUP copy for all locales; EN/RU primary, EN fallback elsewhere |
| `frontend/messages/*/footer.json` | Footer legal link label |
| `frontend/scripts/generate-message-bundles.mjs` | Adds `AcceptableUse` namespace |
| `frontend/src/i18n/client-namespaces.ts` | Includes `AcceptableUse` in marketing namespace list |
| `frontend/src/widgets/footer.tsx` | Adds `/acceptable-use` legal link |
| `frontend/src/shared/lib/__tests__/stage1-acceptable-use-copy.test.ts` | Copy and guardrail tests |

## Next ID

Next ID to execute: `S1-FE-010` - Frontend bundle/env scan. Legal/text work is closed by `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
