# CyberVPN Customer Frontend Rules

Apply the root completion contract plus these customer-web rules.

- Treat `package.json`, TypeScript config and current official documentation as
  the version source of truth; do not rely on stale version prose.
- Use Next.js App Router conventions. In this repository use `src/proxy.ts`,
  not `middleware.ts`, for routing/proxy configuration.
- Prefer Server Components for server data and Client Components only for
  browser APIs, state and interaction.
- Keep server state in TanStack Query and local UI state in the established
  local store/component patterns. Do not duplicate API caches in Zustand.
- Use generated API types/clients. Never manually edit generated artifacts.
- Every mutation must expose pending, success, validation, authorization,
  network and retry states and must reconcile cache/state after success.
- Never hard-code user-visible strings. Register the namespace and update all
  required locale bundles, including RTL behavior where applicable.
- Preserve keyboard navigation, focus management, labels, semantic markup,
  reduced motion and responsive behavior.
- Authentication and authorization must be enforced server-side; proxy code is
  not the trust boundary.
- Test real interaction outcomes with Testing Library/MSW rather than only
  snapshots or component rendering.
- Before VERIFIED run i18n generation, ESLint, TypeScript, Vitest and a
  production Next.js build, plus an HTTP/browser smoke for changed critical
  flows.
