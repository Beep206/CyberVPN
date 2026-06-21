# Partner Attribution Initial Audit

Task: `PARTNER-ATTRIBUTION-HARDENING`

Source: `docs/plans/CyberVPN_partner_attribution_Codex_TZ.md`

Status: Partial implementation evidence. This document records the initial audit findings used for the implemented hardening slice; it is not release evidence for the full referral-system specification.

## Confirmed Existing Risks

- Public capture resolved customer realm through the general request resolver, which allowed client-controlled forwarding or realm metadata to affect the capture path.
- The customer `/p/[publicToken]` BFF forwarded request-derived host information and accepted arbitrary `to=` paths.
- Capture used a fingerprint-style browser key derived from request metadata rather than an opaque first-party browser identifier.
- Repeated capture reloads could create duplicate attribution sessions and touchpoints.
- Transfer consume did not clear the active transfer-token hash after first consumption, leaving the replay state less explicit.
- Order attribution precedence selected passive click data before persistent reseller bindings in at least one production-path regression test.
- Production CORS did not include the partner portal origin for cookie-authenticated unsafe requests.
- Database invariants did not enforce active commercial-binding owner uniqueness or touchpoint idempotency/source-event uniqueness at the database layer.

## Implemented Slice

- Added public customer capture realm resolution that ignores `X-Auth-Realm`, restricts trusted production hosts, and uses `X-Forwarded-Host` only from trusted proxies.
- Updated the frontend `/p/[publicToken]` route to use an HttpOnly opaque browser cookie, emit a deterministic capture idempotency key, strip spoofable forwarding headers, and reject unknown production hosts.
- Preserved backend `429 Retry-After` responses in the frontend `/p/[publicToken]` route instead of converting rate-limit failures into successful registration redirects.
- Added backend capture idempotency by idempotency key and browser key, with reload reuse of the original transfer token.
- Added explicit consumed-transfer-token storage and active token cleanup while preserving replay detection.
- Added a corrective Alembic migration for capture idempotency, consumed transfer-token replay state, touchpoint idempotency uniqueness, source-event uniqueness, and active commercial-binding owner uniqueness.
- Corrected order attribution precedence so persistent reseller binding wins over passive click when applicable.
- Added partner production origin to the S1 CORS allowlist.

## Remaining Gaps

- Redis rate limiting itself, persistent `partner_code_links`, compatibility sunset flags, centralized eligibility policy, quote/order safety net, immutable commission contracts, durable payment-to-earning worker, finance summary, portal runtime, OpenAPI regeneration, and cross-surface E2E coverage remain incomplete.
- The new migration has been syntax-checked and head-listed, but clean PostgreSQL upgrade, downgrade, and re-upgrade validation has not been executed.
- Full repository validation remains red because of repository-wide mypy/type/test/format baselines outside this slice.
