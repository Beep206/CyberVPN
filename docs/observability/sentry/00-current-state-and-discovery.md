# Current State And Discovery

Status: draft
Owner: platform (proposed)
Last updated: 2026-04-25
Scope: `frontend`, `admin`, `partner`, `backend`, `services/*`, `cybervpn_mobile`, `apps/desktop-client`, `apps/android-tv`
Depends on: `README.md`
Related paths: `docs/plans/2026-04-23-monorepo-sentry-integration-scope.md`, `docs/plans/2026-04-23-sentry-discovery-answers.md`

## Summary

CyberVPN is a polyglot monorepo with real web, backend, worker, bot, mobile, desktop, Android TV and control-plane surfaces. Sentry now has verified baseline coverage in `frontend`, `admin`, `partner`, `backend`, `services/task-worker`, `services/telegram-bot`, `cybervpn_mobile`, `services/node-fleet-controller`, `apps/android-tv`, `apps/desktop-client`, `services/helix-adapter` and `services/helix-node`.

The repository already contains enough evidence to treat Sentry rollout as a multi-runtime program, not as a single frontend task.

`Wave 1` closed with a verified baseline for `frontend`, `backend`, `services/task-worker` and `cybervpn_mobile`. `Wave 2 / Step 1` then closed the dedicated smoke carryover for `admin` and `partner`, and moved `services/telegram-bot` from no integration to a documented runtime contract with SDK init and CI validation. `Wave 2 / Step 2` added the first control-plane runtime baseline via `services/node-fleet-controller`, including SDK init, protected runtime probe, workflow and reconcile spans, CI validation and live HTTP smoke proof. `Wave 2 / Step 3` then completed the bot baseline by adding webhook runtime smoke, a protected Sentry contract endpoint and a smoke-safe startup mode that avoids real Telegram API calls in CI. `Wave 2 / Step 4` completed the Android TV baseline by adding the Sentry Android SDK and Gradle plugin, canonical build-time env/release/DSN wiring, release mapping generation/upload path, release assembly validation and targeted unit/runtime contract tests while also closing several pre-existing Android TV build blockers that prevented the app module from assembling at all.

`Wave 3 / Step 1` started the desktop split properly instead of treating Tauri as one opaque runtime: `apps/desktop-client` now has a dedicated renderer init on `@sentry/react`, a separate native Rust init on `sentry`, distinct DSN variables for renderer/native, a shared `desktop@<version>+<build>` release contract, Vite sourcemap generation, `.env.example` coverage and local validation for both layers. Artifact upload, native symbol handling and dedicated smoke proof remain the next step.

`Wave 3 / Step 2` closed the operational desktop carryover: `desktop-client-ci.yml` now validates both contracts, runs renderer/native tests, builds the packaged Tauri app and proves clean startup via a dedicated release-binary smoke script. `desktop-release.yml` now passes the desktop Sentry contract into the real release build, uses the Vite plugin path for renderer sourcemaps and uploads native debug-file candidates with `sentry-cli` when CI credentials are configured.

`Wave 3 / Step 3` completed the `services/helix-adapter` baseline with Rust-native `sentry` init, `sentry-tower` per-request hub binding, protected `/observability/sentry-contract`, smoke-safe startup mode, 5xx-focused error capture, tracing instrumentation around manifest and registry flows, CI contract validation and live HTTP smoke proof.

`Wave 3 / Step 4` completed the `services/helix-node` baseline with Rust-native `sentry` init, protected `/observability/sentry-contract`, smoke-safe startup via `HELIX_NODE_SMOKE_MODE`, lifecycle spans around restore/sync/heartbeat and live HTTP smoke proof against the real daemon process.

`Wave 4 / Step 1` added a machine-readable governance registry for ownership and alert-tier defaults. `Wave 4 / Step 2` then closed the repo-local privacy baseline by adding `privacy-baseline.json`, CI validation for privacy expectations and explicit minimal-PII / replay-masking hooks in the remaining web, backend and worker runtimes which previously relied on weaker or implicit defaults.

`Wave 4 / Step 3` closed the repo-local release-proof baseline by adding `release-proof-registry.json`, CI validation, reusable release-evidence and deploy-marker scripts, release-evidence manifests for `cybervpn_mobile`, `apps/desktop-client` and `apps/android-tv`, and release-build proof artifacts for `services/helix-adapter` and `services/helix-node`. This step also made the deploy-marker split explicit: `desktop-client` and `android-tv` record deploy markers from repo-owned release workflows, while `cybervpn_mobile` and `helix-*` now explicitly rely on an external deployer/store-promotion path for the live deploy event.

`Wave 4 / Step 4` closes the repo-owned Sentry implementation roadmap by adding `production-acceptance-registry.json`, validating it in CI, and separating baseline rollout completion from honest production acceptance blockers. No surface is falsely marked fully accepted without live self-hosted proof or external deployer confirmation.

## Confirmed coverage state

| Surface | Current state | Evidence |
| --- | --- | --- |
| `frontend` | baseline complete | `@sentry/nextjs`, explicit env/release inputs, CI smoke route and HTTP validation |
| `admin` | baseline complete | same as `frontend` plus custom `frontend-observability` runtime layer and dedicated protected Sentry smoke route |
| `partner` | baseline complete | same as `admin` plus product-event telemetry bridge and dedicated protected Sentry smoke route |
| `backend` | baseline complete | `sentry-sdk[fastapi]`, init in `backend/src/main.py`, observability tests and CI smoke assertions |
| `services/task-worker` | baseline complete | `sentry-sdk`, startup init, env/release config and CI startup smoke assertions |
| `services/telegram-bot` | baseline complete | `sentry-sdk` init, env/release config, privacy scrubber, protected `/observability/sentry-contract`, targeted tests and live webhook smoke proof |
| `services/node-fleet-controller` | baseline complete | `sentry-sdk[fastapi]`, protected `/api/v1/observability/sentry-contract`, workflow/reconcile spans, targeted tests and HTTP smoke proof |
| `services/helix-adapter` | baseline complete | Rust `sentry` init, per-request hub layer, protected `/observability/sentry-contract`, smoke mode and CI/live HTTP proof |
| `services/helix-node` | baseline complete | Rust `sentry` init, protected runtime probe, smoke mode, lifecycle spans and CI/live HTTP smoke proof |
| `cybervpn_mobile` | baseline complete | `sentry_flutter`, privacy hooks, user sync, CI symbol upload and `--dart-define` Sentry contract smoke |
| `apps/desktop-client` | baseline complete | renderer/native SDK init, split DSN vars, shared release contract, CI/release artifact wiring and packaged smoke validation |
| `apps/android-tv` | baseline complete | Sentry Android SDK + Gradle plugin, protected build-time contract, CI validation, release assemble and mapping upload path |

## Confirmed gaps

### Common cross-cutting gaps

- Environment and release contracts are now documented and implemented at baseline level, but live-event proof across every real production path still remains incomplete.
- The project registry now exists in-repo, but live self-hosted Sentry projects still need to be reconciled against that registry.
- Repository-level privacy policy is now frozen in `07-privacy-pii-scrubbing-and-replay-policy.md` plus `privacy-baseline.json`, but live self-hosted org/project scrub settings still need to be provisioned and verified.
- CI now validates runtime, privacy, governance and release-proof baselines and emits evidence manifests for the native/mobile surfaces. Remaining gap is live Sentry-side proof that uploaded artifacts symbolicate a real event and that repo-owned deploy markers are accepted in the target self-hosted Sentry organization.
- Production acceptance is now explicitly tracked as a separate gate layer. Remaining blockers are live Sentry project provisioning, org-level privacy/routing application, deploy-marker ownership for some runtimes, and real symbolication proof against the self-hosted Sentry org.

### Web-specific gaps

- Web config now supports explicit `NEXT_PUBLIC_APP_ENV` / `APP_ENV` and `SENTRY_RELEASE`; `frontend` CI also validates the runtime contract through a protected route.
- `frontend`, `admin` and `partner` now explicitly set `sendDefaultPii: false`, replay masking defaults and `beforeSend` scrubbing hooks for client/server/edge Sentry paths.
- `deploy-staging.yml` was aligned for `frontend`, but equivalent rollout paths still need to be standardized across every web deployment workflow.
- `frontend` lacks the richer custom runtime layer already present in `admin` and `partner`.
- No explicit web tunnel policy is implemented.

### Backend and worker gaps

- `backend`, `services/task-worker`, `services/telegram-bot` and `services/node-fleet-controller` now expose `SENTRY_DSN` and `SENTRY_RELEASE` in config; both the bot and controller additionally carry protected runtime smoke contracts via internal observability secrets.
- `backend` and `services/task-worker` now also enforce explicit minimal-PII defaults through `send_default_pii=False`, `max_request_body_size=\"never\"` and local `before_send` scrubbing hooks.
- No formal tag contract for backend and worker-specific context.
- No documented correlation rule from Sentry to Loki/Tempo.
- `services/telegram-bot` now has webhook smoke coverage, but polling mode still relies on startup/unit coverage rather than a separate live runtime probe.

### Mobile and native gaps

- `mobile-release.yml` now mirrors the canonical mobile release contract and debug-file upload behavior more closely; remaining proof work is end-to-end symbolication validation.
- Desktop now has CI/release artifact wiring and packaged smoke coverage; remaining proof work is end-to-end symbolication validation against a configured Sentry project.
- Android TV now has SDK init, release assembly validation and Gradle mapping upload plumbing; remaining work is production symbolication proof, release health and optional ANR/tracing rollout.
- `services/helix-adapter` and `services/helix-node` now build release binaries in CI and emit release-proof manifests, but their real deploy marker still depends on an external deploy system not represented inside this repository.
- `services/node-fleet-controller` is covered at baseline, but alert routing, governance and broader distributed-correlation rules remain open.

## Wave 1 carryover

- repository-approved alert routing and ownership automation
- live self-hosted org/project scrub-rule application and verification
- live Sentry-side symbolication proof and external deploy-marker adoption where this repository is not the deployer

## Known decisions and assumptions

- Planning assumption for this package: Sentry is self-hosted.
- Sentry remains application error/crash/release observability, not the replacement for Prometheus, Grafana, Loki, Tempo or PostHog.
- `packages/*`, shared SDKs and internal libraries are covered indirectly through consuming runtime surfaces.
- `apps/browser-extension` remains out of direct scope until it becomes a real runtime.

## Open items carried forward

- Ownership model for org admins, teams and routing rules.
- Alert channels and escalation policy.
- Volume budgets and retention defaults.
- Live self-hosted application of the repo privacy baseline.
- Live production acceptance of every project in `production-acceptance-registry.json`.
- Final rollout status of some surfaces in real production.
- Exact host platform for some web and native surfaces.

## Source evidence

- [../../plans/2026-04-23-monorepo-sentry-integration-scope.md](../../plans/2026-04-23-monorepo-sentry-integration-scope.md)
- [../../plans/2026-04-23-sentry-discovery-answers.md](../../plans/2026-04-23-sentry-discovery-answers.md)
