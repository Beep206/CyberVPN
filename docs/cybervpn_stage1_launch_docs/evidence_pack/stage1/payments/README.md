# Payments Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Primary payment provider selection | `../../../125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md` |
| CryptoBot sandbox/testnet runtime contract | `../../../126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md` |
| CryptoBot production credential inventory | `../../../127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md` |
| Provider status mapping | `../../../36_STAGE1_PAY_004_PROVIDER_STATUS_MAPPING_EVIDENCE.md` |
| Webhook idempotency | `../../../37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md` |
| Orphan / paid-but-no-access policy | `../../../38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md` |
| Payment -> provisioning failure | `../../../45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md` |
| Webhook signature/authenticity | `../../../46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md` |
| Refund/dispute process | `../../../81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` |
| Wallet/payment history | `../../../82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md` |
| Reconciliation job | `../../../83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md` |
| Provider placeholder replacement | `../../../84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md` |
| Telegram Stars contract readiness | `../../../108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md` |
| PayRam readiness guardrails | `../../../109_STAGE1_PAY_013_PAYRAM_READINESS_EVIDENCE.md` |
| NOWPayments readiness guardrails | `../../../110_STAGE1_PAY_014_NOWPAYMENTS_READINESS_EVIDENCE.md` |
| Digiseller readiness guardrails | `../../../111_STAGE1_PAY_015_DIGISELLER_READINESS_EVIDENCE.md` |
| YooKassa readiness guardrails | `../../../112_STAGE1_PAY_016_YOOKASSA_READINESS_EVIDENCE.md` |

## Required Before Enabling Any Paid Provider

- Real account/credential evidence without secret values.
- Sandbox or provider test-mode success/fail/cancel samples.
- Production callback URL registration proof where applicable.
- Real callback/signature/status recheck samples for the enabled provider.
- Duplicate webhook proof under durable persistence.
- Refund/dispute/reconciliation proof for the enabled provider.
- Paid webhook -> subscription -> Remnawave provisioning proof.
- For Telegram Stars specifically: real BotFather/test/prod XTR invoice, `pre_checkout_query`, `successful_payment`, stored charge ID, `/paysupport`, refundStarPayment/reconciliation and payment->provisioning proof.
- For PayRam specifically: real instance/account proof, `API-Key` storage without values, callback/status-poll samples, underpaid/overpaid/refund/reconciliation proof and payment->provisioning proof.
- For NOWPayments specifically: real account proof, `x-api-key` and IPN secret storage without values, signed IPN/status-poll samples, partial/wrong-asset/refund/reconciliation proof and payment->provisioning proof.
- For Digiseller specifically: real seller account/product proof, seller secret/API token storage without values, signed callback/status-poll samples, duplicate callback proof, refund/dispute/reconciliation proof and payment->provisioning proof.
- For YooKassa specifically: real shop/account proof, shop id/secret storage without values, webhook/status recheck samples, duplicate notification proof, refund/reconciliation proof, receipt/fiscalization decision and payment->provisioning proof.

Current status: CryptoBot / Crypto Pay is selected locally as the first S1 live paid-path candidate in `../../../125_STAGE1_PAY_001_PRIMARY_PAYMENT_PROVIDER_EVIDENCE.md`; local CryptoBot sandbox/testnet runtime support is documented in `../../../126_STAGE1_PAY_002_CRYPTOBOT_SANDBOX_EVIDENCE.md`; local production credential inventory without values is documented in `../../../127_STAGE1_PAY_003_CRYPTOBOT_PRODUCTION_CREDENTIALS_EVIDENCE.md`; Telegram Stars, PayRam, NOWPayments, Digiseller and YooKassa have provider-specific local guardrails; paid beta remains blocked until at least one real provider path is proven.
