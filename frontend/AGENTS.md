# CyberVPN Customer Frontend Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file explicitly before changing `frontend/`.

## Current architecture

Use `frontend/package.json`, TypeScript configuration, Next.js configuration,
generated API types, and current source code as the version/behavior source of
truth.

- Use the Next.js App Router conventions already present in this application.
- Use `src/proxy.ts`, not `middleware.ts`, for routing/proxy configuration.
- Prefer Server Components for server-side composition and data access.
- Add `"use client"` only when browser APIs, hooks, local interaction, or
  client-side libraries require it.
- Treat TanStack Query as server-state ownership. Do not duplicate API data in
  Zustand or component stores.
- Use the established API/BFF abstractions and generated contracts. Do not add
  a second ad-hoc fetch/axios layer for one feature.
- Preserve Feature-Sliced/shared-component boundaries and reuse the design
  system before creating page-local duplicates.

## Data fetching, caching, and mutations

- Define cache ownership, query keys, invalidation, stale behavior, and
  refetch/retry policy explicitly.
- Do not cache personalized or authorization-sensitive data in a shared scope.
- Avoid request waterfalls: start independent work together and use the
  existing server/query prefetch patterns.
- Mutations must expose pending, success, validation, authorization, network,
  conflict, and retry behavior where relevant.
- Disable or deduplicate repeated submissions and use backend idempotency for
  durable operations.
- After a successful mutation, reconcile the authoritative cache/state; do not
  leave optimistic or stale UI behind.
- Cancel or ignore stale in-flight responses when route, filters, identity, or
  component lifetime changes.
- Preserve server-side authorization. `proxy.ts`, hidden controls, route guards,
  and client state are navigation/UX layers, not trust boundaries.

For BFF/route-handler changes:

- forward only allowlisted headers and cookies;
- validate destination/path construction;
- preserve CSRF and Origin/Referer behavior;
- do not leak upstream internals;
- keep timeout, cancellation, error, and status mapping explicit;
- test cookie/header rewriting and unauthorized cases.

## React and TypeScript quality

- Keep strict typing. Do not add `any`, `@ts-ignore`, unchecked double casts, or
  broad ESLint disables. Narrow `unknown` with schemas/type guards.
- Keep render functions pure. Do not perform side effects, mutate inputs, create
  unstable global state, or read changing time directly during render.
- Follow React hook rules. Clean up subscriptions, timers, observers, event
  listeners, animation loops, and requests.
- React Compiler is enabled; do not add manual `useMemo`, `useCallback`, or
  `memo` by habit. Use them only for correctness with external APIs or a
  measured need.
- Hoist static configuration and expensive immutable data out of render.
- Use stable domain IDs for keys; never use array indexes for reorderable data.
- Avoid hydration mismatches. Isolate browser-only values and time-dependent
  content behind client initialization.
- Keep error boundaries and Suspense/loading boundaries at meaningful route or
  feature ownership points.
- Do not suppress runtime errors with empty fallbacks that resemble successful
  state.

## Forms and user interaction

- Use the established form/schema pattern and keep client validation consistent
  with server constraints without treating it as authorization.
- Preserve entered data after recoverable failures.
- Associate field errors with controls and provide a summary/focus transition
  for submission failures when appropriate.
- Confirm irreversible or security-sensitive actions when required by the
  product contract.
- Support keyboard-only operation, visible focus, correct tab order, Escape and
  focus restoration for dialogs, and semantic buttons/links/forms.
- Never attach click behavior to non-interactive elements without full semantic
  keyboard support.

## Localization and presentation

- Do not hard-code user-visible strings, ARIA labels, error text, metadata, or
  toast messages.
- Register new namespaces in the existing i18n loader and update every required
  locale source. Regenerate message bundles; do not edit generated bundles
  manually.
- Preserve interpolation/plural rules and do not build translated sentences by
  string concatenation.
- Verify RTL layout for logical spacing/alignment and directional icons when
  affected.
- Reuse design tokens and shared components. Avoid hard-coded colors and
  one-off styling that bypasses the theme.
- Verify small mobile widths, zoom, long translations, empty content, reduced
  motion, and high-contrast/focus behavior for changed UI.
- Every data table needs a semantic caption, stable row identity, accessible
  sorting/filtering, and usable responsive behavior.

## Security and privacy

- Never expose access/refresh tokens, cookies, raw Telegram initData, payment
  secrets, VPN/subscription URLs, provider data, private keys, or PII to client
  logs, analytics, URLs, localStorage, or error messages.
- Treat URL/search parameters, postMessage payloads, HTML, markdown, file data,
  and third-party responses as untrusted.
- Avoid unsafe HTML. When rich content is required, use the established
  sanitizer and test malicious input.
- Prevent open redirects and unsafe external links; validate schemes and
  destinations.
- Analytics must use approved identifiers and must not capture sensitive field
  values.

## Testing

Use Testing Library, user-event, MSW, and existing test utilities to prove real
interaction outcomes.

Test relevant:

- loading, empty, success, validation, authorization, network, timeout, conflict,
  retry, and stale-response states;
- keyboard and focus behavior;
- query invalidation/cache reconciliation;
- duplicate submission prevention;
- route/BFF cookie, header, and error mapping;
- localization and RTL-sensitive behavior;
- regression behavior for the reported defect.

Prefer accessible queries. Avoid implementation-detail selectors, excessive
snapshots, and assertions that only prove a mock was called or text rendered.
Do not mock TanStack Query, routing, or the feature under test so deeply that
the production path disappears.

## Required validation

From the repository root:

```bash
npm run prepare:i18n -w frontend
npm run lint -w frontend
npm exec -w frontend -- tsc --noEmit
npm run test:run -w frontend
NEXT_TELEMETRY_DISABLED=1 npm run build -w frontend
```

When API contracts change, regenerate API types and require a second generation
with no diff. For critical auth, checkout, subscription, Mini App, VPN
configuration, or account flows, add the relevant HTTP/browser smoke or
cross-stack conformance test. Validation must be rerun after the final relevant
code change.
