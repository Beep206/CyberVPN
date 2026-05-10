# CyberVPN Release Comparison Report

**Generated:** `20260510T140530Z`  
**Base:** `not-provided`  
**Head:** `HEAD`  

## Summary

Base input was not available as a git ref or evidence directory. This report is a checklist-only baseline.

## Mandatory Evidence Presence

| Artifact family | Base count | Head count | Notes |
|---|---:|---:|---|
| release manifests | n/a | n/a | provide evidence directories for exact counts |
| image digests | n/a | n/a | provide evidence directories for exact counts |
| SBOM | n/a | n/a | release candidate must include SBOM |
| Trivy reports | n/a | n/a | release candidate must include Trivy output |
| Grype reports | n/a | n/a | release candidate must include Grype output |
| npm audit reports | n/a | n/a | required when Node dependencies are present |
| pip audit reports | n/a | n/a | required when Python lock files are present |
| secret scan reports | n/a | n/a | required for every release candidate |

## Operator Checklist

- [ ] Security gates passed or reviewed with written exception.
- [ ] SBOM generated for the release candidate.
- [ ] Image digests recorded for deployable images.
- [ ] Sentry release/deploy marker created where applicable.
- [ ] Latest restore drill evidence is not older than 30 days.
- [ ] Dashboard and alerting validators passed.
- [ ] Rollback path and previous image digests are known.
