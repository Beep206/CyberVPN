# Release Closure

This directory is the maintained `Phase N` release-closure surface for Northstar.
It is intentionally narrow: these docs freeze the release checklist, artifact story, supported environment matrix, and accepted limitations behind the final production-ready decision.

## Release Set

- [PRODUCTION_READY_CHECKLIST.md](PRODUCTION_READY_CHECKLIST.md) for the exact closure checklist and evidence refs.
- [ARTIFACT_ATTRIBUTION.md](ARTIFACT_ATTRIBUTION.md) for the attributable build and machine-readable evidence story.
- [SUPPORTED_ENVIRONMENT_MATRIX.md](SUPPORTED_ENVIRONMENT_MATRIX.md) for the explicitly supported validation, staging, and operator-managed production shapes.
- [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for accepted non-blocking limitations and intentional out-of-scope items.

## Machine-Readable Inputs

- `docs/release/production-ready-checklist.json`
- `docs/release/supported-environment-matrix.json`
- `docs/release/known-limitations.json`

## Final Command

- Phase N production-ready signoff: `bash scripts/phase-n-production-ready.sh`

If the checklist, support matrix, limitations ledger, accepted phase summaries, workflow files, or git attribution facts drift or go missing, `Phase N` signoff fails closed instead of guessing that the repository is release-ready.
