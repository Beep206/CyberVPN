> CyberVPN Stage 1 Evidence
> ID: S1-LEGAL-004
> Date: 2026-05-05
> Scope: local refund-policy candidate, frontend/i18n guardrails and owner-approved S1 legal/text closure.

# S1-LEGAL-004 Refund Policy Evidence

## Result

`S1-LEGAL-004` is completed locally for implementation readiness and S1 owner-approved legal/text closure.

The repository now contains a Stage 1 Refund Policy candidate for Controlled Public Beta. Owner-approved S1 legal/text closure is recorded in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`. Provider-specific refund evidence, `refund@cyber-vpn.net` mailbox proof and deployed support/admin workflow evidence remain provider/support evidence.

## Implemented surfaces

| Surface | Result |
|---|---|
| Public route | Added `/refund-policy` under the localized marketing app |
| i18n namespace | Added `RefundPolicy` and generated bundles for 39 locales |
| Primary copy | English and Russian S1 candidate copy added |
| Secondary locales | English fallback copy added to avoid unsafe or missing legal text |
| Footer | Added legal footer link to `/refund-policy` |
| Account deletion copy | Removed old absolute refund-denial wording; now points to Refund Policy/provider rules |
| Tests | Added `stage1-refund-policy-copy.test.ts` |

## S1 Refund Policy Model

The S1 candidate is a request/review policy, not an automatic-refund promise.

Core rules:

- refund requests go to `refund@cyber-vpn.net` or approved Telegram/support flow;
- user should provide account email or Telegram ID, payment/provider invoice ID, date, provider/method and short reason;
- support must not ask for passwords, 2FA codes, full card numbers, CVV/CVC, seed phrases, raw QR codes, raw subscription URLs or raw VPN configuration files;
- no refund is guaranteed before payment status, provider rules, provisioning status, support evidence and abuse checks are reviewed;
- paid-but-no-access/orphan payment cases must not remain unresolved longer than 24 hours without owner/support escalation;
- full refunds normally cancel or disable the related paid subscription period;
- partial refunds may adjust subscription time, quota, wallet balance or another paid entitlement;
- trial access does not create a cash refund entitlement;
- abuse/fraud/AUP violations may reduce refund eligibility where allowed by law.

## Provider-Specific Baseline

| Provider | S1 refund posture |
|---|---|
| PayRam | Crypto refunds are manual; no automatic on-chain chargeback. Refunds require merchant-controlled dashboard/API or direct wallet transfer, wallet-address validation and finance approval. |
| NOWPayments | Completed/partially paid crypto transactions generally become merchant-side responsibility; wrong-asset/wrong-network/minimum-amount cases may require provider validation. |
| CryptoBot / Crypto Pay | Paid invoices can grant access, but refunds require manual finance/support action through an approved transfer/check/provider workflow. |
| Telegram Stars | Refunds are limited to Telegram Bot/Mini App paid flow and require stored `telegram_payment_charge_id`, `/paysupport` support and proven `refundStarPayment` behavior. |
| Digiseller | Refund handling follows Digiseller purchase/dispute flow, seller balance rules, invoice status evidence and manual review for delivered digital credentials. |
| YooKassa | Refunds can be created for `succeeded` payments where method supports it; full/partial refund must use provider evidence, idempotency keys and fiscal/receipt handling where required. |

## External Provider Sources Checked

These sources were used only as implementation/provider guardrails, not as legal approval:

- PayRam payment status: https://docs.payram.com/api-integration/payments-api/payment-status
- PayRam refund/chargeback FAQ: https://docs.payram.com/faqs/general-faqs
- NOWPayments statuses: https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses
- NOWPayments refunds and validation flow: https://nowpayments.zendesk.com/hc/en-us/articles/18316629513757-Refunds-and-Validation-flow
- CryptoBot / Crypto Pay API: https://help.send.tg/en/articles/10279948-crypto-pay-api
- Telegram Stars payments: https://core.telegram.org/bots/payments-stars
- Telegram Bot API `refundStarPayment`: https://core.telegram.org/bots/api#refundstarpayment
- Digiseller refund policy: https://digiseller.com/refundpolicy
- Digiseller API invoice states: https://my.digiseller.com/inside/api_general.asp
- YooKassa refunds: https://yookassa.ru/developers/payment-acceptance/after-the-payment/refunds

## Commands executed

```bash
npm run prepare:i18n
npm run test:run -- stage1-refund-policy-copy
npm run test:run -- stage1-refund-policy-copy stage1-acceptable-use-copy stage1-privacy-policy-copy stage1-terms-copy
npm run lint -- 'src/app/[locale]/(marketing)/refund-policy/page.tsx' src/widgets/footer.tsx src/i18n/client-namespaces.ts src/shared/lib/__tests__/stage1-refund-policy-copy.test.ts
npm audit --audit-level=high
```

## Verification summary

| Check | Result |
|---|---|
| i18n bundle generation | Passed; 39 locale bundles generated |
| Refund Policy copy tests | Passed; 4 tests passed |
| Legal-copy regression pack | Passed; 4 files and 14 tests across Refund, AUP, Privacy and Terms |
| Targeted ESLint | Passed |
| Frontend high-severity audit gate | Passed; only existing moderate Next/PostCSS advisory remains |
| Root high-severity audit gate | Passed; only existing moderate Next/PostCSS advisory remains |

## Remaining go-live blockers

| Blocker | Required before public beta |
|---|---|
| Final legal review | Owner/legal approval of Refund Policy together with Terms, Privacy, AUP and Cookie Policy |
| Refund mailbox proof | Prove delivery and ownership for `refund@cyber-vpn.net` |
| Provider refund evidence | Per enabled provider: real sandbox/prod refund/support evidence, callback/status samples, idempotency and finance approval workflow |
| Support/admin workflow | Prove deployed refund queue, audit trail, operator actions and user notification path |
| Russia path | YooKassa/Digiseller refund, fiscalization/receipt and seller obligations must be approved before Russia paid path |
| Localization | Decide whether English fallback is acceptable for S1 or provide reviewed translations |

## Files changed

| File / path | Purpose |
|---|---|
| `frontend/src/app/[locale]/(marketing)/refund-policy/page.tsx` | Public localized Refund Policy page |
| `frontend/messages/*/RefundPolicy.json` | Refund copy for all locales; EN/RU primary, EN fallback elsewhere |
| `frontend/messages/*/footer.json` | Footer legal link label |
| `frontend/messages/*/delete-account.json` | Removes absolute refund-denial wording |
| `frontend/scripts/generate-message-bundles.mjs` | Adds `RefundPolicy` namespace |
| `frontend/src/i18n/client-namespaces.ts` | Includes `RefundPolicy` in marketing namespace list |
| `frontend/src/widgets/footer.tsx` | Adds `/refund-policy` legal link |
| `frontend/src/shared/lib/__tests__/stage1-refund-policy-copy.test.ts` | Copy and guardrail tests |

## Next ID

Next ID to execute: `S1-FE-010` - Frontend bundle/env scan. Legal/text work is closed by `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`.
