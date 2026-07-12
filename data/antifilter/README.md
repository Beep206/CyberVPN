# Antifilter offline data

This directory contains only small, deterministic examples for the offline
route compiler. It does not contain a production Antifilter feed and must not
be used as a current route snapshot.

- `fixtures/communities/source.json` demonstrates the external canonical CIDR
  importer contract and covers every required Task 2 community.
- `example-policy.json` demonstrates reviewed exclusions, safety thresholds,
  resource limits, and an explicit IPv6-disabled state.
- `production-policy.example.json` is a rollout bootstrap policy with current
  management/self endpoints and broad 2026-07-11 snapshot-derived ranges. It
  is not evidence that a live feed was collected and must be tightened after
  24 hours of observed history.
- Generated candidates, active/LKG stores, and full dynamic feeds belong in an
  operator-controlled artifact store outside Git.

`example-policy.json` is fixture-only and is forbidden for staging or
production rollout.

CIDR files are ASCII, LF-delimited, one CIDR per line, with no comments or
attributes. Every file is bound into `source.json` by SHA-256.
