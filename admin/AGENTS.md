# CyberVPN Admin Surface Rules

Apply root and web rules plus these admin requirements.

- Admin identity, realm, role and permission checks are mandatory at the
  backend/BFF trust boundary for every read and mutation.
- Add negative tests for customer/partner principals, insufficient roles,
  foreign tenant/workspace access and stale/revoked sessions.
- Preserve CSRF, Origin/Referer, secure cookie, session revocation, passkey/2FA
  and audit-event behavior.
- Sensitive operations require explicit confirmation UX where the product
  contract calls for it, idempotent backend handling and an immutable audit
  trail without secrets.
- Tables and bulk operations require stable row IDs, pagination/filter state,
  partial-failure reporting and retry-safe commands.
- Use generated API contracts and keep admin types synchronized with OpenAPI.
- Run admin i18n generation, lint, TypeScript, full Vitest, build and all
  relevant admin/backend conformance packs before VERIFIED.
