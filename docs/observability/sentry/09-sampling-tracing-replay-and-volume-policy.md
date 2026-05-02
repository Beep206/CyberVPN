# Sampling, Tracing, Replay And Volume Policy

Status: draft
Owner: platform
Last updated: 2026-04-24
Scope: initial production sample rates and noise control
Depends on: `07-privacy-pii-scrubbing-and-replay-policy.md`, `08-tags-context-correlation-and-fingerprinting-contract.md`
Related paths: `surfaces/`, `12-alerting-ownership-routing-and-severity-policy.md`

## Initial policy

| Surface type | traces | replay session | replay on error | profiling | Notes |
| --- | --- | --- | --- | --- | --- |
| public web | `0.2` prod, `1.0` non-prod | conservative, start low | `1.0` | off initially | tighten after volume review |
| admin and partner web | `0.2` prod, `1.0` non-prod | conservative | `1.0` | off initially | admin payload masking required |
| backend | `0.1` prod, `1.0` non-prod | n/a | n/a | conservative or off initially | focus on critical spans |
| worker | low for noisy tasks, high for critical tasks | n/a | n/a | off initially | apply task-group policy |
| bot | `0.1` prod, `1.0` non-prod | n/a | n/a | off initially | focus on payment and config flows |
| mobile | keep current tracing baseline initially | n/a | n/a | off initially | revisit after symbol upload is stable |
| desktop and TV | phase in after baseline crash coverage | n/a | n/a | off initially | enable later by evidence |

## Noise controls

- Filter browser extension noise, cancelled navigation and benign network aborts on public web.
- Keep auth, payment, provisioning and release-health signals unsampled or close to unsampled.
- Worker housekeeping jobs should not consume the same budget as payments or reconciliation.

## Guardrails

- Review event, trace and replay volume after each wave before expanding the next wave.
- Any surface with uncontrolled volume must lower sampling before rollout continues.
