# CyberVPN Partner Surface Rules

Apply root and web rules plus these partner requirements.

- Enforce partner account, workspace, code ownership, lane, storefront and role
  boundaries on every backend and BFF operation.
- Attribution, codes, earnings, settlements and withdrawals require explicit
  idempotency, replay protection, concurrent uniqueness and auditable state
  transitions.
- Public referral/attribution tokens must be opaque, bounded, revocable where
  specified and absent from logs/analytics after exchange.
- Never expose another partner's codes, clicks, customers, earnings, payout
  details or internal fraud reasons.
- UI pages must use real backend contracts and implement loading, empty,
  permission, degraded, error, retry, pagination and success behavior.
- Keep OpenAPI and partner generated types synchronized.
- Add component interaction tests plus backend integration/conformance tests
  that verify persisted business state, not only response codes.
- Before VERIFIED run partner i18n generation, lint, TypeScript, full Vitest,
  build and all affected partner/admin/observability conformance packs.
