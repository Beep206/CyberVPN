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

Create a safety snapshot branch before any split work:

- `ai/cyba-163/recovery/snapshot-20260530`

Then split from current GitLab `origin/main` into a cumulative MR chain:

1. `ai/cyba-163/recovery/backend-core`
2. `ai/cyba-163/recovery/admin-partner-commerce`
3. `ai/cyba-163/recovery/customer-frontend-locale`
4. `ai/cyba-163/recovery/client-apps`
5. `ai/cyba-163/recovery/ops-evidence`

Each downstream branch is intended to target the previous branch. The first branch targets `main`.

## W7 Status

W7 gaps are explicitly blocked on CYBA-201:

- Idempotency for direct add-on purchase and subscription upgrade commit paths.
- Currency-stable add-on pricing.
- Promo policy parity through the authoritative resolver.
- Trial policy country/channel/segment context.
- Explicit add-on compatibility and availability matrix.

This recovery package preserves the current workspace and prepares the MR chain, but it does not claim W7 closure without CYBA-201 evidence.

## GitLab Publication Risk

This heartbeat has only read-only GitLab credentials in the Orion runtime. If push or MR creation fails, the precise unblock action is: provide Orion a write-capable GitLab token for `root/CyberVPN` or have SecurityEngineer/local operator publish the prepared local branches and open the MR chain.
