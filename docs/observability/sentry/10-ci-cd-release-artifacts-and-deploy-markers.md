# CI/CD Release Artifacts And Deploy Markers

Status: draft
Owner: platform + runtime owners
Last updated: 2026-04-25
Scope: release creation, artifact upload and deploy lifecycle
Depends on: `05-environment-and-release-contract.md`, `06-secrets-and-config-matrix.md`
Related paths: `release-proof-registry.json`, `../../../scripts/collect-sentry-release-evidence.py`, `../../../scripts/record-sentry-release-deploy.py`, `.github/workflows/`, `11-smoke-tests-and-validation.md`

## Standard pipeline contract

1. Resolve canonical environment and release name.
2. Create or update the Sentry release.
3. Build the artifact.
4. Upload release artifacts:
   - web sourcemaps
   - Flutter Dart debug files
   - Android mappings
   - desktop and Rust native symbols
5. Deploy the runtime.
6. Run post-deploy smoke validation.
7. Record deploy marker.
8. Finalize the release only after validation succeeds.

## Repo-local proof baseline

- `release-proof-registry.json` is the machine-readable contract for which surfaces must emit release-evidence manifests and which surfaces can record deploy markers directly from repo-owned workflows.
- `scripts/collect-sentry-release-evidence.py` turns real build outputs into JSON manifests with file hashes and native/JS metadata where available.
- `scripts/record-sentry-release-deploy.py` records the release/deploy event through the Sentry Releases API when the repository actually owns the deploy step.
- `scripts/validate-sentry-release-proof.py` keeps those contracts aligned with the workflows in CI.

## Current repository gaps to close

- `deploy-staging.yml` now passes both client and server-side DSN plus release contract for `frontend` and writes release metadata into the GitHub job summary; the same artifact contract still needs to be repeated for other web rollout paths.
- `mobile-release.yml` now emits release-evidence manifests for Android build outputs, iOS build outputs and TestFlight IPA artifacts. Deploy markers remain external because the live App Store / Play rollout is not owned by this repository.
- Android TV now resolves a canonical packaged-app release, emits a release-evidence manifest, and records a deploy marker from the tag release workflow after release assets are published.
- Desktop now emits per-platform release-evidence manifests and records a single deploy marker once the matrix release workflow has completed.
- `helix-adapter` and `helix-node` now build release binaries in CI and publish release-proof artifacts, but their deploy markers remain external until a real deploy workflow exists in this repo or an infra repo.
- Remaining proof work is live symbolication validation against a configured self-hosted Sentry project.

## Verification requirements

- CI must fail if artifact upload for a required surface fails.
- CI must expose release name and environment in job summaries.
- Production promotion must not mark deploy success until smoke validation passes.
- Surfaces marked `external_deployer` in `release-proof-registry.json` must not fake a deploy marker from a non-live build-only workflow.
