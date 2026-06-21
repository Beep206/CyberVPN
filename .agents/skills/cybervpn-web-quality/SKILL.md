---
name: cybervpn-web-quality
description: Implement and validate high-quality CyberVPN Next.js/React changes in frontend, admin, or partner, including i18n, accessibility, interaction tests, generated APIs, and production builds.
---

# Web Quality

1. Determine affected workspace(s) and nearest AGENTS.md.
2. Use current local manifests/types and official docs only when API behavior is version-sensitive or unclear.
3. Use generated API contracts and established BFF/query patterns.
4. Implement pending, success, empty, error, permission, retry and degraded states.
5. Preserve Server/Client Component boundaries, cache invalidation and hydration correctness.
6. Update all required locale bundles/namespaces and test RTL-relevant layout.
7. Preserve semantic markup, keyboard/focus behavior, labels, reduced motion and responsive/mobile layout.
8. Add Testing Library/user-event/MSW tests for outcomes and failure recovery; avoid snapshot-only proof.
9. Run for each workspace: i18n generation, ESLint, `tsc --noEmit`, full Vitest and production build.
10. Run critical route/HTTP/browser smoke when auth, checkout, partner/admin, proxy, deep-link or runtime integration changes.
