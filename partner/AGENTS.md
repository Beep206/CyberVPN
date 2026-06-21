# CyberVPN Partner Surface Engineering Rules

Apply the root contract. This file is self-contained for partner work; do not
assume sibling `frontend/AGENTS.md` was loaded.

Use `partner/package.json`, local Next.js/TypeScript configuration, generated
API types, and existing code as the source of truth.

## Architecture and data flow

- Follow the existing App Router, Server/Client Component, BFF/route-handler,
  TanStack Query, and shared UI patterns.
- Use Server Components for server composition and Client Components only for
  interaction/browser state.
- Keep authoritative API state in TanStack Query or the established
  server-fetch path, not duplicated in Zustand/local stores.
- Use generated API contracts and the established transport layer. Never edit
  generated clients manually.
- Partner UI does not own attribution, earning, settlement, withdrawal,
  storefront, lane, or fraud policy. Those invariants belong to backend
  domain/application code.

## Partner trust and ownership boundaries

Every backend/BFF read and mutation must enforce:

- partner auth realm and active session;
- partner account/workspace membership;
- role and permission;
- code/campaign/storefront/lane ownership;
- allowed geography/channel/scope;
- resource state and transition;
- customer-data visibility;
- idempotency, replay, and audit requirements.

Never trust client-supplied partner account, owner, commission, attribution,
storefront, lane, settlement, or payout fields without server-side resolution.
Add negative tests for another partner, foreign workspace/storefront, revoked
membership/session, insufficient role, guessed IDs, and stale state.

Public referral/attribution identifiers must be opaque, bounded, validated,
revocable where specified, and removed from logs/analytics after exchange.
Never expose another partner's codes, clicks, customers, earnings, payout
information, fraud signals, internal rejection reasons, or support-only notes.

For BFF/route handlers:

- allowlist forwarded cookies/headers;
- validate path and upstream destination construction;
- preserve CSRF, origin, secure-cookie, and session behavior;
- use explicit timeouts/cancellation;
- map errors without leaking backend/provider internals;
- test unauthorized and cross-account cases.

## Attribution, finance, and durable mutations

Attribution, code lifecycle, earnings, settlement, and withdrawal workflows
must have:

- explicit state machines and allowed transitions;
- database-enforced uniqueness;
- idempotency keys and replay protection;
- deterministic concurrent winner/loser behavior;
- exact money representation;
- transaction/outbox or documented compensation boundaries;
- immutable audit events without sensitive data;
- safe retry behavior for provider failures.

Do not display or emit success before the intended state is committed.
Do not calculate authoritative commission, eligibility, or payout totals only
in the client. Reconcile/invalidate queries after success.

## UI behavior

Every changed page must implement the relevant:

- loading and skeleton behavior;
- true empty state;
- permission/feature-disabled state;
- degraded/external-provider state;
- validation and conflict state;
- recoverable error and retry;
- pagination/filter/search/sort;
- duplicate-submission prevention;
- success confirmation and refreshed authoritative data.

Tables use stable domain IDs and bounded server pagination. Bulk operations
report per-item results and preserve safe retry semantics.

## React, TypeScript, i18n, and accessibility

- Preserve strict typing; no `any`, `@ts-ignore`, unchecked casts, or blanket
  lint disables.
- Keep render pure and clean up timers, listeners, subscriptions, requests, and
  observers.
- React Compiler is enabled; avoid manual memoization unless required by an
  external API or measured performance issue.
- Do not hard-code user-visible strings, ARIA labels, metadata, errors, or
  toast messages. Register namespaces, update all required locale sources, and
  regenerate bundles.
- Verify RTL logical layout and long translations when affected.
- Use semantic controls, visible focus, keyboard navigation, correct dialog
  focus trapping/restoration, associated errors, and accessible table
  captions/sort status.
- Verify responsive behavior, zoom, reduced motion, and touch target sizing.

## Security and privacy

- Keep credentials, personal information, payment-related details, and private
  partner/customer data out of logs, analytics, URLs, browser storage, and
  public error responses.
- Treat IDs, URL parameters, uploaded assets, HTML/markdown, postMessage, and
  provider responses as untrusted.
- Validate redirect targets and external links.
- Partner exports and analytics require explicit field allowlists and must not
  reveal support-only or fraud-only fields.

## Testing

Use component interaction tests plus backend integration/conformance tests that
assert persisted business state.

Test relevant:

- partner/workspace/role isolation;
- code ownership and lifecycle;
- capture, transfer, claim, expiration, revocation, and replay;
- idempotent and concurrent attribution/financial mutations;
- exact earning/settlement/withdrawal results;
- provider failure and retry;
- query invalidation and refreshed UI;
- loading, empty, permission, degraded, error, retry, pagination, and success;
- keyboard, focus, localization, and RTL-sensitive behavior.

Do not rely only on render/snapshot tests, mock calls, or response status.

## Required validation

From the repository root:

```bash
npm run prepare:i18n -w partner
npm run lint -w partner
npm exec -w partner -- tsc --noEmit
npm run test:run -w partner
NEXT_TELEMETRY_DISABLED=1 npm run build -w partner
```

Run affected backend tests and partner/admin/observability conformance packs.
When API contracts change, regenerate all affected clients twice and require no
drift. Run an authenticated HTTP/browser smoke for changed critical partner,
attribution, finance, or withdrawal flows. Rerun final gates after the last
relevant change.
