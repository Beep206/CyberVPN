# Stage 1 Payment Contracts

This directory stores local, redacted payment-provider contracts for CyberVPN Stage 1.

These files are **not** production credentials and do not prove provider enablement. They define the provider selection, gating rules and evidence required before a paid provider can be enabled for Controlled Public Beta.

| File | Purpose |
|---|---|
| `stage1-primary-payment-provider.json` | `S1-PAY-001` provider readiness matrix and first live path candidate |
| `stage1-cryptobot-sandbox-contract.json` | `S1-PAY-002` CryptoBot mainnet/testnet runtime contract and external evidence gate |
| `stage1-cryptobot-production-credentials-contract.json` | `S1-PAY-003` CryptoBot production credential inventory without secret values and runtime placeholder guards |

Current S1 first live paid-path candidate: `cryptobot`.

Paid beta remains blocked until real `@CryptoTestnetBot` samples, production secret-store evidence, callback registration and payment-to-provisioning evidence are attached without secret values.
