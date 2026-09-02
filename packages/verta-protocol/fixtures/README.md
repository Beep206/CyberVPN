# Verta Fixture Tree

This directory holds authoritative implementation fixtures for the Verta v0.1 baseline.
Keep fixture contents aligned with `docs/spec/` and `docs/testing/CONFORMANCE_AND_FUZZ_PLAN.md`.

Rules:

- Put valid and invalid cases in separate directories.
- Use stable fixture IDs in filenames or sidecar metadata.
- Do not add speculative protocol behavior here.
- Keep secrets, real credentials, and production tokens out of fixtures.

The `remnawave/account` fixtures pin the adapter's automated contract coverage to
Remnawave backend contract `3.4.1`. They are deterministic contract fixtures, not
evidence of a live upstream deployment. The `3_4_1` schema-drift fixtures retain
removed UUID-only resolution and a string user ID as negative regression cases.
