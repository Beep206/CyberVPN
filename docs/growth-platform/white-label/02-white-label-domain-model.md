# White-Label Domain Model

## Objective

Define the core entities required for self-service branded distribution without fragmenting the shared CyberVPN core.

## Entity Overview

| Entity | Purpose |
|---|---|
| `PartnerWorkspace` | Top-level tenant and lifecycle owner |
| `PartnerProfile` | Business identity and operating metadata |
| `PartnerBot` | Branded Telegram runtime object |
| `PartnerBotCredential` | Token and credential lifecycle object |
| `PartnerBotProvisioningJob` | Provisioning orchestration state |
| `PartnerBrandTheme` | Brand assets and display policy |
| `PartnerCommercialPolicy` | Pricing, revenue, settlement, trial rules |
| `PartnerStorefront` | Branded external acquisition shell |
| `PartnerSettlementAccount` | Payout destination and state |
| `PartnerSettlementLedgerEntry` | Append-only settlement history |
| `PartnerRiskProfile` | Risk score, KYB, abuse state |
| `PartnerCustomer` | Partner-attributed customer projection |
| `PartnerAttributedSale` | Commercial attribution record |

## `PartnerWorkspace`

Key fields:

- `id`
- `applicationId`
- `status`
- `workspaceSlug`
- `ownerUserId`
- `riskProfileId`
- `brandThemeId`
- `commercialPolicyId`
- `storefrontId`

Lifecycle:

- `draft`
- `pending_review`
- `approved`
- `active`
- `restricted`
- `suspended`
- `terminated`

## `PartnerProfile`

Key fields:

- business name
- legal entity
- contact data
- primary geographies
- audience type
- support capability notes

Mutable by:

- partner for draft and pending state
- platform for reviewed and verified state

## `PartnerBot`

Key fields:

- `id`
- `workspaceId`
- `status`
- `releaseChannel`
- `telegram.botId`
- `telegram.username`
- `telegram.managedByBotId`
- `binding.storefrontId`
- `binding.miniAppBindingId`
- `binding.commercialPolicyId`

Status values:

- `draft`
- `pending_review`
- `approved`
- `provisioning`
- `active`
- `degraded`
- `suspended`
- `revoked`
- `failed`

## `PartnerBotCredential`

Key fields:

- `id`
- `partnerBotId`
- `credentialType`
- `tokenRef`
- `status`
- `lastValidatedAt`
- `rotatedAt`

Status values:

- `missing`
- `active`
- `rotating`
- `revoked`
- `invalid`

## `PartnerBotProvisioningJob`

Key fields:

- `id`
- `partnerBotId`
- `requestedBy`
- `state`
- `attemptCount`
- `lastErrorCode`
- `lastErrorMessage`

States are defined fully in the provisioning spec.

## `PartnerBrandTheme`

Key fields:

- display name
- logo asset reference
- primary and secondary color tokens
- support links
- localized welcome copy
- legal display copy
- moderation status

## `PartnerCommercialPolicy`

Key fields:

- allowed plan IDs
- markup mode and limits
- discount rules
- trial policy reference
- payment policy by surface
- revenue share model
- payout currency and thresholds

## `PartnerStorefront`

Key fields:

- `id`
- `workspaceId`
- `host`
- `brandThemeId`
- `commercialPolicyId`
- `status`

## `PartnerSettlementAccount`

Key fields:

- payout method type
- payout address or account ref
- verification status
- hold status
- payout eligibility

## `PartnerSettlementLedgerEntry`

Key fields:

- `id`
- `workspaceId`
- `partnerId`
- `paymentId`
- `saleId`
- `entryType`
- `amount`
- `currency`
- `effectiveAt`
- `reasonCode`
- `createdAt`

Entry types:

- `sale_credit`
- `refund_reversal`
- `payout_debit`
- `hold_applied`
- `hold_released`
- `adjustment`

Rule:

- entries are append-only;
- current payout-ready balance is derived, not overwritten.

## `PartnerRiskProfile`

Key fields:

- KYB level
- risk score
- moderation flags
- blocked categories
- payout hold state
- manual review requirements

## `PartnerCustomer`

Projection entity for partner dashboards:

- user ID
- first attribution source
- first purchase date
- current subscription status
- active revenue contribution

## `PartnerAttributedSale`

Key fields:

- sale ID
- user ID
- partner ID
- bot ID
- storefront ID
- payment ID
- order ID
- gross amount
- platform amount
- partner amount
- settlement status

## Audit Requirements

Audit logs are required for:

- provisioning requests
- token rotations
- brand changes
- commercial policy changes
- payout requests and approvals
- ledger hold and release actions
- suspension and restoration actions
