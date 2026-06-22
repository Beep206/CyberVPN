# CyberVPN Admin Surface Engineering Rules

Apply the root contract. This file is self-contained for admin work; do not
assume sibling `frontend/AGENTS.md` was loaded.

Use `admin/package.json`, the local Next.js/TypeScript configuration, generated
API types, and existing code as the source of truth.

## Architecture and data flow

- Follow the existing Next.js App Router, Server Component, Client Component,
  BFF/route-handler, TanStack Query, and shared UI patterns.
- Use Server Components for server composition and Client Components only for
  browser interaction/state.
- Keep server data in TanStack Query or the established server-fetch path. Do
  not duplicate authoritative API state in local stores.
- Use generated API contracts and the established API/BFF abstraction. Never
  manually edit generated files or create a one-off transport layer.
- Keep business policy, authorization, state transitions, and audit decisions
  in the backend. Admin UI may explain and request an action; it does not own
  the invariant.

## Admin trust boundary

For every read and mutation, verify at the backend/BFF boundary:

- admin realm and audience;
- active, non-revoked session;
- MFA/passkey/2FA assurance when required;
- role and granular permission;
- tenant/workspace/storefront scope;
- object ownership/scope;
- allowed source and target state;
- CSRF and Origin/Referer behavior;
- audit event and reason requirements.

Hidden controls, disabled buttons, route guards, and `proxy.ts` are not
authorization. Add negative tests for customer/partner identities,
insufficient roles, foreign workspace/tenant access, stale/revoked sessions,
and object-ID substitution.

For BFF/route handlers:

- allowlist forwarded headers/cookies;
- never accept client-supplied principal/role/tenant as authoritative;
- validate path and upstream destination construction;
- preserve secure cookie attributes and session revocation;
- map upstream errors without leaking internals;
- use explicit timeout/cancellation and test unauthorized/error paths.

## Mutations, tables, and bulk operations

- Mutations must expose pending, success, validation, authorization, conflict,
  partial failure, retry, and terminal failure states where relevant.
- Prevent duplicate submissions. Durable operations must use backend
  idempotency and concurrency-safe state transitions.
- Destructive or security-sensitive actions require the confirmation/reason UX
  defined by the product contract and an immutable backend audit trail.
- Do not optimistically display success before the backend committed the state.
- Reconcile/invalidate authoritative queries after success.

For tables and bulk operations:

- use stable domain row IDs;
- keep pagination, sorting, search, and filter ownership explicit;
- do not fetch or render unbounded collections;
- preserve selection correctly across page/filter changes;
- report per-item success/failure rather than hiding partial failures;
- make retry behavior safe and deterministic;
- keep exports bounded, authorized, and free of secret fields.

## React, TypeScript, i18n, and accessibility

- Preserve strict typing; no `any`, `@ts-ignore`, broad casts, or blanket lint
  disables.
- Keep render pure and clean up timers, listeners, subscriptions, requests, and
  observers.
- React Compiler is enabled; avoid manual memoization unless an external API or
  measured performance issue requires it.
- Do not hard-code user-visible strings, ARIA labels, metadata, errors, or
  toast text. Register namespaces, update all required locale sources, and
  regenerate bundles.
- Verify long translations and RTL logical layout when affected.
- Use semantic controls, accessible names, visible focus, keyboard navigation,
  focus trapping/restoration, and error association.
- Tables require semantic captions and accessible sort/filter status.
- Verify responsive behavior, zoom, reduced motion, loading, empty, permission,
  degraded, error, retry, and success states.

## Security and privacy

- Never expose cookies, JWTs, refresh tokens, OTP/TOTP values, recovery codes,
  raw passkey data, provider secrets, payment data, VPN/subscription URLs,
  private keys, or customer PII in logs, analytics, URLs, localStorage, or
  errors.
- Treat search parameters, IDs, uploaded files, HTML/markdown, postMessage, and
  provider responses as untrusted.
- Validate external links and redirects. Avoid unsafe HTML and remote code.
- Admin exports, diagnostics, impersonation, support, privacy, and security
  operations require explicit field allowlists and audit coverage.

## Testing

Use Testing Library/user-event/MSW and backend tests to prove:

- actual interaction and resulting server/cache state;
- RBAC, tenant/workspace isolation, stale/revoked session behavior;
- MFA/passkey/2FA requirements;
- CSRF/origin and cookie forwarding;
- duplicate submission, conflict, and partial failure behavior;
- table pagination/filter/selection and bulk-operation results;
- confirmation, reason capture, focus, keyboard, and error UX;
- generated contract compatibility.

Do not stop at render/snapshot tests, mock-call assertions, or nominal response
codes. Test persisted backend state for sensitive mutations.

## Required validation

From the repository root:

```bash
npm run prepare:i18n -w admin
npm run lint -w admin
npm exec -w admin -- tsc --noEmit
npm run test:run -w admin
NEXT_TELEMETRY_DISABLED=1 npm run build -w admin
```

Run affected backend tests and admin/backend conformance packs. When API
contracts change, regenerate admin and every other affected client twice and
require no drift. Run an authenticated HTTP/browser smoke for changed critical
admin flows. Rerun all required gates after the final relevant change.
