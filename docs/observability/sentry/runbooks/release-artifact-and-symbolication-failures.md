# Release Artifact And Symbolication Failures

Status: draft
Owner: platform + runtime owners
Last updated: 2026-04-25
Scope: sourcemaps, debug files, native symbols and release linkage
Depends on: `../10-ci-cd-release-artifacts-and-deploy-markers.md`, `../11-smoke-tests-and-validation.md`
Related paths: `../release-proof-registry.json`, `../../../scripts/collect-sentry-release-evidence.py`, `../../../scripts/record-sentry-release-deploy.py`, `.github/workflows/`

## Symptoms

- event arrives without source-mapped stack trace
- native crash is not symbolicated
- release exists but deploy marker is missing
- artifact upload step passed locally but not in CI

## Response flow

1. Confirm the release name attached to the event.
2. Confirm the event environment and project.
3. Confirm artifact upload step logs and auth token scope.
4. Confirm artifact build matches the deployed binary or bundle.
5. Re-run artifact upload if the artifact is valid and retention policy allows it.
6. If release linkage is broken, stop promotion until corrected.
7. Compare the failing release against the stored release-evidence manifest for that workflow run before re-uploading anything.

## Prevention

- fail CI on required artifact upload errors
- keep release naming deterministic
- prove symbolication in smoke validation, not only after a real incident
- keep a release-evidence manifest for every native/mobile/tagged release workflow
- only record deploy markers from workflows that truly represent a live deploy event
