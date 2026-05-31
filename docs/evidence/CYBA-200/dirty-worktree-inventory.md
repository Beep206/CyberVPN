# CYBA-200 Dirty Workspace Recovery Inventory

Date: 2026-05-30
Owner: Orion CTO
Source issue: CYBA-200
Parent issue: CYBA-163
Base observed before recovery: `f63ae0e871253f1865aa8359aadff8eba1965519`
GitLab `origin/main` observed before branch split: `25466b42f967cac09b50174851544116a19d0c72`

## Wake Context

The local Paperclip workspace contained implementation work for the CYBA-163 commercial/pricing/locale program, but GitLab had no CYBA-163 commercial/pricing/locale feature branch or merge request chain.

Latest parent-thread audit also says CYBA-171 remains blocked on W7 add-ons/trials/promotions correctness gaps. Those W7 fixes are not closed by this recovery inventory; they remain explicitly owned by CYBA-201 unless a dedicated W7 repair MR is published separately.

## Dirty Workspace Inventory

Pre-recovery inventory found:

- 188 modified tracked files.
- 58 untracked files.
- 246 total file paths when expanded by file.
- Top-level scope: `admin`, `apps`, `backend`, `cybervpn_mobile`, `docs`, `frontend`, `infra`, `partner`, `scripts`, `services`.

High-level workstreams:

- Backend commercial core: public catalog, pricebooks, quote/checkout sessions, subscription provisioning retry, OpenAPI, backend tests.
- Admin and partner commerce surfaces: generated API clients, pricebook/catalog UIs, reseller/storefront surfaces, commerce messages.
- Customer frontend and locale pricing: pricing catalog copy, country/currency selectors, subscription purchase presentation and tests, generated message bundles.
- Client applications: desktop subscription IPC/catalog integration and mobile subscription catalog integration.
- Operations/evidence: task-worker payment retry jobs, observability metrics/dashboards/alerts, runbooks, screenshots and API docs.

## Local Preservation Plan

Created a safety snapshot branch before any split work:

- `ai/cyba-163/recovery/snapshot-20260530` at `77dc2fe959f8`

Then split from current GitLab `origin/main` into a cumulative MR chain:

| Intended MR | Branch | Target | Commit | Scope |
| --- | --- | --- | --- | --- |
| 1 | `ai/cyba-163/recovery/backend-core` | `main` | `651101a70ba8` | Backend commercial catalog, pricebook lifecycle, quote/checkout/session wiring, provisioning retry storage, OpenAPI and backend tests. |
| 2 | `ai/cyba-163/recovery/admin-partner-commerce` | `ai/cyba-163/recovery/backend-core` | `48fe3aceddc4` | Admin commerce consoles, generated admin API clients, partner reseller/storefront catalog surfaces and related tests. |
| 3 | `ai/cyba-163/recovery/customer-frontend-locale` | `ai/cyba-163/recovery/admin-partner-commerce` | `4c931051926d` | Customer pricing/subscription UI, public commercial catalog client, country/currency selectors and 39 generated locale bundles. |
| 4 | `ai/cyba-163/recovery/client-apps` | `ai/cyba-163/recovery/customer-frontend-locale` | `a57365315cac` | Desktop subscription IPC/catalog integration and mobile subscription commercial catalog integration. |
| 5 | `ai/cyba-163/recovery/ops-evidence` | `ai/cyba-163/recovery/client-apps` | branch head after this handoff commit | Task-worker retry automation, observability dashboards/alerts, runbooks, screenshots and this recovery handoff. |

Each downstream branch is intended to target the previous branch. The first branch targets `main`.

## MR Handoff Requirements

Each MR should include:

- Scope: use the table above.
- Touched paths: include the branch diff stat.
- Tests run by this recovery heartbeat: `npm run prepare:i18n` in `admin`, `npm run prepare:i18n` in `frontend`, `git apply --3way --index` branch split, clean `git status`, and snapshot path-set verification.
- Tests not run here: full backend/admin/frontend/partner/mobile/desktop/task-worker suites. Downstream owners must run targeted suites on the published MRs.
- Known limitations: W7 gaps remain blocked on CYBA-201; this package preserves and publishes existing local implementation work, it does not certify production billing/provisioning correctness.
- Downstream gate owners: Quill QA for user-visible verification, Luma for localization, SecurityEngineer for payment/subscription/provisioning risk review, Scribe for release evidence, Astra for CYBA-183/CYBA-163 final closure.

## W7 Status

W7 gaps are explicitly blocked on CYBA-201:

- Idempotency for direct add-on purchase and subscription upgrade commit paths.
- Currency-stable add-on pricing.
- Promo policy parity through the authoritative resolver.
- Trial policy country/channel/segment context.
- Explicit add-on compatibility and availability matrix.

This recovery package preserves the current workspace and prepares the MR chain, but it does not claim W7 closure without CYBA-201 evidence.

## GitLab Publication Risk

This heartbeat has only read-only GitLab credentials in the Orion runtime.

Evidence:

- `git ls-remote` works with `GITLAB_USERNAME` + `GITLAB_READONLY_TOKEN`.
- GitLab API calls with the same token returned `401`.
- `glab` is not installed in the runtime.
- `git push --dry-run --set-upstream origin ai/cyba-163/recovery/backend-core` returned `403` with `remote: You are not allowed to upload code.`

Precise unblock action: provide Orion a write-capable GitLab token for `root/CyberVPN`, or have SecurityEngineer/local operator publish the prepared local branches and open the MR chain using the branch/target table above.
