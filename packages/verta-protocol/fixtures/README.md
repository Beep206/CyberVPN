# Verta Fixture Tree

This directory holds authoritative implementation fixtures for the Verta v0.1 baseline.
Keep fixture contents aligned with `docs/spec/` and `docs/testing/CONFORMANCE_AND_FUZZ_PLAN.md`.

Rules:

- Put valid and invalid cases in separate directories.
- Use stable fixture IDs in filenames or sidecar metadata.
- Do not add speculative protocol behavior here.
- Keep secrets, real credentials, and production tokens out of fixtures.
