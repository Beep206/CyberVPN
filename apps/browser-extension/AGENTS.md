# CyberVPN Browser Extension Engineering Rules

Apply the root contract. When Codex was started from the repository root, read
this file explicitly before changing `apps/browser-extension/`.

The current package is a minimal scaffold. Its existing `npm test` command is a
placeholder that exits with failure; it is not a quality gate and must never be
reported as passing. Before implementing a real feature, establish the intended
extension manifest version, build tooling, target browsers, and test strategy
from the task or existing project plans rather than inventing an incompatible
stack.

## Security model

- Use Manifest V3 unless an authoritative project contract requires otherwise.
- Request the minimum permissions and host permissions needed for the exact
  feature. Do not add `<all_urls>`, broad tabs/history/cookies access, native
  messaging, webRequest blocking, or unlimited storage by convenience.
- Treat content scripts and page DOM as untrusted. Validate every message and
  verify sender, tab, frame, origin, and expected message schema.
- Keep privileged operations in the background/service-worker context and
  expose narrow typed messages.
- Never use `eval`, `new Function`, remote executable code, remotely hosted
  scripts, unsafe inline script, or relaxed CSP.
- Validate navigation and redirect destinations. Allowlist schemes and hosts.
- Sanitize any remote/page-provided HTML before rendering.
- Keep authentication material, VPN configuration, private user data, and
  provider credentials out of page context, content-script logs, URLs,
  analytics, and extension storage unless the approved design explicitly
  requires a protected minimal value.
- Remember that extension storage is not equivalent to OS secure storage.

## Lifecycle and state

- Manifest V3 service workers are ephemeral. Persist only necessary state and
  design every handler to recover after suspension/restart.
- Make message correlation, cancellation, timeout, retry, and duplicate request
  behavior explicit.
- Clean up listeners and avoid registering the same listener more than once.
- Bound storage, queues, alarms, polling, network requests, and message sizes.
- Do not trust cached auth/entitlement/VPN state without reconciling it with the
  authoritative backend.
- Handle offline, revoked session, permission removal, tab closure, browser
  restart, update, and partial failure states honestly.

## Architecture and code quality

- Introduce a typed build/test stack consistent with the rest of the monorepo
  only when required by a real feature.
- Keep manifest generation/configuration deterministic for each target browser.
- Separate background, content-script, popup/options UI, shared messages, and
  API-client responsibilities.
- Use one canonical message schema and exhaustive handlers.
- Preserve strict typing; do not use `any`, `@ts-ignore`, broad casts, empty
  catches, or blanket lint disables.
- Do not duplicate backend authorization, entitlement, or VPN policy in the
  extension.

## Testing and packaging

A real implementation requires real scripts for lint/typecheck/test/build in
`apps/browser-extension/package.json`; replacing the placeholder test is part
of the first production feature touching this surface.

Add relevant:

- schema/message validation tests;
- sender/origin/permission negative tests;
- service-worker restart and persisted-state tests;
- content-script DOM sanitization tests;
- popup/options interaction tests;
- API timeout, cancellation, unauthorized, offline, and retry tests;
- manifest permission/CSP static checks;
- built-artifact smoke in a supported Chromium/Firefox test environment.

Inspect the final packaged manifest and bundle. Verify that no source maps,
secrets, development endpoints, test fixtures, remote code, or excessive
permissions are shipped.

Use the actual scripts added to `package.json`; do not claim gates that do not
exist. At minimum, a production feature must have deterministic typecheck,
tests, build, and package/manifest validation, all rerun after the final change.
